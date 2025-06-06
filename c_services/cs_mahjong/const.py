from enum import unique, IntEnum
from common.public.base_enum import BaseEnum

ALL_CARDS_WITHOUT_ZI_HUA = (
    11, 12, 13, 14, 15, 16, 17, 18, 19,  # 万字: 1~9
    21, 22, 23, 24, 25, 26, 27, 28, 29,  # 线条: 1~9
    31, 32, 33, 34, 35, 36, 37, 38, 39,  # 筒子：1~9
)

LIU_JU_COUNT = 0  # 控制流局阈值
XUE_LIU_LEFT_BI_HU = 3

class PlayType(BaseEnum):
    XING_YI_MJ = 1,"兴义麻将"
    AN_LONG_XUE_ZHAN = 2,"血流麻将"


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
    WU_GU_JI = 38  # 乌骨鸡
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
    JIN_GOU_DIAO = 113,"金钩钓"
    QING_JIN_GOU = 116,"清金钩"  #（只在二三丁拐下有）

    # 毕节麻将
    YIN_GOU_DIAO = 131, "银勾钓"
    RUAN_WU_DUI = 132, "软5对"
    YING_WU_DUI = 133, "硬5对"
    QYS_RUAN_WU_DUI = 134, "清一色软五对"
    QYS_YING_WU_DUI = 135, "清一色硬五对"


@unique
class SuitType(BaseEnum):
    """ 花色类型 """
    SUIT_WAN = 1, "万"
    SUIT_SUO = 2, "条"
    SUIT_TONG = 3, "筒"
    SUIT_FENG = 4, "风"
    SUIT_JIAN = 5, "剑"

@unique
class FlowStatus(IntEnum):
    """ 游戏流程状态 """
    T_IN_IDLE = 0  # 无状态
    T_IN_CHU_PAI = 1  # 在出牌中
    T_IN_PUBLIC_OPRATE = 2  # 公共操作过程中
    T_IN_MO_PAI = 3  # 在摸牌中暗(未公示)
    T_IN_MO_PAI_CALL = 4  # 在摸牌后的呼叫中
    T_IN_MING_GANG_PAI_CALL = 5  # 抢杠胡判断流程
    T_IN_ZHUAN_WAN_GANG_PAI_CALL = 6  # 抢杠胡判断流程
    T_IN_AN_GANG_PAI_CALL = 7  # 抢杠胡判断流程
    T_IN_ROUND_START = 8  # 一局开始
    T_IN_DEAL_CARDS = 9  # 发牌中
    T_IN_EXCHANGE_CARDS = 10  # 换牌流程
    T_IN_WILL_BEGIN_OPTION = 11  # 开局前的玩家操作选项
    T_IN_TIAN_HU = 12  # 庄家天胡
    T_IN_DI_HU_CHU_PAI = 13  # 庄家天胡结束出牌 地胡判断阶段
    T_IN_CHECK_OUT = 14  # 结算中
    T_IN_TIAN_TING = 15  # 天听中
    T_IN_DING_QUE = 16  # 定缺
    T_IN_GU_MAI = 17  # 估卖
    T_IN_FOUR_BAO_TING = 18  # 4张牌报听中
    T_IN_FAN_JI = 19  # todo:牌摸完之后翻鸡
    T_IN_HUI_TOU_YI_XIAO = 20  # 回头一笑流程
    T_IN_DING_JING = 21  # 定精牌流程
    T_IN_WAIT_CHONG_ZHI = 22  # 充值等待

