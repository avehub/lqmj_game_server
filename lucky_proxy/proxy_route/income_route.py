from nsanic.handler_http import Urls

from lucky_proxy.interface.promotion import PromotionCreator, PromotionCodeQuery
from lucky_proxy.interface.proxy_income import ProxyMonthIncome, \
    ProxyMonthSettlementQuery, MyIncomeDetailQuery, TeamMemberIncomeDetailQuery, GameDataAdapterOrderTest, \
    TeamMemberIncomeQuery, ProxyIncomeQuery
"""
代理收入、统计相关
"""
# 路由请添加在这里
INCOME_APIS = [
    # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)


    # 代理收益(总概览)
    Urls("proxy/ProxyIncomeQuery", ProxyIncomeQuery),

    # 月结算明细查询
    Urls("proxy/ProxyMonthSettlementQuery", ProxyMonthSettlementQuery),

    # 团队成员月收入明细查询
    Urls("proxy/TeamMemberIncomeDetailQuery", TeamMemberIncomeDetailQuery),

    #  团队成员收益
    Urls("proxy/TeamMemberIncomeQuery", TeamMemberIncomeQuery),

    # 我的收益明细查询
    Urls("proxy/MyIncomeDetailQuery", MyIncomeDetailQuery),

    #
    Urls("proxy/GameDataAdapterOrderTest", GameDataAdapterOrderTest)
]
