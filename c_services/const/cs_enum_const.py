from common.public.base_enum import BaseEnum
from enum import unique


@unique
class RoomStatus(BaseEnum):
    """ 桌子状态 """
    T_IDLE = 0, "空闲中"
    T_READY = 1, "准备中"
    T_PLAYING = 2, "游戏中"
    T_RECHARGE_ING = 3, "充值中"
    T_CHECK_OUT = 4, "结算中"
    T_DISMISS = 5, "解散中"
    T_CLOSED = 6, "已关闭"


@unique
class RoomType(BaseEnum):
    """ 房间类型 """
    COMMON = 1, "普通房间（通过匹配）"
    SELF_BUILD = 2, "自建房间"


@unique
class CmdMatch(BaseEnum):
    """ 匹配相关命令 """
    MATCH_LEISURE = 1, "休闲场匹配"
    MATCH_SUC = 2, "匹配成功（主要通知客户端）"
    QUIT_MATCH = 3, "退出匹配"
    REFRESH_CONF_LEISURE = 4, "刷新休闲场配置"
    ADD_FORBID_SERVICE = 5, "增加禁止匹配服务"
    RM_FORBID_SERVICE = 6, "移除禁止匹配服务"


@unique
class CmdWs(BaseEnum):
    """ 网关接收命令 """
    SUCCEED = 0, "成功"
    BEAT = 1, "心跳"
    REJECT = 2, "拒绝弹回"
    ENTER_LEISURE = 3, "进入休闲场"
    OFFLINE = 4, "掉线（服务端内部使用，通知子服务玩家离线）"
    MULT_PROCESS_LOGIN = 5, "多进程登录（广播所有ws服务）"
    BAN_PLAYER = 6, "封禁玩家（广播所有ws服务）"


@unique
class CallCheck(BaseEnum):
    CLIENT = 1, "客户端"
    INNER = 2, "内部调用"


@unique
class CmdClub(BaseEnum):
    ENTER_CLUB = 1, "进入茶馆", CallCheck.INNER.val
    QUIT_CLUB = 2, "退出茶馆", CallCheck.INNER.val
    ROOM_INFO_CHANGE = 3, "茶馆房间改变", CallCheck.INNER.val
    CLUB_OWNER_DISMISS = 4, "茶馆房主解散"
    PLAYER_READY_EXCEPT_OWNER = 5, "所有玩家准备，除了房主", CallCheck.INNER.val
    LEAVE_CLUB = 6, "离开茶馆"
    CLUB_NOTICE = 7,"茶馆公告通知", CallCheck.INNER.val
    UPDATE_ROOM_SET = 8,"茶馆设置更新"
    CHECK_GAME_STATUS = 9, "检查是否在游戏中"
    JOIN_NEW_GAME = 10, "加入新游戏房间"
    JOIN_NEW_GAME_SUC = 11, "加入新游戏房间成功",CallCheck.INNER.val

@unique
class CmdFanOut(BaseEnum):
    LOST_CONNECT = 201, "离线通知公共频道"


@unique
class ClubMsgType(BaseEnum):
    CREATE_ROOM = 1, "创建茶馆游戏房间"
    ENTER_ROOM = 2, "进入茶馆游戏房间"
    QUIT_ROOM = 3, "退出茶馆游戏房间"
    DISMISS_ROOM = 4, "解散茶馆游戏房间"
    UPDATE_ROOM = 5, "更新茶馆游戏房间"

@unique
class CmdCompetition(BaseEnum):
    MATCH_COMPETITION = 1, "加入比赛"
    QUIT_COMPETITION = 2, "退出比赛"
    START_COMPETITION = 3, "开始比赛"
    ROOM_FINISH = 4, "房间结束", CallCheck.INNER.val
    MATCH_FINISH = 5, "比赛结束"
    MATCH_BY_INNER = 6, "加入比赛（内部调用）", CallCheck.INNER.val
    BACK_COMPETITION = 7, "返回比赛"
    COMPETITION_INFO = 8, "比赛信息"
    UPDATE_SCORE = 9, "更新比赛积分", CallCheck.INNER.val


