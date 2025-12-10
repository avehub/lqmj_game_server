from datetime import datetime

from nsanic.libs import tool_dt
from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.records_user_login import RecordsAdEventRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC


class IndexBaseData(AdminAuthApi):
    """ 顶部基础数据 """
    async def get(self, req: Request):
        try:
            start_time, end_time = await self.get_time_range("day")
            yesterday_start_time = start_time - 86400
            yesterday_end_time = end_time - 86400
            data = {
                "today_consumer_gold": 0,
                "yesterday_consumer_gold": 0,
                "today_consumer_discount": 0,
                "yesterday_consumer_discount": 0,
                "today_online_user": 0,
                "yesterday_online_user": 0,
                "today_total_user": 0,
                "yesterday_total_user": 0,
            }
            # 新增、累计用户
            sta, user_data = await BaseUserRC.get_user_filter(start_time=yesterday_start_time, end_time=end_time)
            self.log_info(f"顶部基础数据-新增、累计用户结果：{user_data}")
            if sta:
                yesterday_total_user = today_total_user = 0
                for user in user_data:
                    if user["created"] >= yesterday_start_time and user["created"] <= yesterday_end_time:
                        yesterday_total_user += 1
                    if user["created"] >= start_time and user["created"] <= end_time:
                        today_total_user += 1
                data["today_total_user"] = today_total_user
                data["yesterday_total_user"] = yesterday_total_user
            # 在线用户
            sta, online_user = await RecordsAdEventRC.get_uid_login_list(start_time=yesterday_start_time, end_time=end_time)
            self.log_info(f"顶部基础数据-在线用户结果：{online_user}")
            if sta:
                yesterday_online_user = today_online_user = []
                for user in online_user:
                    if user["created"] >= yesterday_start_time and user["created"] <= yesterday_end_time:
                        yesterday_online_user.append(user["uid"])
                    if user["created"] >= start_time and user["created"] <= end_time:
                        today_online_user.append(user["uid"])
                data["today_online_user"] = len(set(today_online_user))
                data["yesterday_online_user"] = len(set(yesterday_online_user))
            # 资产变化
            sta, resource_change = await ExtraUserResourceChangesRC.get_resource_changes_filter(start_time=yesterday_start_time, end_time=end_time, status=ExtraUserResourceChangesRC.OPERATION_MAP["sub"])
            self.log_info(f"顶部基础数据-资产变化结果：{resource_change}")
            if sta:
                today_consumer_gold = yesterday_consumer_gold = today_consumer_discount = yesterday_consumer_discount = 0
                for item in resource_change:
                    if item["created"] >= yesterday_start_time and item["created"] <= yesterday_end_time:
                        if item["currency"] == 1:
                            yesterday_consumer_gold += item["num"]
                        if item["currency"] == 2:
                            yesterday_consumer_discount += item["num"]
                    if item["created"] >= start_time and item["created"] <= end_time:
                        if item["currency"] == 1:
                            today_consumer_gold += item["num"]
                        if item["currency"] == 2:
                            today_consumer_discount += item["num"]
                data["today_consumer_gold"] = today_consumer_gold
                data["yesterday_consumer_gold"] = yesterday_consumer_gold
                data["today_consumer_discount"] = today_consumer_discount
                data["yesterday_consumer_discount"] = yesterday_consumer_discount
                self.log_info(f"顶部基础数据结果: {data}")
                return self.answer(data=data)
        except Exception as e:
            self.log_err(f"顶部基础数据失败: {str(e)}")
            return self.answer(self.sta_code.FAIL, hint=str(e))



