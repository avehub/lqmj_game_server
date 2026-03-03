from c_services.base.base_leisure_service import BaseLeisureService
from c_services.const.cs_enum_const import CmdRoom
from common.proto.py_pb2.ws_leisure import do_bid_model, do_redouble_model
from common.public.enum_const import StaCode
from .player import Player
from .room_national import NationalRoom


class LandlordsServer(BaseLeisureService):
    """ 斗地主服务 """
    ROOM = NationalRoom
    PLAYER = Player

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.DO_BID.val: self.__on_player_bid,
            CmdRoom.DO_REDOUBLE.val: self.__on_player_redouble,
            CmdRoom.DO_RE_REDOUBLE.val: self.__on_player_re_redouble,
            CmdRoom.PLAY_CARDS.val: self.__on_play_cards,
        })

    async def __on_player_bid(self, player, room, data):
        """ 玩家叫分 """
        do_bid_model.ParseFromString(data)
        bid_score = do_bid_model.bid_score
        code, msg = await room.player_bid(player, bid_score)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.DO_BID, player.uid, code, msg, ws_id=player.ws_id)
        await room.turn_bid()

    async def __on_player_redouble(self, player, room, data):
        """ 玩家加倍 """
        do_redouble_model.ParseFromString(data)
        score = do_redouble_model.score
        code, msg = await room.player_redouble(player, score)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.DO_REDOUBLE, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_re_redouble(self, player, room, data):
        """ 玩家加加倍 """
        cmd = CmdRoom.DO_RE_REDOUBLE
        do_redouble_model.ParseFromString(data)
        score = do_redouble_model.score
        code, msg = await room.player_re_redouble(player, score)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(cmd, player.uid, code, msg, ws_id=player.ws_id)
        if score:  # 进入定庄
            await room.confirm_dealer(player.seat_id)
            return await room.delay_func(1, room.turn_start)
        else:
            await room.turn_re_redouble()

    async def __on_play_cards(self, player, room, data):
        """ 打牌 """
        player, room, _ = await self.on_play_cards(player, room, data)
        if room:
            if not player.cards:
                return await room.round_over()
            return await room.turn_next()
