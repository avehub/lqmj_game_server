from c_services.base.base_service import BaseService
from c_services.const.cs_enum_const import CmdRoom, RoomStatus
from c_services.cs_mahjong.const import OverType
from common.public.enum_const import StaCode


class BaseCardService(BaseService):
    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.REQ_DISMISS.val: self.__req_dismiss_room,
        })

    async def new_match(self,uid,data):
        tid = data.get("tid")
        room = self.get_room(tid)
        if not room:
            room = self.create_room(self.ROOM,data,tid = tid)
            room.creator = uid
        else:
            player = self.get_player(uid)
            if player and player.tid == tid:
                await self.enter_room(player, room)
                return
            if room.in_room_count == room.max_player_count:
                return await self.cs2ws_by_rmq(CmdRoom.ENTER_ROOM, uid, code=StaCode.FAIL, hint="房间已满")
            if not room.room_status_is_equal(RoomStatus.T_IDLE):
                return await self.cs2ws_by_rmq(CmdRoom.ENTER_ROOM, uid, code=StaCode.FAIL, hint=f"房间不处于空闲中({room.room_status})")
        player = self.get_or_create_player(uid, self.PLAYER)
        if player.seat_id <= 0:
            sta = await room.player_join_room([player])
            if sta:
                await room.inner_send(player, CmdRoom.ENTER_ROOM)

        await room.inner_send(player, CmdRoom.NEW_MATCH)


    def get_or_create_player(self,uid,c_player):
        player = self.get_player(uid)
        if player:
            return player
        return self.create_player(c_player,uid,False)

    @staticmethod
    async def __req_dismiss_room(player,room,data):
        if not room.agree_dismiss_seats and not room.timer_dismiss:
            room.call_dismiss(120, room.force_dismiss, OverType.REQ_DISMISS)

        agree = data.get("agree")
        if agree:
            room.add_agree_dismiss(player.seat_id)
        else:
            room.clear_agree_dismiss()

        data = {
            "seat_id": player.seat_id,
            "agree": agree,
            "agree_seats": list(room.agree_dismiss_seats)
        }
        await room.inner_broadcast(CmdRoom.REQ_DISMISS, data)
        if room.agree_dismiss_count() == room.max_player_count:
            return await room.force_dismiss(OverType.REQ_DISMISS)



    async def enter_room(self,player,room):
        player.offline = False  # 此处不改变状态，玩家收不到房间以下两条信息
        if player.trustee:
            await room.do_trustee(player)
        self.info_log(player.uid, "enter_room", player.tid, id(player))
        await self.notify_player_enter_room(room, player)
        # todo: 通知其它玩家该玩家上线
        await room.inner_send(player, CmdRoom.ENTER_ROOM)