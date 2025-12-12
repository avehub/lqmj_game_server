import numpy
from datetime import datetime
from nsanic.libs import tool_dt
from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.records_user_login import RecordsAdEventRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.model_rc.order import OrderRC
from lucky_admin.logic.good_logic import GoodLogic


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
        all_good_ids = GoodLogic.get_gift_good_ids()
        first_good_ids = GoodLogic.get_gift_good_ids("first")
        order_data, msg = await OrderRC.get_order_filter(start_time=last_week_start_time, end_time=end_time, currency=5,
                                                         status=99)
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
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5,
                                                         status=99)
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
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5,
                                                         status=99)
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
        user_dict = {}
        if sta:
            for user in user_data:
                date = tool_dt.dt_str(user["created"], '%Y-%m-%d')
                if date not in user_dict:
                    user_dict[date] = set()
                user_dict[date].add(user.get("uid"))
                if user.get("uid") not in user_all:
                    user_all.add(int(user.get("uid")))
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5,
                                                         status=99,
                                                         uid=list(user_all))
        if order_data:
            data = {}
            for order in order_data:
                date = tool_dt.dt_str(order["created"], '%Y-%m-%d')
                if date not in data:
                    data[date] = set()
                data[date].add(order.get("uid"))
            if user_dict:
                items = {}
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
                result["list"] = list(items.values())
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
            "total": 0,
        }
        result = {}
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5,
                                                         status=99)
        if order_data:
            data = {}
            start_date = tool_dt.dt_str(start_time, '%Y-%m-%d')
            start_user = set()
            pay_user = set()
            max_amount = 0
            min_amount = 0
            max_len = len(order_data)
            all_amount = []
            for order in order_data:
                max_len -= 1
                date = tool_dt.dt_str(order["created"], '%Y-%m-%d')
                if date not in data:
                    data[date] = unit.copy()
                    data[date]["day"] = date
                if start_date == date and order.get("uid") not in start_user:
                    start_user.add(order.get("uid"))
                if order.get("uid") not in pay_user:
                    pay_user.add(order.get("uid"))
                data[date]["start"] = len(start_user)
                data[date]["pay_user"] = len(pay_user)
                data[date]["total"] += order["amount"]
                data[date]["age"] = ("%.2f" % (order["amount"] / len(pay_user)))
                all_amount.append(order["amount"])
                if max_amount < order["amount"]:
                    data[date]["max"] = order["amount"]
                if min_amount < order["amount"]:
                    data[date]["min"] = min_amount
                else:
                    data[date]["min"] = order["amount"]
                if max_len == 0:
                    data[date]["up_quantile"] = 0
                    quartiles = numpy.percentile(all_amount, [25, 50, 75])
                    self.log_info("quartiles:", quartiles)
                    data[date]["down_quantile"] = quartiles[0]
                    data[date]["median"] = quartiles[1]
                    data[date]["up_quantile"] = quartiles[2]

            result["list"] = [value for value in data.values()]
        return self.answer(data=result)


class GiftPayData(AdminAuthApi):
    """ 收入看板-礼包购买情况 """

    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit_gift = {
            "gift_name": "",
            "buy_user": 1,
            "buy_num": 1,
            "buy_money": 0,
        }
        unit = {
            "day": "",
            "total": 0,
            "money": 0,
            "buy_gift": []
        }
        result = {}
        first_good_ids = GoodLogic.get_gift_good_ids("first")
        replenish_good_ids = GoodLogic.get_gift_good_ids("replenish")
        reviver_good_ids = GoodLogic.get_gift_good_ids("reviver")
        return_good_ids = GoodLogic.get_gift_good_ids("return")
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5,
                                                         status=99)
        if order_data:
            data = {}
            buy_gift = {}
            for order in order_data:
                date = tool_dt.dt_str(order["created"], '%Y-%m-%d')
                if date not in data:
                    data[date] = unit.copy()
                    data[date]["day"] = date
                    buy_gift[date] = {}
                if order["good_id"] not in buy_gift[date]:
                    buy_gift[date][order["good_id"]] = unit_gift.copy()
                    if order["good_id"] in first_good_ids:
                        buy_gift[date][order["good_id"]]["gift_name"] = "首充礼包"
                    elif order["good_id"] in replenish_good_ids:
                        buy_gift[date][order["good_id"]]["gift_name"] = "补足礼包"
                    elif order["good_id"] in reviver_good_ids:
                        buy_gift[date][order["good_id"]]["gift_name"] = "复活礼包"
                    elif order["good_id"] in return_good_ids:
                        buy_gift[date][order["good_id"]]["gift_name"] = "返还礼包"
                    else:
                        buy_gift[date][order["good_id"]]["gift_name"] = "其他礼包"
                    buy_gift[date][order["good_id"]]["buy_money"] = order["amount"]
                else:
                    buy_gift[date][order["good_id"]]["buy_money"] += order["amount"]
                    buy_gift[date][order["good_id"]]["buy_user"] += 1

                data[date]["buy_gift"] = list(buy_gift[date].values())
                data[date]["total"] += 1
                data[date]["money"] += order["amount"]
            result["list"] = [unit for unit in data.values()]
        return self.answer(data=result)