@unique
class CmdRoom(BaseEnum):
    """ 房间命令 """
    NEW_MATCH = 1, "新匹配（该命令号服务内部使用）", CallCheck.INNER.val
    LOST_CONNECT = 2, "掉线（该命令号服务内部使用, 通知子服务玩家掉线）"
    ENTER_ROOM = 3, "进入房间"
    ROOM_INFO = 4, "房间信息"
    PLAYER_INFO = 5, "玩家信息"
    QUIT_ROOM = 6, "离开房间"
    READY = 7, "准备/取消准备"
    TRUSTEE = 8, "托管"
    ROUND_START = 9, "游戏开始"
    DEALER_CARDS = 10, "发牌"
    PLAY_CARDS = 11, "打牌"
    PICK_CARDS = 12, "捡/收牌"
    GIVE_UP = 13, "认输"
    TURN_TO = 14, "轮到"
    TURN_END = 15, "一圈结束"
    GO_BROKE = 16, "破产"
    GOLD_NOT_ENOUGH = 17, "金币不足"
    RECHARGE = 18, "充值"
    BROADCAST_CHAT = 19, "广播聊天"
    FORCE_DISMISS = 20, "强制解散", "该命令号服务内部使用(应对流程卡住的桌子)"
    ROUND_OVER = 21, "一局结束"
    GAME_OVER = 22, "游戏结束"
    DEDUCT_TICKETS = 23, "扣门票"
    REFRESH_CONF_LEISURE = 24, "刷新休闲场配置(服务内部使用，当休闲场配置发生变化时通知)", CallCheck.INNER.val
    SAFE_BOX_AUTO_COMPLEMENT = 25, "保险箱自动补足"
    SET_CARDS_IN_DEBUG = 26, "设牌"
    QUERY_PLAYER_IN_SERVICE = 27, "查询用户是否在游戏中（服务端内部使用rpc）", CallCheck.INNER.val
    DO_USER_ABILITY = 28, "使用能力"
    COMPLEMENT_CARDS = 29, "补牌"
    RECHARGE_ING = 30, "充值中回调"

    CONFIRM_DEALER = 40, "确定庄家", "水鱼|斗地主"
    SA_PU = 41, "撒扑", "水鱼"
    START_BET = 42, "开始下注", "水鱼"
    DO_BET = 43, "玩家下注", "水鱼"
    DEALER_OPERATE = 44, "庄操作", "水鱼"
    FARMER_OPERATE = 45, "闲操作", "水鱼"

    START_BID = 46, "开始叫分", "斗地主"
    TURN_BID = 47, "轮到叫分", "斗地主"
    DO_BID = 48, "Do 叫分", "斗地主"
    START_REDOUBLE = 49, "开始加倍", "斗地主（铲？）"
    TURN_REDOUBLE = 50, "轮到加倍"
    DO_REDOUBLE = 51, "Do 加倍", "斗地主（铲？）"
    START_RE_REDOUBLE = 52, "开始加加倍", "斗地主（反铲）"
    TURN_RE_REDOUBLE = 53, "轮到加加倍", "斗地主（反铲）"
    DO_RE_REDOUBLE = 54, "Do 加加倍", "斗地主（反铲）"

    # 麻将
    PLAYER_PASS = 60, "过", "麻将"
    PLAYER_PENG = 61, "碰", "麻将"
    PLAYER_GANG = 62, "杠", "麻将"
    PLAYER_HU = 63, "胡", "麻将"
    PLAYER_MEN = 64, "闷", "麻将"
    PLAYER_JIAN = 65, "捡", "麻将"
    PLAYER_SHANG_GA = 66, "估卖", "麻将(卖分)"
    GAME_START = 67, "游戏开始", "麻将"
    START_EXCHANGE_CARDS = 68, "开始换牌", "麻将"
    PLAYER_EXCHANGE_CARDS = 69, "玩家换牌", "麻将"
    START_DING_QUE = 70, "开始定缺", "麻将"
    PUBLIC_OPERATES = 71, "公共操作", "麻将"
    PLAYER_TIAN_TING = 72, "天听", "麻将"
    PLAYER_SHANG_GA_BEGIN = 73, "开始估卖", "麻将"
    HU_AFTER_CARDS_INFO = 74, "通知所有玩家手牌信息", "麻将"
    PLAYER_MEN_SUC = 75, "闷成功", "麻将"
    PLAYER_JIAN_SUC = 76, "捡成功", "麻将"
    PLAYER_MO_PAI = 77, "摸牌", "麻将"
    AFTER_GANG_MO_CARD = 78, "杠后摸牌", "麻将"
    LIU_JU_NOTIFY = 79, "流局通知", "麻将"
    CONFIRM_CHONG_FENG_JI = 80, "冲锋鸡", "麻将"
    ZHA_HU = 91, "炸胡", "麻将"
    ZHA_MEN = 92, "炸闷", "麻将"
    REQ_DISMISS = 93, "请求解散房间", "麻将"
    NOTIFY_POSITION = 94, "开局通知定位", "麻将"
    PLAYER_DING_QUE = 95, "玩家定缺", "麻将"
    ROOM_DISMISS = 96, "房间解散", "麻将"
    CLUB_OWNER_DISMISS = 97, "茶馆房主解散", CallCheck.INNER.val
    FAN_JI_SCORE = 98, "翻鸡分数", "麻将"
    ROBOT_CAL_ACTION = 99, "机器人出牌计算", CallCheck.INNER.val
    ROBOT_CAL_PENG = 100, "机器人碰计算", CallCheck.INNER.val
    ROBOT_CAL_GANG = 101, "机器人杠计算", CallCheck.INNER.val
    ZHA_JIAN = 102, "炸捡", "麻将"
    CHANGE_CONNECT = 103,"玩家状态变化","麻将"
    CLUB_QUIT_ROOM = 104, "茶馆玩家退出房间", CallCheck.INNER.val
    FORCE_DISMISS_ROOM = 105, "强制解散房间", CallCheck.INNER.val

    #休闲玩法
    TIMELY_KOU_FEN = 110, "即时结算", "麻将"
    START_FAN_JI = 111, "通知开始翻鸡", "麻将"
    FAN_JI = 112, "翻鸡", "麻将"
    FAN_JI_INFO = 113, "翻鸡信息", "麻将"
    MANY_HU = 114, "多人胡", "麻将"
    RECORD_ACCOUNT = 115, "记账", "麻将"


