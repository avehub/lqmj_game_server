from typing import Any


from nsanic.libs import tool_dt
from datetime import timedelta, datetime
from lucky_proxy.model_db.main import ProxyPromotionRelation
from lucky_proxy.model_db.main import ProxyOrderDividendRecords
from lucky_game.model_db.main import Orders
from lucky_proxy.model_db.main import ProxyUser
from common.model_rc.user_good_exchange import UserGoodExchangeRC
from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.base_store import GoodRC
from lucky_game.model_rc.stats_income_daily import StatsIncomeDailyRC
from datetime import timedelta


class DistributionTotal(AdminAuthApi):
    async def get(self, req: Request, **kwargs):
        start_time = tool_dt.day_begin()
        end_time = tool_dt.day_end()
        orders, _ = await OrderRC.get_order_filter(status=99, start_time=start_time, end_time=end_time)
        if not orders:
            return self.answer(data={"total_income": 0, "roomcard_income": 0, "agriculture_income": 0, "total_orders": 0, "roomcard_orders": 0, "agriculture_orders": 0, "pending_settlement": 0})
        sku_list = list[str | Any]({o["sku"] for o in orders})
        goods, _ = await GoodRC.get_good_filter(sku=sku_list)
        g_map = {g["sku"]: g for g in goods} if goods else {}
        total_income = 0
        roomcard_income = 0
        agriculture_income = 0
        total_orders = 0
        roomcard_orders = 0
        agriculture_orders = 0
        for o in orders:
            amount = o.get("amount") or 0
            total_income += amount
            total_orders += 1
            g = g_map.get(o["sku"])
            if g:
                t = g.get("type")
                if t == 4:
                    roomcard_income += amount
                    roomcard_orders += 1
                elif t == 15:
                    agriculture_income += amount
                    agriculture_orders += 1
        pending_settlement = agriculture_income
        return self.answer(data={"total_income": float(total_income), "roomcard_income": float(roomcard_income), "agriculture_income": float(agriculture_income), "total_orders": total_orders, "roomcard_orders": roomcard_orders, "agriculture_orders": agriculture_orders, "pending_settlement": float(pending_settlement)})


def _parse_day_start(val):
    if val is None:
        return datetime.fromtimestamp(tool_dt.day_begin())
    if isinstance(val, (int, float)):
        dt = datetime.fromtimestamp(int(val))
        return datetime(dt.year, dt.month, dt.day)
    if isinstance(val, str) and val.isdigit():
        dt = datetime.fromtimestamp(int(val))
        return datetime(dt.year, dt.month, dt.day)
    try:
        return datetime.strptime(val, "%Y-%m-%d")
    except Exception:
        return datetime.fromtimestamp(tool_dt.day_begin())


class DistributionTrend(AdminAuthApi):
    async def get(self, req: Request, **kwargs):
        s = req.args.get("start_date")
        e = req.args.get("end_date")
        start_date = _parse_day_start(s)
        end_date = _parse_day_start(e)
        today = datetime.fromtimestamp(tool_dt.day_begin())
        out = []
        cur = start_date
        while cur <= end_date:
            if cur < today:
                recs = await StatsIncomeDailyRC.get_range(cur, cur)
                if recs:
                    r = recs[0]
                    out.append({"date": r["date"].strftime("%Y-%m-%d"), "total_income": float(r["total_income"]), "roomcard_income": float(r["roomcard_income"]), "agriculture_income": float(r["agriculture_income"]), "total_orders": r["total_orders"], "roomcard_orders": r["roomcard_orders"], "agriculture_orders": r["agriculture_orders"]})
                else:
                    out.append({"date": cur.strftime("%Y-%m-%d"), "total_income": 0.0, "roomcard_income": 0.0, "agriculture_income": 0.0, "total_orders": 0, "roomcard_orders": 0, "agriculture_orders": 0})
            else:
                start_time = int(cur.timestamp())
                end_time = tool_dt.day_end(start_time)
                orders, _ = await OrderRC.get_order_filter(status=99, start_time=start_time, end_time=end_time)
                total_income = 0
                roomcard_income = 0
                agriculture_income = 0
                total_orders = 0
                roomcard_orders = 0
                agriculture_orders = 0
                if orders:
                    sku_list = list({o["sku"] for o in orders})
                    goods, _ = await GoodRC.get_good_filter(sku=sku_list)
                    g_map = {g["sku"]: g for g in goods} if goods else {}
                    for o in orders:
                        amount = o.get("amount") or 0
                        total_income += amount
                        total_orders += 1
                        g = g_map.get(o["sku"])
                        if g:
                            t = g.get("type")
                            if t == 4:
                                roomcard_income += amount
                                roomcard_orders += 1
                            elif t == 15:
                                agriculture_income += amount
                                agriculture_orders += 1
                out.append({"date": cur.strftime("%Y-%m-%d"), "total_income": float(total_income), "roomcard_income": float(roomcard_income), "agriculture_income": float(agriculture_income), "total_orders": total_orders, "roomcard_orders": roomcard_orders, "agriculture_orders": agriculture_orders})
            cur = cur + timedelta(days=1)
        return self.answer(data=out)