class PlatformBaseData(AdminAuthApi):
    """ 渠道统计-基础数据 """

    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1

        data = {
            "add_user": 0,
            "activate_user": 0,
            "buy_user": 0,
            "buy_money": 0
        }
        sta, user_total = await BaseUserRC.count_user_total(created__gte=date_time, created__lte=end_time)
        if sta:
            data["add_user"] = user_total
        sta, login_user = await RecordsAdEventRC.get_uid_login_list(start_time=date_time, end_time=end_time,
                                                                    filtration="uid", group_by="uid")
        if sta:
            data["activate_user"] = len(login_user)
        order_data, msg = await OrderRC.get_order_filter(start_time=date_time, end_time=end_time, currency=5,
                                                         status=99)
        if order_data:
            buy_user = set()
            for order in order_data:
                if order["user_id"] not in buy_user:
                    buy_user.add(order["user_id"])
                data["buy_money"] += order["amount"]
            data["buy_user"] += len(buy_user)
        return self.answer(data=data)


class PlatformData(AdminAuthApi):
    """ 渠道统计-渠道数据报表 """

    async def get(self, req: Request):
        start_time, end_time = await self.get_time_range(period="day")
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
        result = {}
        sta, today_user = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time)
        today_u_ids = []
        today_p_dict = {}
        if sta:
            for item in today_user:
                today_u_ids.append(item["uid"])
                if item["platform"] not in today_p_dict:
                    today_p_dict[item["platform"]] = set()
                today_p_dict[item["platform"]].add(item["uid"])
        sta, login_user = await RecordsAdEventRC.get_uid_login_list(start_time=start_time, end_time=end_time,
                                                                    filtration="uid", group_by="uid")
        login_u_ids = []
        if sta:
            login_u_ids = [item["uid"] for item in login_user]
        user_group = await BaseUserRC.get_user_group(start_time=start_time, end_time=end_time, group_field="platform")
        if user_group:
            data = {}
            index_data = {index["platform"]: index for index in user_group}
            order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5,
                                                             status=99)
            order_u_ids = set()
            order_total_amount = 0
            order_today_amount = 0
            if order_data:
                for order in order_data:
                    if order["uid"] not in order_u_ids:
                        order_u_ids.add(order["uid"])
                    if order["uid"] in today_u_ids:
                        order_today_amount += order["amount"]
                    order_total_amount += order["amount"]
            for item in user_group:
                if item["platform"] not in data:
                    data[item["platform"]] = unit.copy()
                today_reg_user = set()
                if item["platform"] in today_p_dict:
                    today_reg_user = today_p_dict[item["platform"]]

                old_pay_user = list(order_u_ids - today_reg_user)
                data[item["platform"]]["platform"] = item["platform"]
                data[item["platform"]]["today_user"] = item["group_total"]
                data[item["platform"]]["old_activate_user"] = len(set(login_u_ids) - today_reg_user)
                data[item["platform"]]["new_activate_user"] = len(today_u_ids)
                data[item["platform"]]["old_pay_user"] = len(old_pay_user)
                data[item["platform"]]["new_pay_user"] = len(list(order_u_ids & today_reg_user))
                data[item["platform"]]["old_consume_money"] = order_total_amount - order_today_amount
                data[item["platform"]]["new_consume_money"] = order_today_amount
                data[item["platform"]]["total_money"] = order_total_amount
            result["list"] = list(data.values())
        return self.answer(data=result)


