from enum import unique, IntEnum
from common.public.base_enum import BaseEnum

ALL_CARDS_WITHOUT_ZI_HUA = (
    11, 12, 13, 14, 15, 16, 17, 18, 19,  # 万字: 1~9
    21, 22, 23, 24, 25, 26, 27, 28, 29,  # 线条: 1~9
    31, 32, 33, 34, 35, 36, 37, 38, 39,  # 筒子：1~9
)


class ActionType(BaseEnum):
    """ 动作类型 """
    ACTION_TYPE_PENG = 1, "碰"
    ACTION_TYPE_MING_GANG = 2, "明杠"
    ACTION_TYPE_ZHUAN_WAN_GANG = 3, "转弯杠"
    ACTION_TYPE_AN_GANG = 4, "暗杠"
    ACTION_TYPE_CHI = 5, "吃 (未用预留)"
    ACTION_TYPE_PASS = 6, "过"
    ACTION_TYPE_HU = 7, "胡"
    ACTION_TYPE_QIANG_GANG_HU = 8, "抢杠胡"
    ACTION_TYPE_TIAN_TING = 9, "天听"
    ACTION_TYPE_MEN = 10, "闷"
    ACTION_TYPE_JIAN = 11, "捡"
    ACTION_TYPE_GSP = 12, "杠上炮"
    ACTION_TYPE_ZHA_HU = 13, "炸胡"
    ACTION_TYPE_ZHA_JIAN = 14, "炸捡"
    ACTION_TYPE_ZHA_MEN = 15, "炸闷"


class CardsType(IntEnum):
    """ 牌相关 """
    CARD_COUNT = 4  # 每张牌的牌数
    YAO_JI = 21
    LAI_ZI = 51  # 癞子（红中）
    DONG_FENG = 42  # 东风
    XI_FENG = 44  # 西风
    NAN_FENG = 46  # 南风
    BEI_FENG = 48  # 北风
    FA = 53  # 发
    BAI = 55  # 白
    CHUN = 62  # 春
    XIA = 64  # 夏
    QIU = 66  # 秋
    DONG = 68  # 冬
    MEI = 72  # 梅
    LAN = 74  # 兰
    ZHU = 76  # 竹
    JU = 78  # 菊


@unique
class HuType(BaseEnum):
    """
    胡牌类型：牌型
    仅表示麻将牌的胡牌类型，与手牌有关，和胡牌时机无关
    """
    # 1.牌型
    PING_HU = 101, "平胡"
    DA_DUI_ZI = 102, "大对子"
    QI_DUI = 103, "七对"
    LONG_QI_DUI = 104, "龙七对(5个对子 + 1刻)"
    DI_LONG_QI = 105, "地龙七(5个对子 + 1碰)"
    QING_YI_SE = 106, "清一色"
    QING_DA_DUI = 107, "清大对"
    QING_QI_DUI = 108, "清七对"
    QING_DI_LONG = 109, "清地龙"
    QING_LONG_BEI = 110, "清龙对(清龙背|清龙七对)"


@unique
class SuitType(BaseEnum):
    """ 花色类型 """
    SUIT_WAN = 1, "万"
    SUIT_SUO = 2, "条"
    SUIT_TONG = 3, "筒"
    SUIT_FENG = 4, "风"
    SUIT_JIAN = 5, "剑"
