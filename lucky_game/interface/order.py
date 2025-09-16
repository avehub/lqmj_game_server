"""
订单相关
"""
import traceback
from sanic import Request, response
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse, json_encode
from tortoise.transactions import in_transaction

from common.public.conf import WeChatConf
from common.public.enum_const import DbKey, StaCode
from common.utils.kit_dt import KitDt
from lucky_game.base_api import GameAuthApi, SpecialApi
from lucky_game.handler.huifu import DouGongPay
from lucky_game.handler.up_assets import UpAssets, StatFlow
from lucky_game.handler.wechat import WeChat
from lucky_game.interface.some_pay import BaseSomePay
from lucky_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from lucky_game.model_rc.base_award import AwardRC
from lucky_game.model_rc.base_store import GoodRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.vip_level import UserVipRC, ConfVipRC
from lucky_game.const import OrderStatus, PayMode, GainStatus, PlatForm
from lucky_game.logic.activity import Base, SignIn, Package, InfinitePlay, FirstCharge
from common.aliyun.pay_service import AlipayPayment
from lucky_game.logic.payment import PaymentLogic
from lucky_game.handler.ios_pay import ios_service


class OrderDetail(GameAuthApi):
    """查询订单详情"""

    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        order_no = self.check_str(req.args.get("order_no"), require=True, p_name="订单号")
        query_platform = self.check_int(req.args.get("query_platform"), require=False, default=1, p_name="查询平台")
        if not order_no:
            return self.answer(code=self.sta_code.FAIL, hint="订单号不能为空")
        order, msg = await OrderRC.get_order_info(order_no=order_no)
        if not order:
            return self.answer(code=self.sta_code.FAIL, hint="订单不存在")
        if query_platform != 0:
            # 为待支付订单主动查询支付平台订单状态
            payment = PaymentLogic()
            sta, msg, up_data = await payment.order_method(order.get("pay_mode"), order_no, order.get("out_order_no"))
            trade_status = up_data.get("trade_status")
            if sta and trade_status != order.get("status"):
                if trade_status == OrderStatus.PAID and order.get("status") != OrderStatus.PAID:
                    await payment.completed_order(order_no=order_no, trade_no=up_data.get("trade_no"),
                                                  order_status=trade_status)
                    order, _ = await OrderRC.get_order_info(order_no)
        return self.answer(data=order)


class UnclaimedOrder(GameAuthApi):
    """未领取的订单"""

    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        gain_status = self.check_int(req.args.get("gain_status"), require=False, default=GainStatus.GAINED,
                                     p_name="领取状态")
        order, msg = await OrderRC.get_order_filter(uid=uid, gain_status=gain_status, status=OrderStatus.PAID)
        return self.answer(data=order, hint=msg)


class GainOrder(GameAuthApi):
    """领取订单"""

    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        order_no = self.check_str(req.json.get("order_no"), require=True, p_name="订单号")
        if not order_no:
            return self.answer(code=self.sta_code.FAIL, hint="订单号不能为空")
        order, msg = await OrderRC.get_order_info(order_no=order_no)
        if not order:
            return self.answer(code=self.sta_code.FAIL, hint="订单不存在")
        if order.get("gain_status") == GainStatus.RECEIVED:
            return self.answer(code=self.sta_code.FAIL, hint="订单已领取")
        good = await GoodRC.get_good_info(order.get("sku"))
        sta, msg = await PaymentLogic().pay_after(u_info, good, order_no)
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=msg)
        return self.answer(data={"good": good["content"] if isinstance(good["content"], list) else [good["content"]]},
                           hint=msg)


class CallbackAli(SpecialApi):
    """支付宝订单回调"""

    async def post(self, req: Request, **kwargs):
        form = req.get_form()
        signature = req.json.get("sign", "")
        self.loginfo(f"支付宝回调参数signature: {signature}")
        self.loginfo(f"支付宝回调参数form: {form}")
        sta, data = AlipayPayment().verify_callback(form)
        err_result = response.json({"response": {"code": '40004', "msg": 'Business Failed'}, "sign": signature})
        if not sta:
            return err_result
        order_no = data.get("out_trade_no")
        trade_no = data.get("trade_no")
        trade_status = data.get("trade_status")
        sta, msg, _ = await PaymentLogic().completed_order(order_no=order_no, trade_no=trade_no,
                                                           order_status=trade_status)
        if not sta:
            return err_result
        return response.json({"response": {"code": '10000', "msg": 'Success'}, "sign": signature})