class PlatformAddUserRecord(AdminAuthApi):
    """ 渠道统计-新增用户（按平台） """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit = {
            "x": 0,
            "y": 0,
        }
        result = {}
        sta, user_group = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time)
        if sta:
            data = {}
            for item in user_group:
                key = f"platform_{item['platform']}"
                date = tool_dt.dt_str(item["created"], '%Y-%m-%d')
                if key not in data:
                    data[key] = {}
                if date not in data[key]:
                    data[key][date] = unit.copy()
                    data[key][date]["x"] = date
                data[key][date]["y"] += 1
            result = {key: list(val.values()) for key, val in data.items()}
        return self.answer(data=result)


class PlatformPayMoneyRecord(AdminAuthApi):
    """ 渠道统计-付费金额（按平台） """

    async def get(self, req: Request):
        start_time = end_time = None
        type = self.check_int(req.args.get('type'), require=True, p_name='类型') # 全部:0 新1 老2
        if type == 1:
            start_time, end_time = await self.get_time_range(period="day")
        unit = {
            "x": 0,
            "y": 0,
        }
        result = {}
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5,
                                                         status=99)
        if order_data:
            data = {}
            for order in order_data:
                key = f"platform_{order['platform']}"
                date = tool_dt.dt_str(order["created"], '%Y-%m-%d')
                if key not in data:
                    data[key] = {}
                if date not in data[key]:
                    data[key][date] = unit.copy()
                    data[key][date]["x"] = date
                data[key][date]["y"] += order["amount"]
            result = {key: list(val.values()) for key, val in data.items()}
        return self.answer(data=result)


class PlatformPayUserRecord(AdminAuthApi):
    """ 渠道统计-付费用户（按平台） """

    async def get(self, req: Request):
        start_time = end_time = None
        type = self.check_int(req.args.get('type'), require=True, p_name='类型') # 全部:0 新1 老2
        if type == 1:
            start_time, end_time = await self.get_time_range(period="day")
        unit = {
            "x": 0,
            "y": 0,
        }
        result = {}
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5,
                                                         status=99)
        if order_data:
            data = {}
            for order in order_data:
                key = f"platform_{order['platform']}"
                date = tool_dt.dt_str(order["created"], '%Y-%m-%d')
                if key not in data:
                    data[key] = {}
                if date not in data[key]:
                    data[key][date] = unit.copy()
                    data[key][date]["x"] = date
                data[key][date]["y"] += 1
            result = {key: list(val.values()) for key, val in data.items()}
        return self.answer(data=result)


class PlatformActivateUserRecord(AdminAuthApi):
    """ 渠道统计-活跃用户（按平台） """

    async def get(self, req: Request):
        start_time = end_time = None
        type = self.check_int(req.args.get('type'), require=True, p_name='类型')  # 全部:0 新1 老2
        if type == 1:
            start_time, end_time = await self.get_time_range(period="day")

        unit = {
            "x": 0,
            "y": 0,
        }
        result = {}
        sta, login_user = await RecordsAdEventRC.get_uid_login_list(start_time=start_time, end_time=end_time,
                                                                    filtration="uid", group_by="uid")
        if sta:
            login_u_ids = set(int(item["uid"]) for item in login_user)
            _, user_data = await BaseUserRC.get_user_filter(uid=list(login_u_ids))
            data = {}
            for item in user_data:
                key = f"platform_{item['platform']}"
                date = tool_dt.dt_str(item["created"], '%Y-%m-%d')
                if key not in data:
                    data[key] = {}
                if date not in data[key]:
                    data[key][date] = unit.copy()
                    data[key][date]["x"] = date
                data[key][date]["y"] += 1
            result = {key: list(val.values()) for key, val in data.items()}
        return self.answer(data=result)