class DistributionOrderDetail(AdminAuthApi):
    async def get(self, req: Request, **kwargs):
        page = self.check_int(req.args.get("page"), require=False, default=1, p_name="page")
        page_size = self.check_int(req.args.get("page_size"), require=False, default=20, p_name="page_size")
        offset = (page - 1) * page_size
        sql_count = "SELECT COUNT(1) AS cnt FROM proxy_order_dividend_records"
        total_rows = await ProxyOrderDividendRecords.exec_sql(sql_count, query=True)
        total = total_rows[0]["cnt"] if total_rows else 0
        sql = f"""
        SELECT r.id, r.order_id, o.order_no, r.player_id, r.proxy_id, pu.proxy_name,
               r.order_type, o.num, r.order_amount, r.proxy_income, r.platform_income,
               o.status AS order_status, r.order_time
        FROM proxy_order_dividend_records r
        LEFT JOIN orders o ON o.id = r.order_id
        LEFT JOIN proxy_user pu ON pu.id = r.proxy_id
        ORDER BY r.id DESC
        LIMIT {page_size} OFFSET {offset}
        """
        rows = await ProxyOrderDividendRecords.exec_sql(sql, query=True) or []
        data = []
        for r in rows:
            data.append({
                "order_no": r["order_no"],
                "player_id": r["player_id"],
                "proxy_id": r["proxy_id"],
                "proxy_name": r.get("proxy_name") or "",
                "order_type": r["order_type"],
                "num": r["num"],
                "order_amount": float(r["order_amount"]) if r["order_amount"] is not None else 0.0,
                "proxy_income": float(r["proxy_income"]) if r["proxy_income"] is not None else 0.0,
                "platform_income": float(r["platform_income"]) if r["platform_income"] is not None else 0.0,
                "order_status": r["order_status"],
                "order_time": r["order_time"],
            })
        return self.answer(data={"page": page, "page_size": page_size, "total": total, "list": data})

class DistributionAgriOrders(AdminAuthApi):
    async def get(self, req: Request, **kwargs):
        status_k = self.check_str(req.args.get("status"), require=False, p_name="状态")  # all|shipped|unshipped
        order_no = self.check_str(req.args.get("order_no"), require=False, p_name="订单号")
        tracking_no = self.check_str(req.args.get("tracking_no"), require=False, p_name="快递单号")
        phone = self.check_phone_number(req.args.get("phone"), require=False)
        uid = self.check_int(req.args.get("uid"), require=False, p_name="玩家UID")
        start = self.check_int(req.args.get("start_time"), require=False, p_name="开始时间")
        end = self.check_int(req.args.get("end_time"), require=False, p_name="结束时间")
        page = self.check_int(req.args.get("page"), require=False, default=1, p_name="分页")
        page_size = self.check_int(req.args.get("page_size"), require=False, default=20, p_name="每页数量")
        where = "1=1"
        if uid is not None:
            where += f" AND uid = {uid}"
        if phone is not None:
            where += f" AND phone = {phone}"
        if order_no:
            where += f" AND exchange_no = '{order_no}'"
        if tracking_no:
            where += f" AND express_no = '{tracking_no}'"
        if status_k == "shipped":
            where += f" AND express_no <> ''"
        elif status_k == "unshipped":
            where += f" AND (express_no = '' OR express_no = '0' OR express_no IS NULL)"
        if start is not None:
            where += f" AND updated >= {start}"
        if end is not None:
            where += f" AND updated <= {end}"
        count_sql = f"SELECT COUNT(1) AS total FROM user_good_exchange WHERE {where}"
        total_row = await UserGoodExchangeRC.db_model.exec_sql(count_sql, query=True)
        total = total_row[0]["total"] if total_row else 0
        offset = (page - 1) * page_size
        sql = f"""
        SELECT id, uid, good_id, num, phone, real_name, region, address, exchange_no, express_no, updated, status
        FROM user_good_exchange
        WHERE {where}
        ORDER BY id DESC
        LIMIT {page_size} OFFSET {offset}
        """
        rows = await UserGoodExchangeRC.db_model.exec_sql(sql, query=True) or []
        out = []
        for r in rows:
            g = await GoodRC.get_good_by_id(r["good_id"])
            product_info = {"good_id": r["good_id"], "name": g.get("name") if g else "", "num": r["num"]}
            receiver_info = {"real_name": r.get("real_name") or "", "phone": r.get("phone") or "", "region": r.get("region") or "", "address": r.get("address") or ""}
            out.append({
                "id": r["id"],
                "order_no": r.get("exchange_no") or "",
                "uid": r["uid"],
                "product_info": product_info,
                "receiver_info": receiver_info,
                "tracking_no": r.get("express_no") or "",
                "shipped_time": r.get("updated") or 0,
                "status": r.get("status"),
                "operation": "view",
            })
        return self.answer(data={"page": page, "page_size": page_size, "total": total, "list": out})

