import random
import string

from nsanic.libs.component import LogMeta

from lucky_proxy.config import ConfSrv, conf_srv
from lucky_proxy.model_db.main import ProxyPromotionRelation, ProxyOrderDividendRecords

"""
创建推广码
"""


class ProxySummary(LogMeta):
    conf: ConfSrv = conf_srv
    """
    推广链接下的玩家分页查询
    """

    @classmethod
    async def query_player_page(cls, proxy_id: int, page_size: int, last_id: int,
                                promotion_id=None, sort=None):
        sql = f"select t.id,t.player_id,t.promotion_day ,0 total_player,0 total_amount , '' avatar,'' nick_name," \
              f"t.created from " \
              f"proxy_promotion_relation t   where   t.proxy_id={proxy_id}"

        if last_id:
            sql = sql + f" and t.id <{last_id}"

        if promotion_id:
            sql = sql + f" and t.promotion_id <{promotion_id}"

        if sort:
            sql = sql + f" order by {'total_amount desc' if sort == 1 else 'total_amount asc'}"
        elif last_id:
            sql = sql + f" order by t.id desc"

        sql += f" limit {page_size} "
        return await ProxyPromotionRelation.exec_sql(sql, query=True)

    @classmethod
    async def query_team_member_page(cls, level1_proxy_id: int, page_size: int, last_id: int, promotion_id=None,
                                     sort=None):
        sql = " select t.id ,t.total_player,t.total_amount ,t.created, u.avatar,u.name  " \
              f" from proxy_user_wallet t left join  user u  on u.uid=t.id   " \
              f" where   t.level1_proxy_id={level1_proxy_id}"
        if last_id:
            sql = sql + f" and t.id <{last_id}"

        if promotion_id:
            sql = sql + f" and t.promotion_id <{promotion_id}"

        if sort:
            sql = sql + f" order by {'total_amount desc ' if sort == 1 else 'total_amount asc'},t.id desc"

        elif last_id and last_id > 0:
            sql = sql + f" and t.id <{last_id}"
        sql += f" limit {page_size} "
        return await ProxyPromotionRelation.exec_sql(sql, query=True)


"""
收益明细查询
"""


class IncomeDetailQuery(LogMeta):
    async def get(self
                  , proxy_id: int
                  , level1_proxy_id: int | None = None
                  , order_month: str | None = None
                  , order_day: str | None = None
                  , page_size: int | None = None
                  , last_id: int | None = None):
        sql = f"select  t.id ,t.order_amount,t.order_month,t.order_month" \
              f",t.proxy_income,t.order_type,t.created  from proxy_order_dividend_records t  " \
              f" where t.proxy_id={proxy_id} " \
              f" and t.order_month='{order_month}'"
        if level1_proxy_id:
            sql = sql + f" and level1_proxy_id={level1_proxy_id} "
        if order_day:
            sql = sql + f" and  t.order_day='{order_day}'"
        if last_id and last_id > 0:
            sql = sql + f" and  t.id <{last_id}"
        sql = sql + f" order by t.id desc  limit {page_size}"
        detail = await ProxyOrderDividendRecords.exec_query(sql),
        if detail:
            self.answer(self.sta_code.PASS, detail[0], hint="查询成功!")
        self.answer(self.sta_code.PASS, None, hint="查询成功!")
