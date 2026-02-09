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
        data = {
            "time_node": start_time,
            "total_income": total_income,
            "roomcard_income": roomcard_income,
            "agriculture_income": agriculture_income,
            "total_orders": total_orders,
            "roomcard_orders": roomcard_orders,
            "agriculture_orders": agriculture_orders,
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
        end_ts = tool_dt.day_end(int(end_date.timestamp()))
        data = await cls.db_model.filter(time_node__gte=start_ts, time_node__lte=end_ts).order_by("time_node").values()
        return data or []
