"""
订单相关
"""
import traceback
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse, json_encode
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from common.utils.kit_dt import KitDt
from lucky_game.base_api import GameAuthApi, SpecialApi
from lucky_game.handler.up_assets import UpAssets, StatFlow
from lucky_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from lucky_game.model_rc.base_award import AwardRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.vip_level import UserVipRC, ConfVipRC
from lucky_game.const import ActivityType, ActivitySta, ConditionType, ReasonCostDiamond, ActivityStatus, PayMode
from lucky_game.logic.activity import Base, SignIn, Package, InfinitePlay, FirstCharge
from common.aliyun.pay_service import AlipayPayment
from lucky_game.logic.payment import PaymentLogic


class OrderDetail(GameAuthApi):
    """查询订单详情"""
    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        order_no = self.check_str(req.args.get("order_no"), require=True, p_name="订单号")
        if not order_no:
            return self.answer(code=self.sta_code.FAIL, hint="订单号不能为空")
        order, msg = await OrderRC.get_order_info(order_no=order_no)
        if not order:
            return self.answer(code=self.sta_code.FAIL, hint="订单不存在")
        return self.answer(data=order)

class PayOrder(GameAuthApi):
    """支付订单"""
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        order_no = self.check_str(req.args.get("order_no"), require=True, p_name="订单号")
        if not order_no:
            return self.answer(code=self.sta_code.FAIL, hint="订单号不能为空")
        order, msg = await OrderRC.get_order_info(order_no=order_no)
        if not order:
            return self.answer(code=self.sta_code.FAIL, hint="订单不存在")
        sta, msg = PaymentLogic().pay(uid=uid, data_before=order, express=order.get("express"))
        return self.answer(data=order)

class CallbackAli(SpecialApi):
    """支付宝订单回调"""
    async def post(self, req: Request):
        form = req.get_form()
        json = req.json
        self.loginfo(f"支付宝回调参数form: {form}")
        self.loginfo(f"支付宝回调参数json: {json}")
        sta, data = AlipayPayment().verify_callback(form)
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint="回调失败")
        order_no = data.get("out_trade_no")
        trade_no = data.get("trade_no")
        trade_status = data.get("trade_status")
        sta, msg = PaymentLogic().completed_order(order_no=order_no, trade_no=trade_no, out_trade_status=trade_status,
                                        explain="支付宝回调")
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=msg)
        return self.answer()


class CallbackHf(SpecialApi):
    """汇付天下订单回调"""
    async def post(self, req: Request):
        form = req.get_form()
        json = req.json
        self.loginfo(f"汇付天下回调参数form: {form}")
        self.loginfo(f"汇付天下回调参数json: {json}")
        sta, data = PaymentLogic().verify_callback(form)
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint="回调失败")
        order_no = data.get("out_trade_no")
        trade_no = data.get("trade_no")
        trade_status = data.get("trade_status")
        sta, msg = PaymentLogic().completed_order(order_no=order_no, trade_no=trade_no, out_trade_status=trade_status,
                                        explain="汇付天下回调")
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=msg)
        return self.answer()


