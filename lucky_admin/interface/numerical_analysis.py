from datetime import datetime

from nsanic.libs import tool_dt
from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.records_user_login import RecordsAdEventRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC

class BuyBaseData(AdminAuthApi):
    """ 收入看板-基础数据 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        week_start_time = date_time - 86400 * 7
        yesterday_start_time = date_time - 86400
        yesterday_end_time = end_time - 86400
        last_week_start_time = week_start_time - 86400 * 7
        data = {
            "gift_count": 0,
            "good_count": 0,
            "iap_user": {
                "buy_num": 0,
                "day_ratio": 0,
                "week_ratio": 0,
            },
            "iap_money": {
                "buy_total": 0,
                "day_ratio": 0,
                "week_ratio": 0,
            },
            "iap_activate": {
                "activate_ratio": 0,
                "day_ratio": 0,
                "week_ratio": 0,
            },
        }
        # 首充礼包
        first_good_ids = [25, 52]
        # 补足礼包
        replenish_good_ids = [26, 30, 31, 32]
        # 复活礼包
        reviver_good_ids = [33, 37, 38, 39]
        # 返还礼包
        return_good_ids = [40, 41, 42, 43]
        # 所有礼包
        all_good_ids = first_good_ids + replenish_good_ids + reviver_good_ids + return_good_ids
        order_data, msg = await OrderRC.get_order_filter(start_time=last_week_start_time, end_time=end_time, currency=5, status=99)
        if order_data:
            buy_num = set()
            for order in order_data:
                # 今日
                if order.get("create_time") >= date_time and order.get("create_time") <= end_time:
                    data["gift_count"] += order.get("num")
                # 昨天
                if order.get("create_time") >= yesterday_start_time and order.get("create_time") <= yesterday_end_time:
                    data["gift_count"] += order.get("num")
                # 本周
                if order.get("create_time") >= week_start_time and order.get("create_time") <= end_time:
                    data["gift_count"] += order.get("num")
                # 上周
                if order.get("create_time") >= last_week_start_time and order.get("create_time") <= week_start_time:
                    data["gift_count"] += order.get("num")
                if order.get("good_id") in all_good_ids:
                    data["gift_count"] += order.get("num")
                if order.get("good_id") not in first_good_ids:
                    data["good_count"] += order.get("num")
                buy_num.add(order.get("uid"))
            data["iap_user"]["buy_num"] += len(buy_num)
            data["iap_user"]["day_ratio"] += len(buy_num)
        return self.answer(data=data)


class AddUserPayData(AdminAuthApi):
    """ 收入看板-新增用户付费率 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        result = {}
        unit = {
            "x": "",
            "y": 0,
        }
        sta, user_data = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time)
        if sta:
            data = {}
            for user in user_data:
                date = tool_dt.dt_str(user["created"], '%Y-%m-%d')
                if date not in data:
                    data[date] = unit.copy()
                    data[date]["x"] = date
                data[date]["y"] += 1
            result["list"] = [item for item in data.values()]
        return self.answer(data=result)


class RepeatPayData(AdminAuthApi):
    """ 收入看板-每日复购率 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        result = {}
        unit = {
            "x": "",
            "y": 0.0,
        }
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5, status=99)
        if order_data:
            data = {}
            buy = {}
            for order in order_data:
                item_time = start_time + 86400
                if item_time > end_time:
                    break
                yesterday_date = tool_dt.dt_str(order["created"] - 86400, '%Y-%m-%d')
                date = tool_dt.dt_str(order["created"], '%Y-%m-%d')
                if start_time <= order.get("created") <= item_time:
                    continue
                if yesterday_date not in data:
                    buy[yesterday_date] = set()
                if date not in data:
                    data[date] = unit.copy()
                    data[date]["x"] = date
                    buy[date] = set()
                if order.get("uid") not in buy[yesterday_date]:
                    buy[yesterday_date].add(order.get("uid"))
                if order.get("uid") not in buy[date]:
                    buy[date].add(order.get("uid"))
                data[date]["y"] = ("%.1f" % (len(buy[date] & buy[yesterday_date]) / len(buy[date])))
            result["list"] = [item for item in data.values()]
        return self.answer(data=result)


class PaySituation(AdminAuthApi):
    """ 收入看板-付费金额局势 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=False, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=False, p_name='结束时间')
        if start_time is None or end_time is None:
            end_time = int(datetime.now().timestamp()) - 1
            start_time = end_time - 86400 * 30
        result = {}
        unit = {
            "x": "",
            "y": 0,
        }
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5, status=99)
        if order_data:
            data = {}
            for order in order_data:
                date = tool_dt.dt_str(order["created"], '%Y-%m-%d')
                if date not in data:
                    data[date] = unit.copy()
                    data[date]["x"] = date
                data[date]["y"] += order.get("amount")
            result["list"] = [item for item in data.values()]
        return self.answer(data=result)


