from enum import unique

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


@unique
class YuYinUniqueTurn1(BaseEnum):
    """
    游戏第一轮
    该枚举定义打妖怪每种场景下的语音内容
    师傅用10用S来替代
    """
    # 第一轮的各种情况
    CASE_1 = 1, "JQK385S"
    CASE_2 = 2, "JQK38S"
    CASE_3 = 3, "JQK35S"
    CASE_4 = 4, "JQK3S"
    CASE_5 = 5, "JQK85S"
    CASE_6 = 6, "JQK8S"
    CASE_7 = 7, "JQK5S"
    CASE_8 = 8, "JQ385S"
    CASE_9 = 9, "JQ38S"
    CASE_10 = 10, "JQ35S"
    CASE_11 = 11, "JQ3S"
    CASE_12 = 12, "JQ85S"
    CASE_13 = 13, "JQ8S"
    CASE_14 = 14, "JQ5S"
    CASE_15 = 15, "JK385S"
    CASE_16 = 16, "JK38S"
    CASE_17 = 17, "JK35S"
    CASE_18 = 18, "JK3S"
    CASE_19 = 19, "JK85S"
    CASE_20 = 20, "JK8S"
    CASE_21 = 21, "JK5S"
    CASE_22 = 22, "J385S"
    CASE_23 = 23, "J38S"
    CASE_24 = 24, "J35S"
    CASE_25 = 25, "J3S"
    CASE_26 = 26, "J85S"
    CASE_27 = 27, "J8S"
    CASE_28 = 28, "J5S"


@unique
class YuYinUniqueTurn2(BaseEnum):
    """
    游戏第二轮
    该枚举定义打妖怪每种场景下的语音内容
    师傅用10用S来替代
    """
    CASE_1 = 29, "JQK"
    CASE_2 = 30, "QK"
    CASE_3 = 31, "JK"
    CASE_4 = 32, "K"


@unique
class WuKongSkillMovie(BaseEnum):
    """
    徒弟技能动画enum
    按照师傅出现以后，徒弟出牌数量根据C-> B -> A的顺序播放
    """
    A_WU_KONG = 1, "棍搅乾坤"
    B_WU_KONG = 2, "法天象地"
    C_WU_KONG = 3, "神针撼海"


@unique
class BaJieSkillMovie(BaseEnum):
    # 八戒
    A_BA_JIE = 1, "天蓬真身"
    B_BA_JIE = 2, "天罡三十六变"
    C_BA_JIE = 3, "九尺神威"


@unique
class ShaSengSkillMovie(BaseEnum):
    # 沙僧
    A_SHA_SENG = 1, "弱水流沙"
    B_SHA_SENG = 2, "禅杖三十六变"
    C_SHA_SENG = 3, "九命念珠"


@unique
class TangMonkSkillMovie(BaseEnum):
    """ 唐僧技能 """
    A_TANG_MONK = 1, "打坐念经"


@unique
class SkillMovie(BaseEnum):
    """ 技能动画 """
    # 悟空
    A_WU_KONG = 1, "棍搅乾坤"
    B_WU_KONG = 2, "神针撼海"
    C_WU_KONG = 3, "法天象地"

    # 八戒
    A_BA_JIE = 4, "九尺神威"
    B_BA_JIE = 5, "天罡三十六变"
    C_BA_JIE = 6, "天蓬真身"

    # 沙僧
    A_SHA_SENG = 7, "弱水流沙"
    B_SHA_SENG = 8, "禅杖三十六变"
    C_SHA_SENG = 9, "九命念珠"

    # 唐僧
    A_TANG_MONK = 10, "禅心驭马"


# skin_id: 技能特效
SKIN_SKILL_MOVIE_MAP = {
    5001: SkillMovie.A_WU_KONG,
    5002: SkillMovie.B_WU_KONG,
    5003: SkillMovie.C_WU_KONG,
    5005: SkillMovie.A_BA_JIE,
    5006: SkillMovie.B_BA_JIE,
    5007: SkillMovie.C_BA_JIE,
    5009: SkillMovie.A_SHA_SENG,
    5010: SkillMovie.B_SHA_SENG,
    5011: SkillMovie.C_SHA_SENG,
    5013: SkillMovie.A_TANG_MONK,
}


@unique
class InteractType(BaseEnum):
    """ 互动类型 """
    AFTER_PICK_CARDS_SELF = 1, "自己捡牌后"
    AFTER_PICK_CARDS_OTHER = 2, "其他人捡牌后"
    AFTER_RECV_GOOD_PROP = 3, "收到一个好道具"
    AFTER_RECV_BAD_PROP = 4, "收到一个坏道具"
    AFTER_PLAYED_BUDDHA_BEN_BO_ER_BA_COMB = 5, "上家打出佛祖奔波儿霸霸波儿奔组合"


INITIATIVE_INTERACT = {
    InteractType.AFTER_PICK_CARDS_SELF,
    InteractType.AFTER_PICK_CARDS_OTHER,
    InteractType.AFTER_PLAYED_BUDDHA_BEN_BO_ER_BA_COMB,
}