from .player import Player
from .room_blood_flow import RoomBf
from .service import MonsterServer


class MonsterBfServer(MonsterServer):
    ROOM = RoomBf
    PLAYER = Player

    def __init__(self):
        super().__init__()
