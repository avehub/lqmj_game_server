from nsanic.handler_http import Urls

from lucky_proxy.interface.proxy import ProxyInfoQuery, ProxyBankQuery, ProxyPromotionCodeQuery
"""
代理用户相关
"""
# 路由请添加在这里
USER_APIS = [
    # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)

    #  代理信息查询
    Urls("proxy/ProxyInfoQuery", ProxyInfoQuery),

    # 代理银行卡信息
    Urls("proxy/ProxyBankQuery", ProxyBankQuery),

    # 代理推广码查询
    Urls("proxy/ProxyPromotionCodeQuery", ProxyPromotionCodeQuery)
]
