# coding=utf-8
from nsanic.base_blue import BaseBlue
from nsanic.handler_http import Urls
from lucky_admin.interface.login import LoginByAccount, LoginByToken
from lucky_admin.interface.test_api import TestApi
from lucky_admin.interface.index import IndexBaseData, IndexUserData, IndexBaseTable, IndexGameData, IndexGameUserChart, \
    IndexPayMoneyRealTime, IndexPayMoneyTotalChart, IndexAddUserTable, IndexAddUserChart, IndexPayMoneyChart, \
    IndexPayUserChart, IndexOnlineUserChart
from lucky_admin.interface.mail import Email
from lucky_admin.interface.club import Club, ClubEvent
from lucky_admin.interface.user import User, UserStatus, OrderList, OrderStatistics, ResourceChanges, ResourceChangeChart, \
     UserResource
from lucky_admin.interface.room import GameRoom, GameRecord
from lucky_admin.interface.award import Award
from lucky_admin.interface.config import Config


class MainBp(BaseBlue):
    # 路由请添加在这里
    DEFAULT_APIS = [
        # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)
        Urls("/testapi", TestApi),
        Urls("/LoginByAccount", LoginByAccount),
        Urls("/LoginByToken", LoginByToken),

        # 首页相关
        Urls("/IndexBaseData", IndexBaseData),
        Urls("/IndexUserData", IndexUserData),
        Urls("/IndexBaseTable", IndexBaseTable),
        Urls("/IndexGameData", IndexGameData),
        Urls("/IndexGameUserChart", IndexGameUserChart),
        Urls("/IndexOnlineUserChart", IndexOnlineUserChart),
        Urls("/IndexPayMoneyRealTime", IndexPayMoneyRealTime),
        Urls("/IndexPayMoneyTotalChart", IndexPayMoneyTotalChart),
        Urls("/IndexAddUserTable", IndexAddUserTable),
        Urls("/IndexAddUserChart", IndexAddUserChart),
        Urls("/IndexPayMoneyChart", IndexPayMoneyChart),
        Urls("/IndexPayUserChart", IndexPayUserChart),

        # 邮件相关
        Urls("/Email", Email),

        # 用户模块
        Urls("/User", User),
        Urls("/UserStatus", UserStatus),
        Urls("/UserResource", UserResource),
        Urls("/OrderList", OrderList),
        Urls("/OrderStatistics", OrderStatistics),
        Urls("/ResourceChanges", ResourceChanges),
        Urls("/ResourceChangeChart", ResourceChangeChart),

        # 茶馆模块
        Urls("/Club", Club),
        Urls("/ClubEvent", ClubEvent),

        # 游戏房间模块
        Urls("/GameRoom", GameRoom),
        Urls("/GameRecord", GameRecord),

        # 奖励模块
        Urls("/Award", Award),

        # 配置模块
        Urls("/Config", Config),






        # 资产相关
        # Urls("/QueryAssetsEnum", QueryAssetsEnum),  # 查询资产枚举
        # Urls("/ModifyUserAssets", ModifyUserAssets),  # 修改玩家资产
        # Urls("/GetAllItemsHandler", GetAllItemsHandler),  # 获取所有子物品
        # Urls("/GetAllStoresHandler", GetAllStoresHandler),  # 获取所有商品/充值

        # 通知相关
        # Urls("/AnnouncementsHandler", AnnouncementsHandler),
        # Urls("/BanHandler", BanHandler),
        # Urls("/MailsHandler", MailsManagerSend),
        #
        # Urls("/PlayerHandler", PlayerHandler),  # 玩家管理
        # Urls("/PlayerRankingHandler", PlayerRankingHandler),  # 更新玩家修为
        # Urls("/ModifyPassword", ModifyPassword),  # 更新玩家修为
        # Urls("/RoomPlayerHandler", RoomPlayerHandler),  # 房间玩家管理（解散）
        #
        # Urls("/OperatesRecordsHandler", OperatesRecordsHandler),  # 操作记录
        # Urls("/BackgroundRecordsTaskHandler", BackgroundRecordsTaskHandler),  # 后台定时任务记录
        # Urls("/GetActiveMails", GetActiveMails),  # 获取活跃邮件
        # Urls("/ItemRemovalCompensator", ItemRemovalCompensator),  # 物品下架补偿器
        #
        # # 统计相关
        # Urls("/GetAdsEventStats", GetAdsEventStats),  # 获取广告事件统计
        # Urls("/GetFunnelAnalysis", GetFunnelAnalysis),  # 获取漏斗分析结果
        # Urls("/GetUserRetentionStats", GetUserRetentionStats),  # 获取用户留存统计
        # Urls("/GetUserDataAnalysis", GetUserDataAnalysis),  # 获取用户数据分析
        # Urls("/GetAdsUserStats", GetAdsUserStats),  # 获取广告用户统计（个人）
        # Urls("/GetAdsParams", GetAdsParams),  # 获取广告参数
        #
        # # 订单相关
        # Urls("/OrderHandler", OrderHandler),  # 订单记录
        # Urls("/ReplenishmentOrder", ReplenishmentOrder),  # 订单记录
    ]
