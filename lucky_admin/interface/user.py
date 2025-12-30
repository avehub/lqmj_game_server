from nsanic.libs import tool_jwt, tool_dt
from sanic import Request
from datetime import datetime, date
from common.public.enum_const import JWType
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.const import AdminPermission
from lucky_admin.model_rc.base_admin import BaseAdminRC
from lucky_game.const import ReasonCostGold
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.user_activity import UserActivityProgressRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.model_rc.base_store import GoodRC
from common.utils.utils import UtilsTool
from lucky_admin.logic.order_logic import OrderLogic


class User(AdminAuthApi):

    async def get(self, req: Request, **kwargs):
        """ 用户列表 """
        is_vip = self.check_int(req.args.get('is_vip'), require=False, p_name='是否是会员')
        uid = self.check_int(req.args.get('uid'), require=False, p_name='玩家ID')
        address = self.check_str(req.args.get('address'), require=False, p_name='归属地')
        phone = self.check_str(req.args.get('phone'), require=False, p_name='手机号')
        id_card = self.check_str(req.args.get('id_card'), require=False, p_name='身份证')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        sta, data = await BaseUserRC.get_user_filter(uid=uid, is_vip=is_vip, address=address, phone=phone,
                                                      id_card=id_card,page=page, page_size=page_size)
        online_uid = await BaseUserRC.get_online_uid([item['uid'] for item in data['list']])
        for item in data['list']:
            item['is_online'] = 1 if item['uid'] in online_uid else 0
        return self.answer(data=data if sta else [])

    async def put(self, req: Request, **kwargs):
        """ 更新用户信息 """
        uid = self.check_int(req.json.get('uid'), require=True, p_name='玩家ID')
        name = self.check_str(req.json.get('name'), require=False, p_name='玩家昵称')
        real_name = self.check_str(req.json.get('real_name'), require=False, p_name='玩家真实姓名')
        phone = self.check_str(req.json.get('phone'), require=False, p_name='手机号')
        id_card = self.check_str(req.json.get('id_card'), require=False, p_name='身份证')
        openid = self.check_str(req.json.get('openid'), require=False, p_name='微信授权单平台用户唯一标识')
        unionid = self.check_str(req.json.get('unionid'), require=False, p_name='微信授权多平台用户唯一标识')
        ban_time = self.check_int(req.json.get('ban_time'), require=False, p_name='封禁时间：0未封禁 -1永久封禁 大于0为封禁时间')
        discount = self.check_float(req.json.get('discount'), require=False, p_name='消费折扣')
        u_info = await BaseUserRC.cache_by_pk(uid)
        if not u_info:
            return self.answer(self.sta_code.FAIL, hint="用户不存在")
        up_data = {}
        if name is not None:
            up_data['name'] = name
        if real_name:
            up_data['real_name'] = real_name
        if phone is not None:
            up_data['phone'] = phone
        if id_card is not None:
            up_data['id_card'] = id_card
        if openid is not None:
            up_data['openid'] = openid
        if unionid is not None:
            up_data['unionid'] = unionid
        if ban_time is not None:
            up_data['ban_time'] = ban_time
        if discount is not None:
            up_data['discount'] = discount
        data = None
        if up_data:
            data = await BaseUserRC.update_info(u_info, up_data)
        if not data:
            return self.answer(self.sta_code.FAIL, hint="无任何跟新")
        return self.answer(data=data)

class UserStatus(AdminAuthApi):
    """ 用户状态 """

    async def get(self, req: Request, **kwargs):
        uid = self.check_int(req.args.get('uid'), require=True, p_name='玩家ID')
        u_info = await BaseUserRC.cache_by_pk(uid)
        if not u_info:
            return self.answer(self.sta_code.FAIL, hint="用户不存在")
        sta, act_progress = await UserActivityProgressRC.get_activity_progress(uid=uid)
        data = {
            "user_info": u_info,
            "activity_progress": act_progress if sta else []
        }
        return self.answer(data=data)


class OrderList(AdminAuthApi):
    """ 充值记录 """

    async def get(self, req: Request, **kwargs):
        order_no = self.check_str(req.args.get('order_no'), require=False, p_name='订单号')
        status = self.check_int(req.args.get('status'), require=False, p_name='订单状态')
        pay_mode = self.check_int(req.args.get('pay_mode'), require=False, p_name='支付方式')
        uid = self.check_int(req.args.get('uid'), require=False, p_name='用户ID')
        start_time = self.check_int(req.args.get('start_time'), require=False, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=False, p_name='结束时间')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        data, msg = await OrderRC.get_order_filter(order_no=order_no, status=status, pay_mode=pay_mode, uid=uid,
                                              start_time=start_time, end_time=end_time, page=page, page_size=page_size)
        if data and data['list']:
            data['list'] = await OrderLogic.order_sku_good(data['list'])
        return self.answer(data=data, hint=msg)