class IndexUserData(AdminAuthApi):
    """ 用户基础数据 """
    async def get(self, req: Request):
        start_time, end_time = await self.get_time_range("day")
        week_start_time = start_time - 86400 * 7
        yesterday_start_time = start_time - 86400
        yesterday_end_time = end_time - 86400
        data = {
            "today_add_user": 0,
            "yesterday_add_user": 0,
            "week_add_user": 0,
            "today_login_user": 0,
            "yesterday_login_user": 0,
            "week_login_user": 0,
            "today_activate_user": 0,
            "yesterday_activate_user": 0,
            "week_activate_user": 0,
            "today_pay_money": 0,
            "yesterday_pay_money": 0,
            "week_pay_money": 0,
        }
        # 新增用户
        self.log_info(f"用户基础数据-新增用户")
        sta, user_data = await BaseUserRC.get_user_filter(start_time=week_start_time, end_time=end_time)
        self.log_info(f"用户基础数据-新增用户结果：{user_data}")
        if sta:
            yesterday_add_user = today_add_user = week_add_user = 0
            for user in user_data:
                if user["created"] >= yesterday_start_time and user["created"] <= yesterday_end_time:
                    yesterday_add_user += 1
                if user["created"] >= start_time and user["created"] <= end_time:
                    today_add_user += 1
            data["today_add_user"] = today_add_user
            data["yesterday_add_user"] = yesterday_add_user
            data["week_add_user"] = len(user_data)
        # 登录用户
        sta, online_user = await RecordsAdEventRC.get_uid_login_list(start_time=week_start_time, end_time=end_time)
        self.log_info(f"用户基础数据-登录用户结果：{online_user}")
        if sta:
            yesterday_login_user = today_login_user = week_login_user = []
            for user in online_user:
                if user["created"] >= yesterday_start_time and user["created"] <= yesterday_end_time:
                    yesterday_login_user.append(user["uid"])
                if user["created"] >= start_time and user["created"] <= end_time:
                    today_login_user.append(user["uid"])
                week_login_user.append(user["uid"])
            data["today_login_user"] = len(set(today_login_user))
            data["yesterday_login_user"] = len(set(yesterday_login_user))
            data["week_login_user"] = len(set(week_login_user))
        data["today_activate_user"] = data["today_login_user"]
        data["yesterday_activate_user"] = data["yesterday_login_user"]
        data["week_activate_user"] = data["week_login_user"]
        # 充值统计
        order_data, msg = await OrderRC.get_order_filter(start_time=week_start_time, end_time=end_time, currency=5, status=99)
        self.log_info(f"用户基础数据-充值统计结果：{order_data}")
        if order_data:
            today_pay_money = yesterday_pay_money = week_pay_money = 0
            for order in order_data:
                if order["created"] >= yesterday_start_time and order["created"] <= yesterday_end_time:
                    yesterday_pay_money += order["amount"]
                if order["created"] >= start_time and order["created"] <= end_time:
                    today_pay_money += order["amount"]
            data["week_pay_money"] += week_pay_money
            data["today_pay_money"] = today_pay_money
            data["yesterday_pay_money"] = yesterday_pay_money
        return self.answer(data=data)

