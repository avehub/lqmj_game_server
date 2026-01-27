"""
通用枚举
注意事项：
1.修改枚举一定要检查proto是否同步最新枚举
2.含有ID类枚举，需与数据库同步
"""
from enum import unique, StrEnum
from c_services.const.cs_enum_const import RedDotType
from common.proto.py_pb2.common import red_dots_opportunity
from common.public.base_enum import BaseEnum


class PlatForm(BaseEnum):
    """ 平台 """
    WEBPAGE = 1, "webpage", '网页'
    WECHAT_MP = 2, "wechat_mp", '微信公众号平台'
    NATIVE_APP = 3, "native_app", '原生app'
    WECHAT_MINI_GAME = 4, "minigame_wechat", '微信小游戏'
    ALI_MINI_GAME = 5, "minigame_alipay", '支付宝小游戏'
    DOUYIN_MINI_GAME = 6, "minigame_douyin", '抖音小游戏'
    ANDROID_APP = 7, "android", '安卓app'
    IOS_APP = 8, "ios", '苹果app'

    @classmethod
    def get_val_by_phrase(cls, phrase):
        for name, p_enum in cls._member_map_.items():
            if p_enum.phrase == phrase:
                return p_enum.val
        return 0


class OperatingSystem(StrEnum):
    """ 操作系统 """
    Android = "android"
    IOS = "ios"
    PC = "pc"
    VIVO = "vivo"


class PlayTemplate(BaseEnum):
    """ 游戏玩法类型 """
    MJ_XTMJ = 1, "玄筒麻将"
    MJ_JLXL = 2, "捡漏血流"
    MJ_MHXL = 3, "闷胡血流"
    MJ_GZZJ = 4, "贵州捉鸡"
    MJ_SDG = 5, "三丁拐"
    MJ_EDG = 6, "二丁拐"
    MJ_BJMJ = 7, "毕节麻将"
    PK_PDK = 8, "跑得快"


@unique
class AliGrantType(StrEnum):
    """阿里token授权方式"""
    GET_TOKEN = "authorization_code"  # 用 auth_code 换取授权令牌
    REF_TOKEN = "refresh_token"  # 用 refresh_token 刷新授权令牌


class PayMode(BaseEnum):
    """支付方式"""
    DEFAULT_MODE = 0, "免费领取"
    HUI_FU_PAY = 1, "汇付天下(App_Android、H5、微信小程序_IOS)"
    ALIPAY = 2, "支付宝支付(H5)"
    WECHAT_PAY = 3, "微信(微信小程序_Android)"
    VIVO_PAY = 4, "VIVO支付"
    APPLE_PAY = 5, "苹果支付"
    ALIPAY_APP = 6, "支付宝支付(App)"


class PayType(BaseEnum):
    """ 支付类型 """
    BY_FREE = 0, "免费领取"
    BY_GOLD = 1, "金币兑换"
    BY_DIAMOND = 2, "钻石兑换"
    BY_ROOM_CARD = 3, "房卡兑换"
    BY_YELLOW_DIAMOND = 4, "黄钻兑换"
    BY_RMB = 5, "人民币"
    BY_FUTURE_VALUE = 6, "福袋兑换"
    BY_WATCH_AD = 7, "看广告领取"


class CurrencyType(BaseEnum):
    """ 货币类型 """
    DEFAULT = 0, "免费"
    BY_GOLD = 1, "金币"
    BY_DIAMOND = 2, "钻石"
    BY_ROOM_CARD = 3, "房卡"
    BY_YELLOW_DIAMOND = 4, "黄钻"
    BY_RMB = 5, "人民币"
    BY_FUTURE_VALUE = 6, "福袋"


@unique
class OrderStatus(BaseEnum):
    """充值订单的状态"""
    WAIT_PAY = 0, "等待支付"
    FAIL = 1, "支付失败"
    CLOSED = 2, "订单关闭"
    REFUND = 3, "已退款"
    PAID = 99, "支付成功"


class GainStatus(BaseEnum):
    """领取状态"""
    DEFAULT = 0, "未发放"
    GAINED = 1, "已发放"
    RECEIVED = 99, "已领取"


