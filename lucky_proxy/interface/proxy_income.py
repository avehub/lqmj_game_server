import time
from datetime import datetime

from nsanic.libs import tool_jwt, tool_dt

from common.public.enum_const import JWType
from lucky_proxy.base_api import ProxyAuthApi
from sanic import Request

from lucky_proxy.game_adapter.game_data_adapter import GameDataAdapter, PromotionOrderDataDTO, PromotionAddUserDTO
from lucky_proxy.logic.order_statistics import ProxyOrderStatistics
from lucky_proxy.model_db.main import ProxyUserWallet, ProxyMonthSettlement, ProxyOrderDividendRecords

"""
代理钱包收益
"""


class ProxyWallet(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        wallet = await ProxyUserWallet.get_by_pk(kwargs.get("uid"),
                                                 field=["assistance_program_income", "room_income"])
        income = {
            "today_income": 0.00,
            "current_month_income": 0.00,
            "assistance_program_income": wallet.get("assistance_program_income"),
            "room_income": wallet.get("room_income")
        }
        self.answer(self.sta_code.PASS, income, hint='查询成功!')


"""
代理 月收入
"""


class ProxyMonthIncome(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        last_id = self.check_int(req.args.get("last_id"), require=True, p_name="last_id")
        # promotion_page = await PromotionCode.query_promotion_code(proxy_id=kwargs.get("uid"),
        #                                                           last_id=last_id, page_size=20, )
        # self.answer(self.sta_code.PASS, promotion_page, hint="查询成功成功!")


class ProxyMonthSettlementQuery(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")

        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False
                                   , p_name="page_size", minval=10, maxval=100)
        sql = f"select  t.id ,t.month,t.created,t.total_income  from proxy_month_settlement t  where t.proxy_id={proxy_id}"
        if last_id and last_id > 0:
            sql = sql + f" and  t.id <{last_id}"
        sql = sql + f" order by t.id desc  limit {page_size}"
        settlement_page = await ProxyMonthSettlement.exec_query(sql),
        if settlement_page:
            self.answer(self.sta_code.PASS, settlement_page[0], hint="查询成功!")
        self.answer(self.sta_code.PASS, [], hint="查询成功!")


class TeamMemberIncomeDetailQuery(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")

        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        order_month = self.check_str(req.args.get("order_month"), require=True, p_name="order_month")
        member_id = self.check_int(req.args.get("member_id"), require=True, p_name="member_id")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False
                                   , p_name="page_size", minval=10, maxval=100)
        detail = await ProxyOrderStatistics.proxy_income_detail_query(proxy_id=member_id, level1_proxy_id=proxy_id
                                                                      , order_month=order_month
                                                                      , page_size=page_size,
                                                                      last_id=last_id)

        self.answer(self.sta_code.PASS, detail, hint="查询成功!")


"""

"""


class TeamMemberIncomeQuery(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        order_month = self.check_str(req.args.get("order_month"), require=True, p_name="order_month")
        order_day = self.check_str(req.args.get("order_day"), require=False, p_name="order_day")

        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False
                                   , p_name="page_size", minval=10, maxval=100)
        sql_offset = ""
        order_day_query = ""
        if last_id and last_id > 0:
            sql_offset = f" and t.proxy_id<{last_id}"
        if order_day:
            order_day_query = f" and t.order_day='{order_day}'"
        sql = f"""
            select 
                  t.proxy_id
                  ,sum(t.level1_proxy_income) level1_total_income
                 ,sum(t.order_amount) total_amount
                 ,sum(t.proxy_income) total_income
                 ,sum(case when t.order_type=1 then t.proxy_income else 0 end) total_room_income
                 ,sum(case when t.order_type=2 then t.proxy_income else 0 end) total_assistance_program_income
                 ,sum(case when t.order_type=1 then t.order_amount else 0 end) total_room_amount
                 ,sum(case when t.order_type=2 then t.order_amount else 0 end) total_assistance_program_amount
            from proxy_order_dividend_records t  where  t.level1_proxy_id={proxy_id}
                  and  t.order_month='{order_month}'
                  {sql_offset}
                  {order_day_query}
            group by t.proxy_id  order by t.proxy_id desc  limit {page_size}
        """
        detail = await ProxyOrderDividendRecords.exec_sql(sql, query=True)
        self.answer(self.sta_code.PASS, detail, hint="查询成功!")


"""
我的收益明细查询
"""


class MyIncomeDetailQuery(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")

        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        order_month = self.check_str(req.args.get("order_month"), require=True, p_name="order_month")
        order_day = self.check_str(req.args.get("order_day"), require=False, p_name="order_day")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False
                                   , p_name="page_size", minval=10, maxval=100)
        detail = await ProxyOrderStatistics.proxy_income_detail_query(proxy_id=proxy_id, order_month=order_month
                                                                      , order_day=order_day, page_size=page_size,
                                                                      last_id=last_id)

        self.answer(self.sta_code.PASS, detail, hint="查询成功!")


class GameDataAdapterOrderTest(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        """
         order_id: int
        # 订单号
        order_no: int
        player_id: int
        # 订单类型  1:房卡 2:助农收益
        order_type: int
        # 商品数量
        goods_number: int
        # 单价 如：18.00 28.00
        price: Decimal
        # 订单总金额
        order_amount: Decimal
        # 代理分成比例 0.6 0.8
        dividend_rate: Decimal
        # 订单时间（创建时间）
        order_time: int
        """
        json = req.json
        p = PromotionOrderDataDTO(111, 1, 555, 1, 1, 18.00, 100.00, 0.65, time.time())
        await  GameDataAdapter.sync_promotion_order_data(p)
        self.answer(self.sta_code.PASS, {}, hint="查询成功!")
