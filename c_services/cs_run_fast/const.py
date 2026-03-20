from enum import unique, IntEnum

from common.public.base_enum import BaseEnum


class FlowStatus(BaseEnum):
    """ 流程状态 """
    F_IN_IDLE = 0, "无状态"
    F_IN_DEAL_CARDS = 1, "发牌中"
    F_IN_QIANG_GUAN = 2, "抢关中"
    F_IN_REDOUBLE = 3, "加倍中"
    F_IN_PLAYING = 5, "在行牌中"
    F_IN_TURN_TO = 6, "轮到某人"
    F_IN_CHECK_OUT = 7, "结算中"


class DoubleType(BaseEnum):
    """ 加倍类型 """
    DOUBLE_DFT = 0, "未操作"
    DONE_NO_DOUBLE = 1, "已操作不加倍"
    DONE_REDOUBLE = 2, "已操作加倍"

class FirstPlayType(BaseEnum):
    """ 优先出牌类型 """
    HT_3 = 0,"黑桃3"
    HX_3 = 1,"红桃3"
    LAST_ROUND_WIN = 2,"上轮胜者"
    IN_TURN = 3,"轮流"
