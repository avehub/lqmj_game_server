from c_services.const.cs_enum_const import CmdRoom
from c_services.cs_mahjong.player import Player
from common.public.enum_const import StaCode
from .room_bijie import RoomBJ
from .service import MahjongServer


class MahjongServerBj(MahjongServer):
    ROOM = RoomBJ
    PLAYER = Player

    def __init__(self):
        super().__init__()