@unique
class DeliverStatus(BaseEnum):
    """发货状态"""
    UNSHIPPED = 1, "未发货"
    SHIPPED = 2, "已发货"


@unique
class RandType(BaseEnum):
    """商品返利类型"""
    NONE = 0, "不返利"
    BACK_AND_DISCOUNT = 1, "反还金币并打折"


@unique
class LimitPeriod(BaseEnum):
    """限制周期"""
    NONE = 0, "不限制"
    DAILY = 1, "每日限制"
    WEEKLY = 2, "每周限制"
    MONTH = 3, "每月限制"
    QUARTERLY = 4, "每季限制"
    YEAR = 5, "每年限制"


@unique
class GoodsType(BaseEnum):
    """物品类型"""
    DEFAULT = 0, "默认"
    V_ASSET = 1, "虚拟资产（1、2级主要货币）"
    COSMETIC = 2, "游戏装扮"
    GAME_PROP = 3, "游戏道具"
    CARD_SKIN = 4, "卡牌皮肤"
    SKIN_SHARD = 5, "皮肤精魄"
    MAGIC = 6, "法宝"
    G_ASSET = 7, "游戏资产（附属、限时、特定货币）"


@unique
class CosmeticType(BaseEnum):
    """装扮类型"""
    DEFAULT = 0, "默认"
    AVATAR_FRAME_1 = 1, "头像框"
    CHAT_BUBBLE_2 = 2, "聊天气泡"
    CARD_TABLE_3 = 3, "牌桌类"
    CARD_BACK_4 = 4, "牌背类"


@unique
class GamePropType(BaseEnum):
    """游戏道具类型"""
    DEFAULT = 0, "默认"
    SHIELD_CARD = 1, "护盾卡"
    MULTIPLIER_CARD = 2, "加倍卡"
    PROTECT_SCORE_CARD = 3, "保分卡（固元丹）"
    BOOST_SCORE_CARD = 4, "速修卡（聚气丹）"
    TREASURE_BOX = 5, "宝盒"
    LIMITED_TIME_SKIN = 6, "限时法相"


@unique
class StoreType(BaseEnum):
    """商品类型"""
    DEFAULT = 0, "默认", ''
    DIAMOND = 1, "道具", ''
    GOLD = 2, "金币", 'gold'
    PROP = 3, "钻石", 'diamond'
    SKIN = 4, "房卡", 'room_card'
    S_MAGIC = 5, "法宝", ''
    S_PACKAGE = 6, "礼包", ''


@unique
class BossType(BaseEnum):
    """商店老板类型"""
    GAME_STORE = 0, "游戏商店"
    MONOPOLY_STORE = 1, "大富翁商店"


@unique
class BagType(BaseEnum):
    """背包类型"""
    DEFAULT = 0, "默认"
    B_PROP = 1, "道具"
    B_SKIN_SHARD = 2, "精魄"


@unique
class AddType(BaseEnum):
    """物品累加类型"""
    ADD_COUNT = 0, "按数量累加"
    ADD_TIME = 1, "按时效累加"


@unique
class PutType(BaseEnum):
    """存放类型"""
    U_WALLET = 0, "钱包"
    U_BAG = 1, "背包"
    U_COSMETIC = 2, "装扮"
    U_SKIN = 3, "皮肤"


@unique
class GotType(BaseEnum):
    """道具获得类型"""
    NOT_GOT = 0, "未获得"
    USED = 1, "正在使用"
    UNUSED = 2, "获得未使用"


@unique
class AwardType(BaseEnum):
    """参与类型（和动作有关）"""
    DEFAULT = 0, "默认"
    LOGIN = 1, "登录"
    SIGN_IN_RF = 2, "抽奖签到"
    ADVERT_RF = 3, "广告抽奖"
    SHARE = 4, "分享"
    ACTIVE = 5, "活跃"
    OPEN_TREASURE_BOX = 6, "开启宝盒"
    MONOPOLY_RAND_AWARD = 7, "大富翁随机奖励"
    TOP_UP = 8, "充值"


