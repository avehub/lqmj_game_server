from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_proxy.game_adapter.game_data_adapter import GameDataAdapter
from lucky_proxy.logic.game_data_sync import Level1ProxyDTO
from lucky_proxy.logic.proxy_user import ProxyUserLogic


class ProxyUser(AdminAuthApi):
    """ 代理用户相关接口 """

    async def post(self, req: Request, **kwargs):
        """
        添加代理
        """
        uid = self.check_int(req.json.get('uid'), require=True, p_name='用户ID')
        phone = self.check_phone_number(req.json.get('phone'), require=True)
        name = self.check_str(req.json.get('name'), require=False, p_name='代理名称')
        avatar = self.check_str(req.json.get('avatar'), require=False, p_name='代理头像')
        u_info = await BaseUserRC.cache_by_pk(uid)
        add_data = Level1ProxyDTO(player_id=uid, unionid=u_info["unionid"], phone=phone, name=name, avatar=avatar)
        sta, msg = await GameDataAdapter.add_level1_proxy(add_data)
        if not sta:
            self.answer(self.sta_code.FAIL, hint=msg)
        self.answer()


    async def put(self, req: Request, **kwargs):
        """
        更新代理
        """
        player_id = self.check_int(req.json.get('uid'), require=True, p_name='用户ID')
        promotion_code = self.check_str(req.json.get('promotion_code'), require=False, p_name='推广码')
        phone = self.check_phone_number(req.json.get('phone'), require=False)
        is_deleted = self.check_int(req.json.get('is_deleted'), require=False, p_name='删除')
        status = self.check_int(req.json.get('status'), require=False, p_name='状态')
        sta, msg = await ProxyUserLogic.update_proxy_user(player_id, {"phone": phone, "promotion_code": promotion_code, "is_deleted": is_deleted, "status": status})
        if not sta:
            self.answer(self.sta_code.FAIL, hint=msg)
        self.answer()

    async def get(self, req: Request, **kwargs):
        """
        获取代理列表
        """
        uid = self.check_int(req.args.get('uid'), require=False, p_name='用户ID')
        proxy_level = self.check_int(req.args.get('proxy_level'), require=False, p_name='代理等级')
        phone = self.check_phone_number(req.args.get('phone'), require=False)
        promotion_code = self.check_str(req.args.get('promotion_code'), require=False, p_name='推广码')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='分页')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        result = await ProxyUserLogic.get_proxy_user_filter(player_id=uid, proxy_level=proxy_level, phone=phone, promotion_code=promotion_code, page=page, page_size=page_size)
        self.answer(data=result)