class PayUserActivate(AdminAuthApi):
    """ 收入看板-付费用户留存 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        result = {}
        unit = {
            "day": "",
            "one": 0,
            "two": 0,
            "three": 0,
            "four": 0,
            "five": 0,
            "six": 0,
            "seven": 0,
        }
        sta, user_data = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time)
        user_all = set()
        if sta:
            user_dict = {}
            for user in user_data:
                date = tool_dt.dt_str(user["created"], '%Y-%m-%d')
                if date not in user_dict:
                    user_dict[date] = set()
                user_dict[date].add(user.get("uid"))
                if user.get("uid") not in user_all:
                    user_all.add(user.get("uid"))
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5, status=99,
                                                         uid=user_all)
        if order_data:
            data = {}
            for order in order_data:
                date = tool_dt.dt_str(order["created"], '%Y-%m-%d')
                if date not in data:
                    data[date] = set()
                data[date].add(order.get("uid"))
            items = {}
            if user_dict:
                for date, item in user_dict.items():
                    if date not in data:
                        data[date] = unit.copy()
                        data[date] = set()
                    items[date]["one"] = len(data[date] & user_dict[date])
                    items[date]["two"] = len(data[date] & user_dict[date])
                    items[date]["three"] = len(data[date] & user_dict[date])
                    items[date]["four"] = len(data[date] & user_dict[date])
                    items[date]["five"] = len(data[date] & user_dict[date])
                    items[date]["six"] = len(data[date] & user_dict[date])
                    items[date]["seven"] = len(data[date] & user_dict[date])
        result["list"] = [value for value in items.values()]
        return self.answer(data=result)

class PayUserGap(AdminAuthApi):
    """ 收入看板-付费用户间隔时长 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit = {
            "day": "",
            "start": 0,
            "pay_user": 0,
            "age": 0,
            "min": 0,
            "max": 0,
            "up_quantile": 0,
            "down_quantile": 0,
            "median": 0,
        }
        data = {}
        data["list"] = [unit]
        return self.answer(data=data)

class GiftPayData(AdminAuthApi):
    """ 收入看板-礼包购买情况 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit = {
            "day": "",
            "total": 0,
            "money": 0,
            "buy_gift": {
                "gift_name": "",
                "buy_user": "",
                "buy_num": 0,
                "buy_money": 0,
            }
        }
        data = {}
        data["list"] = [unit]
        return self.answer(data=data)

class PlatformBaseData(AdminAuthApi):
    """ 渠道统计-基础数据 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        now_time = int(datetime.now().timestamp())
        data = {
            "add_user": "",
            "activate_user": 0,
            "buy_user": 0,
            "buy_money": 0
        }
        return self.answer(data=data)

class PlatformData(AdminAuthApi):
    """ 渠道统计-渠道数据报表 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit = {
            "platform": 0,
            "today_user": 0,
            "old_activate_user": 0,
            "new_activate_user": 0,
            "old_pay_user": 0,
            "new_pay_user": 0,
            "old_consume_money": 0,
            "new_consume_money": 0,
            "total_money": 0,
        }
        data = {}
        data["list"] = [unit]
        return self.answer(data=data)

class PlatformAddUserRecord(AdminAuthApi):
    """ 渠道统计-新增用户（按平台） """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit = {
            "x": 0,
            "y": 0,
        }
        data = {}
        data["platform_x"] = [unit]
        return self.answer(data=data)

class PlatformPayMoneyRecord(AdminAuthApi):
    """ 渠道统计-付费金额（按平台） """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        type = self.check_int(req.args.get('type'), require=True, p_name='类型')
        unit = {
            "x": 0,
            "y": 0,
        }
        data = {}
        data["platform_x"] = [unit]
        return self.answer(data=data)

class PlatformPayUserRecord(AdminAuthApi):
    """ 渠道统计-付费用户（按平台） """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        type = self.check_int(req.args.get('type'), require=True, p_name='类型')
        unit = {
            "x": 0,
            "y": 0,
        }
        data = {}
        data["platform_x"] = [unit]
        return self.answer(data=data)

class PlatformActivateUserRecord(AdminAuthApi):
    """ 渠道统计-活跃用户（按平台） """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        type = self.check_int(req.args.get('type'), require=True, p_name='类型')
        unit = {
            "x": 0,
            "y": 0,
        }
        data = {}
        data["platform_x"] = [unit]
        return self.answer(data=data)


class PlatformAddUser(AdminAuthApi):
    """ 渠道统计-新增用户统计详情 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        now_time = int(datetime.now().timestamp())
        platform_x = {
            "add_user": 0,
            "platform_user": 0,
            "man": 0,
            "woman": 0,
            "add_rotai": 0,
        }
        data = {
            "sex_statistics": {
                "man": 0,
                "woman": 0,
            },
            "platform_statistics": [platform_x],
            "address_statistics": {
                "address": "",
                "add_num": 0,
            },
            "total": 0,
        }
        return self.answer(data=data)