@unique
class ActivityType(BaseEnum):
    """活动类型"""
    DEFAULT = 0, "默认"
    MONTH_CARD = 1, "月卡"
    FIRST_CHARGE = 2, "首充"
    WEEK_CARD = 3, "周卡"
    LIFETIME_CARD = 4, "终生卡"
    WAR_ORDER = 5, "战令"
    PACKAGE = 6, "限时登录"
    SHARE = 7, "分享"
    INFINITE_PLAY = 8, "救济金"
    LUCK_SIGN_IN = 9, "抽奖签到"
    AUTHENTICATION = 10, "实名认证"
    REPLENISH_GIFT = 11, "金币补足礼包"
    REVIVE_GIFT = 12, "复活礼包"
    RETURN_GIFT = 13, "返还礼包"


@unique
class ActivitySta(BaseEnum):
    """活动参与状态"""
    ACT_NOT_JOIN = 0, "未参与"
    ACT_INCOMPLETE = 1, "未完结"
    ACT_COMPLETED = 99, "已完结"


@unique
class ActivityStatus(BaseEnum):
    """活动状态"""
    ACT_NOT_BEGUN = 0, "未开始"
    ACT_UNDER_WAY = 1, "进行中"
    ACT_FINISHED = -1, "已结束"


@unique
class ConditionType(BaseEnum):
    """活动参与条件类型"""
    DEFAULT = 0, "默认立即获得"
    LOGIN_TOTAL = 1, "累计登录"
    LOGIN_ONG = 2, "连续登录"
    DAY_REGULAR = 3, "每天固定数量"
    TIME_ONCE = 4, "有效期内一次"
    PULL_TOTAL = 5, "总领奖次数限制"


@unique
class AchieveType(BaseEnum):
    """获奖达成类型（和统计有关）"""
    DONE = 0, "完成"
    TOTAL = 1, "统计值"
    CONTINUE = 2, "连续值"
    DURATION = 3, "时长"


@unique
class QuickChatType(BaseEnum):
    """ 快捷聊天类型 """
    HU_DONG = 1, "互动"
    AUDIO_TEXT = 2, "音频文本"
    GIF = 3, "小龙人"


@unique
class InteractPropType(BaseEnum):
    """ 互动道具类型 """
    GOOD = 1, "好"
    BAD = 2, "坏"


@unique
class MatchType(BaseEnum):
    """比赛类型"""
    DFT = 0, "默认"
    XXC = 1, "休闲场"
    PWS = 2, "排位赛"


@unique
class LanguageType(BaseEnum):
    """语言类型"""
    MANDARIN = 0, "普通话"
    XING_YI = 1, "兴义话"
    NAN_NING = 2, "南宁话"


@unique
class MailSender(BaseEnum):
    """ 邮件发送者 """
    SYSTEM = 1, "system"


@unique
class MailSta(BaseEnum):
    """邮件状态"""
    DELETED = 1, "已删除"
    UNREAD = 2, "未读"
    READ = 3, "已读 邮件包含奖励时，已读状态标记为领奖或未领奖状态"


@unique
class MailType(BaseEnum):
    """邮件类型"""
    DEFAULT = 0, "默认"
    SYS = 1, "系统邮件"
    SEASON_SETTLE = 2, "赛季结算邮件"


@unique
class MailOpType(BaseEnum):
    """邮件操作类型"""
    READ = 1, "标记已读"
    PULL = 2, "领取奖励"
    DEL = 3, "删除"


@unique
class PullSta(BaseEnum):
    """领奖状态"""
    UN_PULL = 1, "未领取"
    PULLED = 2, "已领取"


@unique
class BagSta(BaseEnum):
    """背包状态"""
    B_DEFAULT = 0, "默认有效"
    B_DELETED = 1, "已删除"


@unique
class SignInSta(BaseEnum):
    """签到状态"""
    UN_SIGN = 1, "未签到"
    SIGNED = 2, "已签到"
    BACK_SIGNED = 3, "已补签"


@unique
class TaskType(BaseEnum):
    """ 任务类型 """
    DAILY_TASK = 1, "每日任务"
    ROOKIE_TASK = 2, "新手任务"
    WARFARE_TASK = 3, "战令任务"
    MONOPOLY_TASK = 4, "大富翁任务"


