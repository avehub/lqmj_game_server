import time
from datetime import datetime
from decimal import Decimal

from nsanic.libs import tool_jwt, tool_dt

from common.public.enum_const import JWType
from lucky_proxy.base_api import ProxyAuthApi, BaseApi
from sanic import Request

from lucky_proxy.const import ProxyLevel
from lucky_proxy.game_adapter.game_data_adapter import GameDataAdapter, PromotionOrderDataDTO, PromotionAddUserDTO
from lucky_proxy.logic.game_data_sync import Level1ProxyDTO, UpgradeProxyDTO
from lucky_proxy.logic.order_statistics import ProxyOrderStatistics
from lucky_proxy.logic.proxy_settlement import ProxySettlementProcessor, ProxysJobExecutor
from lucky_proxy.model_db.main import ProxyUserWallet, ProxyMonthSettlement, ProxyOrderDividendRecords
from lucky_proxy.model_db.main import ProxyOrderDividendRecords

"""
代理钱包收益
"""


class ProxyIncomeQuery(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        wallet = await ProxyUserWallet.get_by_pk(kwargs.get("uid"),
                                                 field=["assistance_program_income", "room_income", "proxy_level"])
        today = datetime.now().strftime('%Y-%m-%d')
        month = datetime.now().strftime('%Y-%m')
        month_income = await ProxyOrderStatistics.proxy_month_income_query(kwargs.get("uid"), month, today)
        if ProxyLevel.LEVEL_1 == wallet.get("proxy_level"):
            level2_month_income = await ProxyOrderStatistics.proxy_level2_income_query(kwargs.get("uid"), month, today)
            income = {
                "today_income": month_income.get("today_income") + level2_month_income.get("today_income"),
                "current_month_income": month_income.get("income") + level2_month_income.get("income"),
                "assistance_program_income": wallet.get("assistance_program_income") + level2_month_income.get(
                    "assistance_program_income"),
                "room_income": wallet.get("room_income") + level2_month_income.get("room_income"),
            }
        else:
            income = {
                "today_income": month_income.get("today_income"),
                "current_month_income": month_income.get("income"),
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
        start_day = self.check_str(req.args.get("start_day"), require=False, p_name="start_day")
        end_day = self.check_str(req.args.get("end_day"), require=False, p_name="end_day")

        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False, p_name="page_size", minval=10,
                                   maxval=100)

        sql_offset = ""
        order_day_query = " "
        if last_id and last_id > 0: 
            sql_offset = f" and t.proxy_id<{last_id}"
        if start_day and end_day:
            order_day_query = f" and t.order_day>='{start_day}' and t.order_day<='{end_day}'"
        sql = f"""
            select 
                  t.proxy_id as uid,
                  t.proxy_id
                 ,u.name
                 ,u.avatar
                 ,sum(t.level1_proxy_income) level1_total_income
                 ,sum(t.order_amount) total_amount
                 ,sum(t.proxy_income) total_income
                 ,sum(case when t.order_type=1 then t.proxy_income else 0 end) total_room_income
                 ,sum(case when t.order_type=2 then t.proxy_income else 0 end) total_assistance_program_income
                 ,sum(case when t.order_type=1 then t.order_amount else 0 end) total_room_amount
                 ,sum(case when t.order_type=2 then t.order_amount else 0 end) total_assistance_program_amount
            from proxy_order_dividend_records t  
                  LEFT JOIN  user u  on u.uid=t.proxy_id 
                  LEFT JOIN  proxy_user pu  on pu.id=t.proxy_id  
            where  t.level1_proxy_id={proxy_id} 
                    {sql_offset}
                    {order_day_query}
            group by t.proxy_id ,u.name,u.avatar order by t.proxy_id desc  limit {page_size}
        """
        print(sql)
        detail = await ProxyOrderDividendRecords.exec_sql(sql, query=True)
        self.answer(self.sta_code.PASS, detail, hint="查询成功!")


"""
我的收益明细查询
"""


class MyIncomeDetailQuery(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")

        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        player_id = self.check_int(req.args.get("uid"), require=False, p_name="uid")
        start_day = self.check_str(req.args.get("start_day"), require=False, p_name="start_day")
        end_day = self.check_str(req.args.get("end_day"), require=False, p_name="end_day")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False
                                   , p_name="page_size", minval=10, maxval=100)
        detail = await ProxyOrderStatistics.proxy_income_detail_query(proxy_id=proxy_id, player_id=player_id, start_day=start_day, end_day=end_day, page_size=page_size,
                                                                      last_id=last_id)

        self.answer(self.sta_code.PASS, detail, hint="查询成功!")

class MyRechargeOrders(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        page = self.check_int(req.args.get("page"), require=False, default=1, p_name="page")
        page_size = self.check_int(req.args.get("page_size"), require=False, default=20, p_name="page_size", minval=10, maxval=100)
        start_day = self.check_str(req.args.get("start_day"), require=False, p_name="start_day")
        end_day = self.check_str(req.args.get("end_day"), require=False, p_name="end_day")
        where = f" o.purchase_uid={proxy_id} "
        try:
            from datetime import datetime
            if start_day:
                start_ts = int(datetime.strptime(start_day + " 00:00:00", "%Y-%m-%d %H:%M:%S").timestamp())
                where += f" and o.updated>={start_ts} "
            if end_day:
                end_ts = int(datetime.strptime(end_day + " 23:59:59", "%Y-%m-%d %H:%M:%S").timestamp())
                where += f" and o.updated<={end_ts} "
        except Exception:
            pass
        offset = (page - 1) * page_size
        sql_count = f"select count(1) as cnt from orders o where {where}"
        print(sql_count)
        total_row = await ProxyOrderDividendRecords.exec_sql(sql_count, query=True, for_one=True)
        total = total_row.get("cnt", 0) if isinstance(total_row, dict) else 0
        sql = f"""
        select o.id, o.order_no, o.created, o.amount, o.status, o.updated, o.num, o.sku, o.currency, o.pay_mode,
               u.name as user_name, u.avatar as user_avatar, o.purchase_uid as uid, g.name as good_name
        from orders o
        left join goods g on g.sku = o.sku
        left join user u on u.uid = o.purchase_uid
        where {where}
        order by o.id desc
        limit {page_size} offset {offset}
        """
        print(sql)
        rows = await ProxyOrderDividendRecords.exec_sql(sql, query=True) or []
        return self.answer(self.sta_code.PASS, {"page": page, "page_size": page_size, "total": total, "list": rows}, hint="查询成功!")

class MyRechargeTotal(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        start_day = self.check_str(req.args.get("start_day"), require=False, p_name="start_day")
        end_day = self.check_str(req.args.get("end_day"), require=False, p_name="end_day")
        where = f" purchase_uid={proxy_id} "
        try:
            from datetime import datetime
            if start_day:
                start_ts = int(datetime.strptime(start_day + " 00:00:00", "%Y-%m-%d %H:%M:%S").timestamp())
                where += f" and updated>={start_ts} "
            if end_day:
                end_ts = int(datetime.strptime(end_day + " 23:59:59", "%Y-%m-%d %H:%M:%S").timestamp())
                where += f" and updated<={end_ts} "
        except Exception:
            pass
        sql = f"select ifnull(sum(amount),0.00) as total_amount, count(1) as total_orders from orders where {where}"
        row = await ProxyOrderDividendRecords.exec_sql(sql, query=True, for_one=True) or {}
        return self.answer(self.sta_code.PASS, {"total_amount": float(row.get("total_amount", 0.0)), "total_orders": row.get("total_orders", 0)}, hint="查询成功!")

class GameDataAdapterOrderTest(BaseApi):
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
        p = PromotionOrderDataDTO(1113, 1, 555, 1, 1, 18.00, 0.1, 0.7, time.time())

        #sync_promotion_order_data_res = await  GameDataAdapter.sync_promotion_order_data(p)
        # await  GameDataAdapter.sync_promotion_user(PromotionAddUserDTO(999,"pMHib1TpYH",1,1))

        p1 = Level1ProxyDTO(100003,"ddd","ssss",1,1)
        res = await  GameDataAdapter.add_level1_proxy(p1)

        # await  ProxysJobExecutor.every_month_summary()
        # await processor.process_monthly_settlement()
        self.answer(self.sta_code.PASS, res, hint="查询成功!")


class TestOrder(BaseApi):
    async def post(self, req: Request, **kwargs):
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

        data = req.json
        p = PromotionOrderDataDTO(data.get("order_id")
                                  , data.get("order_no")
                                  , data.get("player_id")
                                  , data.get("order_type")
                                  , data.get("goods_number")
                                  , data.get("price")
                                  , data.get("order_amount")
                                  , data.get("dividend_rate")
                                  , data.get("order_time")
                                  )
        sync_promotion_order_data_res = await  GameDataAdapter.sync_promotion_order_data(p)
        self.answer(self.sta_code.PASS, sync_promotion_order_data_res, hint="提交成功!")


class TestInvite(BaseApi):
    async def post(self, req: Request, **kwargs):
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

        data = req.json
        p = PromotionAddUserDTO(data.get("player_id")
                                , data.get("promotion_code")
                                , 1
                                , time.time()
                                )
        sync_promotion_order_data_res = await  GameDataAdapter.sync_promotion_user(p)
        self.answer(self.sta_code.PASS, sync_promotion_order_data_res, hint="提交成功!")
