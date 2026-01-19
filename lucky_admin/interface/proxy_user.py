from nsanic.libs import tool_dt
from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_proxy.game_adapter.game_data_adapter import GameDataAdapter
from lucky_proxy.logic.game_data_sync import Level1ProxyDTO, UpgradeProxyDTO, PromotionAddUserDTO
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
        vip_level = self.check_int(req.json.get('vip_level'), require=True, p_name='VIP等级')
        vip_expire_time = self.check_int(req.json.get('vip_expire_time'), require=True, p_name='VIP过期时间')
        u_info = await BaseUserRC.cache_by_pk(uid)
        if not u_info:
            self.answer(self.sta_code.FAIL, hint="用户不存在")
        existed_list = await ProxyUserLogic.get_proxy_user_filter(phone=phone)
        if isinstance(existed_list, list) and existed_list:
            self.answer(self.sta_code.FAIL, hint="手机号已存在")
        add_data = Level1ProxyDTO(player_id=uid, unionid=u_info["unionid"], phone=phone, name=name, avatar=avatar, vip_level=vip_level, vip_expire_time=vip_expire_time)
        sta, msg = await GameDataAdapter.add_level1_proxy(add_data)
        if not sta:
            self.answer(self.sta_code.FAIL, hint=msg)
        conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_PROXY_VIP_DISCOUNT)
        discount = conf.get("discount")
        if u_info["discount"] != conf.get("discount"):
            await BaseUserRC.update_info(u_info, {"discount": discount})
        self.answer()


    async def put(self, req: Request, **kwargs):
        """
        更新代理
        """
        player_id = self.check_int(req.json.get('uid'), require=True, p_name='用户ID')
        promotion_code = self.check_str(req.json.get('promotion_code'), require=False, maxlen=10, p_name='推广码')
        phone = self.check_phone_number(req.json.get('phone'), require=False)
        is_deleted = self.check_int(req.json.get('is_deleted'), require=False, p_name='删除')
        status = self.check_int(req.json.get('status'), require=False, p_name='状态')
        vip_level = self.check_int(req.json.get('vip_level'), require=False, p_name='VIP等级')
        vip_expire_time = self.check_int(req.json.get('vip_expire_time'), require=False, p_name='VIP过期时间')
        if phone:
            dup_list = await ProxyUserLogic.get_proxy_user_filter(phone=phone)
            if isinstance(dup_list, list):
                for one in dup_list:
                    if one.get("id") != player_id:
                        self.answer(self.sta_code.FAIL, hint="手机号已存在")
        up_data = {
            "promotion_code": promotion_code,
            "phone": phone,
            "is_deleted": is_deleted,
            "status": status,
            "vip_level": vip_level,
            "vip_expire_time": vip_expire_time,
        }
        sta, msg = await ProxyUserLogic.update_proxy_user(player_id, up_data)
        if not sta:
            self.answer(self.sta_code.FAIL, hint=msg)
        # 检查用户折扣
        if status is not None:
            u_info = await BaseUserRC.cache_by_pk(player_id)
            if not u_info:
                self.answer(self.sta_code.FAIL, hint="用户不存在")
            conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_PROXY_VIP_DISCOUNT)
            discount = 1
            if status == 1:
                discount = conf.get("discount")
            if u_info["discount"] != conf.get("discount"):
                await BaseUserRC.update_info(u_info, {"discount": discount})
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


class ProxyUserLevel(AdminAuthApi):
    """ 代理用户等级相关接口 """
    async def put(self, req: Request, **kwargs):
        """
        更新代理等级
        """
        uid = self.check_int(req.json.get('uid'), require=True, p_name='用户ID')
        u_info = await BaseUserRC.cache_by_pk(uid)
        if not u_info:
            self.answer(self.sta_code.FAIL, hint="用户不存在")
        up_data = UpgradeProxyDTO(player_id=uid, opt_user_id=1)
        sta, msg = await GameDataAdapter.upgrade_level1_proxy(up_data)
        if not sta:
            self.answer(self.sta_code.FAIL, hint=msg)
        self.answer()

class ProxyUserBind(AdminAuthApi):
    """ 代理用户绑定接口 """

    async def post(self, req: Request, **kwargs):
        """
        代理用户绑定接口
        """
        uid = self.check_int(req.json.get('uid'), require=True, p_name='用户ID')
        invite_code = self.check_str(req.json.get('invite_code'), require=True, p_name='邀请码')
        u_info = await BaseUserRC.cache_by_pk(uid)
        if not u_info:
            self.answer(self.sta_code.FAIL, hint="用户不存在")
        invite_data = PromotionAddUserDTO(player_id=uid, promotion_code=invite_code,
                                          promotion_time=tool_dt.cur_time(), promotion_type=0)
        sta = await GameDataAdapter.sync_promotion_user(invite_data)
        self.log_info(f"用户{uid}绑定邀请关系返回{sta}")
        if not sta:
            self.log_err(f"用户{uid}绑定邀请关系{invite_code}失败")
            self.answer(self.sta_code.FAIL, hint="调用绑定接口失败")
        self.answer()
