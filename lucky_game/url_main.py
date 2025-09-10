# coding=utf-8
from nsanic.base_blue import BaseBlue
from nsanic.handler_http import Urls
# from lucky_game.interface.ads_stats import JuLiangAdsMonitor, CommonAdsMatchedData, DataNexusAdsMonitor
# from lucky_game.interface.friend import GetUserFriendList, FriendshipOperate
# from lucky_game.interface.game_chat import GetQuickChatConf, GetChatRecords, SendChatMessage
# from lucky_game.interface.game_ranking import GetUserRankingInfo, GetRankingList, RankingPullAwards, \
#     ModifyUserRankingInfo, GetSeasonRankingConf, GetPlayerRankingInfo
# from lucky_game.interface.interaction import AnnouncementsHandler
# from lucky_game.interface.player_skin import SkinDharmaForm, SkinDharmaAppear, UseSkinItem, UpgradeSkinItem, \
#     GetGameSkinUsedItems, GetSkinAllStarItems, UseLimitedTimeSkin
from lucky_game.interface.test_api import TestApi, TestCreatGameRecords
# from lucky_game.interface.get_u_info import QueryUserInfo, RefreshAssets, QueryUserGameStates, \
#     QueryUserAllNumOfGames, QueryUserGameGrade, QueryUserIsInCService, GetLeisureList, QueryUserVipLevel, \
#     QueryUserAdditionInfo, FetchRedDotsByOpportunity, QueryUserSkinAmount, QueryUserAdFreePrivilege
# from lucky_game.interface.player_vault import BagHandler, DropBagItem, SafeBoxHandler, \
#     SafeBoxOperateUser, GetCosmeticUsedItems, UseCosmeticItem, GetCosmeticHandler, \
#     ClickNewGoodsItem, GetGamePropHandler, GetDetailShardInfo, GetGoodsJumpChance
from lucky_game.interface.login import LoginByGuest, LoginByToken, LoginByWechat, \
    LoginByApple, SendCode, LoginByPhone, BindByWechat
# from lucky_game.interface.up_u_info import ModifyGeneralUserInfo, TestAddGold, GetSessionKey, \
#     GetWeChatGzhOpenid
# from lucky_game.interface.some_pay import AliPayNotify, MiniGameRecvPush, MakeOrder, MiniGameQueryOrder, \
#     GetBalanceByAliMiniProgram, AliPayQueryStatus, ReduceBalanceByAliMiniProgram, AliPayRefund, DouYinGamePayNotify, \
#     DouYinGameQueryOrder, GetBalanceByDouYinGame, ReduceBalanceByDouYinGame, ReduceBalanceByWechatMiniProgram, \
#     GetBalanceByWechatMiniProgram, MiniProgramRecvPush, HuiFuGetPayInfo, HuiFuPayQueryOrder, HuiFuPayNotify, \
#     CompletePaidOrder
from lucky_game.interface.store import StoreHandler, PayByGood, SwitchStaHandler, StoreList, StoreBuy
# from lucky_game.interface.interaction import MakeAdOrder, CompleteAdOrder, SignInHandler, SignInComplete, \
#     SignInTotalComplete, GetReliefHandler, GetReliefConf, GetCommonAwardsConf, PullCommonAwards, OpenTreasureBox
from lucky_game.interface.mails import MailsListHandler, MailsOperateUser, MailsOperateOneClick
# from lucky_game.interface.game_tasks import GameTaskComplete, GameActiveComplete, GameTaskHandler, GameTaskUpdate, \
#     GameTaskUpdateForRookie
from lucky_game.interface.activitys import ActivityDetail, JoinActivity, GainActivity, ProgressActivity, ActivityList, \
    ActivityReturnGold
from lucky_game.interface.club import ClubCreate, ClubList, ClubHall, ClubApply, ClubApplyList, ClubCheck, ClubSearch, \
    ClubCheckList, ClubUserInfo, ClubUpdate, ClubDetail, ClubDismiss, ClubRoomCard, ClubRoomCardList
from lucky_game.interface.game_room import CreateRoom, JoinRoom, LeaveRoom, RoomDetail
from lucky_game.interface.club_room_template import RoomTemplateCreate, RoomTemplateUpdate, RoomTemplateList, \
    RoomTemplateDelete
