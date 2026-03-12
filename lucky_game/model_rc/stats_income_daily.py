from datetime import datetime, timedelta
from nsanic.orm.rc_model import RCModel
from lucky_game.model_db.main import StatsIncomeDaily
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.base_store import GoodRC
from nsanic.libs import tool_dt


class StatsIncomeDailyRC(RCModel):
    db_model = StatsIncomeDaily
    tb_name = db_model.sheet_name()

    @classmethod
    async def upsert_for_day(cls, day: datetime):
        start_time = int(datetime(day.year, day.month, day.day).timestamp())
        end_time = tool_dt.day_end(int(day.timestamp()))
        
        # 全部订单
        orders_all, _ = await OrderRC.get_order_filter(status=99, start_time=start_time, end_time=end_time)
        
        # 分销订单
        sql_dist = """
            SELECT o.*
            FROM orders o
            JOIN proxy_order_dividend_records r ON o.id = r.order_id
            WHERE o.status = 99 AND o.create_time >= ? AND o.create_time <= ?
        """
        orders_dist = await OrderRC.exec_sql(sql_dist, [start_time, end_time], query=True) or []
        
        # 自然流订单
        sql_nat = """
            SELECT o.*
            FROM orders o
            LEFT JOIN proxy_order_dividend_records r ON o.id = r.order_id
            WHERE o.status = 99 AND o.create_time >= ? AND o.create_time <= ? AND r.order_id IS NULL
        """
        orders_nat = await OrderRC.exec_sql(sql_nat, [start_time, end_time], query=True) or []
        
        async def calc_stats(orders):
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
            return total_income, roomcard_income, agriculture_income, total_orders, roomcard_orders, agriculture_orders
        
        # 计算各类统计数据
        all_stats = calc_stats(orders_all)
        dist_stats = calc_stats(orders_dist)
        nat_stats = calc_stats(orders_nat)
        
        data = {
            "time_node": start_time,
            "total_income": all_stats[0],
            "roomcard_income": all_stats[1],
            "agriculture_income": all_stats[2],
            "total_orders": all_stats[3],
            "roomcard_orders": all_stats[4],
            "agriculture_orders": all_stats[5],
            # 分销分类统计
            "distribution_income": dist_stats[0],
            "distribution_orders": dist_stats[3],
            "distribution_roomcard_income": dist_stats[1],
            "distribution_roomcard_orders": dist_stats[4],
            "distribution_agriculture_income": dist_stats[2],
            "distribution_agriculture_orders": dist_stats[5],
            # 自然流分类统计
            "natural_income": nat_stats[0],
            "natural_orders": nat_stats[3],
            "natural_roomcard_income": nat_stats[1],
            "natural_roomcard_orders": nat_stats[4],
            "natural_agriculture_income": nat_stats[2],
            "natural_agriculture_orders": nat_stats[5],
            "updated": tool_dt.cur_time(),
        }
        exist = await cls.db_model.filter(time_node=start_time).count()
        if exist:
            await cls.db_model.filter(time_node=start_time).update(**data)
        else:
            await cls.db_model.add_one(data)
        return True, data

    @classmethod
    async def get_range(cls, start_date: datetime, end_date: datetime):
        start_ts = int(datetime(start_date.year, start_date.month, start_date.day).timestamp())
        end_ts = int(datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59).timestamp())
        data = await cls.db_model.filter(time_node__gte=start_ts, time_node__lte=end_ts).order_by("time_node").values()
        return data or []