class DistributionAgriShip(AdminAuthApi):
    async def post(self, req: Request, **kwargs):
        nos = req.json.get("order_nos")
        tracking_no = self.check_str(req.json.get("tracking_no"), require=True, p_name="快递单号")
        express_id = self.check_int(req.json.get("express_id"), require=False, p_name="物流公司")
        if isinstance(nos, str):
            nos = [s.strip() for s in nos.split(",") if s.strip()]
        if not isinstance(nos, list) or not nos:
            return self.answer(self.sta_code.FAIL, hint="订单号列表为空")
        now = tool_dt.cur_time()
        express_id_sql = f", express_id = {express_id}" if express_id is not None else ""
        in_list = ",".join([f"'{x}'" for x in nos])
        sql = f"UPDATE user_good_exchange SET express_no = '{tracking_no}'{express_id_sql}, status = 1, updated = {now} WHERE exchange_no IN ({in_list})"
        sta = await UserGoodExchangeRC.db_model.exec_sql(sql)
        return self.answer(data={"updated": sta or 0, "order_nos": nos})

class DistributionAgriTrend(AdminAuthApi):
    async def get(self, req: Request, **kwargs):
        s = req.args.get("start_date")
        e = req.args.get("end_date")
        start_date = _parse_day_start(s)
        end_date = _parse_day_start(e)
        today = datetime.fromtimestamp(tool_dt.day_begin())
        out = []
        cur = start_date
        while cur <= end_date:
            if cur < today:
                recs = await StatsIncomeDailyRC.get_range(cur, cur)
                if recs:
                    r = recs[0]
                    out.append({"date": r["date"].strftime("%Y-%m-%d"), "agriculture_income": float(r["agriculture_income"]), "agriculture_orders": r["agriculture_orders"]})
                else:
                    out.append({"date": cur.strftime("%Y-%m-%d"), "agriculture_income": 0.0, "agriculture_orders": 0})
            else:
                start_time = int(cur.timestamp())
                end_time = tool_dt.day_end(start_time)
                orders, _ = await OrderRC.get_order_filter(status=99, start_time=start_time, end_time=end_time)
                agriculture_income = 0
                agriculture_orders = 0
                if orders:
                    sku_list = list({o["sku"] for o in orders})
                    goods, _ = await GoodRC.get_good_filter(sku=sku_list)
                    g_map = {g["sku"]: g for g in goods} if goods else {}
                    for o in orders:
                        g = g_map.get(o["sku"])
                        if g and g.get("type") == 15:
                            amount = o.get("amount") or 0
                            agriculture_income += amount
                            agriculture_orders += 1
                out.append({"date": cur.strftime("%Y-%m-%d"), "agriculture_income": float(agriculture_income), "agriculture_orders": agriculture_orders})
            cur = cur + timedelta(days=1)
        return self.answer(data=out)


class PromotionUserTrend(AdminAuthApi):
    async def get(self, req: Request, **kwargs):
        s = req.args.get("start_date")
        e = req.args.get("end_date")
        start_date = _parse_day_start(s)
        end_date = _parse_day_start(e)
        
        start_ts = int(start_date.timestamp())
        end_ts = tool_dt.day_end(int(end_date.timestamp()))
        sql = f"""
        SELECT DATE_FORMAT(FROM_UNIXTIME(created),'%Y-%m-%d') AS d, COUNT(DISTINCT player_id) AS cnt
        FROM proxy_promotion_relation
        WHERE created BETWEEN {start_ts} AND {end_ts}
        GROUP BY d
        ORDER BY d ASC
        """
        rows = await ProxyPromotionRelation.exec_sql(sql, query=True) or []
        m = {r["d"]: r["cnt"] for r in rows}
        out = []
        cur = start_date
        while cur <= end_date:
            ds = cur.strftime("%Y-%m-%d")
            out.append({"date": ds, "new_users": int(m.get(ds, 0))})
            cur = cur + timedelta(days=1)
        return self.answer(data=out)

class DistributionStatistics(AdminAuthApi):
    """ 获取订单统计金额 """
    async def get(self, req: Request, **kwargs):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        out = {"total_amount": 0, "proxy_amount": 0}
        orders, _ = await OrderRC.get_order_filter(status=99, currency=5, start_time=start_time, end_time=end_time)
        sql_count = f"SELECT SUM(order_amount) AS proxy_amount FROM proxy_order_dividend_records WHERE order_time>={start_time} AND order_time<={end_time}"
        proxy_amount = await ProxyOrderDividendRecords.exec_sql(sql_count, query=True)
        if orders:
            for o in orders:
                out["total_amount"] += o.get("amount") or 0
        if proxy_amount:
            out["proxy_amount"] = proxy_amount[0]["proxy_amount"] or 0
        return self.answer(data=out)