class CallbackHf(SpecialApi):
    """汇付天下订单回调"""

    async def post(self, req: Request, **kwargs):
        form = req.get_form()
        self.loginfo(f"汇付天下回调参数: {form}")
        sta, data = await DouGongPay.dou_gong_notify(form)
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint="回调失败")
        order_no = data.get("order_no")
        trade_no = data.get("trade_no")
        trade_status = data.get("trade_status")
        sta, msg, _ = await PaymentLogic().completed_order(order_no=order_no, trade_no=trade_no,
                                                           order_status=trade_status)
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=msg)

        return response.json({"ErrCode": self.sta_code.PASS, "ErrMsg": "Success"})


class CallbackIos(GameAuthApi):
    """苹果订单校验"""

    async def post(self, req: Request, **kwargs):
        order_no = self.check_str(req.json.get("order_no"), require=True, p_name="订单号")
        receipt_data = self.check_str(req.json.get("receipt_data"), require=True, p_name="购买凭据")
        sta, data = await ios_service.process_payment(order_no, receipt_data)
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint="订单校验失败")
        order_no = data.get("order_no")
        trade_no = data.get("trade_no")
        trade_status = data.get("trade_status")
        sta, msg, _ = await PaymentLogic().completed_order(order_no=order_no, trade_no=trade_no,
                                                           order_status=trade_status)
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=msg)
        return self.answer()

class MiniProgramRecvPush(BaseSomePay):
    """
    微信小程序回调通知
    参考文档：https://developers.weixin.qq.com/miniprogram/dev/framework/server-ability/message-push.html#
    """
    decorators = []

    @classmethod
    def parse_session_from(cls, session_from):
        """
        解析session_from字符串为字典
        :param session_from: 形如 "key1=value1,key2=value2" 的字符串
        """
        params_dict = {}
        for item in session_from.split(','):
            if not item:  # 跳过空字符串项
                continue
            try:
                key, value = item.split('=', 1)
                params_dict[key] = int(value)  # 尝试将值转换为整数
            except ValueError as e:
                cls.log_info(f"无法解析项 '{item}' 到键值对: {e}")
                continue  # 跳过这个项，继续下一个
        return params_dict

    async def get(self, req: Request):
        """测试用"""
        self.wechat_check_signature(req, WeChatConf.WE_CHAT_MP_PUSH_TOKEN)
        _ = await self.wechat_decode_data(req, WeChatConf.WE_CHAT_MP_PUSH_TOKEN, WeChatConf.WE_CHAT_MP_AES_KEY,
                                          WeChatConf.WE_CHAT_MG_APP_ID)
        self.log_info("MiniProgramRecvPush 消息推送解密测试：", req.args)
        return response.text(body=req.args.get("echostr"))

    async def post(self, req: Request):
        """
        用户发给小程序的消息以及开发者需要的事件推送，都将被微信转发至该服务器地址中
        参考文档：https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Receiving_event_pushes.html
        """
        self.wechat_check_signature(req, WeChatConf.WE_CHAT_MP_PUSH_TOKEN)
        payload_data = await self.wechat_decode_data(req, WeChatConf.WE_CHAT_MP_PUSH_TOKEN,
                                                     WeChatConf.WE_CHAT_MP_AES_KEY, WeChatConf.WE_CHAT_MG_APP_ID)
        self.log_info("MiniProgramRecvPush 接收到微信消息推送回调", payload_data)
        session_from = payload_data.get("SessionFrom") or ""
        if not session_from:
            # session_from字段是个自用拓展字段，若是来自前端一定非空，则不处理即可，若为空则大可能来自客户聊天；
            # 目前重点处理支付，其他的客服人员处理
            return response.json({"ErrCode": 0, "ErrMsg": "Success"})
        from_user_name = payload_data.get("FromUserName")  # 发送方账号（一个OpenID）

        # 1.解析数据:客户端获取-传给微信-回调发送后端
        params_dict = self.parse_session_from(session_from)
        self.log_info("MiniProgramRecvPush SessionFrom:", params_dict)
        if params_dict is None:
            return response.json({"ErrCode": self.sta_code.ERR_ARG, "ErrMsg": '参数格式错误，不予回复！'})

        params_key = {"trade_item", "uid", "c_platform", "count"}
        if not params_key.issubset(params_dict.keys()):
            return response.json({"ErrCode": self.sta_code.ERR_ARG, "ErrMsg": '参数缺失，不予回复！'})

        # 2.创建订单
        uid = params_dict.get("uid")
        trade_item = params_dict.get("trade_item")
        platform = params_dict.get('c_platform') or ''
        count = req.json.get("count") or 1

        # order_info, hint = await OrderRC.create_order(uid, trade_item, PayMode.IOS_TO_H5, platform, req, count=count)
        order_info = {}
        if order_info:
            # 3.发送客服消息（支付界面相关信息）
            access_token = await self.wechat_get_access_token()
            errcode, req_data = await WeChat.wechat_send_custom_msg(uid, from_user_name, access_token, order_info)
            self.log_info(uid, "sendCustomMessage 发送客服消息：", req_data, errcode)
            if not errcode:
                return response.json({"ErrCode": 0, "ErrMsg": "Success"})
            return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": '发送客服消息失败'})
        return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": "订单创建失败"})


