from nsanic.libs import tool_dt
from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.logic.recharge_juhe import RechargeJuhe
from lucky_game.model_rc.base_store import GoodRC
from lucky_game.model_db.main import RecordsAdminOperates
from common.model_rc.user_good_exchange import UserGoodExchangeRC


class AdminExchangeList(AdminAuthApi):
    async def get(self, req: Request, **kwargs):
        phone = self.check_phone_number(req.args.get("phone"), require=False)
        status = self.check_int(req.args.get("status"), require=False, p_name="状态")
        check_status = self.check_int(req.args.get("check_status"), require=False, p_name="审核状态")
        page = self.check_int(req.args.get("page"), require=False, default=1, p_name="页码")
        page_size = self.check_int(req.args.get("page_size"), require=False, default=20, p_name="每页数量")
        sta, data = await UserGoodExchangeRC.get_exchange_filter(phone=phone, status=status, check_status=check_status, page=page, page_size=page_size)
        if not sta:
            self.answer(self.sta_code.FAIL, hint="查询失败")
        self.answer(data=data)


class ExchangeRecharge(AdminAuthApi):
    async def post(self, req: Request, **kwargs):
        exchange_id = self.check_int(req.json.get("exchange_id"), require=True, p_name="兑换ID")
        approve = self.check_int(req.json.get("approve"), require=True, p_name="审核通过标记")
        phone = self.check_phone_number(req.json.get("phone"), require=True)
        amount = self.check_int(req.json.get("amount"), require=True, p_name="面值")
        mask_phone = f"{phone[:3]}****{phone[-4:]}"
        self.log_info(f"后台审核充值接收参数 exchange_id={exchange_id}, 审核标记={approve}, 手机={phone}, 面值={amount}")
        record = await UserGoodExchangeRC.db_model.get_by_pk(exchange_id)
        if not record:
            self.answer(self.sta_code.FAIL, hint="兑换记录不存在")
        if approve != 1:
            await RecordsAdminOperates.insert_one(admin.get("username", ""), req.path, "ExchangeReject", req.method, req.json, self.sta_code.PASS, "ok")
            self.log_info(f"兑换审核拒绝 exchange_id={exchange_id}")
            self.answer()
        use_phone = phone or record.phone
        mask_use_phone = f"{use_phone[:3]}****{use_phone[-4:]}" if use_phone else None
        face_value = int(amount)
        if face_value <= 0:
            self.answer(self.sta_code.FAIL, hint="面值缺失")
        order_id = f"ex_{exchange_id}"
        self.log_info(f"准备发起话费充值 exchange_id={exchange_id}, 订单号={order_id}, 手机={mask_use_phone}, 面值={face_value}")
        sta, msg, result = await RechargeJuhe.recharge(use_phone, face_value, order_id)
        admin = kwargs.get("u_info") or {}
        await RecordsAdminOperates.insert_one(admin.get("username", ""), req.path, "ExchangeRecharge", req.method, req.json, self.sta_code.PASS if sta else self.sta_code.FAIL, msg or "")
        if not sta:
            self.log_info(f"话费充值失败 exchange_id={exchange_id}, 原因={msg}")
            self.answer(self.sta_code.FAIL, hint=f"充值失败:{msg}")
        third_order_id = result.get("orderid") or order_id
        await UserGoodExchangeRC.db_model.filter(id=exchange_id).update(status=1, express_no=third_order_id, updated=tool_dt.cur_time())
        self.log_info(f"话费充值成功 exchange_id={exchange_id}, 第三方订单号={third_order_id}")
        self.answer()


class ExchangeQuery(AdminAuthApi):
    async def get(self, req: Request, **kwargs):
        exchange_id = self.check_int(req.args.get("exchange_id"), require=False, p_name="兑换ID")
        orderid = self.check_str(req.args.get("orderid"), require=False, p_name="订单号")
        if not orderid and not exchange_id:
            self.answer(self.sta_code.ERR_ARG, hint="缺少订单号或兑换ID")
        if not orderid and exchange_id:
            record = await UserGoodExchangeRC.db_model.get_by_pk(exchange_id)
            if not record:
                self.answer(self.sta_code.FAIL, hint="兑换记录不存在")
            orderid = record.express_no or f"ex_{exchange_id}"
        self.log_info(f"查询话费充值状态 exchange_id={exchange_id}, 订单号={orderid}")
        sta, msg, result = await RechargeJuhe.query_status(orderid)
        admin = kwargs.get("u_info") or {}
        await RecordsAdminOperates.insert_one(admin.get("username", ""), req.path, "ExchangeQueryStatus", req.method, req.args, self.sta_code.PASS if sta else self.sta_code.FAIL, msg or "")
        if not sta:
            self.answer(self.sta_code.FAIL, hint=f"查询失败:{msg}")
        game_state = result.get("game_state")
        status_text = "已提交充值，请耐心等待"
        new_status = None
        if game_state == "1":
            status_text = "充值成功"
            new_status = 99
        elif game_state == "9":
            status_text = "充值失败"
            new_status = 1
        if new_status is not None and exchange_id:
            await UserGoodExchangeRC.db_model.filter(id=exchange_id).update(status=new_status, updated=tool_dt.cur_time())
            self.log_info(f"更新兑换状态 exchange_id={exchange_id}, 新状态={new_status}")
        self.answer(self.sta_code.PASS, {"status": new_status or 1, "game_state": game_state}, hint=status_text)
