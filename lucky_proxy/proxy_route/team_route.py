"""
代理团队路由
"""
from nsanic.handler_http import Urls

from lucky_proxy.interface.proxy import AddLevel2Proxy, RemoveLevel2Proxy, ModifyLevel2ProxyRate
from lucky_proxy.interface.team import TeamSummary, Player, TeamMemberQuery, TeamMemberInfoDetailQuery

# 路由请添加在这里
TEAM_APIS = [
    # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)

    # 设置二级代理
    Urls("proxy/AddLevel2Proxy", AddLevel2Proxy),

    # 团队人数概览
    Urls("proxy/TeamSummary", TeamSummary),

    # 绑定用户查询
    Urls("proxy/PlayerQuery", Player),

    #  团队成员查询
    Urls("proxy/TeamMemberQuery", TeamMemberQuery),

    #  团队成员详细信息查询
    Urls("proxy/TeamMemberInfoDetailQuery", TeamMemberInfoDetailQuery),

    # 删除二级代理
    Urls("proxy/RemoveLevel2Proxy", RemoveLevel2Proxy),

    # 修改二级代理分成比例
    Urls("proxy/ModifyLevel2ProxyRate", ModifyLevel2ProxyRate),
]
