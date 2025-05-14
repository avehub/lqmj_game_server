from c_services.base.base_poker import BasePoker
from c_services.const.base_card import BaseCard
from common.utils.meta_class import with_meta


class BaseCards(BaseCard):
    # 方块
    FK_A = 101, 1, 1
    FK_2 = 102, 1, 2
    FK_3 = 103, 1, 3
    FK_4 = 104, 1, 4
    FK_5 = 105, 1, 5
    FK_6 = 106, 1, 6
    FK_7 = 107, 1, 7
    FK_8 = 108, 1, 8
    FK_9 = 109, 1, 9
    FK_10 = 110, 1, 10
    FK_J = 111, 1, 11
    FK_Q = 112, 1, 12
    FK_K = 113, 1, 13

    # 梅花
    MH_A = 201, 2, 1
    MH_2 = 202, 2, 2
    MH_3 = 203, 2, 3
    MH_4 = 204, 2, 4
    MH_5 = 205, 2, 5
    MH_6 = 206, 2, 6
    MH_7 = 207, 2, 7
    MH_8 = 208, 2, 8
    MH_9 = 209, 2, 9
    MH_10 = 210, 2, 10
    MH_J = 211, 2, 11
    MH_Q = 212, 2, 12
    MH_K = 213, 2, 13

    # 红心
    HX_A = 301, 3, 1
    HX_2 = 302, 3, 2
    HX_3 = 303, 3, 3
    HX_4 = 304, 3, 4
    HX_5 = 305, 3, 5
    HX_6 = 306, 3, 6
    HX_7 = 307, 3, 7
    HX_8 = 308, 3, 8
    HX_9 = 309, 3, 9
    HX_10 = 310, 3, 10
    HX_J = 311, 3, 11
    HX_Q = 312, 3, 12
    HX_K = 313, 3, 13

    # 黑桃
    HT_A = 401, 4, 1
    HT_2 = 402, 4, 2
    HT_3 = 403, 4, 3
    HT_4 = 404, 4, 4
    HT_5 = 405, 4, 5
    HT_6 = 406, 4, 6
    HT_7 = 407, 4, 7
    HT_8 = 408, 4, 8
    HT_9 = 409, 4, 9
    HT_10 = 410, 4, 10
    HT_J = 411, 4, 11
    HT_Q = 412, 4, 12
    HT_K = 413, 4, 13