class PlatformAddUser(AdminAuthApi):
    """ 渠道统计-新增用户统计详情 """

    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        platform_x = {
            "add_user": 0,
            "platform_user": 0,
            "man": 0,
            "woman": 0,
            "add_ratio": 0,
        }
        address_x = {
            "address": "",
            "add_num": 0,
        }
        data = {
            "sex_statistics": {
                "man": 0,
                "woman": 0,
            },
            "platform_statistics": {},
            "address_statistics": [],
            "total": 0,
        }

        sta, user_data = await BaseUserRC.get_user_filter(start_time=date_time, end_time=end_time)
        if sta:
            add_user = len(user_data)
            address = {}
            for item in user_data:
                key = f"platform_{item['platform']}"
                if key not in data:
                    data["platform_statistics"][key] = platform_x.copy()
                    data["platform_statistics"][key]["add_user"] = add_user
                data["platform_statistics"][key]["platform_user"] += 1
                if item["sex"] == 1:
                    data["sex_statistics"]["man"] += 1
                    data["platform_statistics"][key]["man"] += 1
                else:
                    data["sex_statistics"]["woman"] += 1
                    data["platform_statistics"][key]["woman"] += 1
                data["platform_statistics"][key]["add_ratio"] = ("%.2f" % (data["platform_statistics"][key]["platform_user"]/data["platform_statistics"][key]["add_user"]))
                if item["region"] not in address:
                    address[item["region"]] = address_x.copy()
                    address[item["region"]]["address"] = item["region"]
                address[item["region"]]["add_num"] += 1
            data["address_statistics"] = list(address.values())
            data["total"] = add_user
        return self.answer(data=data)


class PlatformPayUser(AdminAuthApi):
    """ 渠道统计-充值用户统计详情 """

    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        platform_x = {
            "today_user": 0,
            "old_user": 0,
            "new_user": 0,
            "platform_ratio": 0,
        }
        address_x = {
            "address": "",
            "add_num": 0,
        }
        data = {
            "today_user": 0,
            "old_user": 0,
            "new_user": 0,
            "platform_statistics": {},
            "address_statistics": [],
        }

        order_data, msg = await OrderRC.get_order_filter(start_time=date_time, end_time=end_time, currency=5,
                                                         status=99)
        if order_data:
            order_u_ids = set(item["uid"] for item in order_data)
            _, user_data = await BaseUserRC.get_user_filter(uid=list(order_u_ids))
            new_u_ids = set()
            user_dict = {}
            for item in user_data:
                if item["created"] >= date_time:
                    new_u_ids.add(item["uid"])
                user_dict[item["uid"]] = item
            total_user = len(order_u_ids)
            address = {}
            for item in order_data:
                key = f"platform_{item['platform']}"
                if key not in data:
                    data["platform_statistics"][key] = platform_x.copy()
                data["platform_statistics"][key]["today_user"] += 1
                if item["uid"] in new_u_ids:
                    data["platform_statistics"][key]["new_user"] += 1
                else:
                    data["platform_statistics"][key]["old_user"] += 1
                data["platform_statistics"][key]["platform_ratio"] = ("%.2f" % (data["platform_statistics"][key]["today_user"] / total_user))
                if item["uid"] in user_dict and user_dict[item["uid"]]["region"] not in address:
                    address[item["region"]] = address_x.copy()
                    address[item["region"]]["address"] = item["region"]
                address[item["region"]]["add_num"] += 1
            data["address_statistics"] = list(address.values())
        return self.answer(data=data)


class PlatformPayMoney(AdminAuthApi):
    """ 渠道统计-充值金额统计详情 """

    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        platform_x = {
            "today_money": 0,
            "old_money": 0,
            "new_money": 0,
            "platform_ratio": 0,
        }
        address_x = {
            "address": "",
            "add_num": 0,
        }
        data = {
            "today_money": 0,
            "old_money": 0,
            "new_money": 0,
            "platform_statistics": {},
            "address_statistics": [],
        }

        order_data, msg = await OrderRC.get_order_filter(start_time=date_time, end_time=end_time, currency=5,
                                                         status=99)
        if order_data:
            order_u_ids = set()
            order_amount = 0
            for item in order_data:
                if item["uid"] not in order_u_ids:
                    order_u_ids.add(item["uid"])
                order_amount += item["amount"]
            _, user_data = await BaseUserRC.get_user_filter(uid=list(order_u_ids))
            new_u_ids = set()
            user_dict = {}
            for item in user_data:
                if item["created"] >= date_time:
                    new_u_ids.add(item["uid"])
                user_dict[item["uid"]] = item
            address = {}
            for item in order_data:
                key = f"platform_{item['platform']}"
                if key not in data:
                    data["platform_statistics"][key] = platform_x.copy()
                data["platform_statistics"][key]["today_money"] += item["amount"]
                if item["uid"] in new_u_ids:
                    data["platform_statistics"][key]["new_money"] += item["amount"]
                else:
                    data["platform_statistics"][key]["old_money"] += item["amount"]
                data["platform_statistics"][key]["platform_ratio"] = (
                            "%.2f" % (data["platform_statistics"][key]["today_money"] / order_amount))
                if item["uid"] in user_dict and user_dict[item["uid"]]["region"] not in address:
                    address[item["region"]] = address_x.copy()
                    address[item["region"]]["address"] = item["region"]
                address[item["region"]]["add_num"] += 1
            data["address_statistics"] = list(address.values())
        return self.answer(data=data)


