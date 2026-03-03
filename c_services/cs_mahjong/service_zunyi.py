from c_services.const.cs_enum_const import CmdRoom
from c_services.cs_mahjong.player import Player
from .room_zunyi import RoomZY
from .service import MahjongServer


class MahjongServerZy(MahjongServer):
    ROOM = RoomZY
    PLAYER = Player

    def __init__(self):
        super().__init__()