@unique
class CompleteSta(BaseEnum):
    """条件达成领取状态"""
    INCOMPLETE = 1, "未达成"
    COMPLETED = 2, "已达成"
    CLAIMED = 3, "奖励已领取"


@unique
class JumpTarget(BaseEnum):
    """跳转目标"""
    DEFAULT = 0, "默认"
    GO_SIGN_IN = 1, "去签到"
    GO_LEISURE_GAME = 2, "去休闲场"
    GO_STORE = 3, "去商店"
    GO_FIRST_CHARGE = 4, "去首充"
    GO_DOUYIN_REVISIT = 5, "去抖音侧边栏复访"
    GO_OPEN_BOX = 6, "去开盒子"
    GO_MONOPOLY = 7, "去大富翁"
    GO_RANKING = 8, "去排位赛"
    GO_CARD_SKIN = 9, "去法相"
    GO_SIGN_IN_SEVEN = 10, "去七日签到"
    GO_VIP = 11, "去VIP"
    GO_MONOPOLY_STORE = 12, "去大富翁商店"
    GO_SHARE = 13, "去分享"
    GO_NOTHING = 99, "获得但目标失效"  # 例如：跳转到排位赛，但是赛季结束了


@unique
class JumpType(BaseEnum):
    """跳转类型"""
    GO_FOREVER = 0, "永不过时"
    GO_LIMITED = 1, "活动限时"
    GO_SEASON = 2, "赛季限时"


@unique
class GiftType(BaseEnum):
    REVENGE = 1, "复仇礼包"
    REFUND = 2, "返还礼包"
    GOLD_NOT_ENOUGH = 3, "豆子不足"


@unique
class SafeBoxOpType(BaseEnum):
    """保险箱操作类型"""
    SAVE = 1, "存入"
    DRAW = 2, "取出"
    SET_COMPLEMENT = 3, "设置自动补足"
    USE_COMPLEMENT = 4, "领取自动补足"


@unique
class HeldSta(BaseEnum):
    """持有状态"""
    NOT_HELD = 0, "未持有"
    HELD = 1, "正常持有"
    MAX_LEVEL = 2, "持有并满级"
    CAN_MAX_LEVEL = 3, "持有并可升到满级"
    LIMITED_HELD = 4, "限时持有"


@unique
class CellType(BaseEnum):
    """格子类型"""
    EMPTY_CELL = 0, "空格子"
    START_POINT = 1, "起点格"
    SOLID_AWARD_CELL = 2, "固定奖励格"
    RAND_AWARD_CELL = 3, "随机奖励格"
    SPECIAL_EVENT_CELL = 4, "特殊事件格"
    COMMON_EVENT_CELL = 5, "通用事件格"


@unique
class EventType(BaseEnum):
    """事件类型"""
    COMMON_EVENT = 0, "通用事件"
    SPECIAL_EVENT = 1, "特殊事件"


@unique
class EndingType(BaseEnum):
    """事件结局类型"""
    DEFAULT = 0, "默认"
    GOOD = 1, "好"
    NEUTRAL = 2, "一般"
    BAD = 3, "坏"


################ 含有ID类枚举，需与数据库同步 ################
@unique
class ActivityItem(BaseEnum):
    """活动升级key"""
    FIRST_CHARGE = 3001, "首充"
    WEEK_CARD_1 = 3002, "黄金周卡"
    WEEK_CARD_2 = 3003, "铂金周卡"
    LIFETIME_CARD_1 = 3004, "超值终生卡"
    LIFETIME_CARD_2 = 3005, "至尊终生卡"
    LIFETIME_CARD_3 = 3006, "终生卡大礼包"


@unique
class GoodsItem(BaseEnum):
    """物品统计key"""
    DIAMOND = 1001, "钻石", 'diamond'
    GOLD = 1002, "金币", 'gold'
    RELICS = 1013, "法相舍利", ''
    DICE = 1014, "骰子", ''
    FIVE_AGGREGATES = 1018, "五蕴丹", ''
    RAND_MAGIC = 1019, "随机法宝", ''


