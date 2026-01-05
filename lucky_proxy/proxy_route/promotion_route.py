from nsanic.handler_http import Urls

from lucky_proxy.interface.promotion import PromotionCreator, PromotionCodeQuery, PromotionCodeDetailQuery
"""
推广码相关接口
"""
# 路由请添加在这里
PROMOTION_APIS = [
    # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)
    # 创建推广码
    Urls("/PromotionCodeCreate", PromotionCreator),

    # 推广码查询
    Urls("/PromotionCodeQuery", PromotionCodeQuery),

    # 推广码收益明细
    Urls("/PromotionCodeDetailQuery", PromotionCodeDetailQuery),


]