class IndexBaseTable(AdminAuthApi):
    """ 基础数据报表 """

    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        date_range = await self.date_time_range(start_time, end_time)
        data = {}
        for item_day in date_range:
            date_time = str(item_day)
            unit = {
                "date": date_time,
                "add_user": 0,
                "activate_user": 0,
                "pay_money": 0,
                "pay_user": 0,
                "pay_rate": 0,
                "arpu": 0,  # 平均每用户支付金额
                "arppu": 0,  # 平均每用户支付次数
            }
            data[date_time] = unit
        # 新增用户
        sta, user_data = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time)
        if sta:
            for user in user_data:
                if user['created'] < start_time:
                    continue
                day = tool_dt.dt_str(user['created'], '%Y-%m-%d')
                data[day]["add_user"] += 1
        # 活跃用户
        sta, online_user = await RecordsAdEventRC.get_uid_login_list(start_time=start_time, end_time=end_time)
        if sta:
            activate_day = {}
            for user in online_user:
                day = tool_dt.dt_str(user['created'], '%Y-%m-%d')
                if day not in activate_day:
                    activate_day[day] = set()
                if user["uid"] not in activate_day[day]:
                    activate_day[day].add(user["uid"])
                data[day]["activate_user"] = len(activate_day[day])
        # 付费用户
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, status=99)
        if order_data:
            pay_user = {}
            for order in order_data:
                day = tool_dt.dt_str(order['created'], '%Y-%m-%d')
                data[day]["pay_money"] += order["amount"]
                if day not in pay_user:
                    pay_user[day] = set()
                if order["uid"] not in pay_user[day]:
                    pay_user[day].add(order["uid"])
                data[day]["pay_user"] = len(pay_user[day])
                data[day]["pay_rate"] = ("%.2f" % (data[day]["pay_user"] / data[day]["activate_user"])) if data[day]["activate_user"] > 0 else 0
                data[day]["arpu"] = ("%.2f" % (data[day]["pay_money"] / data[day]["pay_user"])) if data[day]["pay_user"] > 0 else 0
                data[day]["arppu"] = ("%.2f" % (data[day]["pay_user"] / data[day]["activate_user"])) if data[day]["activate_user"] > 0 else 0
        result = [item for item in data.values()]
        return self.answer(data=result)

class IndexGameData(AdminAuthApi):
    """ 游戏玩法数据 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        uid = self.check_int(req.args.get('uid'), require=False, p_name='用户ID')
        yesterday_start_time = date_time - 86400
        yesterday_end_time = date_time - 1
        today_end_time = date_time + 86400 - 1
        data, msg = await RecordsGameTotalRC.get_record_total_by_filter(start_time=yesterday_start_time, end_time=today_end_time, uid=uid)
        result = {}
        if data:
            for item in data:
                today_key = f"today_play_{item['play_type']}"
                if today_key not in result:
                    result[today_key] = 0
                if item["created"] >= yesterday_start_time and item["created"] <= yesterday_end_time:
                    result[today_key] += 1
                yesterday_key = f"yesterday_play_{item['play_type']}"
                if yesterday_key not in result:
                    result[yesterday_key] = 0
                if item["created"] >= date_time and item["created"] <= today_end_time:
                    result[yesterday_key] += 1
        return self.answer(data=result)

class IndexGameUserChart(AdminAuthApi):
    """ 游戏对局人数折线图 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        data, msg = await RecordsGameTotalRC.get_record_total_by_filter(start_time=start_time, end_time=end_time)
        result = {}
        unit = {
            "x": "",
            "y": 0,
        }
        if data:
            data_dict = {}
            for item in data:
                key = f"play_{item['play_type']}"
                day = tool_dt.dt_str(item['created'], '%Y-%m-%d')
                if key not in data_dict:
                    data_dict[key] = {}
                if day not in data_dict[key]:
                    data_dict[key][day] = unit.copy()
                    data_dict[key][day]["x"] = day
                data_dict[key][day]["y"] += 1
            result = {key: list(data_dict[key].values()) for key in data_dict}
        return self.answer(data=result)


