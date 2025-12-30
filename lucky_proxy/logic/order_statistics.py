# coding=utf-8
"""
代理统计相关
"""
from lucky_proxy.model_db.main import ProxyOrderDividendRecords
from nsanic.libs.component import LogMeta


class ProxyOrderStatistics(LogMeta):

    @classmethod
    async def proxy_income_detail_query(cls
                                        , proxy_id: int
                                        , level1_proxy_id: int | None = None
                                        , order_month: str | None = None
                                        , order_day: str | None = None
                                        , last_id: int | None = None
                                        , page_size=20):
        sql = f"select  t.id ,t.order_amount,t.order_month" \
              f",t.proxy_income,t.order_type,t.created  " \
              f" from proxy_order_dividend_records t  " \
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
            return detail[0]
        return []

    @classmethod
    async def proxy_today_income_query(cls, proxy_id: int, today: str):
        sql = f"""
           select  ifnull(sum(t.proxy_income),0.00)  income  from proxy_order_dividend_records t 
           where  t.proxy_id={proxy_id}  and  t.order_day='{today}' 
        """
        return await ProxyOrderDividendRecords.exec_query(sql, for_one=True)

    @classmethod
    async def proxy_level2_income_query(cls, proxy_id: int, month: str, today: str):
        sql = f"""
                 select  ifnull(sum(t.level1_proxy_income),0.00)  income
                   , ifnull(sum(case when t.order_day='{today}'  then t.level1_proxy_income else 0 end),0.00) today_income
                    , ifnull(sum(case when t.order_type=1  then t.level1_proxy_income else 0 end),0.00) room_income
                    , ifnull(sum(case when t.order_type=2  then t.level1_proxy_income else 0 end),0.00) assistance_program_income
                   from proxy_order_dividend_records t 
                 where  t.level1_proxy_id={proxy_id}  and  t.order_month='{month}' and t.level=2
              """
        return await ProxyOrderDividendRecords.exec_query(sql, for_one=True)
    @classmethod
    async def proxy_month_income_query(cls, proxy_id: int, month: str, today: str):
        sql = f"""
           select  ifnull(sum(t.proxy_income),0.00)  income
             , ifnull(sum(case when t.order_day='{today}'  then t.proxy_income else 0 end),0.00) today_income
             , ifnull(sum(case when t.order_type=1  then t.proxy_income else 0 end),0.00) room_income
              , ifnull(sum(case when t.order_type=2  then t.proxy_income else 0 end),0.00) assistance_program_income
             from proxy_order_dividend_records t 
           where  t.proxy_id={proxy_id}  and  t.order_month='{month}' 
        """
        return await ProxyOrderDividendRecords.exec_query(sql, for_one=True)