class TimerDelay(IntEnum):
    """ 延时时间 """
    ROBOT_TIME = 1  # 机器人操作时间
    WAIT_SECONDS = 2  # 等待时间
    TIAN_TING_SECONDS = 10  # 天听等待时间
    CALL_SECONDS = 16  # 等待玩家响应的秒数
    FIRST_CALL_SECONDS = 16  # 第一位玩家的等待时间
    CHU_PAI_AFTER_WAIT_TIME = 16  # 没正常操作时等待时间
    GUESS_TIME = 30  # 竞猜时间
    WAIT_CHONG_ZHI_TIME = 30  # 充值等待时间
    EXCHANGE_CARDS = 16  # 10秒换牌时间
    SHANG_GA_TIME = 15  # 上嘎时间
    CHU_PAI_TIME = 16  # 出牌时间
    READY_TIME = 15  # 准备时间
    CHONG_ZHI_TIME = 30  # 充值时间
    KOU_FEI_TIME = 2  # 及时结算等待
    TUO_GUAN_TIME = 2  # 托管时间
    TUO_GUAN_TIME_PENG = 2  # 托管时间
    TUO_GUAN_TIME_GANG = 10  # 托管时间
    TUO_GUAN_TIME_CHU_PAI = 2  # 托管时间
    ZHUN_BEI_SHI_XIAN = 20  # 桌子中不准备踢出时限
    ROUND_OVER_WAIT = 5  # 一局结束等待(比赛场)
    FAN_JI_TIME = 10  # todo:翻鸡时间
    DING_QUE_TIME = 10  # todo:定缺时间
    KAI_HU_TIME = 1  # 自动胡时间

@unique
class ChangeThreeType(IntEnum):
    """ 换三张类型 """
    NO_CHANGE = 0  # 不换牌
    PER_ROUND = 1  # 每局都换
    SAME_POINT = 2  # 豹子换
    LIU_JU = 3  # 流局换

@unique
class ChangeCardsType(IntEnum):
    """ 换牌类型 """
    ANY_CARDS = 1  # 任意牌
    SAME_SUIT_CARDS = 2  # 同色牌

@unique
class OverType(IntEnum):
    DEFAULT = -1  # 默认值
    LIU_JU = 1  # 流局
    HU_KAI = 2  # 胡开
    ZHA_HU_KAI = 3  # 炸胡开
    FORCE = 4  # 强制解散
    OTHERS_GIVE_UP = 5  # 其它玩家认输

@unique
class ExtraHuPai(IntEnum):
    """ 额外胡牌定义 """
    # 1.额外胡
    TIAN_HU = 201  # 天胡
    DI_HU = 202  # 地胡
    TIAN_TING = 203  # 天听/报听
    SHA_BAO = 204  # 杀报
    GANG_SHANG_HUA = 205  # 杠上花（杠开）
    QIANG_GANG_HU = 206  # 抢杠胡
    GANG_SHANG_PAO = 207  # 杠上炮（热炮）

    # 2.特殊牌型
    BAO_TING_QING_QI_DUI = 208  # 报听清七对
    BAO_TING_QING_LONG_QI_DUI = 209  # 报听清龙七对

    # 1筒赖子独有
    XI_PAI = 210  # 喜牌
    YING_HU = 211  # 硬胡
    COMMON_TIAN_TING = 212  # 普通报听
    COMMON_SHA_BAO = 213  # 普通杀报
    SEA_MOON = 214  # todo:海底捞月

    # 4.返分key
    AN_GANG = 301  # 暗杠
    MING_GANG = 302  # 明杠
    ZHUAN_WAN_GANG = 303  # 转弯杠
    MEN_HU = 304  # 闷胡
    JIAN_HU = 305  # 捡胡
    HUA_ZHU = 306  # todo:花猪

    # 江西麻将
    DE_GUO = 307
    DE_ZHONG_DE = 308
    ZHUANG_HU = 311
    JING_DIAO = 312

@unique
class JiType(IntEnum):
    """
    鸡/杠type
    以2开头
    """
    DEFAULT = 201
    CHONG_FENG_JI = 202
    ZE_REN_JI = 203
    MAN_TANG_JI = 204
    SHANG_XIA_JI = 205
    BEN_JI = 206
    WU_GU_JI = 207
    WU_GU_CFJ = 208
    WU_GU_ZRJ = 209
    JIN_JI = 210
    WU_GU_JIN_JI = 211
    CHONG_FENG_JIN_JI = 212
    WU_GU_CF_JIN_JI = 213

    YIN_JI = 214  # 银鸡（1筒和1万）
    CF_YI_TONG = 215  # 冲锋1筒
    JIN_CF_YI_TONG = 216  # 金冲锋1筒
    JIN_YI_TONG = 217  # 金1筒
    JIN_YI_WAN = 218  # 一万金鸡
    CF_YI_WAN = 219  # 一万冲锋鸡
    YI_WAN_ZRJ = 220  # 一万责任鸡
    JIN_CF_YI_WAN = 221  # 一万冲锋金鸡

    AN_GANG = 301  # 暗杠
    MING_GANG = 302  # 明杠
    ZHUAN_WAN_GANG = 303  # 转弯杠
    JING_GANG = 304  # 精杠

