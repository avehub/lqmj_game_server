# coding=utf-8
import decimal

from nsanic.base_blue import BaseBlue
from nsanic.handler_http import Urls

from lucky_proxy.interface.proxy_login import ProxyLogin, ProxySendSmsCode, ProxyRefreshToken
from lucky_proxy.proxy_route.income_route import INCOME_APIS
from lucky_proxy.proxy_route.promotion_route import PROMOTION_APIS
from lucky_proxy.proxy_route.setting_route import SETTING_APIS
from lucky_proxy.proxy_route.statistics_route import STATISTICS_APIS
from lucky_proxy.proxy_route.team_route import TEAM_APIS
from lucky_proxy.proxy_route.user_route import USER_APIS
from lucky_proxy.proxy_route.withdraw_route import WITHDRAW_APIS


class MainBp(BaseBlue):
    # 路由请添加在这里
    APIS = [
        # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)
        # 代理登录功能
        Urls("/proxy/Login", ProxyLogin),
        Urls("/proxy/ProxySendSmsCode", ProxySendSmsCode),
        # token刷新
        Urls("/proxy/RefreshToken", ProxyRefreshToken),

    ]
    DEFAULT_APIS = APIS \
                   + PROMOTION_APIS \
                   + INCOME_APIS \
                   + WITHDRAW_APIS \
                   + SETTING_APIS \
                   + STATISTICS_APIS \
                   + USER_APIS \
                   + TEAM_APIS
