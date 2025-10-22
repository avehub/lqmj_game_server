from common.public.base_enum import BaseEnum
from enum import StrEnum


class MatchingMode(BaseEnum):
    """ 匹配模式 """
    COMMON = 1, "普通匹配"
    RANKING = 2, "修为匹配"
    RAND_TIME = 3, "随机时间"


class ExtensionType(StrEnum):
    """ 扩展类型 """
    E1 = "first_expend_time"
    E2 = "second_expend_time"
    E3 = "force_start_time"