@unique
class CmdRobotCal(BaseEnum):
    CAL_ACTION = 1, "出牌", CallCheck.INNER.val
    CAL_PONG = 2, "麻将碰", CallCheck.INNER.val
    CAL_GANG = 3, "麻将杠", CallCheck.INNER.val


class CmdWorkers(BaseEnum):
    """ 消费服务命令（服务端内部使用） """
    UPDATE_GAME_TIMES = 1, "更新游戏次数"
    INSERT_GAME_GRADE = 2, "插入游戏战绩"
    INSERT_GOLD_STATEMENT = 3, "插入金币流水"
    UPDATE_GAME_TASK = 4, "更新游戏内任务"
    MANAGER_SEND_MAILS = 10, "后台群发邮件"
    UPDATE_USER_ASSET = 11, "批量更新资产"
    INSERT_DIAMOND_STATEMENT = 12, "插入钻石流水"
    UPDATE_USER_TASK = 13, "更新任务"
    NEW_USER_GIVE_GIFT = 14, "新用户赠送礼物"
    GET_RED_DOT_LIST = 15, "批量获取红点"
    UPDATE_USER_VIP_LEVEL = 16, "更新VIP经验值"
    PROCESS_SAFE_BOX = 17, "更新保险箱"
    UPDATE_ITEM_ORDER_COUNT = 18, "更新完成订单数"
    UPDATE_BAG_PROP = 19, "更新背包物品"
    BAN_PLAYER = 20, "封禁玩家"
    SET_NEW_SEASON = 21, "设置新赛季"
    CHECK_LIMITED_GOODS = 22, "检查限时物品"
    NOTIFY_ANNOUNCEMENT = 23, "通知公告（顶部公告）"
    LOGIN_SIGN_IN = 24, "登陆签到"
    BACKGROUND_SCHEDULED_TASK = 25, "后台定时任务"
    CANCEL_BACKGROUND_SCHEDULED_TASK = 26, "取消后台定时任务"
    FETCH_ACTIVE_MAILS = 27, "获取活跃（一段时间）邮件"
    USER_EVENT_TRACKING = 28, "用户事件追踪"
    UPDATE_GAME_RECORD_TIMES = 29, "更新游戏战绩次数"
    INSERT_GAME_RECORD_TOTAL = 30, "插入游戏战绩总分"
    UPDATE_CYCLE_POINT_LEADERBOARD = 31, "更新赛季积分排行榜"
    UPDATE_COMPETITION_RESULT = 32, "更新竞赛结果"
    PROXY_INVITE_BIND = 41, "分销-邀请绑定"
    PROXY_ORDER_SYNC = 42, "分销-订单同步"
    PROXY_USER_SET = 43, "分销-用户配置"
    PROXY_USER_UP = 44, "分销-用户更新"
    CLUB_EVENT_LOG = 51, "茶馆事件日志"