class PlatformActivateUser(AdminAuthApi):
    """ 渠道统计-活跃用户统计详情 """

    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        platform_x = {
            "today_activate": 0,
            "old_activate": 0,
            "new_activate": 0,
            "platform_ratio": 0,
        }
        address_x = {
            "address": "",
            "add_num": 0,
        }
        statistics = {
            "man": 0,
            "woman": 0,
        }
        data = {
            "today_activate": 0,
            "old_activate": 0,
            "new_activate": 0,
            "today_statistics": statistics.copy(),
            "new_statistics": statistics.copy(),
            "old_statistics": statistics.copy(),
            "platform_statistics": {},
            "address_statistics": [],
            "total": 0,
        }

        sta, login_user = await RecordsAdEventRC.get_uid_login_list(start_time=date_time, end_time=end_time,
                                                                    filtration="uid", group_by="uid")
        if sta:
            login_u_ids = set(item["uid"] for item in login_user)
            today_activate = len(login_u_ids)
            _, user_data = await BaseUserRC.get_user_filter(uid=list(login_u_ids))
            new_u_ids = set()
            address = {}
            for item in user_data:
                if item["sex"] == 1:
                    data["today_statistics"]["man"] += 1
                else:
                    data["today_statistics"]["woman"] += 1
                if item["created"] >= date_time:
                    new_u_ids.add(item["uid"])
                    if item["sex"] == 1:
                        data["new_statistics"]["man"] += 1
                    else:
                        data["new_statistics"]["woman"] += 1
                else:
                    if item["sex"] == 1:
                        data["old_statistics"]["man"] += 1
                    else:
                        data["old_statistics"]["woman"] += 1
                if item["region"] not in address:
                    address[item["region"]] = address_x.copy()
                    address[item["region"]]["address"] = item["region"]
                address[item["region"]]["add_num"] += 1
                key = f"platform_{item['platform']}"
                if key not in data:
                    data["platform_statistics"][key] = platform_x.copy()
                data["platform_statistics"][key]["today_activate"] += 1
                if item["uid"] in new_u_ids:
                    data["platform_statistics"][key]["new_activate"] += 1
                else:
                    data["platform_statistics"][key]["old_activate"] += 1
                data["platform_statistics"][key]["platform_ratio"] = (
                            "%.2f" % (data["platform_statistics"][key]["today_activate"] / today_activate))
            data["today_activate"] = today_activate
            data["new_activate"] = len(new_u_ids)
            data["old_activate"] = today_activate - len(new_u_ids)
            data["address_statistics"] = list(address.values())
            data["total"] = len(new_u_ids)
        return self.answer(data=data)


class RoomcardBaseStatistics(AdminAuthApi):
    """ 房卡统计-基础数据 """

    async def get(self, req: Request):
        data = {
            "total_money": 0,
            "total_count": 0,
        }
        order_data, msg = await OrderRC.get_order_filter(currency=5, status=99)
        if order_data:
            data["total_money"] = sum(item["amount"] for item in order_data)
            data["total_count"] = len(order_data)
        return self.answer(data=data)


class RoomcardListStatistics(AdminAuthApi):
    """ 房卡统计-列表 """

    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        unit = {
            "date": "",
            "pay_money": 0,
            "pay_count": 0,
            "consume_num": 0,
        }
        result = {}
        sta, consume_data = await ExtraUserResourceChangesRC.get_resource_changes_filter(start_time=start_time, end_time=end_time,
                                                                              status=ExtraUserResourceChangesRC.OPERATION_MAP["sub"])
        data = {}
        if sta and consume_data:
            for item in consume_data:
                date = tool_dt.dt_str(item["created"], "%Y-%m-%d")
                if date not in data:
                    data[date] = unit.copy()
                    data[date]["date"] = date
                data[date]["consume_num"] += item["num"]
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5, status=99)
        if order_data:
            for item in order_data:
                date = tool_dt.dt_str(item["created"], "%Y-%m-%d")
                if date not in data:
                    data[date] = unit.copy()
                    data[date]["date"] = date
                data[date]["pay_money"] += item["amount"]
                data[date]["pay_count"] += 1
            result["list"] = list(data.values())
        return self.answer(data=result)