class GoodsSku(StrEnum):
    """特定商品SKU"""
    SKU_FIRST = "NOMYLPAA"  #首充
    SKU_FIRST_MINI = "NOMYLPAB"  #微信小游戏首充
    SKU_FREE = "XXOLQQTL"   #免费
    SKU_REPLENISH_1 = "OCNMZOAS"    #金币补足初级场礼包
    SKU_REPLENISH_2 = "AAIAHTGS"    #金币补足中级场礼包
    SKU_REPLENISH_3 = "IGBEZPJS"    #金币补足高级场礼包
    SKU_REPLENISH_4 = "YPKOBVLR"    #金币补足王者场礼包
    SKU_REVIVE_1 = "UJFPSNTT"   #复活初级场礼包
    SKU_REVIVE_2 = "LUYTHXES"   #复活中级场礼包
    SKU_REVIVE_3 = "YSYNBZFC"   #复活高级场礼包
    SKU_REVIVE_4 = "LGYUEJAX"   #复活王者场礼包
    SKU_RETURN_1 = "DPUWCOBL"   #返还初级场礼包
    SKU_RETURN_2 = "NSPEJTCZ"   #返还中级场礼包
    SKU_RETURN_3 = "MWSZUWJK"   #返还高级场礼包
    SKU_RETURN_4 = "TIAOJRKA"   #返还王者场礼包
    # 赛事农产品
    SKU_TOURNAMENT = "WCRVIABC"


@unique
class StoreItem(BaseEnum):
    """商品统计key"""
    FREE_GOLD = 2000, "免费金币"
    FREE_DICE = 2100, "免费骰子"


@unique
class AdSlotItem(BaseEnum):
    """广告奖励位，对应award_id或store_id"""
    DY_RAFFLE_LUCK = 4000, "每日看广告运势抽奖", 't_raffle_luck'
    DY_AWARD = 4001, "每日看广告获得金币", 't_award'
    DY_RELIEF = 4002, "每日看广告救济翻倍", 't_relief'
    DY_DICE = 2127, "看广告免费获得骰子", 't_dice'
    DY_GOLD_NOT_ENOUGH_FIRST = 3015, "看广告领取金币不足礼包（上篇）", 't_gold_not_enough_first'
    DY_GOLD_NOT_ENOUGH_SECOND = 3023, "看广告领取金币不足礼包（下篇）", 't_gold_not_enough_second'
    DY_SIGN_WK = 4003, "看广告每周七日签到", 't_sign_in_wk'


@unique
class MagicType(BaseEnum):
    """能使用的法宝类型"""
    DEFAULT = 0, "默认"
    WIND_STILLING_PEARL = 1015, "定风珠"
    THOUSAND_FORMS_DICE = 1016, "万象骰子"
    SOMERSAULT_CLOUD = 1017, "筋斗云"


################ 排位相关 ################
@unique
class SeasonStatus(BaseEnum):
    OUT_OF_TIME = 0, "过期的"
    ACTIVE_SEASON = 1, "正在进行中的"
    OFF_SEASON = 2, "休赛期"
    DAN_RESET = 3, "段位重置期间（关榜期）"
    NEXT_SEASON = 4, "即将下一个赛季"


@unique
class LvDefendType(BaseEnum):
    """ 段位保护类型 """
    NO_DEFEND = 0, "不保护"
    DEFEND_FLOOR = 1, "保护下限"
    DEFEND_WHOLE = 2, "完全保护"


RED_DOTS_OPPORTUNITY_MAP = {
    red_dots_opportunity.GAME_RETURN_HALL: [RedDotType.RD_MAILS, RedDotType.RD_CLUB_APPLY, RedDotType.RD_LIMIT_LOGIN, RedDotType.RD_RELIEF],
    red_dots_opportunity.RECONNECT: [RedDotType.RD_MAILS, RedDotType.RD_CLUB_APPLY, RedDotType.RD_LIMIT_LOGIN, RedDotType.RD_RELIEF],
}


