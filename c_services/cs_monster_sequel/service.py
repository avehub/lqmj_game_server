from c_services.cs_monster.service import MonsterServer
from common.public.enum_const import StaCode
from .player import Player
from .room_base import Room
from ..const.cs_enum_const import CmdRoom


class MonsterSeqServer(MonsterServer):
    """ 续篇 """
    ROOM = Room
    PLAYER = Player

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.DO_USER_ABILITY: self.__on_player_do_use_ability
        })

    async def _on_play_cards(self, player, room, data):
        """ 打牌 """
        _, room, cards = await self.on_play_cards(player, room, data)
        if room:
            await room.match_select_ability(player, cards[0])

    async def __on_player_do_use_ability(self, player, room, data):
        code, msg = await room.player_do_use_ability(player, data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.DO_USER_ABILITY, player.uid, code, msg, ws_id=player.ws_id)
        await room.turn_next()

