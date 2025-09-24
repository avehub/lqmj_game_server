from c_services.base.base_leisure_service import BaseLeisureService
from c_services.const.cs_enum_const import CmdRoom
from common.proto.py_pb2.ws_leisure import do_bet_model, operate_model, sa_pu_model
from .room_base import Room
from .player import Player
from common.public.enum_const import StaCode


class WaterFishServer(BaseLeisureService):
    ROOM = Room
    PLAYER = Player

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.BET.val: self.__on_player_bet,
            CmdRoom.SA_PU.val: self.__on_player_sa_pu,
            CmdRoom.DEALER_OPERATE.val: self.__on_dealer_operate,
            CmdRoom.FARMER_OPERATE.val: self.__on_farmer_operate,
        })

    async def __on_player_bet(self, player, room, data):
        """ 玩家下注 """
        do_bet_model.ParseFromString(data)
        bet = do_bet_model.bet
        code, msg = await room.player_bet(player, bet)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.BET, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_sa_pu(self, player, room, data):
        """ 玩家撒扑 """
        sa_pu_model.ParseFromString(data)
        cards = sa_pu_model.cards
        sp_status = sa_pu_model.sp_status
        code, msg = await room.player_sa_pu(player, cards, sp_status)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.SA_PU, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_dealer_operate(self, player, room, data):
        """ 庄操作 """
        operate_model.ParseFromString(data)
        operate = operate_model.operate
        seat_id = operate_model.seat_id
        code, msg = await room.player_dealer_operate(player, operate, seat_id)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.DEALER_OPERATE, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_farmer_operate(self, player, room, data):
        """ 闲操作 """
        operate_model.ParseFromString(data)
        operate = operate_model.operate
        code, msg = await room.player_farmer_operate(player, operate)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.FARMER_OPERATE, player.uid, code, msg, ws_id=player.ws_id)
