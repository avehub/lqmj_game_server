from nsanic.handler_http import Urls

from lucky_proxy.interface.proxy import ProxyBaseInfoSetting, ProxyBankCardSetting
from lucky_proxy.interface.proxy_withdraw import ProxyWithdraw

"""
设置模块
"""
# 路由请添加在这里
SETTING_APIS = [
    # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)

    # 基础资料设置
    Urls("proxy/ProxyBaseInfoSetting", ProxyBaseInfoSetting),
    Urls("proxy/ProxyBankCardSetting", ProxyBankCardSetting),


]
