from enum import unique

from common.public.base_enum import BaseEnum


class FlowStatus(BaseEnum):
    """ 流程状态 """
    F_IN_IDLE = 0, "无状态"
    F_IN_DEAL_CARDS = 1, "发牌中"
    F_IN_BID = 2, "叫分中"
    F_IN_REDOUBLE = 3, "加倍中", "铲"
    F_IN_RE_REDOUBLE = 4, "加加倍", "反铲"
    F_IN_CONFIRM_DEALER = 5, "确定地主中"
    F_IN_PLAYING = 6, "在行牌中"
    F_IN_TURN_TO = 7, "轮到某人"
    F_IN_CHECK_OUT = 8, "结算中"


@unique
class ActionType(BaseEnum):
    """ 动作类型 """
    TYPE_0_PASS = 0, "PASS", "0"
    TYPE_1_SINGLE = 1, "单张", "1"
    TYPE_2_PAIR = 2, "一对", "2"
    TYPE_3_TRIPLE = 3, "3不带", "3"
    TYPE_4_BOMB = 4, "4张炸弹", "4"
    TYPE_5_KING_BOMB = 5, "王炸", "5"
    TYPE_6_3_1 = 6, "三带一", "6"
    TYPE_7_3_2 = 7, "三带二", "7"
    TYPE_8_SERIAL_SINGLE = 8, "单连牌：最少5张", "8"
    TYPE_9_SERIAL_PAIR = 9, "连对", "9"
    TYPE_10_SERIAL_TRIPLE = 10, "飞机不带", "10"
    TYPE_11_SERIAL_3_1 = 11, "飞机带单", "11"
    TYPE_12_SERIAL_3_2 = 12, "飞机带双", "12"
    TYPE_13_4_2 = 13, "四带2", "13"
    TYPE_14_4_22 = 14, "四带2对", "14"
    TYPE_15_SERIAL_BOMB = 15, "滚炸", "15"
    TYPE_16_WRONG = 16, "错误", "16"


class DoubleType(BaseEnum):
    """ 加倍类型 """
    DOUBLE_DFT = 0, "未操作"
    DONE_NO_DOUBLE = 1, "已操作不加倍"
    DONE_REDOUBLE = 2, "已操作加倍"
    DONE_RE_REDOUBLE = 3, "已操作超级加倍"