class IndexOnlineUserChart(AdminAuthApi):
    """ 实时在线人数折线图 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        now_online = await BaseUserRC.get_online_uid()
        now_time = int(datetime.now().timestamp())
        now_hour = tool_dt.dt_str(tool_dt.cut_utctime(), '%Y-%m-%d %H')
        now_hour_arr = now_hour.split(' ')
        hours = range(1, 24, 1)
        unit_list = []
        for hour in hours:
            if hour > int(now_hour_arr[1]):
                break
            unit_list.append({
                "x": f"{now_hour_arr[0]} {hour:02d}",
                "y": 0,
            })
        result = {
            "list": unit_list,
            "now_online": len(now_online),
            "now_time": now_time,
            "avg": 0,
            "total": 0,
        }
        sta, login_user = await RecordsAdEventRC.get_uid_login_list(start_time=date_time, end_time=end_time)
        if sta:
            result["total"] = len(login_user)
            hour_user = {}
            for user in login_user:
                hour_time = tool_dt.dt_str(user["created"], '%Y-%m-%d %H')
                if hour_time not in hour_user:
                    hour_user[hour_time] = set()
                else:
                    if user["uid"] not in hour_user[hour_time]:
                        hour_user[hour_time].add(user["uid"])
                for key in result["list"]:
                    if key["x"] == hour_time:
                        key["y"] = len(hour_user[hour_time])
            result["avg"] = ("%.2f" % (len(login_user) / len(unit_list)))
        return self.answer(data=result)

class IndexPayMoneyRealTime(AdminAuthApi):
    """ 实时付费金额折线图 """
    async def get(self, req: Request):
        date_time = self.check_int(req.args.get('date_time'), require=True, p_name='时间')
        end_time = date_time + 86400 - 1
        now_time = int(datetime.now().timestamp())
        hour = int(tool_dt.dt_str(now_time, '%H'))
        hours = range(0, hour, 1)
        unit_list = []
        for hour in hours:
            unit_list.append({
                "x": hour,
                "y": 0,
            })
        result = {
            "list": unit_list,
            "last_money": 0,
            "last_time": 0,
            "avg": 0,
            "total": 0,
        }
        order_data, msg = await OrderRC.get_order_filter(start_time=date_time, end_time=end_time, currency=5, status=99)
        if order_data:
            hour_money = hour_user = {}
            for order in order_data:
                hour_time = int(tool_dt.dt_str(order["created"], '%H'))
                if hour_time not in hour_money:
                    hour_money[hour_time] = 0
                # if hour_time not in hour_user:
                #     hour_user[hour_time] = set()
                # if order["uid"] not in hour_user[hour_time]:
                #     hour_user[hour_time].add(order["uid"])
                hour_money[hour_time] += order["amount"]
                for key in result["list"]:
                    if key["x"] == hour_time:
                        key["y"] = hour_money[hour_time]
                result["total"] += order["amount"]
                result["last_money"] = order["amount"]
                result["last_time"] = int(order["created"].timestamp())
            result["avg"] = result["total"] / len(hours)
        return self.answer(data=result)

class IndexPayMoneyTotalChart(AdminAuthApi):
    """ 累计付费金额折线图 """
    async def get(self, req: Request):
        now_time = int(datetime.now().timestamp())
        hour = int(tool_dt.dt_str(now_time, '%H'))
        hours = range(0, hour, 1)
        unit_list = []
        for hour in hours:
            unit_list.append({
                "x": hour,
                "y": 0,
            })
        result = {
            "list": unit_list,
            "total": 0,
        }
        order_data, msg = await OrderRC.get_order_filter(currency=5, status=99)
        if order_data:
            hour_money = {}
            for order in order_data:
                hour_time = int(tool_dt.dt_str(order["created"], '%H'))
                if hour_time not in hour_money:
                    hour_money[hour_time] = 0
                hour_money[hour_time] += order["amount"]
                for key in result["list"]:
                    if key["x"] == hour_time:
                        key["y"] = hour_money[hour_time]
                result["total"] += order["amount"]
        return self.answer(data=result)

class IndexAddUserTable(AdminAuthApi):
    """ 过去七日新增用户报表 """

    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        platform = self.check_int(req.args.get('platform'), require=False, p_name='平台')
        sta, user_data = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time, platform=platform, order_field="uid")
        unit = {
            "date": "",
            "one_day": 0,
            "two_day": 0,
            "three_day": 0,
            "four_day": 0,
            "five_day": 0,
            "six_day": 0,
            "seven_day": 0,
        }
        data = {}
        result = {}
        if sta:
            dates = set()
            one_day = two_day = three_day = four_day = five_day = six_day = 0
            for user in user_data:
                date = tool_dt.dt_str(user["created"], '%Y-%m-%d')
                if date not in dates:
                    data_unit = unit.copy()
                    data_unit["date"] = date
                    data[date] = data_unit
                    dates.add(date)
                if date in dates and len(dates) == 1:
                    data[date]["one_day"] += 1
                    one_day += 1
                elif date in dates and len(dates) == 2:
                    data[date]["one_day"] = one_day
                    data[date]["two_day"] += 1
                    two_day += 1
                elif date in dates and len(dates) == 3:
                    data[date]["two_day"] = two_day
                    data[date]["three_day"] += 1
                    three_day += 1
                elif date in dates and len(dates) == 4:
                    data[date]["three_day"] = three_day
                    data[date]["four_day"] += 1
                    four_day += 1
                elif date in dates and len(dates) == 5:
                    data[date]["four_day"] = four_day
                    data[date]["five_day"] += 1
                    five_day += 1
                elif date in dates and len(dates) == 6:
                    data[date]["five_day"] = five_day
                    data[date]["six_day"] += 1
                    six_day += 1
                elif date in dates and len(dates) == 7:
                    data[date]["six_day"] = six_day
                    data[date]["seven_day"] += 1
            if data:
                result["list"] = [item for item in data.values()]
        return self.answer(data=result)


class IndexAddUserChart(AdminAuthApi):
    """ 过去七日留存率折线图 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        sta, user_data = await BaseUserRC.get_user_filter(start_time=start_time, end_time=end_time)
        login_sta, login_user = await RecordsAdEventRC.get_uid_login_list(start_time=start_time, end_time=end_time)
        data = result = {}
        unit = {
            "x": "",
            "y": 0,
        }
        if sta:
            dates = set()
            date_user = {}
            for user in user_data:
                date = tool_dt.dt_str(user["created"], '%Y-%m-%d')
                if date not in dates:
                    data_unit = unit.copy()
                    data_unit["x"] = date
                    data[date] = data_unit
                    dates.add(date)
                    date_user[date] = set()
                date_user[date].add(user["uid"])
            item_login = set()
            for item in login_user:
                day = tool_dt.dt_str(item["created"], '%Y-%m-%d')
                if item["uid"] not in item_login:
                    item_login.add(item["uid"])
                    if day in date_user and item["uid"] in date_user[day]:
                        data[day]["y"] += 1
            result = [item for item in data.values()]
        return self.answer(data=result)

