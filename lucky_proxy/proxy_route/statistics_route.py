from nsanic.handler_http import Urls

from lucky_proxy.interface.proxy_statistics import ProxyIndexStatistics

"""
代理统计相关统计相关
"""
# 路由请添加在这里
STATISTICS_APIS = [
    # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)
    # 主页统计
    Urls("/IndexStatistics", ProxyIndexStatistics),


]
