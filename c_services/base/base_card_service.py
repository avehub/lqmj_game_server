from asyncio import sleep

from c_services.base.base_service import BaseService
from c_services.const.cs_enum_const import CmdRoom, RoomStatus, CmdClub, ClubMsgType
from c_services.cs_mahjong.const import OverType
from common.proto.py_pb2.ws_c2s import req_dismiss_model, enter_room_model
from common.proto.py_pb2.ws_leisure import S2CReqDismissRoom
from common.public.enum_const import StaCode, ServiceEnum
from lucky_game.model_rc.game_rooms import GameRoomsRC


class BaseCardService(BaseService):
    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.REQ_DISMISS.val: self.__req_dismiss_room,
            CmdRoom.CLUB_OWNER_DISMISS.val: self.__club_owner_dismiss,
        })

    async def _on_new_match(self, uid, data):
        """ 新匹配（服务器内部使用，不能给其它人调用） """
        print("匹配",data)
        await self.new_match(uid, data)

    async def new_match(self, uid, data):
        tid = data.get("room_id")
        club_id = data.get("club_id")
        room = self.get_room(tid)
        if not room:
            room = self.create_room(self.ROOM, data,tid = tid)
            self.log_info(f"创建房间{room.tid}")
            room.creator = uid
            if club_id > 0:
                await room.cs2club_by_rmq(CmdClub.ROOM_INFO_CHANGE, room.club_room_info(ClubMsgType.CREATE_ROOM))
        else:
            player = self.get_player(uid)
            if player and player.tid == tid:
                player.set_position(data.get("x", 0), data.get("y", 0))
                enter_room_model.reenter = True
                reenter = enter_room_model.SerializeToString()
                await self.enter_room(player, room, reenter)
                return
            if room.in_room_count == room.max_player_count:
                return await self.cs2ws_by_rmq(CmdRoom.ENTER_ROOM, uid, code=StaCode.FAIL, hint="房间已满")
            if not room.room_status_is_equal(RoomStatus.T_IDLE):
                return await self.cs2ws_by_rmq(CmdRoom.ENTER_ROOM, uid, code=StaCode.FAIL, hint=f"房间不处于空闲中({room.room_status})")
        player = self.get_or_create_player(uid, self.PLAYER)
        player.set_position(data.get("x", 0), data.get("y", 0))
        if player.seat_id <= 0:
            await room.player_join_room([player])
        self.log_info("玩家加入房间", player.uid, player.seat_id,"最大人数",room.max_player_count)
        await room.inner_send(player, CmdRoom.NEW_MATCH)


    def get_or_create_player(self, uid, c_player):
        player = self.get_player(uid)
        if player:
            return player
        return self.create_player(c_player, uid, False)

    @staticmethod
    async def __req_dismiss_room(player, room, data):
        if not room.agree_dismiss_seats and not room.timer_dismiss:
            room.call_dismiss(120, room.force_dismiss, OverType.FORCE)
            if room.room_status not in (RoomStatus.T_DISMISS,RoomStatus.T_CLOSED):
                room.set_not_playing_dismiss(room.room_status,True)
                await room.async_set_room_status(RoomStatus.T_DISMISS)

        req_dismiss_model.ParseFromString(data)
        agree = req_dismiss_model.agree or False
        if agree:
            room.add_agree_dismiss(player.seat_id)
        else:
            room.clear_agree_dismiss()
            await room.back_room_status()

        data = {
            "seat_id": player.seat_id,
            "agree": agree,
            "agree_seats": list(room.agree_dismiss_seats),
            "total_time":120,
            "left_seconds":room.dismiss_left_seconds(),
        }
        print("data",data)
        if room.in_room_count > 1:
            data_model = S2CReqDismissRoom.pb_model(**data)
            await room.inner_broadcast(CmdRoom.REQ_DISMISS, data_model)
        room.log_info("请求解散房间",player.uid,"结果:",agree)
        if room.agree_dismiss_count() == room.in_room_count:
            room.clear_agree_dismiss()
            return await room.force_dismiss(OverType.FORCE)
        if player.uid == room.owner and room.in_room_count == 1:
            room.clear_agree_dismiss()
            return await room.force_dismiss(OverType.FORCE)

    async def __club_owner_dismiss(self, _, data):
        print("解散",data)
        tid = data.get("room_id")
        room = self.get_room(tid)
        if not room:
            self.log_info("__club_owner_dismiss, 房间不存在")
            return
        club_id = data.get("club_id")
        if room.club_id != club_id:
            self.log_info("__club_owner_dismiss, club id对不上", room.club_id, club_id)
            return
        room.set_not_playing_dismiss(room.room_status, True)
        await room.force_dismiss(OverType.CLUB_OWNER_DISMISS)


    async def clear_in_service(self):
        await GameRoomsRC.abnormal_cs_type(self.service_type,"重启子游戏服务")
        await super().clear_in_service()

