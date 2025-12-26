import random
import string

from nsanic.libs.component import LogMeta

from lucky_proxy.config import ConfSrv, conf_srv
from lucky_proxy.model_db.main import ProxyPromotionCode, ProxyPromotionRelation, ProxyUser

"""
创建推广码
"""


class ProxyPromotionUser:
    pass


class PromotionCode(LogMeta):
    conf: ConfSrv = conf_srv

    @classmethod
    async def create_promotion_code(cls, proxy_id, promotion_code_name):
        promotion_code = {
            "proxy_id": proxy_id,
            "promotion_code_name": promotion_code_name,
            "promotion_code": cls.generate_invite_code(10),
            "url": "http://test.com",
            "is_deleted": 0,
            "level": 1,
        }
        try:
            # h5_url=await cls.conf.rds.g
            # promotion_code.update({"url": h5_url})
            proxy_user: ProxyUser = await ProxyUser.get_by_pk(proxy_id, field=["id", "proxy_level"])
            promotion_code["level"] = proxy_user.get("proxy_level")
            promotion_code = await ProxyPromotionCode.add_one(promotion_code)
            return promotion_code.to_dict()
        except Exception as e:
            cls.log_err(f"代理邀请码创建失败err{e}")
            return None

    """
    推广链接分页查询（滚动分页）
    """

    @classmethod
    async def query_promotion_code(cls, proxy_id, last_id, page_size):
        param = {"proxy_id": proxy_id, "is_deleted": 0}
        if last_id and last_id > 0:
            param["id__lt"] = last_id

        return await ProxyPromotionCode.get_by_dict(param, limit=page_size, orders=["-id"])

    """
    推广链接下的玩家分页查询
    """

    @classmethod
    async def query_player_page(cls, proxy_id: int, page_size: int, last_id: int, level1_proxy_id: int,
                                promotion_id=None, sort=None):
        sql = f"select t.id,t.player_id,t.promotion_day ,0 total_player,0 total_income ,'' nick_name,t.created from " \
              f"proxy_promotion_relation t   where   t.proxy_id={proxy_id}"
        if last_id:
            sql = sql + f" and t.id <{last_id}"
        if promotion_id:
            sql = sql + f" and t.promotion_id <{promotion_id}"
        sql += f" order by t.id  desc  limit {page_size} "
        return await ProxyPromotionRelation.exec_sql(sql, query=True)
