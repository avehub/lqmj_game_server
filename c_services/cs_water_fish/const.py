# coding=utf-8
from common.public.base_enum import BaseEnum


# 请在此处创建枚举对象


class CardsType(BaseEnum):
    SAN_PAI = 1, "散牌"
    PAIR = 2, "对子"
    SHUI_YU = 3, "水鱼"
    SHUI_YU_TX = 4, "水鱼天下"


class FlowStatus(BaseEnum):
    FLOW_IN_FREE = 0, "空闲中"
    FLOW_IN_READY = 1, "就绪中"
    FLOW_IN_BET = 2, "下注中"
    FLOW_IN_DEAL_CARDS = 3, "发牌中"
    FLOW_IN_SA_PU = 4, "撒扑中"
    FLOW_IN_SA_PU_END = 5, "撒扑结束"
    FLOW_IN_OPERATE = 6, "操作中",
    FLOW_IN_OPERATE_END = 7, "操作结束",
    FLOW_IN_CHECK = 8, "结算中"


class OperateType(BaseEnum):
    FARMER_MP = 1, "闲闷赔"
    FARMER_LP = 2, "闲亮牌"
    FARMER_MI = 3, "闲密牌"
    FARMER_QG = 4, "闲强攻"
    LANDLORD_ZOU = 5, "闲亮庄走"
    LANDLORD_SHA = 6, "闲亮庄杀"
    LANDLORD_KAI = 7, "闲密庄开"
    LANDLORD_XIN = 8, "闲密庄信"
    FARMER_ZOU_XIN = 9, "庄走闲信"
    FARMER_ZOU_FAN = 10, "庄走闲反"
    FARMER_SHA_XIN = 11, "庄杀闲信"
    FARMER_SHA_FAN = 12, "庄杀闲反"


OPERATE_RATE = {
    OperateType.FARMER_QG: 2,  # 强攻2倍
    OperateType.LANDLORD_XIN: 2,  # 密信
    OperateType.LANDLORD_KAI: 5,  # 密开
    OperateType.FARMER_ZOU_FAN: 2,  # 走反
    OperateType.FARMER_SHA_XIN: 1,  # 杀信
    OperateType.FARMER_SHA_FAN: 3,  # 杀反

}


class CompareRes(BaseEnum):
    DRAW = 0, "平局"
    WIN = 1, "赢"
    LOSE = 2, "输"