################ 资产流水原因短语 ################
@unique
class ReasonCostGold(BaseEnum):
    """ 金币流水原因 """
    QUICK_CHAT = 1, "游戏内快捷聊天"
    TEST_ADD = 2, "测试修改资产"
    TICKETS_LEISURE = 3, "休闲场门票"
    CHECK_OUT_MONSTER_FIRST = 4, "打妖怪上结算"
    CHECK_OUT_MONSTER_SECOND = 5, "打妖怪下结算"
    CHECK_OUT_LANDLORDS = 6, "斗地主结算"
    DIAMOND_EX_GOLD = 7, "钻石兑换金币"
    RELIEF_GET = 8, "救济金领取"
    STORE_SHOPPING_GIFT = 9, "商店购物赠品"
    ACT_PACKAGE = 10, "游戏礼包"
    ACT_FIRST_CHARGE = 11, "首充礼包"
    ACT_WEEK_CARD = 12, "开通周卡"
    ACT_LIFETIME_CARD = 13, "开通终生卡"
    STORE_FREE_GOLD = 14, "商店免费金币"
    WEEK_CARD_AWARDS = 15, "周卡日奖"
    LIFETIME_CARD_AWARDS = 16, "终生卡日奖"
    VIP_LEVEL_AWARDS = 17, "VIP等级奖"
    VIP_DAILY_AWARDS = 18, "VIP日奖"
    ROOKIE_TASK = 19, "新手引导任务"
    GOLD_EXCHANGE = 20, "商店金币兑换"
    DAILY_TASK = 21, "每日任务完成"
    DAILY_ACTIVE = 22, "每日活跃达成"
    AD_FREE_GOLD = 23, "每日看广告获得金币"
    RAFFLE_LUCK = 24, "每日运势抽奖"
    SIGN_IN_TOTAL = 25, "累计签到天数达成"
    MAILS_GIFT = 26, "邮件赠品"
    SAFE_BOX_SAVE = 27, "保险箱存"
    SAFE_BOX_DRAW = 28, "保险箱取"
    SAFE_BOX_COMPLEMENT = 29, "保险箱补足"
    RANKING_LEVEL_AWARDS = 30, "排位段位奖"
    RANKING_SEASON_AWARDS = 31, "排位赛季奖"
    OPEN_TREASURE_BOX = 32, "开启宝盒"
    SKIN_EQUIP_EFFECT = 33, "皮肤装备打出效果"
    MONOPOLY_AWARDS = 34, "玩大富翁奖励"
    CONVERT_AWARDS = 35, "兑换/充值礼包"
    SIGN_IN_AWARDS = 36, "签到立得奖励"
    CHECK_OUT_MAHJONG = 37, "麻将结算"
    ACTIVITY_GIFT = 38, "活动礼包"
    ACTIVITY_PACKAGE = 39, "限时登录"
    ACTIVITY_SHARE = 40, "分享奖励"
    CLUB_ROOM_CARD = 41, "茶馆房卡变更"
    CLUB_YELLOW_DIAMOND = 42, "茶馆黄钻变更"
    CLUB_ROOM_CARD_TICKETS = 43, "游戏房卡门票"
    CLUB_YELLOW_DIAMOND_TICKETS = 44, "游戏黄钻门票"
    ACTIVITY_RETURN_GOLD = 45, "活动返还金币"
    WECHAT_STORE_SHOPPING = 46, "微信商店购物"
    PREHEAT_COMPETITION_AWARDS = 47, "预热赛奖励"


    # 100 - 200留给管理员使用
    ADMIN_ALTER_USER = 100, "修改用户资产"


@unique
class ReasonCostDiamond(BaseEnum):
    """ 钻石流水原因 """
    DIAMOND_EXCHANGE = 1, "商店钻石兑换"
    STORE_BUY_DIAMOND = 2, "商店钻石礼包"
    STORE_SHOPPING_GIFT = 3, "商店购物赠品"
    ACT_FIRST_CHARGE = 4, "首充礼包"
    ACT_WEEK_CARD = 5, "开通周卡"
    ACT_LIFETIME_CARD = 6, "开通终生卡"
    LIFETIME_CARD_AWARDS = 7, "终生卡日奖"
    VIP_LEVEL_AWARDS = 8, "VIP等级奖"
    MAILS_GIFT = 9, "邮件赠品"
    RANKING_LEVEL_AWARDS = 10, "排位段位奖"
    RANKING_SEASON_AWARDS = 11, "排位赛季奖"


