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
from lucky_game.interface.test_api import TestApi
# from lucky_game.interface.get_u_info import QueryUserInfo, RefreshAssets, QueryUserGameStates, \
#     QueryUserAllNumOfGames, QueryUserGameGrade, QueryUserIsInCService, GetLeisureList, QueryUserVipLevel, \
#     QueryUserAdditionInfo, FetchRedDotsByOpportunity, QueryUserSkinAmount, QueryUserAdFreePrivilege
# from lucky_game.interface.player_vault import BagHandler, DropBagItem, SafeBoxHandler, \
#     SafeBoxOperateUser, GetCosmeticUsedItems, UseCosmeticItem, GetCosmeticHandler, \
#     ClickNewGoodsItem, GetGamePropHandler, GetDetailShardInfo, GetGoodsJumpChance
from lucky_game.interface.login import LoginByGuest, LoginByToken, LoginByWechatMiniProgram, LoginByWechat, \
    LoginByAlipayGame, LoginByDouYinGame
# from lucky_game.interface.up_u_info import ModifyGeneralUserInfo, Certification, TestAddGold, GetSessionKey, \
#     GetWeChatGzhOpenid
# from lucky_game.interface.some_pay import AliPayNotify, MiniGameRecvPush, MakeOrder, MiniGameQueryOrder, \
#     GetBalanceByAliMiniProgram, AliPayQueryStatus, ReduceBalanceByAliMiniProgram, AliPayRefund, DouYinGamePayNotify, \
#     DouYinGameQueryOrder, GetBalanceByDouYinGame, ReduceBalanceByDouYinGame, ReduceBalanceByWechatMiniProgram, \
#     GetBalanceByWechatMiniProgram, MiniProgramRecvPush, HuiFuGetPayInfo, HuiFuPayQueryOrder, HuiFuPayNotify, \
#     CompletePaidOrder
# from lucky_game.interface.store import StoreHandler, PayByRedemption, SwitchStaHandler
# from lucky_game.interface.interaction import MakeAdOrder, CompleteAdOrder, SignInHandler, SignInComplete, \
#     SignInTotalComplete, GetReliefHandler, GetReliefConf, GetCommonAwardsConf, PullCommonAwards, OpenTreasureBox
# from lucky_game.interface.mails import MailsListHandler, MailsOperateUser, MailsOperateOneClick
# from lucky_game.interface.game_tasks import GameTaskComplete, GameActiveComplete, GameTaskHandler, GameTaskUpdate, \
#     GameTaskUpdateForRookie
# from lucky_game.interface.activitys import GetActivityAwards, VipLevelHandler, VipLevelPullAwards, \
#     GetActivityHandler
# from lucky_game.interface.west_way import WestWayQueryMap, WestWayQueryGoods, WestWayPlaySteps
from lucky_game.interface.club import ClubCreate


