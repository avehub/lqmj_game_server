from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from common.model_rc.user_good_exchange import UserGoodExchangeRC

class Exchange(AdminAuthApi):
    """ 更新/查询 兑换管理 """
    async def put(self, req: Request, **kwargs):
        exchange_id = self.check_int(req.json.get('exchange_id'), require=True, p_name='兑换ID')
        phone = self.check_phone_number(req.json.get('phone'), require=False)
        real_name = self.check_str(req.json.get('real_name'), require=False, p_name='玩家真实姓名')
        region = self.check_str(req.json.get('region'), require=False, p_name='地区/行政区域')
        address = self.check_str(req.json.get('address'), require=False, p_name='所在详细地址')
        check_status = self.check_int(req.json.get('check_status'), require=False, p_name='审核状态')
        express_id = self.check_str(req.json.get('express_id'), require=False, p_name='快递平台')
        express_no = self.check_str(req.json.get('express_no'), require=False, p_name='快递单号')
        status = self.check_int(req.json.get('status'), require=False, p_name='领取状态')
        up_data ={}
        if phone is not None:
            up_data["phone"] = phone
        if real_name is not None:
            up_data["real_name"] = real_name
        if region is not None:
            up_data["region"] = region
        if address is not None:
            up_data["address"] = address
        if check_status is not None:
            up_data["check_status"] = check_status
        if express_id is not None:
            up_data["express_id"] = express_id
        if express_no is not None:
            up_data["express_no"] = express_no
        if status is not None:
            up_data["status"] = status
        sta, msg = await UserGoodExchangeRC.up_exchange(exchange_id, up_data)
        if not sta:
            self.answer(self.sta_code.FAIL, hint='更新失败')
        self.answer()


    async def get(self, req: Request, **kwargs):
        uid = self.check_int(req.args.get('uid'), require=False, default=1, p_name='玩家ID')
        phone = self.check_phone_number(req.args.get('phone'), require=False)
        start_time = self.check_int(req.args.get('start_time'), require=False, p_name='开始时间')
        end_time = self.check_int(req.args.get('end_time'), require=False, p_name='结束时间')
        status = self.check_int(req.args.get('status'), require=False, p_name='领取状态')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        sta, data = await UserGoodExchangeRC.get_exchange_filter(uid=uid, phone=phone, status=status, page=page, page_size=page_size, start_time=start_time, end_time=end_time)
        self.answer(data=data)
