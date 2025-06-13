from c_services.base.base_service import BaseService
from c_services.const.cs_enum_const import CmdRoom, RoomStatus
from c_services.cs_mahjong.const import OverType
from common.proto.py_pb2.ws_c2s import req_dismiss_model
from common.proto.py_pb2.ws_leisure import S2CReqDismissRoom
from common.public.enum_const import StaCode



class BaseCardService(BaseService):
    def __init__(self):
        super().__init__()
        self.tid_test = 0
        self.add_handlers({
            CmdRoom.REQ_DISMISS.val: self.__req_dismiss_room,
        })
        import asyncio
        data = {"tid": 0,"room_type":2,"play_type":1,"max_player":3,
                "rule_details":{"shang_xia_ji":0,"ben_ji":1,"wu_gu_ji":0,"man_tang_ji":0,
                                "chong_feng_ji":1,"zhan_ji":1,"jian_gang_san":1,"bao_ting":1,
                                "bi_men_yi_shou":1,"shang_ga":1,"gu_mai_score":2,"suo_de_jia_1":1,
                                "hu_pai_ti_shi":1,"huang_zhuang_bu_huang_ji":1,"four_card_bao_ting":0,
                                "tui_zhang_can_hu":1,"bao_ting_bi_men":1,"exchange_three":0,
                                "exchange_cards_type":1}}
        uid = 123
        count = 0
        while 1:
            asyncio.create_task(self.new_match(uid+count, data))
            count += 1
            if count == 3:
                break
            asyncio.sleep(2)


    async def new_match(self,uid,data):
        tid = data.get("tid")
        if tid ==0:
            tid = self.tid_test
        room = self.get_room(tid)
        if not room:
            room = self.create_room(self.ROOM,data)
            self.log_info(f"创建房间{tid}")
            self.tid_test = room.tid
            room.creator = uid
        else:
            player = self.get_player(uid)
            if player and player.tid == tid:
                player.set_position(data.get("x", 0), data.get("y", 0))
                await self.enter_room(player, room)
                return
            if room.in_room_count == room.max_player_count:
                return await self.cs2ws_by_rmq(CmdRoom.ENTER_ROOM, uid, code=StaCode.FAIL, hint="房间已满")
            if not room.room_status_is_equal(RoomStatus.T_IDLE):
                return await self.cs2ws_by_rmq(CmdRoom.ENTER_ROOM, uid, code=StaCode.FAIL, hint=f"房间不处于空闲中({room.room_status})")
        player = self.get_or_create_player(uid, self.PLAYER)
        player.set_position(data.get("x", 0), data.get("y", 0))
        if player.seat_id <= 0:
            sta = await room.player_join_room([player])
            if sta:
                await room.inner_send(player, CmdRoom.ENTER_ROOM)
        self.log_info(f"进入房间{player.uid}",player.seat_id)
        await room.on_player_ready(player)
        if player.uid == 125:
            await room.try_start_game()
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

        req_dismiss_model.ParFromString(data)
        agree = req_dismiss_model.agree or False
        if agree:
            room.add_agree_dismiss(player.seat_id)
        else:
            room.clear_agree_dismiss()

        data = {
            "seat_id": player.seat_id,
            "agree": agree,
            "agree_seats": list(room.agree_dismiss_seats)
        }
        data_model = S2CReqDismissRoom.pb_model(**data)
        await room.inner_broadcast(CmdRoom.REQ_DISMISS, data_model)
        room.log_info(player.uid, "请求解散房间", player.tid)
        if room.agree_dismiss_count() == room.max_player_count:
            return await room.force_dismiss(OverType.REQ_DISMISS)



    async def enter_room(self,player,room):
        player.offline = False  # 此处不改变状态，玩家收不到房间以下两条信息
        if player.trustee:
            await room.do_trustee(player)
        self.log_info(player.uid, "enter_room", player.tid, id(player))
        await self.notify_player_enter_room(room, player)