@unique
class PlayerStatusType(IntEnum):
    """
    主要表示游戏结束后玩家各种状态
    """
    DEFAULT = -1  # 默认值
    ZHA_HU_2 = 1  # 2个炸胡（赔）
    ZHA_HU_AND_JIAO = 2  # 存在炸胡和一个叫牌玩家（赔）
    ZHA_HU_AND_NO_JIAO = 3  # 存在炸胡和一个未叫牌玩家（赔）
    JIAO_AND_NO_JIAO = 4  # 存在一个叫一个未叫牌玩家（赔）
    NO_JIAO_2 = 5  # 2个均未叫（赔）
    JIAO_2 = 6  # 2个都叫牌


# 鸡牌分
JI_PAI_SCORE = {
    # 鸡牌分(默认鸡)
    CardsType.YAO_JI: 1,
    CardsType.WU_GU_JI: 2,

    # 鸡牌类型分
    JiType.DEFAULT: 1,
    JiType.CHONG_FENG_JI: 3,
    JiType.CHONG_FENG_JIN_JI: 6,
    JiType.ZE_REN_JI: 2,
    JiType.JIN_JI: 2,
    JiType.WU_GU_JI: 2,
    JiType.WU_GU_CFJ: 4,
    JiType.WU_GU_ZRJ: 2,
    JiType.WU_GU_JIN_JI: 4,
    JiType.WU_GU_CF_JIN_JI: 8,
    # 此处给3分，其余外面逻辑判断
    JiType.AN_GANG: 3,
    JiType.MING_GANG: 3,
    JiType.ZHUAN_WAN_GANG: 3,
}

# 额外分(与牌型无关，与时机有关)
EXTRA_SCORE_MAP = {
    ExtraHuPai.GANG_SHANG_PAO: 1,  # 杠上炮
    ExtraHuPai.GANG_SHANG_HUA: 1,  # 杠上花(自摸)
    ExtraHuPai.QIANG_GANG_HU: 0,  # 抢杠只能开，安抢杠者两倍牌型分赔付
    ExtraHuPai.TIAN_TING: 10,  # 天听
    ExtraHuPai.DI_HU: 10,  # 地胡
    ExtraHuPai.TIAN_HU: 10,  # 天胡
    ExtraHuPai.SHA_BAO: 10,  # 杀报

    ActionType.ACTION_TYPE_MING_GANG: 3,
    ActionType.ACTION_TYPE_ZHUAN_WAN_GANG: 3,
    ActionType.ACTION_TYPE_AN_GANG: 3,
}

# 特殊胡牌类型(元组，外部不可变)
SPECIAL_HU_TYPE = (
    ExtraHuPai.TIAN_HU,
    ExtraHuPai.DI_HU,
    ExtraHuPai.TIAN_TING,
    ExtraHuPai.COMMON_TIAN_TING,
    ExtraHuPai.SHA_BAO
)

# 去杀报
SPECIAL_HU_TYPE1 = (
    ExtraHuPai.TIAN_HU,
    ExtraHuPai.DI_HU,
    ExtraHuPai.TIAN_TING,
)

PAI_XING_SCORE_MAP = {
    # 基础牌型
    HuType.PING_HU: 1,
    HuType.DA_DUI_ZI: 5,
    HuType.QI_DUI: 10,
    HuType.LONG_QI_DUI: 20,
    HuType.DI_LONG_QI: 10,
    HuType.JIN_GOU_DIAO: 10,
    HuType.QING_YI_SE: 10,
    HuType.QING_DA_DUI: 15,
    HuType.QING_QI_DUI: 20,
    HuType.QING_DI_LONG: 30,
    HuType.QING_LONG_BEI: 30,
    HuType.QING_JIN_GOU: 20,
}

