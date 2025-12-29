from nsanic.handler_http import Urls

from lucky_proxy.interface.proxy_withdraw import ProxyWithdraw

"""
提现路由
"""
# 路由请添加在这里
WITHDRAW_APIS = [
    # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)

    # 代理提现
    Urls("/ProxyWithdraw", ProxyWithdraw),


]
