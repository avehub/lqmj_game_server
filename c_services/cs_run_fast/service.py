from c_services.const.cs_enum_const import CmdRoom
from common.proto.py_pb2.ws_c2s import do_re_double_model, qiang_guan_model
from common.proto.py_pb2.ws_leisure import do_bid_model, do_redouble_model
from common.public.enum_const import StaCode
from .player import Player
from .room_base import Room
from ..base.base_card_service import BaseCardService


class RunFastServer(BaseCardService):
    """ 跑得快服务 """
    ROOM = Room
    PLAYER = Player

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.DO_REDOUBLE.val: self.__on_player_redouble,
            CmdRoom.PLAY_CARDS.val: self.__on_play_cards,

            CmdRoom.NOTIFY_POSITION.val: self.__notify_position,
            CmdRoom.READY.val: self.__on_player_ready,
            CmdRoom.QIANG_GUAN.val: self.__on_player_qiang_guan,
        })

    async def __on_player_redouble(self, player, room, data):
        """ 玩家加倍 """
        do_re_double_model.ParseFromString(data)
        is_double = do_re_double_model.do_double
        code, msg = await room.player_redouble(player, is_double)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.DO_REDOUBLE, player.uid, code, msg, ws_id=player.ws_id)
        if room.check_player_multiple_finish():
            await room.turn_start()

    async def __on_play_cards(self, player, room, data):
        """ 打牌 """
        player, room, cards = await self.on_play_cards(player, room, data)
        if room:
            if not player.cards:
                if player.is_qiang_guan == 1:
                    room.qiang_guan_win = True
                if len(cards) == 1:
                    last_player = room.next_player_reverse(player.seat_id)
                    if last_player.not_play_best:
                        last_player.is_bao_pei = True
                        room.has_bao_pei = True
                return await room.round_over()
            if cards and player.is_qiang_guan != 1 and room.has_qiang_guan:
                player.is_bao_pei = True
                room.qiang_guan_win = False
                return await room.round_over()
            return await room.turn_next()

    async def __notify_position(self, player, room, data):
        self.log_info("收到定位信息", player.uid)
        await room.set_player_position(player, data)

    async def __on_player_ready(self, player, room, _):
        code, msg = await room.on_player_ready(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.READY, player.uid, code, msg, ws_id=player.ws_id)
        await room.try_start_game()

    async def __on_player_qiang_guan(self, player, room, data):
        """ 玩家抢关 """
        qiang_guan_model.ParseFromString(data)
        qiang_guan = qiang_guan_model.qiang_guan
        code, msg = await room.on_player_qiang_guan(player, qiang_guan)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.QIANG_GUAN, player.uid, code, msg, ws_id=player.ws_id)
        if room.check_player_qiang_guan():
            await room.start_redouble_or_turn_start()
        else:
            next_seat_id = room.next_player(player.seat_id).seat_id
            room.curr_seat_id = next_seat_id
            await room.start_qiang_guan(next_seat_id)
