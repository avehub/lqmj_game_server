# coding=utf-8
from enum import unique
from common.public.base_enum import BaseEnum


# 请在此处创建枚举对象

class AdminStatus(BaseEnum):
    FORBID = 0, '禁用'
    PENDING = 1, '待审核'
    ENABLE = 2, '启用/激活'


class ProxyPermission(BaseEnum):
    """ 管理员权限 """
    P1 = 1, '4级权限'
    P2 = 2, '3级权限'
    P3 = 3, '2级权限'
    P4 = 4, '1级权限'


class AssetEnum(BaseEnum):
    """ 资产枚举 """
    GOLD = 1, 'gold', '金币'
    DIAMOND = 2, 'diamond', '钻石'
    RELICS = 3, '法相舍利', ""
    DICE = 4, '骰子', ""
    FIVE_AGGREGATES = 5, '五蕴丹', ""
    RAND_MAGIC = 6, '随机法宝', ""


class UserGroup(BaseEnum):
    """ 用户群体 """
    USER_ALL = 1, "所有用户"
    USER_VIP = 2, "VIP用户"


@unique
class AnnouncementsStatus(BaseEnum):
    """ 公告状态 """
    DRAFT = 1, "草稿"
    CURRENT = 2, "当前"
    OUT_OF_TIME = 3, "过期"


@unique
class WeightEnum(BaseEnum):
    """ 权重枚举 """
    W1 = 1, "一级", "临时级别，如游戏中的"
    W2 = 2, "二级", "后台新增的公告最低是2级"
    W3 = 3, "三级", ""
    W4 = 4, "四级", ""
    W5 = 5, "五级", ""


class BackTaskSta(BaseEnum):
    """ 后台任务状态 """
    CANCELED = 0, "已取消"
    PENDING = 1, "待执行"
    FINISHED = 2, "已完成"


class MailSta(BaseEnum):
    """ 邮件状态 """
    OUT_OF_DATE = 0, "已失效"
    NORMAL = 1, "正常"
    CANCELED = 2, "已撤销"