class MiniProgramRecvPush(SpecialApi):
    """
    微信小程序回调通知
    参考文档：https://developers.weixin.qq.com/miniprogram/dev/framework/server-ability/message-push.html#
    """

    @classmethod
    def parse_session_from(cls, session_from):
        """ 解析session_from字符串为字典: param session_from: 形如 "key1=value1,key2=value2" 的字符串 """
        if not session_from:
            return None
        params_dict = {}
        for item in session_from.split(','):
            if not item:  # 跳过空字符串项
                continue
            try:
                key, value = item.split('=', 1)
                params_dict[key] = value
            except ValueError as e:
                cls.log_info(f"无法解析项 '{item}' 到键值对: {e}")
                continue  # 跳过这个项，继续下一个
        return params_dict

    async def __handel_data(self, req: Request):
        payload_data = req.json
        signature = req.args.get("signature") or ""
        timestamp = req.args.get("timestamp")
        nonce = req.args.get("nonce")
        sta, msg = await WeChat.wechat_check_signature(signature, timestamp, nonce)
        if not sta:
            return False, response.json({"ErrCode": self.sta_code.ERR_AUTH, "ErrMsg": msg})
        return True, payload_data
    async def get(self, req: Request):
        """测试用"""
        await WeChat.wechat_get_access_token_stable()
        sta, payload_data = await self.__handel_data(req)
        if not sta:
            return payload_data

        session_from = payload_data.get("debug_str") or ""
        from_user_name = payload_data.get("FromUserName")
        params_dict = self.parse_session_from(session_from)
        uid = params_dict.get("uid")
        sku = params_dict.get("item_id")
        express = await GoodRC.get_good_info(str(sku))
        if not express:
            return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": '商品异常，请联系客服'})
        pay_info, msg = await PaymentLogic().create_order(uid, express, PayMode.HUI_FU_PAY, PlatForm.WECHAT_MP, purchase_uid=uid)
        self.log_info(uid, "微信小程序创建订单：", pay_info, msg)
        if not pay_info:
            return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": msg})
        # 3.发送客服消息（支付界面相关信息）
        errcode, req_data = await WeChat.wechat_send_custom_msg(uid, from_user_name, pay_info)
        self.log_info(uid, "微信小程序发送客服消息：", req_data, errcode)
        return response.text(body="Success")

    async def post(self, req: Request):
        """
        用户发给小程序的消息以及开发者需要的事件推送，都将被微信转发至该服务器地址中
        参考文档：https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Receiving_event_pushes.html
        """
        sta, payload_data = await self.__handel_data(req)
        if not sta:
            return payload_data
        event = payload_data.get('Event')
        session_from = payload_data.get("SessionFrom") or ""
        from_user_name = payload_data.get("FromUserName")  # 发送方账号（一个OpenID）
        if not session_from:
            # session_from字段是个自用拓展字段，若是来自前端一定非空，则不处理即可，若为空则大可能来自客户聊天；
            # 目前重点处理支付，其他的客服人员处理
            return response.json({"ErrCode": 0, "ErrMsg": "Success"})
        errcode = StaCode.FAIL
        if event == "user_enter_tempsession":
            # 客服会话
            # if mini_game: # 小游戏场景
            # 1.解析数据:客户端获取-传给微信-回调发送后端
            params_dict = self.parse_session_from(session_from)
            self.log_info("MiniProgramRecvPush SessionFrom:", params_dict)
            if params_dict is None:
                return response.json({"ErrCode": self.sta_code.ERR_ARG, "ErrMsg": '参数格式错误，不予回复！'})
            # 2.创建订单 不清楚这块参数是根据什么生成的，目前按老版本逻辑生成
            uid = params_dict.get("uid")
            sku = params_dict.get("item_id")
            platform = params_dict.get('platform') or PlatForm.WECHAT_MP
            express = await GoodRC.get_good_info(str(sku))
            if not express:
                return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": '商品异常，请联系客服'})
            pay_info, msg = await PaymentLogic().create_order(uid, express, PayMode.HUI_FU_PAY, platform, purchase_uid=uid)
            if not pay_info:
                return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": msg})
            # 3.发送客服消息（支付界面相关信息）
            errcode, req_data = await WeChat.wechat_send_custom_msg(uid, from_user_name, pay_info)
            self.log_info(uid, "sendCustomMessage 发送客服消息：", req_data, errcode)
        elif event == "minigame_deliver_goods":
            # 发放礼包场景
            pass
        else:
            # 其他客服人员处理
            pass
        if errcode:
            return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": '发送客服消息失败'})
        return response.json({"ErrCode": errcode, "ErrMsg": "Success"})


