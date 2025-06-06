
from c_services.const.cs_enum_const import CmdRoom
from c_services.cs_mahjong.player import Player
from c_services.cs_mahjong.room_base import Room
from common.public.enum_const import StaCode
from .const import FlowStatus
from ..base.base_card_service import BaseCardService


class MahjongServer(BaseCardService):
    ROOM = Room
    PLAYER = Player
    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.PLAYER_PASS.val: self.__on_player_pass,
            CmdRoom.PLAYER_PENG.val: self.__on_player_peng,
            CmdRoom.PLAYER_GANG.val: self.__on_player_gang,
            CmdRoom.PLAYER_HU.val: self.__on_player_hu,
            CmdRoom.PLAYER_MEN.val: self.__on_player_men,
            CmdRoom.PLAYER_JIAN.val: self.__on_player_jian,
            CmdRoom.PLAYER_SHANG_GA.val: self.__on_player_shang_ga,
            CmdRoom.READY.val: self.__on_player_ready,
            CmdRoom.PLAYER_EXCHANGE_CARDS.val: self.__on_player_exchange_cards,
            CmdRoom.PLAY_CARDS.val: self.__on_player_chu_pai,
            CmdRoom.PLAYER_TIAN_TING.val: self.__on_player_tian_ting,
        })



    async def __on_player_pass(self, player, room):
        code, msg = await room.on_player_pass(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_PASS, player.uid, code, msg, ws_id=player.ws_id)
        if room.flow_status in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL,
                                FlowStatus.T_IN_TIAN_TING,FlowStatus.T_IN_FOUR_BAO_TING):
            room.clear_record_operates(player.seat_id)
            self.info_log(room.tid, player.uid, player.seat_id, "server 玩家选择过：", room.record_operates)
            if not room.record_operates:
                return room.check_action_end()

    async def __on_player_peng(self, player, room):
        code, msg = await room.on_player_peng(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_PENG, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_gang(self, player, room, data):
        code, msg = await room.on_player_gang(player,data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_GANG, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_hu(self,player, room):
        code, msg = await room.on_player_hu(player)
        if code != StaCode.Pass:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_HU, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_men(self,player, room):
        code, msg = await room.on_player_men(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_MEN,player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_jian(self, player, room):
        code, msg =await room.on_player_jian(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_JIAN, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_shang_ga(self,player, room, data):
        code, msg = await room.on_player_shang_ga(player, data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_SHANG_GA, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_ready(self,player,room):
        code, msg = await room.on_player_ready(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.READY, player.uid, code, msg, ws_id=player.ws_id)
        room.try_start_game()

    async def __on_player_exchange_cards(self,player, room, data):
        code, msg = await room.on_player_exchange_cards(player, data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_EXCHANGE_CARDS, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_chu_pai(self,player,room,data):
        code, msg = await room.on_player_chu_pai(player, data)
        if code != StaCode.Pass:
            return await self.cs2ws_by_rmq(CmdRoom.PLAY_CARDS,player.uid, code, msg, ws_id = player.ws_id)
        await room.enter_chu_pai_call()

    async def __on_player_tian_ting(self,player,room,data):
        code, msg = await room.on_player_tian_ting(player,data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_TIAN_TING,player.uid, code, msg, ws_id = player.ws_id)
        if player.cards_len == 13:
            room.check_tian_ting_end()
        else:
            room.check_action_end()