class MainBp(BaseBlue):
    # 路由请添加在这里
    DEFAULT_APIS = [
        # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)
        Urls("/testapi/", TestApi),

        # 登录/授权
        Urls("/LoginByGuest/", LoginByGuest),  # 游客登陆
        Urls("/LoginByToken/", LoginByToken),  # Token登录
        Urls("/LoginByPhone/", LoginByWechatMiniProgram),  # 手机号登陆
        Urls("/LoginByWechat/", LoginByWechat),  # 微信登录
        Urls("/LoginByApple/", LoginByAlipayGame),  # AppleID登录

        # 茶馆
        Urls("/ClubCreate/", ClubCreate),  # 茶馆创建
        # Urls("/ClubApply/", ClubApply),  # 茶馆申请
        # Urls("/ClubApplyList/", ClubApplyList),  # 茶馆申请列表
        # Urls("/ClubCheck/", ClubCheck),  # 茶馆审批
        # Urls("/ClubList/", ClubList),  # 我的茶馆列表
        # Urls("/ClubHall/", ClubHall),  # 茶馆大厅
        # Urls("/ClubSearch/", ClubSearch),  # 茶馆搜索
        # Urls("/ClubRoomCreate/", ClubRoomCreate),  # 茶馆房间创建
        # Urls("/ClubRoomList/", ClubRoomList),  # 茶馆房间列表
        # Urls("/ClubRoomJoin/", ClubRoomJoin),  # 茶馆房间加入
        # Urls("/ClubRoomLeave/", ClubRoomLeave),  # 茶馆房间离开

        # 用户数据相关
        # Urls("/ModifyGeneralUserInfo/", ModifyGeneralUserInfo),  # 更新用户必要信息
        # Urls("/Certification/", Certification),  # 实名认证
        # Urls("/TestAddGold/", TestAddGold),  # 修改金币（测试）
        # Urls("/QueryUserInfo/", QueryUserInfo),  # 查询用户信息
        # Urls("/GetSessionKey/", GetSessionKey),  # 微信session_key更新
        # Urls("/RefreshAssets/", RefreshAssets),  # 刷新玩家资产
        # Urls("/FetchRedDotsByOpportunity/", FetchRedDotsByOpportunity),  # 批量获取红点
        # Urls("/GetWeChatGzhOpenid/", GetWeChatGzhOpenid),  # 获取微信公众号的Openid
        #
        # # 游戏相关
        # Urls("/GetLeisureList/", GetLeisureList),  # 获取休闲场列表
        # Urls("/QueryUserGameStates/", QueryUserGameStates),  # 获取玩家游戏次数等
        # Urls("/QueryUserAllNumOfGames/", QueryUserAllNumOfGames),  # 查询玩家总对局数
        # Urls("/QueryUserGameGrade/", QueryUserGameGrade),  # 获取玩家游戏战绩
        # Urls("/QueryUserIsInCService/", QueryUserIsInCService),  # 查询玩家是否在游戏中
        # Urls("/QueryUserAdditionInfo/", QueryUserAdditionInfo),  # 查询玩家加成信息
        # Urls("/GetReliefHandler/", GetReliefHandler),  # 领取救济金
        # Urls("/GetReliefConf/", GetReliefConf),  # 救济金配置
        # Urls("/GetQuickChatConf/", GetQuickChatConf),  # 获取快捷聊天配置
        #
        # # 支付相关
        # Urls("/MakeOrder/", MakeOrder),  # 创建订单
        # Urls("/MiniGameRecvPush/", MiniGameRecvPush),  # 微信MG支付回调通知
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
        # # 邮件相关
        # Urls("/MailsListHandler/", MailsListHandler),  # 获取邮件列表
        # Urls("/MailsOperateUser/", MailsOperateUser),  # 指定操作邮件
        # Urls("/MailsOperateOneClick/", MailsOperateOneClick),  # 一键操作邮件
        #
        # # 任务/活跃系统
        # Urls("/GameTaskHandler/", GameTaskHandler),  # 加载任务配置
        # Urls("/GameTaskUpdate/", GameTaskUpdate),  # 更新任务状态
        # Urls("/GameTaskComplete/", GameTaskComplete),  # 任务完成领奖
        # Urls("/GameActiveComplete/", GameActiveComplete),  # 活跃值达成领奖
        # Urls("/GameTaskUpdateForRookie/", GameTaskUpdateForRookie),  # 新手引导中更新任务（西行路新手引导中专用）
        #
        # # 充值/消费相关
        # Urls("/StoreHandler/", StoreHandler),  # 加载各类型商店
        # Urls("/PayByRedemption/", PayByRedemption),  # 商店兑换购物
        # Urls("/GetActivityHandler/", GetActivityHandler),  # 获取充值活动配置
        # Urls("/GetActivityAwards/", GetActivityAwards),  # 领取活动奖励
        # Urls("/SwitchStaHandler/", SwitchStaHandler),  # 开关类型
        #
        # # VIP相关
        # Urls("/VipLevelHandler/", VipLevelHandler),  # 获取VIP等级配置
        # Urls("/VipLevelPullAwards/", VipLevelPullAwards),  # VIP用户领取奖励
        # Urls("/QueryUserVipLevel/", QueryUserVipLevel),  # 查询用户VIP等级信息
        #
        # # 皮肤系统
        # Urls("/SkinDharmaForm/", SkinDharmaForm),  # 法相一级：法相之形
        # Urls("/SkinDharmaAppear/", SkinDharmaAppear),  # 法相二级：法相显现
        # Urls("/UseSkinItem/", UseSkinItem),  # 装备卡牌皮肤
        # Urls("/UpgradeSkinItem/", UpgradeSkinItem),  # 卡牌皮肤升星
        # Urls("/GetGameSkinUsedItems/", GetGameSkinUsedItems),  # 皮肤使用项查询
        # Urls("/GetSkinAllStarItems/", GetSkinAllStarItems),  # 获取所有星级信息
        # Urls("/UseLimitedTimeSkin/", UseLimitedTimeSkin),  # 使用限时皮肤
        # Urls("/QueryUserSkinAmount/", QueryUserSkinAmount),  # 查询玩家持有皮肤数
        # Urls("/QueryUserAdFreePrivilege/", QueryUserAdFreePrivilege),  # 查询用户免广告特权
        #
        # # 漫漫西行路
        # Urls("/WestWayQueryMap/", WestWayQueryMap),  # 西行路地图
        # Urls("/WestWayQueryGoods/", WestWayQueryGoods),  # 西行路物资
        # Urls("/WestWayPlaySteps/", WestWayPlaySteps),  # 西行路行进
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
