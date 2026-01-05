"""
通用枚举
注意事项：
1.修改枚举一定要检查proto是否同步最新枚举
2.含有ID类枚举，需与数据库同步
"""
from .base_enum import BaseEnum, BaseCode
from enum import unique, StrEnum


class Sex(BaseEnum):
    """ 性别 """
    DEFAULT = 0, "默认"
    MALE = 1, "男"
    FEMALE = 2, "女"


class Switch(BaseEnum):
    DEFAULT = 0, "默认"
    CLOSE = 1, "关闭"
    OPEN = 2, "打开"


@unique
class StaCode(BaseCode):
    """ 状态码 """
    DEFAULT = 0, 200, ''
    PASS = 1, 200, 'Finished.'
    TEND = -2, 200, 'Under maintenance.'
    FAIL = -3, 200, 'Failed.'
    '''公用请求失败，不确定响应状态请使用该项，并确保响应的文字描述'''
    ERR_ARG = -4, 200, 'Invalid params.'
    '''参数错误或无效'''
    ERR_AUTH = -5, 200, 'Invalid authorization.'
    ERR_SIGN = -6, 200, 'Invalid sign in.'
    FORBID = -7, 200, 'Forbidden'
    NON_PMS = -8, 200, 'Non enough permission.'
    EXPIRED = -9, 200, 'Request was expired.'
    REAPED = -10, 200, 'Request is repeated.'
    ERR_CONF = -11, 200, 'Error by configuration.'
    MULT_LOGIN = -12, 200, '您的账号已在其他设备登录，若不是本人操作，请注意账号安全！'
    NO_PLAYER_INFO = -13, 200, '没有玩家信息'
    EXTERNAL_ERR = -14, 200, '外部错误'  # 外部错误需要解data进一步确认
    TOKEN_ERR = -15, 200, 'TOKEN 错误'
    HAD_CERTIFICATED = -16, 200, '玩家已实名认证过了'
    REQ_FREQUENT = -17, 200, '操作频繁，请稍后再试'
    WITHOUT_MODIFY = -18, 200, '未修改任何数据'
    ORDER_NOT_FOUND = -19, 200, '无此订单'
    GOODS_NOT_FOUND = -20, 200, '无此物品'
    ALREADY_SIGN_IN = -21, 200, '已经签到过'
    ALREADY_RAFFLE = -22, 200, '已经抽奖过'
    CONDITION_NOT_MET = -23, 200, '未满足指定条件'
    EMAIL_NOT_FOUND = -24, 200, '无此邮件'
    DIAMOND_NOT_ENOUGH = -25, 200, '钻石不足'
    ACTIVITY_NOT_EXIST = -26, 200, '活动不存在'
    NO_CONFIGURATION = -27, 200, '无配置数据'
    NOT_WITHIN_VALID_PERIOD = -28, 200, '不在有效期内'
    NOT_IN_VALID_STATE = -29, 200, '不是有效状态'
    SESSION_KEY_EXPIRED = -30, 200, 'SESSION_KEY失效'

    # 以下主要为子游戏的状态码 之前的预留给web
    ALREADY_IN_SERVICE = -101, 200, '已经在某个服务（游戏）中'
    GOLD_NOT_ENOUGH = -102, 200, '金币不足'
    NOT_YOUR_TURN = -103, 200, '未轮到你'
    RULE_ERR = -104, 200, '规则错误'
    FLOW_ERR = -105, 200, '流程错误'
    ALREADY_DO = -106, 200, '已经操作过'
    RESOURCE_NOT_ENOUGH = -107, 200, '资源不足'


@unique
class JWType(BaseEnum):
    """
    jwt授权类型
    """
    MANAGER = 1, "system_manager", 7 * 86400
    '''管理账户'''
    AGENT = 2, "sales_agent", 30 * 86400
    '''分销用户'''
    USER = 3, "normal_user", 2 * 86400
    '''普通用户'''


@unique
class LoginWay(BaseEnum):
    GUEST = 1, "游客登录"
    WECHAT = 2, "微信登录"
    PHONE = 3, "手机号登录"
    EMAIL = 4, "邮箱登录"
    TOKEN = 5, "Token登录"
    ALIPAY = 6, "支付宝登录"
    DOUYIN = 7, "抖音登录"
    APPLE = 8, "AppleID登录"


# class PlayType(BaseEnum):
#     """ 玩法类型 """
#     CLASSICAL = 1, "经典玩法（通用玩法）"
#     OTHER = 2, "其它玩法（通用玩法）"


class GameType(BaseEnum):
    """ 游戏类型: 如休闲场、比赛场、话费场、... """
    DEFAULT = 0, "默认"
    LEISURE = 1, "休闲场"
    ROOM_CARD = 2, "房卡场"