@unique
class CmdNotice(BaseEnum):
    """ 通知命令：通过ws下发通知，如红点之类的消息 """
    RED_DOT = 1, "红点通知"
    TOP_ANNOUNCEMENT = 2, "顶部公告"

    # 以下的未用（备选）
    LOGIN = 3, "登录下发"
    MAILS = 4, "邮件"
    FRIEND_APPLY = 5, "好友申请"
    LOTTERY = 6, "抽奖"
    SIGN_INFO = 7, "签到"
    AVATAR_BOX = 8, "头像框装扮"
    BUB_BOX = 9, "聊天气泡装扮"
    CHENG_HAO = 10, "称号"
    YU_YIN = 11, "语音包"
    ACTIVITY = 12, "首充活动"
    FU_LI = 13, "福利活动"
    FRIEND_MSG = 14, "好友消息"
    AD_GOT_VIP = 15, "看广告获得VIP经验"
    INVITE_ROOM = 16, "邀请加入房间"


class RedDotType(BaseEnum):
    """红点通知类型"""
    RD_SIGN_IN_RF = 1, "可签到/累计签到达成（运势）"
    RD_STORE = 2, "商店免费礼包"
    RD_TASK = 3, "任务完成/活跃达成"
    RD_MAILS = 4, "未读/新邮件"
    RD_VIP = 5, "VIP奖励"
    RD_FIRST_CHARGE = 6, "可首充/可领奖"
    RD_WEEK_CARD = 7, "周卡奖励"
    RD_LIFETIME_CARD = 8, "终生卡奖励"
    RD_PERSONAL = 9, "新装扮道具"
    RD_RELIEF = 10, "可领取救济金"
    RD_BAG = 11, "背包新获得"
    RD_SKIN = 12, "新皮肤/可升级"
    RD_MONOPOLY = 13, "大富翁有骰子"
    RD_MONOPOLY_FREE_DICE = 14, "大富翁免费骰子"
    RD_MONOPOLY_TASK = 15, "大富翁任务"
    RD_SIGN_IN = 16, "可签到/累计签到达成（每月）"
    RD_RANKING_AWARDS = 17, "境界突破奖励"
    RD_DOUYIN_REVISIT = 18, "抖音侧边栏奖励"
    RD_SIGN_IN_WK = 19, "可签到 / 累计签到达成（每周七日）"
    RD_SHARE = 20, "分享奖励"
    RD_LIMIT_LOGIN = 21, "限时登录"
    RD_CLUB_APPLY = 22, "俱乐部申请"
    RD_CLUB_CHECK = 23, "俱乐部审批"
    RD_CLUB_USER_LIST = 24, "俱乐部用户列表"
    RD_CLUB_KICK = 25, "俱乐部踢出"
    RD_CLUB_CHECK_REFRESH = 26, "俱乐部审批刷新"


class CmdRobotMethods(BaseEnum):
    """
    todo: 所有游戏共同使用命令[子游戏 -> 机器人]
    规范所有从子游戏发送过来的回调方法命令
    方法命令[201 - 299]
    """
    CAL_ACTION = 201, "出牌"
    CAL_PONG = 202, "麻将碰"
    CAL_GONG = 203, "麻将杠"
    CAL_SP = 204, "水鱼撒扑"
    CAL_FARMER_LP = 205, "水鱼闲家亮牌"
    CAL_FARMER_QG = 206, "水鱼闲家强攻"
    CAL_FARMER_MI = 207, "水鱼闲家密"
    CAL_LANDLORD_SHA = 208, "水鱼庄家杀"
    CAL_LANDLORD_ZOU = 209, "水鱼庄家走"
    CAL_FARMER_XIN = 210, "水鱼闲家信"
    CAL_FARMER_FAN = 211, "水鱼闲家反"
    CAL_WORLD_CHAT = 212, "世界聊天"
    CAL_PYH_CHAT = 213, "牌友会聊天"
    CAL_SINGLE_CHAT = 214, "单聊"
    CAL_BID = 215, "斗地主叫牌"
    CAL_CHAN = 216, "斗地主铲"
    CAL_RE_CHAN = 217, "斗地主反铲"
    CAL_EXCHANGE_THREE = 218, "斗地主换三张"
    CAL_EXCHANGE_FIVE = 219, "斗地主换五张"


class CmdChat(BaseEnum):
    """ 聊天服务命令 """
    RECEIVE_CHAT_MSG = 1, "接收聊天消息", CallCheck.INNER.val


@unique
class GameAnnouncement(BaseEnum):
    """ 游戏大赢公告类型 """
    SENTENCE_PATTERN_1 = 1, "句式1"
    SENTENCE_PATTERN_2 = 2, "句式2"
    SENTENCE_PATTERN_3 = 3, "句式3"
    SENTENCE_PATTERN_4 = 4, "句式4"


if __name__ == '__main__':
    res = GameAnnouncement.rand_choice_member()
    print(res)