from lucky_game.interface.user import UserInfo, UpdateUserInfo, UpdateUserResource, Certification, FetchRedDotsByOpportunity, \
    WriteOff
from lucky_game.interface.game_rule import GameRuleAll
from lucky_game.interface.game_user import QueryUserIsInCService
from lucky_game.interface.records_game import UserRecords, TotalRecords, SegmentRecords, ClubRanks, PastRanks, \
    UserAggregateRanks, ClubAggregateRanks, SegmentRecordsByReplayLabel
from lucky_game.interface.club_group import CreatGroup, GetGroup, UpdateGroup, DelGroup
from lucky_game.interface.club_behavior import GetBehaviorExtra
from lucky_game.interface.club_user import JoinBlack, CancelBlack, UpdateRelation, KickRelation, GetClubUser
from lucky_game.interface.file_handle import FileUploadHandler, FileDeleteHandler
from lucky_game.interface.game import GetLeisureList
from lucky_game.interface.config import GetConf
from lucky_game.interface.order import OrderDetail, CallbackAli, UnclaimedOrder, GainOrder, CallbackHf, CallbackIos, MiniProgramRecvPush
from lucky_game.interface.tools import GetWeChatShareData, GetAppVersion, GetWechatCode



class MainBp(BaseBlue):
    # 路由请添加在这里
    DEFAULT_APIS = [
        # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)
        Urls("/testapi", TestApi),
        Urls("/TestCreatGameRecords", TestCreatGameRecords),
        Urls("/FileUpload", FileUploadHandler),
        Urls("/FileDelete", FileDeleteHandler),
        # 配置相关
        Urls("/QueryConf/", GetConf),
        # 工具类接口
        Urls("/GetWeChatShareData/", GetWeChatShareData),  # 微信分享数据
        Urls("/GetAppVersion/", GetAppVersion),  # 获取应用版本信息
        Urls("/GetWechatCode/", GetWechatCode),

        # 登录/授权
        Urls("/LoginByGuest/", LoginByGuest),  # 游客登陆
        Urls("/LoginByToken/", LoginByToken),  # Token登录
        Urls("/SendCode/", SendCode),  # 发送验证码
        Urls("/LoginByPhone/", LoginByPhone),  # 手机号登陆
        Urls("/LoginByWechat/", LoginByWechat),  # 微信登录(公众号/小程序/微信APP)
        Urls("/LoginByApple/", LoginByApple),  # AppleID登录
        Urls("/BindByWechat/", BindByWechat),  # 绑定微信

        # 茶馆
        Urls("/ClubCreate/", ClubCreate),  # 茶馆创建
        Urls("/ClubUpdate/", ClubUpdate),  # 编辑茶馆
        Urls("/ClubDetail/", ClubDetail),  # 茶馆详情
        Urls("/ClubApply/", ClubApply),  # 茶馆申请
        Urls("/ClubApplyList/", ClubApplyList),  # 茶馆申请列表
        Urls("/ClubCheck/", ClubCheck),  # 茶馆审批
        Urls("/ClubCheckList/", ClubCheckList),  # 茶馆审批列表
        Urls("/ClubList/", ClubList),  # 我的茶馆列表
        Urls("/ClubHall/", ClubHall),  # 茶馆大厅
        Urls("/ClubSearch/", ClubSearch),  # 茶馆搜索
        Urls("/ClubUserInfo/", ClubUserInfo),  # 茶馆搜索
        Urls("/ClubRoomCreate/", CreateRoom),  # 茶馆房间创建
        Urls("/ClubRoomJoin/", JoinRoom),  # 茶馆房间加入
        Urls("/ClubRoomLeave/", LeaveRoom),  # 茶馆房间离开
        Urls("/ClubRoomTemplateCreate/", RoomTemplateCreate),  # 茶馆房间模板创建
        Urls("/ClubRoomTemplateList/", RoomTemplateList),  # 茶馆房间模板列表
        Urls("/ClubRoomTemplateDelete/", RoomTemplateDelete),  # 茶馆房间模板删除
        Urls("/ClubRoomTemplateUpdate/", RoomTemplateUpdate),  # 茶馆房间模板更新
        Urls("/ClubGroupCreate/", CreatGroup),  # 创建隔离组
        Urls("/ClubGroupList/", GetGroup),  # 获取隔离组列表
        Urls("/ClubGroupUpdate/", UpdateGroup),  # 更新隔离组
        Urls("/ClubGroupDelete/", DelGroup),  # 删除隔离组
        Urls("/ClubBehaviorExtra/", GetBehaviorExtra),  # 获取用户行为记录列表
        Urls("/ClubJoinBlack/", JoinBlack),  # 加入小黑屋
        Urls("/ClubCancelBlack/", CancelBlack),  # 取消小黑屋
        Urls("/ClubUpdateRelation/", UpdateRelation),  # 编辑茶馆与用户关系
        Urls("/ClubKickRelation/", KickRelation),  # 踢出茶馆
        Urls("/ClubUserList/", GetClubUser),  # 获取茶馆用户列表
        Urls("/ClubDismiss/", ClubDismiss),  # 解散茶馆
        Urls("/ClubRoomCard/", ClubRoomCard),  # 茶馆基金
        Urls("/ClubRoomCardList/", ClubRoomCardList),  # 茶馆基金记录列表
        Urls("/RoomDetail/", RoomDetail),  # 茶馆基金记录列表

        # 用户数据相关
        Urls("/ModifyGeneralUserInfo/", UpdateUserInfo),  # 更新用户必要信息
        Urls("/Certification/", Certification),  # 实名认证
        Urls("/TestUpdateUserResource/", UpdateUserResource),  # 更新用户资源（测试）
        Urls("/QueryUserInfo/", UserInfo),  # 查询用户信息
        # Urls("/GetSessionKey/", GetSessionKey),  # 微信session_key更新
        # Urls("/RefreshAssets/", RefreshAssets),  # 刷新玩家资产
        Urls("/FetchRedDotsByOpportunity/", FetchRedDotsByOpportunity),  # 批量获取红点
        # Urls("/GetWeChatGzhOpenid/", GetWeChatGzhOpenid),  # 获取微信公众号的Openid
        Urls("/WriteOff/", WriteOff),  # 注销账号
        #
        # # 游戏相关
        Urls("/GameRuleAll/", GameRuleAll),  # 获取所有游戏规则
        Urls("/GetLeisureList/", GetLeisureList),  # 获取休闲场列表
        # Urls("/QueryUserGameStates/", QueryUserGameStates),  # 获取玩家游戏次数等
        # Urls("/QueryUserAllNumOfGames/", QueryUserAllNumOfGames),  # 查询玩家总对局数
        # Urls("/QueryUserRecords/", UserRecords),  # 获取玩家游戏战绩
        # Urls("/QueryTotalRecords/", TotalRecords),  # 获取总局游戏战绩
        Urls("/QuerySegmentRecords/", SegmentRecords),  # 获取子局游戏战绩
        Urls("/QuerySegmentRecordsByReplayLabel/", SegmentRecordsByReplayLabel),  # 获取游戏回放记录
        Urls("/QueryClubRanks/", ClubRanks),  # 获取茶馆战绩排行榜
        Urls("/QueryPastRanks/", PastRanks),  # 获取茶馆、我的历史战绩
        Urls("/QueryUserAggregateRanks/", UserAggregateRanks),  # 获取用户战绩总计
        Urls("/QueryClubAggregateRanks/", ClubAggregateRanks),  # 获取茶馆战绩总计
        Urls("/QueryUserIsInCService/", QueryUserIsInCService),  # 查询玩家是否在游戏中
        # Urls("/QueryUserAdditionInfo/", QueryUserAdditionInfo),  # 查询玩家加成信息
        # Urls("/GetReliefHandler/", GetReliefHandler),  # 领取救济金
        # Urls("/GetReliefConf/", GetReliefConf),  # 救济金配置
        # Urls("/GetQuickChatConf/", GetQuickChatConf),  # 获取快捷聊天配置

        # 活动相关
        Urls("/QueryActivity/", ActivityDetail),  # 查询活动详情
        Urls("/ActivityList/", ActivityList),  # 查询活动列表
        Urls("/JoinActivity/", JoinActivity),  # 参与活动
        Urls("/GiveAward/", GainActivity),  # 领取活动奖励
        Urls("/ProgressActivity/", ProgressActivity),  # 活动进度
        Urls("/ActivityReturnGold/", ActivityReturnGold),  # 返还活动用户金币

        # # 邮件相关
        Urls("/MailsListHandler/", MailsListHandler),  # 获取邮件列表
        Urls("/MailsOperateUser/", MailsOperateUser),  # 指定操作邮件
        Urls("/MailsOperateOneClick/", MailsOperateOneClick),  # 一键操作邮件
        #
        # # 任务/活跃系统
        # Urls("/GameTaskHandler/", GameTaskHandler),  # 加载任务配置
        # Urls("/GameTaskUpdate/", GameTaskUpdate),  # 更新任务状态
        # Urls("/GameTaskComplete/", GameTaskComplete),  # 任务完成领奖
        # Urls("/GameActiveComplete/", GameActiveComplete),  # 活跃值达成领奖
        # Urls("/GameTaskUpdateForRookie/", GameTaskUpdateForRookie),  # 新手引导中更新任务（西行路新手引导中专用）
        #
        # # 充值/消费相关
        Urls("/StoreHandler/", StoreHandler),  # 获取商店商品
        Urls("/PayByGood/", PayByGood),  # 商店购物
        Urls("/StoreList/", StoreList),  # 获取商店商品列表
        Urls("/StoreBuy/", StoreBuy),  # 商店购物
        # Urls("/GetActivityHandler/", GetActivityHandler),  # 获取充值活动配置
        # Urls("/GetActivityAwards/", GetActivityAwards),  # 领取活动奖励
        # Urls("/SwitchStaHandler/", SwitchStaHandler),  # 开关类型

        # 微信公众H5网页支付

        # # 支付相关
        Urls("/QueryOrder/", OrderDetail),  # 查询订单详情
        Urls("/CallbackAli/", CallbackAli),  # 支付宝订单回调
        Urls("/CallbackHf/", CallbackHf),  # 汇付天下订单回调
        Urls("/CallbackIos/", CallbackIos),  # 苹果订单校验
        Urls("/UnclaimedOrder/", UnclaimedOrder),  # 未领取订单
        Urls("/GainOrder/", GainOrder),  # 领取订单
        Urls("/MiniProgramRecvPush/", MiniProgramRecvPush),  # 小程序订单（小程序回调创建订单）
        # Urls("/MiniGameQueryOrder/", MiniGameQueryOrder),  # 微信MG订单查询
        # Urls("/ReduceBalanceByWechatMiniProgram/", ReduceBalanceByWechatMiniProgram),  # 微信扣除游戏币
        # Urls("/GetBalanceByWechatMiniProgram/", GetBalanceByWechatMiniProgram),  # 微信查询游戏币
        # Urls("/AliPayNotify/", AliPayNotify),  # 支付宝MG支付回调通知
        # Urls("/AliPayQueryStatus/", AliPayQueryStatus),  # 支付宝MG订单查询
        # Urls("/GetBalanceByAliMiniProgram/", GetBalanceByAliMiniProgram),  # 支付宝查询游戏币
        # Urls("/ReduceBalanceByAliMiniProgram/", ReduceBalanceByAliMiniProgram),  # 支付宝扣减游戏币
        # Urls("/AliPayRefund/", AliPayRefund),  # 支付宝MG充值退款（测试）
        # Urls("/DouYinGamePayNotify/", DouYinGamePayNotify),  # 抖音MG支付回调通知
        # Urls("/DouYinGameQueryOrder/", DouYinGameQueryOrder),  # 抖音MG订单查询
        # Urls("/GetBalanceByDouYinGame/", GetBalanceByDouYinGame),  # 抖音查询游戏币
        # Urls("/ReduceBalanceByDouYinGame/", ReduceBalanceByDouYinGame),  # 抖音扣减游戏币
        # Urls("/MiniProgramRecvPush/", MiniProgramRecvPush),  # 微信小程序回调通知
        # Urls("/HuiFuGetPayInfo/", HuiFuGetPayInfo),  # 获取汇付支付信息
        # Urls("/HuiFuPayQueryOrder/", HuiFuPayQueryOrder),  # 汇付天下交易查询
        # Urls("/HuiFuPayNotify/", HuiFuPayNotify),  # 汇付天下支付回调通知
        # Urls("/CompletePaidOrder/", CompletePaidOrder),  # 完成已支付订单
        #
        # # 虚拟资产相关
        # Urls("/BagHandler/", BagHandler),  # 获取背包全部
        # Urls("/DropBagItem/", DropBagItem),  # 删除指定背包项
        # Urls("/GetCosmeticHandler/", GetCosmeticHandler),  # 获取游戏装扮
        # Urls("/GetCosmeticUsedItems/", GetCosmeticUsedItems),  # 装扮使用项查询
        # Urls("/ClickNewGoodsItem/", ClickNewGoodsItem),  # 新获得物品点击
        # Urls("/UseCosmeticItem/", UseCosmeticItem),  # 使用游戏装扮
        # Urls("/SafeBoxHandler/", SafeBoxHandler),  # 获取保险箱配置
        # Urls("/SafeBoxOperateUser/", SafeBoxOperateUser),  # 保险箱操作
        # Urls("/GetGamePropHandler/", GetGamePropHandler),  # 获取游戏道具
        # Urls("/GetDetailShardInfo/", GetDetailShardInfo),  # 获取碎片详细信息
        # Urls("/GetGoodsJumpChance/", GetGoodsJumpChance),  # 获取跳转机会
        #
        # # 用户互动相关
        # Urls("/MakeAdOrder/", MakeAdOrder),  # 创建广告订单
        # Urls("/CompleteAdOrder/", CompleteAdOrder),  # 完成广告订单
        # Urls("/SignInHandler/", SignInHandler),  # 通用获取签到配置
        # Urls("/SignInTotalComplete/", SignInTotalComplete),  # 通用累计签到领奖
        # Urls("/SignInComplete/", SignInComplete),  # 通用完成签到
        # Urls("/GetCommonAwardsConf/", GetCommonAwardsConf),  # 获取通用奖励配置
        # Urls("/PullCommonAwards/", PullCommonAwards),  # 通用奖励领取
        # Urls("/OpenTreasureBox/", OpenTreasureBox),  # 开启宝盒
        #

        #
        # # VIP相关
        # Urls("/VipLevelHandler/", VipLevelHandler),  # 获取VIP等级配置
        # Urls("/VipLevelPullAwards/", VipLevelPullAwards),  # VIP用户领取奖励
        # Urls("/QueryUserVipLevel/", QueryUserVipLevel),  # 查询用户VIP等级信息
        #
        # # 排位系统
        # Urls("/GetSeasonRankingConf/", GetSeasonRankingConf),  # 获取排位赛季配置
        # Urls("/GetUserRankingInfo/", GetUserRankingInfo),  # 获取用户排位信息
        # Urls("/GetRankingList/", GetRankingList),  # 获取排行榜：地区/世界
        # Urls("/RankingPullAwards/", RankingPullAwards),  # 排位赛领取奖励
        # Urls("/ModifyUserRankingInfo/", ModifyUserRankingInfo),  # 更新用户排位信息（地区）
        # Urls("/GetPlayerRankingInfo/", GetPlayerRankingInfo),  # 批量获取玩家排位信息（游戏内使用）
        #
        # # 通知|公告类
        # Urls("/AnnouncementsHandler/", AnnouncementsHandler),  # 批量获取玩家排位信息（游戏内使用
        #
        # # 广告
        # Urls("/JuLiangAdsMonitor/", JuLiangAdsMonitor),  # 巨量广告监测转化数据
        # Urls("/DataNexusAdsMonitor/", DataNexusAdsMonitor),  # 腾讯广告监测转化数据
        # Urls("/CommonAdsMatchedData/", CommonAdsMatchedData),  # 通用广告匹配转化数据
        #
        # # 好友相关
        # Urls("/GetUserFriendList/", GetUserFriendList),  # 通用获取好友列表
        # Urls("/FriendshipOperate/", FriendshipOperate),  # 通用好友操作
        #
        # # 聊天相关
        # Urls("/GetChatRecords/", GetChatRecords),  # 获取聊天记录
        # Urls("/SendChatMessage/", SendChatMessage),  # 发送聊天消息
    ]