class OrderStatistics(AdminAuthApi):
    """ 充值统计 """

    async def get(self, req: Request, **kwargs):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        date_range = await self.date_time_range(start_time, end_time)
        result = []
        for item_day in date_range:
            date_time = str(item_day)
            unit = {
                "date_time": date_time,
                "amount": 0,
                "count": 0,
                "first_amount": 0,
                "first_count": 0,
                "return_gift_amount": 0,
                "return_gift_count": 0,
                "revive_gift_amount": 0,
                "revive_gift_count": 0,
                "replenish_gift_amount": 0,
                "replenish_gift_count": 0,
                "diamond_amount": 0,
                "diamond_count": 0,
                "room_card_amount": 0,
                "room_card_count": 0,
                "yellow_diamond_amount": 0,
                "yellow_diamond_count": 0,
            }
            result.append(unit)

        data, msg = await OrderRC.get_order_filter(start_time=start_time, status=99, end_time=end_time, page=page, page_size=page_size)
        if not data or not data['list']:
            return self.answer(data=result)
        tmp_dict = await OrderLogic.order_sku_good(data['list'], type='order_statistics', range_tmp=date_range)
        if tmp_dict:
            results = []
            for day, item in tmp_dict.items():
                if day in result:
                    result[day].update(item)
                results.append(item)
            result = results
        return self.answer(data=result)


class ResourceChanges(AdminAuthApi):
    """ 资产流水 """

    async def get(self, req: Request, **kwargs):
        start_time = self.check_int(req.args.get('start_time'), require=False, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=False, p_name='结束时间')
        uid = self.check_int(req.args.get('uid'), require=False, p_name='用户ID')
        status = self.check_int(req.args.get('status'), require=False, p_name='方式')
        currency = self.check_int(req.args.get('currency'), require=False, p_name='类型')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        sta, data = await ExtraUserResourceChangesRC.get_resource_changes_filter(uid=uid, status=status,
                                                                                 currency=currency, start_time=start_time,
                                                                                 end_time=end_time, page=page, page_size=page_size)
        return self.answer(data=data)


class ResourceChangeChart(AdminAuthApi):
    """资源消耗折线图"""
    async def get(self, req: Request, **kwargs):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        currency = self.check_int(req.args.get('currency'), require=False, default=3, p_name='类型')
        status = self.check_int(req.args.get('status'), require=False, default=0, p_name='方式')
        date_range = await self.date_time_range(start_time, end_time)
        sta, data = await ExtraUserResourceChangesRC.get_resource_changes_filter(start_time=start_time, status=status,
                                                                                 end_time=end_time, currency=currency)
        result = []
        for item_day in date_range:
            x = str(item_day)
            unit = {
                "x": x,
                "y": 0,
            }
            if sta and data:
                for item in data:
                    day = tool_dt.dt_str(item['created'], '%Y-%m-%d')
                    if x == day:
                        unit['y'] += item['num']
            result.append(unit)

        return self.answer(data=result)


class UserResource(AdminAuthApi):
    """修改用户资源"""

    async def put(self, req: Request, **kwargs):
        operation_values = await ExtraUserResourceChangesRC.change_operation()
        field_values = await ExtraUserResourceChangesRC.change_field()
        def is_valid_operation(x):
            return x in operation_values
        def is_valid_field(x):
            return x in field_values

        operation = self.check_type(
            req.json.get("operation"),
            query_fun=is_valid_operation,
            require=True,
            is_int=False,
            p_name="operation"
        )
        change_field = self.check_type(
            req.json.get("change_field"),
            query_fun=is_valid_field,
            is_int=False,
            require=True,
            p_name="change_field"
        )
        change_val = self.check_int(req.json.get("change_val"), require=True, minval=0, p_name="change_val")
        uid = self.check_str(req.json.get("uid"), require=True, p_name="uid")
        sta, e = await ExtraUserResourceChangesRC.change_user_resource(
            uid,
            change_field,
            change_val,
            operation,
            reason=ReasonCostGold.ADMIN_ALTER_USER
        )
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=e)
        p_info = await BaseUserRC.cache_by_pk(uid)
        return self.answer(data=p_info)