class IndexPayMoneyChart(AdminAuthApi):
    """ 过去七日充值金额折线图 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5, status=99)
        result = {}
        if order_data:
            unit = {
                "x": "",
                "y": 0,
            }
            data = {}
            dates = set()
            for item in order_data:
                x = tool_dt.dt_str(item["created"], '%Y-%m-%d')
                if x not in dates:
                    data_unit = unit.copy()
                    data_unit["x"] = x
                    data[x] = data_unit
                    dates.add(x)
                if x in dates:
                    data[x]["y"] += item["amount"]
            result["list"] = [item for item in data.values()]
        return self.answer(data=result)

class IndexPayUserChart(AdminAuthApi):
    """ 过去七日充值用户折线图 """
    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        order_data, msg = await OrderRC.get_order_filter(start_time=start_time, end_time=end_time, currency=5, status=99)
        result = {}
        if order_data:
            unit = {
                "x": "",
                "y": 0,
            }
            data = {}
            users = {}
            for item in order_data:
                x = tool_dt.dt_str(item["created"], '%Y-%m-%d')
                if x not in users:
                    data_unit = unit.copy()
                    data_unit["x"] = x
                    data[x] = data_unit
                    users[x] = set()
                if item["uid"] not in users:
                    users[x].add(item["uid"])
                if x in users:
                    data[x]["y"] = len(users[x])
            result["list"] = [item for item in data.values()]
        return self.answer(data=result)
