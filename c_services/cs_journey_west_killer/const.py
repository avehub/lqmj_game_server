from common.public.base_enum import BaseEnum


class FlowStatus(BaseEnum):
    """ 流程状态 """
    T_IN_IDLE = 0, "无状态"
    T_IN_DEAL_CARDS = 1, "发牌中"
    T_IN_PLAYING = 2, "在行牌中"
    T_IN_TURN_TO = 3, "轮到某人"
    T_IN_RECHARGE = 4, "充值中"
    T_IN_SHOU_PAI = 5, "在收牌中"
    T_IN_CHECK_OUT = 6, "结算中"