class PlatformPayUser(AdminAuthApi):
    """ 渠道统计-充值用户统计详情 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        now_time = int(datetime.now().timestamp())
        platform_x = {
            "today_user": 0,
            "old_user": 0,
            "new_user": 0,
            "platform_ratio": 0,
        }
        data = {
            "today_user": 0,
            "old_user": 0,
            "new_user": 0,
            "platform_statistics": [platform_x],
            "address_statistics": {
                "address": "",
                "add_num": 0,
            },
        }
        return self.answer(data=data)

class PlatformPayMoney(AdminAuthApi):
    """ 渠道统计-充值金额统计详情 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        now_time = int(datetime.now().timestamp())
        platform_x = {
            "today_money": 0,
            "old_money": 0,
            "new_money": 0,
            "platform_ratio": 0,
        }
        data = {
            "today_money": 0,
            "old_money": 0,
            "new_money": 0,
            "platform_statistics": [platform_x],
            "address_statistics": {
                "address": "",
                "add_num": 0,
            },
        }
        return self.answer(data=data)

class PlatformActivateUser(AdminAuthApi):
    """ 渠道统计-活跃用户统计详情 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        now_time = int(datetime.now().timestamp())
        platform_x = {
            "today_activate": 0,
            "old_activate": 0,
            "new_activate": 0,
            "platform_ratio": 0,
        }
        data = {
            "today_activate": 0,
            "old_activate": 0,
            "new_activate": 0,
            "platform_statistics": [platform_x],
            "address_statistics": {
                "address": "",
                "add_num": 0,
            },
            "total": 0,
        }
        return self.answer(data=data)

class RoomcardBaseStatistics(AdminAuthApi):
    """ 房卡统计-基础数据 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        now_time = int(datetime.now().timestamp())
        data = {
            "total_money": 0,
            "total_count": 0,
        }
        return self.answer(data=data)

class RoomcardListStatistics(AdminAuthApi):
    """ 房卡统计-列表 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        now_time = int(datetime.now().timestamp())
        unit = {
            "date": "",
            "pay_money": 0,
            "pay_count": 0,
            "consume_num": 0,
            "play_x": 0,
        }
        data = {}
        data["list"] = [unit]
        return self.answer(data=data)

class PropertyRankingList(AdminAuthApi):
    """ 资产排行-列表 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        currency = self.check_int(req.args.get('currency'), require=True, p_name='货币类型')
        page = self.check_int(req.args.get('page'), require=False, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, p_name='每页数量')
        data = {}
        return self.answer(data=data)

class PropertyRankingRecord(AdminAuthApi):
    """ 资产排行-用户资产事迹轨迹 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        uid = self.check_int(req.args.get('uid'), require=True, p_name='用户ID')
        data = {}
        return self.answer(data=data)

class UserPortrait(AdminAuthApi):
    """ 用户画像-地区分布/性别统计 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        uid = self.check_int(req.args.get('uid'), require=True, p_name='用户ID')
        unit = {
            "address": "",
            "count": 0,
        }
        data = {
            "total": 0,
            "man": 0,
            "woman": 0,
        }
        return self.answer(data=data)

class UserPortraitDiff(AdminAuthApi):
    """ 用户画像-新老用户对比 """
    async def get(self, req: Request):
        unit = {
            "x": "",
            "y": 0,
        }
        data = {
            "old_user": [unit],
            "new_user": [unit],
        }
        return self.answer(data=data)

class UserActivityChart(AdminAuthApi):
    """ 用户生命周期-周期图表 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit = {
            "add_user": 0,
            "keep_user": 0,
            "backflow_user": 0,
            "churn_rate_user": 0,
            "date": "",
        }
        data = {}
        data["list"] = [unit]
        return self.answer(data=data)

class UserActivityList(AdminAuthApi):
    """ 用户生命周期-列表 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit = {
            "add_user": 0,
            "keep_user": 0,
            "backflow_user": 0,
            "churn_rate_user": 0,
            "date": "",
            "activate_user": 0,
            "keep_ratio": 0,
            "pay_ratio": 0,
        }
        data = {}
        data["list"] = [unit]
        return self.answer(data=data)

class UserActivityValue(AdminAuthApi):
    """ 用户生命周期-用户生命价值"""
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit = {
            "ltv": 0,  # 用户生命周期价值
            "arpu": 0,  # 用户平均费用
            "avg": 0,  # 平均留存时间
            "month": 0,
        }
        data = {}
        data["list"] = [unit]
        return self.answer(data=data)