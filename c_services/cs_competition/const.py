from common.public.base_enum import BaseEnum
from enum import StrEnum


class GameRoomStatus(BaseEnum):
    """ 房间状态 """
    PLAYING = 1, "游戏中"
    WAITING = 2, "等待中"
    FINISH = 3, "已结束"