@unique
class AdEventType(BaseEnum):
    """ 广告事件类型 """
    AD_ACTIVE = 0, "active", '激活'
    AD_ACTIVE_REGISTER = 1, "active_register", '注册'
    AD_ACTIVE_PAY = 2, "active_pay", '付费'
    AD_ACTIVE_AD = 3, "active_ad", '看完广告'
    AD_FIRST_PAY = 4, "", '首次付费'
    AD_CLICK_AD = 5, "click_ad", '点击广告'


AD_EVENT_FIELD_MAP = {
    AdEventType.AD_ACTIVE: 'active_times',  # 激活次数
    AdEventType.AD_ACTIVE_REGISTER: 'register_times',  # 注册次数
    AdEventType.AD_ACTIVE_AD: 'ads_times',  # 看广告次数
    AdEventType.AD_ACTIVE_PAY: 'pay_times',  # 付费次数
    AdEventType.AD_FIRST_PAY: 'first_pay_times',  # 首次付费次数
    AdEventType.AD_CLICK_AD: '',  # 点击广告暂不统计
}


@unique
class EventTracking(BaseEnum):
    """ 埋点/事件追踪 """
    AFTER_REGISTER = 0, "注册成功"
    AFTER_ROOKIE_TASK_FIRST = 1, "上篇新手引导完成"
    AFTER_ROOKIE_TASK_SECOND_1 = 2, "下篇新手引导一完成"
    AFTER_ROOKIE_TASK_SECOND_2 = 3, "下篇新手引导二完成"
    AFTER_ROOKIE_TASK_MONOPOLY = 4, "西行路新手引导完成"
    AFTER_FIRST_GAME = 5, "首次对局完成"
    AFTER_FIRST_PAY = 6, "首次付费"
    AFTER_GAME = 7, "对局完成"
    AFTER_PAY = 8, "付费成功"


QUERY_EVENT = (
    EventTracking.AFTER_REGISTER.val,
    EventTracking.AFTER_ROOKIE_TASK_FIRST.val,
    EventTracking.AFTER_ROOKIE_TASK_SECOND_1.val,
    EventTracking.AFTER_ROOKIE_TASK_SECOND_2.val,
    EventTracking.AFTER_ROOKIE_TASK_MONOPOLY.val,
    EventTracking.AFTER_FIRST_GAME.val,
    EventTracking.AFTER_FIRST_PAY.val,
)


@unique
class FriendshipSta(BaseEnum):
    """友情状态"""
    PENDING = 0, '追求中（待处理）'
    ACCEPTED = 1, '答应了（已接受）'
    REJECTED = 2, '没答应（已拒绝）'
    BLOCKED = 3, '拉黑咯（已屏蔽）'
    UNFRIENDED = 4, '分手了（已解除）'


@unique
class FriendOpType(BaseEnum):
    """好友操作类型"""
    REQUEST = 0, '发起好友申请'
    ACCEPT = 1, '同意好友申请'
    REJECT = 2, '拒绝好友申请'
    BLOCK = 3, '屏蔽好友'
    UNBLOCK = 4, '取消屏蔽好友'
    REMOVE = 5, '删除好友'


class ChatConst:
    """ 聊天相关常量 """
    WORLD_MAX_VAL = 50  # 世界最大消息长度
    COOLDOWN_TIME = 5  # 冷却时间设置为5秒

class CompetitionType(BaseEnum):
    """ 赛事类型 """
    DEFAULT = 0, "默认"
    POINT = 1, "积分制"

class PriceType(BaseEnum):
    """ 支付类型 """
    BY_FREE = 0, "免费"
    BY_DIAMOND = 1, "钻石"
    BY_GOLD = 2, "金币"
    BY_POINT = 3, "积分"

class CompetitionStatus(BaseEnum):
    """ 赛事状态 """
    DEFAULT = 0, "默认"
    PLAYING = 1, "进行中"
    CLOSED = 2, "已结束"