@unique
class CheckType(IntEnum):
    """
    结算明细type
    """
    CHECK_HU_ZI_MO = 1001  # 结算胡自摸类型
    CHECK_HU_ZI_MO_ZHA = 1002  # 炸胡自摸开牌
    CHECK_HU_DIAN_PAO = 1003  # 结算点炮类型
    CHECK_HU_DIAN_PAO_ZHA = 1004  # 结算点炮类型
    CHECK_MEN = 1005  # 结算闷类型
    CHECK_MEN_ZHA = 1006  # 结算炸闷闷类型
    CHECK_JIAN = 1007  # 结算捡类型
    CHECK_JIAN_ZHA = 1008  # 结算炸捡类型
    LOU_MEN = 1000  # 结算漏闷类型
    LOU_JIAN = 1010  # 结算漏捡类型
    CHECK_LIU_JU_CHA_JIAO = 1011  # 结算查叫类型
    CHECK_CHONG_FENG_JI = 1012  # 结算冲锋鸡
    CHECK_ZE_REN_JI = 1013  # 结算责任鸡
    CHECK_JI = 1014  # 结算鸡类型(翻牌鸡)
    CHECK_MING_GANG = 1015  # 明杠
    CHECK_SUO_GANG = 1016  # 转弯杠
    CHECK_AN_GANG = 1017  # 暗杠
    CHECK_GU_MAI = 1018  # 估卖
    CHECK_KAI_HU_BAO = 1019  # 开胡炸胡包牌
    CHECK_LIAN_ZHUANG = 1020  # 连庄
    CHECK_CHA_QUE = 1021  # 查缺
    CHECK_YUAN_QUE = 1022  # 源缺
    CHECK_YING_HU = 1023  # 硬胡
    CHECK_YING_JIAO = 1024  # 硬叫
    CHECK_LAI_ZI_PENG = 1025  # 赖子碰
    CHECK_LAI_ZI_GNAG = 1026  # 赖子杠
    CHECK_LAI_ZI_JI = 1027  # 赖子鸡
    CHECK_LAI_ZI_CHONG_XI = 1028  # 赖子冲喜
    CHECK_MAI_LEI_JING = 1029  # 埋雷精
    CHECK_TYSG_JING = 1030  # 同一首歌精
    CHECK_HTYX_JING = 1031  # 回头一笑精
    CHECK_BA_WANG_JING = 1032  # 霸王精
    CHECK_ZHAO_JING_ZI_JING = 1033  # 照镜子
    CHECK_SHAI_YUE_LIANG_JING = 1034  # 晒月亮
    CHECK_CHONG_GUAN_JING = 1035  # 冲关
    CHECK_SHANG_JING = 1036  # 上精
    CHECK_JING_GANG = 1037  # 精杠

# 动作优先级（仅房卡场）
ACTION_PRIORITY = {
    ActionType.ACTION_TYPE_HU: 99,
    ActionType.ACTION_TYPE_QIANG_GANG_HU: 99,
    ActionType.ACTION_TYPE_MEN: 99,
    ActionType.ACTION_TYPE_AN_GANG: 98,
    ActionType.ACTION_TYPE_TIAN_TING: 98,

    ActionType.ACTION_TYPE_ZHA_HU: 97,
    ActionType.ACTION_TYPE_ZHA_MEN: 97,
    ActionType.ACTION_TYPE_ZHUAN_WAN_GANG: 96,
    ActionType.ACTION_TYPE_MING_GANG: 96,
    ActionType.ACTION_TYPE_PENG: 96,
    ActionType.ACTION_TYPE_JIAN: 95,
    ActionType.ACTION_TYPE_ZHA_JIAN: 94,
    ActionType.ACTION_TYPE_PASS: 1,
}