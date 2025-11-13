from nsanic.libs import tool_jwt, tool_dt
from sanic import Request
from datetime import datetime, date
from common.public.enum_const import JWType
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.const import AdminPermission
from lucky_admin.model_rc.base_admin import BaseAdminRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.user_activity import UserActivityProgressRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.model_rc.base_store import GoodRC
from common.utils.utils import UtilsTool


class User(AdminAuthApi):

    async def get(self, req: Request):
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
        if not sta:
            return self.answer(self.sta_code.FAIL, hint="暂无数据")
        return self.answer(data=data)

    async def put(self, req: Request):
        """ 更新用户信息 """
        uid = self.check_int(req.json.get('uid'), require=True, p_name='玩家ID')
        name = self.check_str(req.json.get('name'), require=False, p_name='玩家昵称')
        real_name = self.check_str(req.json.get('real_name'), require=False, p_name='玩家真实姓名')
        phone = self.check_str(req.json.get('phone'), require=False, p_name='手机号')
        id_card = self.check_str(req.json.get('id_card'), require=False, p_name='身份证')
        openid = self.check_str(req.json.get('openid'), require=False, p_name='微信授权单平台用户唯一标识')
        unionid = self.check_str(req.json.get('unionid'), require=False, p_name='微信授权多平台用户唯一标识')
        ban_time = self.check_int(req.json.get('ban_time'), require=False, p_name='封禁时间：0未封禁 -1永久封禁 大于0为封禁时间')
        discount = self.check_int(req.json.get('discount'), require=False, p_name='消费折扣')
        u_info = await BaseUserRC.cache_by_pk(uid)
        if not u_info:
            return self.answer(self.sta_code.FAIL, hint="用户不存在")
        up_data = {}
        if name:
            up_data['name'] = name
        if real_name:
            up_data['real_name'] = real_name
        if phone:
            up_data['phone'] = phone
        if id_card:
            up_data['id_card'] = id_card
        if openid:
            up_data['openid'] = openid
        if unionid:
            up_data['unionid'] = unionid
        if ban_time:
            up_data['ban_time'] = ban_time
        if discount:
            up_data['discount'] = discount
        data = None
        if up_data:
            data = await BaseUserRC.update_info(u_info, up_data)
        if not data:
            return self.answer(self.sta_code.FAIL, hint="无任何跟新")
        return self.answer(data=data)

class UserStatus(AdminAuthApi):
    """ 用户状态 """

    async def get(self, req: Request):
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

    async def get(self, req: Request):
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
        return self.answer(data=data, hint=msg)


class OrderStatistics(AdminAuthApi):
    """ 充值统计 """

    async def get(self, req: Request):
        start_time = self.check_int(req.args.get('start_time'), require=True, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=True, p_name='结束时间')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        data, msg = await OrderRC.get_order_filter(start_time=start_time, status=99, end_time=end_time, page=page, page_size=page_size)
        start_date = tool_dt.dt_str(start_time, '%Y-%m-%d').split('-')
        end_date = tool_dt.dt_str(end_time, '%Y-%m-%d').split('-')
        date_range = tool_dt.date_range(start=datetime(int(start_date[0]), int(start_date[1]), int(start_date[2])),
                                        end=datetime(int(end_date[0]), int(end_date[1]), int(end_date[2])))

        tmp = {}
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
            # tmp[date_time] = unit
            result.append(unit)
        # if data and data['list']:
        #     sku_list = [item['sku_id'] for item in data['list']]
        #     # 过滤掉重复的sku
        #     sku_list = list(set(sku_list))
        #     sku_data = await GoodRC.get_good_filter(sku=sku_list)
        #     if sku_data:
        #         # 类型：1首充 2金币 3钻石 4房卡 5黄钻 6VIP 7周卡 8月卡 9终身卡 10金币补足 11复活礼包 12返还礼包
        #         sku_dict = {item['sku']: item for item in sku_data}
        #         for item in data:
        #             day = tool_dt.dt_str(item['created'], '%Y-%m-%d')
        #             tmp[day]['amount'] += item['amount']
        #             tmp[day]['count'] += 1
        #             if item['sku_id'] in sku_dict:
        #                 if sku_dict[item['sku_id']]['type'] == 1:
        #                     tmp[day]['first_amount'] += item['amount']
        #                     tmp[day]['first_count'] += 1
        #                 elif sku_dict[item['sku_id']]['type'] == 3:
        #                     tmp[day]['diamond_amount'] += item['amount']
        #                     tmp[day]['diamond_count'] += 1
        #                 elif sku_dict[item['sku_id']]['type'] == 4:
        #                     tmp[day]['room_card_amount'] += item['amount']
        #                     tmp[day]['room_card_count'] += 1
        #                 elif sku_dict[item['sku_id']]['type'] == 5:
        #                     tmp[day]['yellow_diamond_amount'] += item['amount']
        #                     tmp[day]['yellow_diamond_count'] += 1
        #                 elif sku_dict[item['sku_id']]['type'] == 10:
        #                     tmp[day]['replenish_gift_amount'] += item['amount']
        #                     tmp[day]['replenish_gift_count'] += 1
        #                 elif sku_dict[item['sku_id']]['type'] == 11:
        #                     tmp[day]['revive_gift_amount'] += item['amount']
        #                     tmp[day]['revive_gift_count'] += 1
        #                 elif sku_dict[item['sku_id']]['type'] == 12:
        #                     tmp[day]['return_gift_amount'] += item['amount']
        #                     tmp[day]['return_gift_count'] += 1
        #             result.append(tmp[day])
        return self.answer(data=result)


class ResourceChanges(AdminAuthApi):
    """ 资产流水 """

    async def get(self, req: Request):
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
