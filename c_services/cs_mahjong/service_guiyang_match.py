from c_services.const.cs_enum_const import CmdRoom
from c_services.cs_mahjong.player import Player
from common.public.enum_const import StaCode
from .room_guiyang import RoomGY
from .room_guiyang_match import RoomGyMatch
from .service import MahjongServer
from .service_guiyang import MahjongServerGy


class MahjongServerGyMatch(MahjongServerGy):
    ROOM = RoomGyMatch
    PLAYER = Player

    def __init__(self):
        super().__init__()
