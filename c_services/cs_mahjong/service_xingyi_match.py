from c_services.cs_mahjong.player import Player
from .room_xingyi_match import RoomXyMatch
from .service import MahjongServer


class MahjongServerXyMatch(MahjongServer):
    ROOM = RoomXyMatch
    PLAYER = Player

    def __init__(self):
        super().__init__()