class PropertyRankingList(AdminAuthApi):
    """ 资产排行-列表 """

    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        currency = self.check_int(req.args.get('currency'), require=True, p_name='货币类型')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        order_field = "gold"
        if currency == 2:
            order_field = "diamond"
        elif currency == 3:
            order_field = "room_card"
        elif currency == 4:
            order_field = "yellow_diamond"
        sta, user_data = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time, order_field=order_field,
                                                          page=page, page_size=page_size)
        # data = user_data["total"]
        # if sta and user_data["list"]:
        #     for item in data["list"]:
        #         unit = {
        #             "uid": item["uid"],
        #             "avatar": item["avatar"],
        #             order_field: item[order_field],
        #         }
        #         data["list"].append(unit)
        return self.answer(data=user_data)


class PropertyRankingRecord(AdminAuthApi):
    """ 资产排行-用户资产事迹轨迹 """

    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        uid = self.check_int(req.args.get('uid'), require=True, p_name='用户ID')
        sta, consume_data = await ExtraUserResourceChangesRC.get_resource_changes_filter(start_time=start_time,
                                                                                         end_time=end_time,uid=uid)
        data = {}
        if sta:
            data["list"] = consume_data
        return self.answer(data=data)


class UserPortrait(AdminAuthApi):
    """ 用户画像-地区分布/性别统计 """

    async def get(self, req: Request):
        unit = {
            "address": "",
            "count": 0,
        }
        data = {
            "total": 0,
            "man": 0,
            "woman": 0,
            "list": [],
        }

        sta, user_data = await BaseUserRC.get_user_filter()
        if sta:
            data["total"] = len(user_data)
            address_data = {}
            for item in user_data:
                if item["region"] not in address_data:
                    address_data[item["region"]] = unit.copy()
                    address_data[item["region"]]["address"] = item["region"]
                address_data[item["region"]]["count"] += 1
                if item["sex"] == 1:
                    data["man"] += 1
                else:
                    data["woman"] += 1
            data["list"] = list(address_data.values())

        return self.answer(data=data)


class UserPortraitDiff(AdminAuthApi):
    """ 用户画像-新老用户对比 """
    async def get(self, req: Request):
        end_time, _ = await self.get_time_range(period="day")
        start_time = end_time - 86400 * 7
        unit = {
            "x": "",
            "y": 0,
        }
        data = {
            "old_user": [],
            "new_user": [],
        }

        sta, user_total = await BaseUserRC.count_user_total(created__lte=start_time)
        sta, user_data = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time)
        if sta:
            dates = {}
            new_user = 0
            for item in user_data:
                date = tool_dt.dt_str(item["created"], "%Y-%m-%d")
                if date not in dates:
                    dates[date] = unit.copy()
                    dates[date]["x"] = date
                    user_total += new_user
                    new_user = 0
                new_user += 1
                new_user_unit = dates[date]
                new_user_unit["y"] = new_user
                data["new_user"].append(new_user_unit)
                old_user_unit = dates[date]
                old_user_unit["y"] = user_total
                data["old_user"].append(old_user_unit)
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
        result = {}
        sta, login_data = await RecordsAdEventRC.get_uid_login_list(start_time=start_time, end_time=end_time)
        sta, user_data = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time)
        if sta:
            data = {}
            user_u_ids = set([item["uid"] for item in user_data])
            user_dict = {item["uid"]: item for item in user_data}
            for item in login_data:
                date = tool_dt.dt_str(item["created"], "%Y-%m-%d")
                if date not in data:
                    data[date] = unit.copy()
                    data[date]["date"] = date
                if item["uid"] in user_u_ids and date == tool_dt.dt_str(user_dict[item["uid"]]["created"], "%Y-%m-%d"):
                    data[date]["add_user"] += 1
                elif item["uid"] in user_u_ids and date != tool_dt.dt_str(user_dict[item["uid"]]["created"], "%Y-%m-%d"):
                    data[date]["keep_user"] += 1
                else:
                    data[date]["backflow_user"] += 1
                data[date]["backflow_user"] = data[date]["add_user"] - data[date]["keep_user"]
            result["list"] = [item for item in data.values()]
        return self.answer(data=result)


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
            "pay_user": 0,
        }
        result = {}
        sta, login_data = await RecordsAdEventRC.get_uid_login_list(start_time=start_time, end_time=end_time)
        sta, user_data = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time)
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5, status=99)
        order_dict = {}
        if order_dict:
            order_dict = {item["uid"]: item for item in order_data}
        if sta:
            data = {}
            user_u_ids = set([item["uid"] for item in user_data])
            user_dict = {item["uid"]: item for item in user_data}
            for item in login_data:
                date = tool_dt.dt_str(item["created"], "%Y-%m-%d")
                if date not in data:
                    data[date] = unit.copy()
                    data[date]["date"] = date
                if item["uid"] in user_u_ids and date == tool_dt.dt_str(user_dict[item["uid"]]["created"], "%Y-%m-%d"):
                    data[date]["add_user"] += 1
                elif item["uid"] in user_u_ids and date != tool_dt.dt_str(user_dict[item["uid"]]["created"],
                                                                          "%Y-%m-%d"):
                    data[date]["keep_user"] += 1
                else:
                    data[date]["backflow_user"] += 1
                if item["uid"] in order_dict:
                    data[date]["pay_user"] += 1
                data[date]["activate_user"] += 1
                data[date]["backflow_user"] = data[date]["add_user"] - data[date]["keep_user"]
                data[date]["keep_ratio"] = ("%.2f%%" % (data[date]["keep_user"] / data[date]["activate_user"]))
                data[date]["pay_ratio"] = ("%.2f%%" % (data[date]["pay_user"] / data[date]["activate_user"]))
            result["list"] = [item for item in data.values()]
        return self.answer(data=result)


