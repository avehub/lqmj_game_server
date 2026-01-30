
from c_services.base.base_service import BaseService
from c_services.const.cs_enum_const import CmdRoom, RoomStatus, CmdClub, ClubMsgType
from c_services.cs_mahjong.const import OverType
from common.proto.py_pb2.ws_c2s import req_dismiss_model, enter_room_model
from common.public.conf import C_SERVICE_SECRET_KEY, R_UID_THRESHOLD
from common.public.enum_const import StaCode, ServiceEnum
from common.utils.kit_async import DelayCall
from lucky_game.model_rc.game_rooms import GameRoomsRC


class BaseCardService(BaseService):
    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.REQ_DISMISS.val: self.__req_dismiss_room,
            CmdRoom.CLUB_OWNER_DISMISS.val: self.__club_owner_dismiss,
            CmdRoom.FORCE_DISMISS_ROOM.val: self.__force_dismiss_room,
        })

        DelayCall(120, self.close_room_timeout_idle).loop_start()

    async def close_room_timeout_idle(self):
        # 这里遍历副本，不然会报错：dictionary changed size during iteration
        for room in list(self.rooms.values()):
            await room.close_room_timeout_idle()

    async def _on_new_match(self, uid, data):
        """ 新匹配（服务器内部使用，不能给其它人调用） """
        self.log_info("匹配信息", data)
        await self.conf.locker.locked(uid, self.new_match, (uid, data))

    async def new_match(self, uid, data):

        player = self.get_player(uid)
        if player:
            old_room = self.get_room(player.tid)
            if old_room:
                enter_room_model.reenter = True
                reenter = enter_room_model.SerializeToString()
                return await self.enter_room(player, old_room, reenter)

        tid = data.get("room_id")
        room = self.get_room(tid)
        if not room:
            room = self.create_room(self.ROOM, data, tid=tid)
            self.log_info(f"创建房间{room.tid}")
        else:
            if room.in_room_count == room.max_player_count:
                return await self.cs2ws_by_rmq(CmdRoom.ENTER_ROOM, uid, code=StaCode.FAIL, hint="房间已满")
            if not room.room_status_is_equal(RoomStatus.T_IDLE):
                return await self.cs2ws_by_rmq(CmdRoom.ENTER_ROOM, uid, code=StaCode.FAIL, hint=f"房间不处于空闲中({room.room_status})")
        is_robot = uid < R_UID_THRESHOLD
        player = self.get_or_create_player(uid, self.PLAYER, is_robot=is_robot)
        match_room_id = data.get("match_room_id") or 1 #这里测试内存问题给他改成1了 应该默认是0
        if player.seat_id <= 0:
            room.online_group_user = data.get("online_group_user") or []
            await room.player_join_room([player])
        self.log_info("玩家加入房间", player.uid, player.seat_id, "最大人数", room.max_player_count)
        await room.inner_send(player, CmdRoom.NEW_MATCH)

        if match_room_id > 0:
            match_round = data.get("match_round") or 0
            total_match_round = data.get("total_match_round") or 0
            player_score = data.get("player_score") or 0
            player.round_score = player_score
            room.match_competition(player, match_room_id, match_round, total_match_round)

    def get_or_create_player(self, uid, c_player, is_robot=False):
        player = self.get_player(uid)
        if player:
            return player
        return self.create_player(c_player, uid, is_robot)

    async def __req_dismiss_room(self, player, room, data):
        req_dismiss_model.ParseFromString(data)
        agree = req_dismiss_model.agree or False
        code, msg = await room.req_dismiss_room(player, agree)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.REQ_DISMISS, player.uid, code, msg)

    async def __club_owner_dismiss(self, uid, data):
        tid = data.get("room_id")
        room = self.get_room(tid)
        if not room:
            self.log_info("__club_owner_dismiss, 房间不存在")
            return
        club_id = data.get("club_id")
        req_id = data.get("req_id")
        if uid == 1:
            uid = data.get("uid") or 1
        from_club = data.get("from_club") or False
        if room.club_id != club_id:
            self.log_info("__club_owner_dismiss, club id对不上", room.club_id, club_id)
            return
        if not room.timer_dismiss:
            room.set_not_playing_dismiss(room.room_status, True)
            await room.async_set_room_status(RoomStatus.T_DISMISS)
        await room.force_dismiss(OverType.CLUB_OWNER_DISMISS)
        self.log_info("茶馆解散游戏房间", "tid",room.tid, "club_id", room.club_id, "uid", uid)
        if from_club:
            data = {"req_id": req_id, "secret": C_SERVICE_SECRET_KEY}
            await self.cs2cs_by_rmq(ServiceEnum.C_CLUB, CmdClub.JOIN_NEW_GAME_SUC, data, uid)

    async def __force_dismiss_room(self, _, data):
        tid = data.get("room_id")
        room = self.get_room(tid)
        if room:
            await room.force_dismiss(OverType.ULTIMATE_DISMISS)

    async def clear_in_service(self):
        await GameRoomsRC.abnormal_cs_type(self.service_type, "重启子游戏服务")
        await super().clear_in_service()
