from tortoise.functions import Sum
from common.public.conf import R_UID_THRESHOLD
from lucky_admin.base_api import AdminAuthApi
from lucky_game.const import OrderStatus, PayMode
from lucky_game.interface.some_pay import DouYinGameQueryOrder
from lucky_game.model_db.main import RecordsTradeOrder
from lucky_game.model_rc.base_user import BaseUserRC


class OrderHandler(AdminAuthApi):
    """ 订单处理 """

    async def post(self, req, **_b):
        order_status = req.json.get("order_status")
        query_p = {}
        if order_status:
            order_status = self.check_int(
                order_status, minval=OrderStatus.DEFAULT, maxval=OrderStatus.REFUND, p_name='order_status(订单状态)')
            query_p["order_status"] = order_status

        uid = req.json.get("uid")
        if uid:
            uid = self.check_int(uid, minval=R_UID_THRESHOLD + 1, p_name='uid')
            query_p["uid"] = uid

        gte_time = req.json.get("gte_time")
        if gte_time:
            created = self.check_int(gte_time, minval=0, p_name='created')
            query_p["created__gte"] = created

        limit = 10
        page = req.json.get('page') or 1
        self.check_int(page, require=True, default=1, minval=1, p_name='page')
        offset = (page - 1) * limit

        count = await RecordsTradeOrder.filter(**query_p).count()
        dlist = await RecordsTradeOrder.get_by_dict(query_p, limit=limit, offset=offset)
        data = {
            'count': count,
            'records': dlist
        }

        is_sum = req.json.get("is_sum") or 0
        if is_sum:
            self.check_int(is_sum, minval=0, maxval=1, p_name='is_sum')
            res = await RecordsTradeOrder.filter(**query_p).annotate(
                total_amount=Sum("trade_amount")).values('total_amount')
            total_amount = res[0]['total_amount'] if res else 0
            data["total_amount"] = total_amount

        self.answer(data=data)


class ReplenishmentOrder(AdminAuthApi):
    """ 补充订单 """

    DOU_YIN_GAME = DouYinGameQueryOrder()
    HANDLER_LIST = [DOU_YIN_GAME]
    for h in HANDLER_LIST:
        h.decorators = []

    async def post(self, req, **_):
        order_id = req.json.get("order_id")
        order_id = self.check_str(order_id, require=True, p_name="order_id")
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
        if not order_info:
            self.answer(self.sta_code.FAIL, hint="订单不存在")
        if order_info.get("order_status") == OrderStatus.PAID:
            self.answer(hint="订单状态已支付，请勿重复操作")
        uid = order_info.get("uid")
        if not uid:
            self.answer(hint=f"uid有误：{uid}")
        u_info = await BaseUserRC.cache_by_uid(uid)
        if not u_info:
            self.answer(hint=f"获取不到玩家信息：{uid}")

        self.log_info("补单：", uid, order_id)
        pay_mode = order_info.get("pay_mode")
        match pay_mode:
            case PayMode.DOUYIN_MINI_GAME:
                return await self.DOU_YIN_GAME.post(req, u_info=u_info, call_admin=True)
            case _:
                self.answer(self.sta_code.FAIL, hint="订单不支持该操作！")