class UserActivityValue(AdminAuthApi):
    """ 用户生命周期-用户生命价值"""
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        result = {}
        unit = {
            "ltv": 0,  # 用户生命周期价值
            "arpu": 0,  # 用户平均费用
            "avg": 0.0,  # 平均留存时间
            "month": 0,
        }
        # LTV（用户生命周期价值） = ARPU * 平均用户寿命
        # 其中，ARPU（平均每用户收入）为：总收入/活跃用户数
        # 平均用户寿命为：1 / 流失率
        # 流失率 = 流失用户数 / 活跃用户数
        # 所以，LTV = （总收入 / 活跃用户数）* （1 / 流失率）
        data = {}
        time_range = await self.get_month_start_timestamps(start_time, end_time)
        for s_time in time_range:
            e_time = await self.get_month_end_timestamp(s_time)
            last_s_time = tool_dt.month_begin(tool_dt.to_datetime((s_time - 1)))
            last_e_time = await self.get_month_end_timestamp(last_s_time)
            login_last_u_ids = set()
            login_u_ids = set()
            order_u_ids = set()
            order_total_amount = 0
            sta, login_last = await RecordsAdEventRC.get_uid_login_list(start_time=last_s_time, end_time=last_e_time, filtration="uid", group_by="uid")
            if sta:
                login_last_u_ids = set([item["uid"] for item in login_last])
            sta, login_data = await RecordsAdEventRC.get_uid_login_list(start_time=s_time, end_time=e_time, filtration="uid", group_by="uid")
            if sta:
                login_u_ids = set([item["uid"] for item in login_data])
            order_data, msg = await OrderRC.get_order_filter(start_time=s_time, end_time=e_time, currency=5, status=99)
            if order_data:
                for order in order_data:
                    if order["uid"] not in order_u_ids:
                        order_u_ids.add(order["uid"])
                    order_total_amount += order["amount"]
            backflow_rate = round(len(login_last_u_ids & login_u_ids) / len(login_last_u_ids) if login_last_u_ids else 0, 2)
            date_m = tool_dt.dt_str(s_time, "%Y-%m")
            if date_m not in data:
                data[date_m] = unit.copy()
                data[date_m]["month"] = date_m
            data[date_m]["arpu"] = order_total_amount / len(order_u_ids) if order_u_ids else 0
            data[date_m]["avg"] = round(1 / backflow_rate if backflow_rate else 0, 2)
            data[date_m]["ltv"] = data[date_m]["arpu"] * data[date_m]["avg"]
        result["list"] = [item for item in data.values()]
        return self.answer(data=result)
