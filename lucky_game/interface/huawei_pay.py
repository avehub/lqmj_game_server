from sanic import Request
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.huawei import HuaweiPay
from lucky_game.model_rc.order import OrderRC
from lucky_game.const import OrderStatus
from lucky_game.logic.payment import PaymentLogic


class HuaweiPayVerify(GameAuthApi):
    async def post(self, req: Request, **kwargs):
        order_no = self.check_str(req.json.get("order_no"), require=True, p_name="order_no")
        purchase_token = self.check_str(req.json.get("purchase_token"), require=True, p_name="purchase_token")
        product_id = self.check_str(req.json.get("product_id"), require=False, p_name="product_id")
        mask_token = f"{purchase_token[:10]}****" if isinstance(purchase_token, str) else ""
        self.log_info(f"华为支付校验请求 order_no={order_no}, product_id={product_id}, token前缀={mask_token}")
        sta, msg, result = await HuaweiPay.verify(order_no, purchase_token, product_id)
        self.log_info(f"华为支付校验结果 状态={sta}, 原因={msg}, 返回={result}")
        if not sta:
            self.answer(self.sta_code.FAIL, hint=msg)
        q_sta, q_msg, q_res = await HuaweiPay.query_order_status(result.get("order_no") or order_no, product_id, purchase_token)
        self.log_info(f"鸿蒙订单状态查询 结果={q_sta}, 原因={q_msg}, 返回={q_res}")
        if not q_sta:
            self.answer(self.sta_code.FAIL, hint=q_msg)
        c_sta, c_msg, _ = await PaymentLogic().completed_order(order_no=order_no, trade_no=result.get("order_no") or order_no, order_status=OrderStatus.PAID)
        self.log_info(f"订单完成处理 订单号={order_no}, 结果={c_sta}, 信息={c_msg}")
        s_sta, s_msg, s_res = await HuaweiPay.confirm_shipped(order_no, purchase_token)
        self.log_info(f"确认发货 结果={s_sta}, 信息={s_msg}, 返回={s_res}")
        self.answer(self.sta_code.PASS, {"order_no": order_no, "product_id": product_id, "order_state": q_res.get("state")}, hint="华为支付校验成功")