class Cards(BaseCard):
    PAN_TAO_DA_HUI = 1, "蟠桃大会"
    SAN_MEI_SHEN_FENG = 2, "三昧神风"

    SHOU_1 = 3, "守"
    SHOU_2 = 4, "守"

    PAN_TAO_1 = 5, "蟠桃1"
    SI_HAI_BU_YU_1 = 6, "四海布雨"

    PAN_TAO_2 = 7, "蟠桃2"
    SI_HAI_BU_YU_2 = 8, "四海布雨"

    FU_LONG_SUO = 9, "缚龙索"
    JIN_DOU_YUN_1 = 10, "筋斗云1"

    PAN_TAO_3 = 11, "蟠桃3"
    DING_SHEN_SHU_1 = 12, "定身术1"

    PAN_TAO_4 = 13, "蟠桃4"
    SHEN_WAI_HUA_WU_1 = 14, "身外化物1"

    PAN_TAO_5 = 15, "蟠桃5"
    SHEN_WAI_HUA_WU_2 = 16, "身外化物2"

    PAN_TAO_6 = 17, "蟠桃6"
    SHEN_WAI_HUA_WU_3 = 18, "身外化物3"

    GONG_1 = 19, "攻1"
    GONG_2 = 20, "攻2"

    GONG_3 = 21, "攻3"
    SHEN_WAI_HUA_WU_4 = 22, "身外化物4"

    PAN_TAO_7 = 22, "蟠桃7"
    HUANG_JIN_SHENG_1 = 23, "幌金绳1"
    TIAN_LEI_GUN_GUN_1 = 24, "天雷滚滚1"

    SHOU_3 = 25, "守3"
    XIAO_BAI_LONG_1 = 26, "小白龙1"

    DUI_JUE_1 = 27, "对决1"
    TIAN_LEI_GUN_GUN_2 = 28, "天雷滚滚2"

    BAI_GU_SHUANG_JIAN = 29, "白骨双剑"
    JIN_LAN_JIA_SHA_1 = 30, "锦斓袈裟1"
    HUN_TIAN_LING = 31, "混天绫"

    HUANG_JIN_SHENG_2 = 32, "幌金绳2"
    JIN_GANG_ZHUO_1 = 33, "金刚琢1"
    XIAN_NIANG_1 = 34, "仙酿1"

    HUANG_JIN_SHENG_3 = 35, "幌金绳3"
    JIN_GANG_ZHUO_2 = 36, "金刚琢2"

    HUN_TIE_GUN = 37, "混铁棍"
    XIAO_BAI_LONG_2 = 38, "小白龙2"

    DING_SHEN_SHU_2 = 39, "定身术2"
    ZHAN_MO_JIAN = 40, "斩魔剑"

    GONG_4 = 41, "攻4"
    FENG_HUO_LEI_DIAN_1 = 42, "风火雷电1"

    GONG_5 = 43, "攻5"
    GONG_6 = 44, "攻6"

    GONG_7 = 44, "攻7"
    GONG_8 = 45, "攻8"
    XIAN_NIANG_2 = 46, "仙酿2"

    GONG_9 = 47, "攻9"
    GONG_10 = 48, "攻10"

    JIN_GANG_ZHUO_3 = 49, "金刚琢3"
    HUO_YAN_JIN_JING_1 = 50, "火眼金睛1"

    HUANG_JIN_SHENG_4 = 51, "幌金绳4"
    JIU_CHI_DING_PA = 52, "九齿钉耙"

    FENG_HUO_LEI_DIAN_2 = 53, "风火雷电2"
    JIN_DOU_YUN_2 = 54, "筋斗云2"

    CHEN_WU_ZHEN_1 = 55, "宸午针1"
    DUI_JUE_2 = 56, "对决2"

    SHOU_4 = 57, "守4"
    SHOU_5 = 58, "守5"

    SHOU_6 = 59, "守6"
    JIN_GANG_ZHUO_4 = 60, "金刚琢4"

    SHOU_7 = 61, "守7"
    JIN_GANG_ZHUO_5 = 62, "金刚琢5"

    SHOU_8 = 63, "守8"
    SAN_JIAN_LIANG_REN_DAO = 64, "三尖两刃刀"

    GONG_11 = 65, "攻11"
    SHOU_9 = 66, "守9"

    GONG_12 = 67, "攻12"
    SHOU_10 = 68, "守10"

    GONG_13 = 69, "攻13"
    SHOU_11 = 70, "守11"

    GONG_14 = 71, "攻14"
    SHOU_12 = 72, "守12"
    XIAN_NIANG_3 = 73, "仙酿3"

    GONG_15 = 74, "攻15"
    SHOU_13 = 75, "守13"

    SHOU_14 = 76, "守14"
    SHOU_15 = 77, "守15"

    PAN_TAO_8 = 78, "蟠桃8"
    JIN_GU_BANG = 79, "金箍棒"
    HUO_YAN_JIN_JING_2 = 80, "火眼金睛2"

    GONG_16 = 81, "攻16"
    JIN_DOU_YUN_3 = 82, "筋斗云3"

    DUI_JUE_3 = 83, "对决3"
    CHEN_WU_ZHEN_2 = 84, "宸午针2"

    GONG_17 = 85, "攻17"
    JIN_LAN_JIA_SHA_2 = 86, "锦斓袈裟2"
    BI_MO_QUAN = 87, "避魔圈"
    XIAN_NIANG_4 = 88, "仙酿4"

    GONG_18 = 89, "攻18"
    HUANG_JIN_SHENG_5 = 90, "幌金绳5"

    GONG_19 = 91, "攻19"
    HUANG_JIN_SHENG_6 = 92, "幌金绳6"

    GONG_20 = 93, "攻20"
    XIAO_BAI_LONG_3 = 94, "小白龙3"

    GONG_21 = 95, "攻21"
    DING_SHEN_SHU_3 = 96, "定身术3"

    GONG_22 = 97, "攻22"
    FENG_HUO_LEI_DIAN_3 = 98, "风火雷电3"

    GONG_23 = 99, "攻23"
    GONG_24 = 100, "攻24"

    GONG_25 = 101, "攻25"
    GONG_26 = 102, "攻26"
    XIAN_NIANG_5 = 103, "仙酿5"

    GONG_27 = 104, "攻27"
    GONG_28 = 105, "攻28"

    GONG_29 = 106, "攻29"
    GONG_30 = 107, "攻30"

    LIU_ER_HUO_XIN_1 = 108, "六耳祸心"
    HUO_YAN_JIN_JING_3 = 109, "火眼金睛3"

    LIU_ER_HUO_XIN_2 = 110, "六耳祸心"
    HUO_YAN_JIN_JING_4 = 111, "火眼金睛4"


Poker = with_meta(type, BasePoker)
Poker.CARDS_ENUM = Cards
