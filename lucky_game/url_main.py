# coding=utf-8
from nsanic.base_blue import BaseBlue
from nsanic.handler_http import Urls
from lucky_game.interface.test_api import TestApi, TestCreatGameRecords
from lucky_game.interface.login import LoginByGuest, LoginByToken, LoginByWechat, \
    LoginByApple, SendCode, LoginByPhone, BindByWechat, BindByPhone
from lucky_game.interface.store import StoreHandler, PayByGood, SwitchStaHandler, StoreList, StoreBuy
from lucky_game.interface.mails import MailsListHandler, MailsOperateUser, MailsOperateOneClick
from lucky_game.interface.activitys import ActivityDetail, JoinActivity, GainActivity, ProgressActivity, ActivityList, \
    ActivityReturnGold
from lucky_game.interface.club import ClubCreate, ClubList, ClubHall, ClubApply, ClubApplyList, ClubCheck, ClubSearch, \
    ClubCheckList, ClubUserInfo, ClubUpdate, ClubDetail, ClubDismiss, ClubRoomCard, ClubRoomCardList
from lucky_game.interface.game_room import CreateRoom, JoinRoom, LeaveRoom, RoomDetail
from lucky_game.interface.club_room_template import RoomTemplateCreate, RoomTemplateUpdate, RoomTemplateList, \
    RoomTemplateDelete
from lucky_game.interface.user import UserInfo, UpdateUserInfo, UpdateUserResource, Certification, FetchRedDotsByOpportunity, \
    WriteOff, UpWechatUserInfo
from lucky_game.interface.game_rule import GameRuleAll
from lucky_game.interface.game_user import QueryUserIsInCService
from lucky_game.interface.records_game import UserRecords, SegmentRecords, ClubRanks, PastRanks, \
    UserAggregateRanks, ClubAggregateRanks, SegmentRecordsByReplayLabel
from lucky_game.interface.club_group import CreatGroup, GetGroup, UpdateGroup, DelGroup
from lucky_game.interface.club_behavior import GetBehaviorExtra
from lucky_game.interface.club_user import JoinBlack, CancelBlack, UpdateRelation, KickRelation, GetClubUser
from lucky_game.interface.file_handle import FileUploadHandler, FileDeleteHandler
from lucky_game.interface.game import GetLeisureList
from lucky_game.interface.config import GetConf
from lucky_game.interface.order import OrderDetail, CallbackAli, UnclaimedOrder, GainOrder, CallbackHf, CallbackIos, \
    MiniProgramRecvPush
from lucky_game.interface.tools import GetWeChatShareData, GetAppVersion, GetWechatCode, GetGameRecord
from lucky_game.interface.ad_event import CreateAdRecord
from lucky_game.interface.club_user_group import AlterUserGroup, GetUserGroup


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
        Urls("/GetWechatCode/", GetWechatCode),  # 获取微信登录code
        Urls("/CreateAdRecord/", CreateAdRecord),  # 添加广告记录
        Urls("/GetGameRecord/", GetGameRecord),  # 获取游戏回放战绩

        # 登录/授权
        Urls("/LoginByGuest/", LoginByGuest),  # 游客登陆
        Urls("/LoginByToken/", LoginByToken),  # Token登录
        Urls("/SendCode/", SendCode),  # 发送验证码
        Urls("/LoginByPhone/", LoginByPhone),  # 手机号登陆
        Urls("/LoginByWechat/", LoginByWechat),  # 微信登录(公众号/小程序/微信APP)
        Urls("/LoginByApple/", LoginByApple),  # AppleID登录
        Urls("/BindByWechat/", BindByWechat),  # 绑定微信
        Urls("/BindByPhone/", BindByPhone),  # 绑定手机号



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
        Urls("/RoomDetail/", RoomDetail),  # 房间详情
        Urls("/UpWechatUserInfo/", UpWechatUserInfo),  # 更新用户信息
        Urls("/AlterUserGroup/", AlterUserGroup),  # 禁止同桌-新增、修改
        Urls("/GetUserGroup/", GetUserGroup),  # 禁止同桌-查询

        # 用户数据相关
        Urls("/ModifyGeneralUserInfo/", UpdateUserInfo),  # 更新用户必要信息
        Urls("/Certification/", Certification),  # 实名认证
        Urls("/TestUpdateUserResource/", UpdateUserResource),  # 更新用户资源（测试）
        Urls("/QueryUserInfo/", UserInfo),  # 查询用户信息
        Urls("/FetchRedDotsByOpportunity/", FetchRedDotsByOpportunity),  # 批量获取红点
        Urls("/WriteOff/", WriteOff),  # 注销账号
        #
        # # 游戏相关
        Urls("/GameRuleAll/", GameRuleAll),  # 获取所有游戏规则
        Urls("/GetLeisureList/", GetLeisureList),  # 获取休闲场列表
        # Urls("/QueryUserRecords/", UserRecords),  # 获取玩家游戏战绩
        Urls("/QuerySegmentRecords/", SegmentRecords),  # 获取子局游戏战绩
        Urls("/QuerySegmentRecordsByReplayLabel/", SegmentRecordsByReplayLabel),  # 获取游戏回放记录
        Urls("/QueryClubRanks/", ClubRanks),  # 获取茶馆战绩排行榜
        Urls("/QueryPastRanks/", PastRanks),  # 获取茶馆、我的历史战绩
        Urls("/QueryUserAggregateRanks/", UserAggregateRanks),  # 获取用户战绩总计
        Urls("/QueryClubAggregateRanks/", ClubAggregateRanks),  # 获取茶馆战绩总计
        Urls("/QueryUserIsInCService/", QueryUserIsInCService),  # 查询玩家是否在游戏中

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

        # # 充值/消费相关
        Urls("/StoreHandler/", StoreHandler),  # 获取商店商品
        Urls("/PayByGood/", PayByGood),  # 商店购物（游戏内部）
        Urls("/StoreList/", StoreList),  # 获取商店商品列表
        Urls("/StoreBuy/", StoreBuy),  # 商店购物（微信网页）

        # # 支付相关
        Urls("/QueryOrder/", OrderDetail),  # 查询订单详情
        Urls("/CallbackAli/", CallbackAli),  # 支付宝订单回调
        Urls("/CallbackHf/", CallbackHf),  # 汇付天下订单回调
        Urls("/CallbackIos/", CallbackIos),  # 苹果订单校验
        Urls("/UnclaimedOrder/", UnclaimedOrder),  # 未领取订单
        Urls("/GainOrder/", GainOrder),  # 领取订单
        Urls("/MiniProgramRecvPush/", MiniProgramRecvPush),  # 小程序订单（小程序回调创建订单）
    ]
