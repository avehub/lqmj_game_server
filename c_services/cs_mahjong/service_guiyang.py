from c_services.const.cs_enum_const import CmdRoom
from c_services.cs_mahjong.player import Player
from c_services.cs_mahjong.room_base import Room
from common.public.enum_const import StaCode
from .const import FlowStatus
from .room_guiyang import RoomGY
from ..base.base_card_service import BaseCardService


class MahjongServer(BaseCardService):
    ROOM = RoomGY
    PLAYER = Player

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.PLAYER_PASS.val: self.__on_player_ding_que,
        })

    async def __on_player_ding_que(self, player, room):
        code, msg = await room.on_player_ding_que(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_DING_QUE, player.uid, code, msg, ws_id=player.ws_id)