@unique
class ServiceEnum(BaseEnum):
    """ 服务枚举号 """
    WS_HALL = 1, "lucky_ws", '大厅网关'
    WS_CHILD = 2, "lucky_wsc", '子网关'
    C_MATCHING = 3, "lucky_matching", '子服务-匹配服务'
    C_WORKERS = 4, "lucky_workers", '任务服务（异步调度任务（不停地消费）：服务端内部使用）'

    C_MONSTER = 5, "monster", GameType.LEISURE
    C_MONSTER_SEQUEL = 6, "monster_sequel", GameType.LEISURE
    C_MONSTER_MANY = 7, "monster_many", GameType.LEISURE
    C_NOTICE = 8, "notice", '通知服务号，不以服务启动，只作为消息通知服务号'
    C_CHAT = 9, "lucky_chat", '聊天服务'
    C_CLUB = 10, "lucky_club", '俱乐部服务'

    C_MAHJONG_FC = 11, "mahjong_fc", GameType.LEISURE
    C_COMPETITION = 12, "competition","比赛场匹配服务"

    C_MAHJONG_XY = 22, "mahjong_xy", GameType.ROOM_CARD
    C_MAHJONG_GY = 23, "mahjong_gy", GameType.ROOM_CARD
    C_MAHJONG_ZY = 24, "mahjong_zy", GameType.ROOM_CARD
    C_MAHJONG_BJ = 25, "mahjong_bj", GameType.ROOM_CARD
    C_MAHJONG_RH = 26, "mahjong_rh", GameType.ROOM_CARD
    C_MAHJONG_GY_MATCH = 27, "mahjong_gy_match", GameType.ROOM_CARD

    # 子游戏 -> 机器人，子服务游戏枚举[101 - 199]，接收游戏发送
    ROBOT_MONSTER = 101, "monster", '打妖怪机器人'
    ROBOT_MONSTER_SEQ = 102, "monster_seq", '神魔仙逆下篇机器人'
    ROBOT_WATER_FISH = 103, "water_fish", '暗水鱼机器人'
    ROBOT_LANDLORDS = 104, "landlords", '斗地主机器人'
    ROBOT_MAHJONG_FC = 105, "mahjong_fc_robot", '麻将发财捉鸡机器人'


LEISURE_GAME_LIST = [ServiceEnum.C_MONSTER_SEQUEL.val, ServiceEnum.C_MONSTER_MANY.val]


class Channel(StrEnum):
    C_SERVICES = "C_SERVICES"  # 子服务频道前缀
    CHANNEL_SYSTEM_MSG = "CHANNEL_SYSTEM_MSG"  # 系统消息
    C_SERVICES_COMMON = "C_SERVICES_COMMON" #公共广播消息


class CacheKey(StrEnum):
    IN_SERVICE = "IN_SERVICE"  # 在子服务（在哪个子服务）
    WS_ONLINE_INFO = "WS_ONLINE_INFO"  # ws在线信息
    PLAYER_GOLD = "PLAYER_GOLD" #休闲场玩家起始金币
    PLAYER_GAME_STA = "PLAYER_GAME_STA" #玩家游戏状态
    IN_MATCH = "IN_MATCH"  # 在比赛中


class DbKey(StrEnum):
    DEFAULT = "default"
    LOG = "log"


@unique
class TaskId(BaseEnum):
    """ 任务ID """
    # 每日任务（普通）
    RAFFLE_SIGN_IN = 1, "每日运势签到"
    SURPASS_MONSTER_6 = 2, "打赢6次妖怪"
    SURPASS_SHIFU_4 = 3, "收走4次师傅"
    COMPLETE_GAME_6 = 4, "完成任意对局6次"
    COMPLETE_GAME_12 = 5, "完成任意对局12次"
    COMPLETE_GAME_18 = 6, "完成任意对局18次"
    BUY_PACKAGE_1 = 7, "购买任意礼包1个"
    # 每日任务（分享）
    FIRST_SHARE_WX = 17, "每日首次分享（微信）", "allow_update"
    FIRST_SHARE_DY = 18, "每日首次分享（抖音）", "allow_update"
    FIRST_SHARE_AL = 19, "每日首次分享（阿里）", "allow_update"
    # 新手任务
    DOUYIN_REVISIT = 8, "抖音侧边栏复访", "allow_update"
    ROOKIE_PART_FIRST = 9, "西游上篇新手引导", "allow_update"
    ROOKIE_PART_SECOND_1 = 10, "西游下篇新手引导一", "allow_update"
    ROOKIE_PART_SECOND_2 = 16, "西游下篇新手引导二", "allow_update"
    ROOKIE_PART_MONOPOLY = 11, "漫漫西行路新手引导", "allow_update"
    ROOKIE_SEVEN_SIGN_IN = 15, "新人七日签到"
    # 大富翁任务
    MONOPOLY_ROLL_DICE_1 = 12, "掷1次骰子"
    MONOPOLY_COMPLETE_GAME_1 = 13, "完成任意对局1次"
    MONOPOLY_COMPLETE_GAME_3 = 14, "完成任意对局3次"


class LevelType(BaseEnum):
    LEVEL_0 = 0, "等级0"
    LEVEL_1 = 1, "等级1"
    LEVEL_2 = 2, "等级2"
    LEVEL_3 = 3, "等级3"
    LEVEL_4 = 4, "等级4"
    LEVEL_5 = 5, "等级5"
    LEVEL_6 = 6, "等级6"
    LEVEL_7 = 7, "等级7"
    LEVEL_8 = 8, "等级8"
    LEVEL_9 = 9, "等级9"
    LEVEL_10 = 10, "等级10"


