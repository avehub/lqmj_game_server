from c_services.base.base_leisure_service import BaseLeisureService
from c_services.const.cs_enum_const import CmdRoom
from .room_base import Room
from .player import Player
from common.public.enum_const import StaCode


class MonsterServer(BaseLeisureService):
    """
    打妖怪服务
    """
    ROOM = Room
    PLAYER = Player

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.PLAY_CARDS.val: self._on_play_cards,
            CmdRoom.PICK_CARDS.val: self.__on_pick_cards,
        })

    async def _on_play_cards(self, player, room, data):
        """ 打牌 """
        _, room, _ = await self.on_play_cards(player, room, data)
        if room:
            await room.turn_next()

    async def __on_pick_cards(self, player, room, _):
        """ 捡/收牌 """
        code, msg = await room.player_pick_cards(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PICK_CARDS, player.uid, code, msg, ws_id=player.ws_id)