@unique
class RankingDanLevel(BaseEnum):
    """排位大段位"""
    DAN_LEVEL_1 = 1, "凡夫俗子", 'season_awards_1'
    DAN_LEVEL_2 = 2, "修真行者", 'season_awards_2'
    DAN_LEVEL_3 = 3, "得道地仙", 'season_awards_3'
    DAN_LEVEL_4 = 4, "证道天仙", 'season_awards_4'
    DAN_LEVEL_5 = 5, "大罗天仙", 'season_awards_5'
    DAN_LEVEL_6 = 6, "无量天尊", 'season_awards_6'
    DAN_LEVEL_7 = 7, "齐天大圣", 'season_awards_7'


@unique
class MonsterCardType(BaseEnum):
    """打妖怪卡牌类型（和角色相关）"""
    DEFAULT = 0, "", ''
    SUN_WUKONG = 1, "孙悟空", ''
    ZHU_BAJIE = 2, "猪八戒", ''
    SHA_WUJING = 3, "沙悟净", ''
    TANG_SANZANG = 4, "唐三藏", ''


@unique
class RegionEnum(BaseEnum):
    """ 行政区域（省份） """
    DEFAULT = 0, "默认未划分"
    Beijing = 1, "北京"
    Tianjin = 2, "天津"
    Hebei = 3, "河北"
    Shanxi = 4, "山西"
    InnerMongolia = 5, "内蒙古"
    Liaoning = 6, "辽宁"
    Jilin = 7, "吉林"
    Heilongjiang = 8, "黑龙江"
    Shanghai = 9, "上海"
    Jiangsu = 10, "江苏"
    Zhejiang = 11, "浙江"
    Anhui = 12, "安徽"
    Fujian = 13, "福建"
    Jiangxi = 14, "江西"
    Shandong = 15, "山东"
    Henan = 16, "河南"
    Hubei = 17, "湖北"
    Hunan = 18, "湖南"
    Guangdong = 19, "广东"
    Guangxi = 20, "广西"
    Hainan = 21, "海南"
    Chongqing = 22, "重庆"
    Sichuan = 23, "四川"
    Guizhou = 24, "贵州"
    Yunnan = 25, "云南"
    Tibet = 26, "西藏"
    Shaanxi = 27, "陕西"
    Gansu = 28, "甘肃"
    Qinghai = 29, "青海"
    Ningxia = 30, "宁夏"
    Xinjiang = 31, "新疆"
    HongKong = 32, "香港"
    Macao = 33, "澳门"
    Taiwan = 34, "台湾"


REGION_ENUM_MAP = {
    "北京": RegionEnum.Beijing,
    "天津": RegionEnum.Tianjin,
    "河北": RegionEnum.Hebei,
    "山西": RegionEnum.Shanxi,
    "内蒙古": RegionEnum.InnerMongolia,
    "辽宁": RegionEnum.Liaoning,
    "吉林": RegionEnum.Jilin,
    "黑龙江": RegionEnum.Heilongjiang,
    "上海": RegionEnum.Shanghai,
    "江苏": RegionEnum.Jiangsu,
    "浙江": RegionEnum.Zhejiang,
    "安徽": RegionEnum.Anhui,
    "福建": RegionEnum.Fujian,
    "江西": RegionEnum.Jiangxi,
    "山东": RegionEnum.Shandong,
    "河南": RegionEnum.Henan,
    "湖北": RegionEnum.Hubei,
    "湖南": RegionEnum.Hunan,
    "广东": RegionEnum.Guangdong,
    "广西": RegionEnum.Guangxi,
    "海南": RegionEnum.Hainan,
    "重庆": RegionEnum.Chongqing,
    "四川": RegionEnum.Sichuan,
    "贵州": RegionEnum.Guizhou,
    "云南": RegionEnum.Yunnan,
    "西藏": RegionEnum.Tibet,
    "陕西": RegionEnum.Shaanxi,
    "甘肃": RegionEnum.Gansu,
    "青海": RegionEnum.Qinghai,
    "宁夏": RegionEnum.Ningxia,
    "新疆": RegionEnum.Xinjiang,
    "香港": RegionEnum.HongKong,
    "澳门": RegionEnum.Macao,
    "台湾": RegionEnum.Taiwan,
}


@unique
class UserSource(BaseEnum):
    """ 用户来源 """
    Own = 0, "自有"
    JuLiang = 1, "巨量广告"
    DataNexus = 2, "腾讯广告"


@unique
class OnlineStatus(BaseEnum):
    """在线状态"""
    IDLE = 1, "空闲"
    IN_GAME = 2, "游戏中"
    OFFLINE = 3, "离线"


@unique
class ChatChannel(BaseEnum):
    """聊天频道"""
    WORLD = 1, "世界频道"
    FRIENDS = 2, "好友频道"


@unique
class BanType(BaseEnum):
    """封禁类型（仅某个功能的封禁）"""
    DEFAULT = 0, "默认"
    WORLD_CHAT_BAN = 1, "世界频道禁言"
