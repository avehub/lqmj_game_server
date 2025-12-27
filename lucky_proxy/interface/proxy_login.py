# coding=utf-8
from nsanic.libs import tool_jwt

from common.public.conf import WeChatConf
from common.public.enum_const import StaCode, JWType
from lucky_game.const import PlatForm
from lucky_game.handler.ali_verification import AliVerification
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_proxy.base_api import BaseApi, ProxyAuthApi
from sanic import Request

from lucky_proxy.const import ProxyLoginType
from lucky_proxy.handler.wechat_mp import WeChatMpLogin
from lucky_proxy.model_db.main import ProxyUser

"""
发送验证码
"""


class ProxySendSmsCode(BaseApi):

    async def post(self, req: Request):
        login_data = req.json
        phone_number = login_data.get('phone_number')
        sta, e = await AliVerification.send_code(phone_number, "login")
        if sta is False:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


"""
登陆
"""


class ProxyLogin(BaseApi):

    async def post(self, req: Request):
        login_data = req.json
        code = login_data.get('code')
        proxy_login_type = login_data.get('proxy_login_type')
        if proxy_login_type == ProxyLoginType.WECHAT_MP_LOGIN:
            status, wechat_map_user_data = await WeChatMpLogin.wechat_gzh_login(code)
            if not status:
                self.log_info(f"代理端微信公众号授权登陆失败：{wechat_map_user_data}")
                # elf.answer(StaCode.EXTERNAL_ERR, {}, hint='登录出错,请重试!')
            if not wechat_map_user_data.get("unionid"):
                self.log_err("代理端微信公众号授权登陆失败，没有获取unionid")
                self.answer(StaCode.FAIL, hint="登陆失败")
            unionid = wechat_map_user_data.get("unionid")
            self.log_info(f"获取的unionid={unionid}")
            query_param = {"unionid": unionid}
            # TODO union 查询用户是否注册
        if proxy_login_type == ProxyLoginType.PHONE_LOGIN:
            phone_number = self.check_phone_number(req.json.get('phone_number'), require=True)
            scene = self.check_str(req.json.get('scene'), require=False, default="login", p_name="验证码场景")
            code = self.check_str(req.json.get('code'), require=True, p_name="验证码")
            sta, e = await AliVerification.verify_code(phone_number, code, scene)
            if sta is False:
                self.answer(StaCode.FAIL, hint=e)
            query_param = {"phone": phone_number}
        user: ProxyUser = await ProxyUser.get_by_dict(query_param, limit=1)

        if not user:
            self.answer(self.sta_code.FORBID, {}, hint='无权限登录!')
        extra = {
            "proxy_name": user.get("proxy_name"),
            "proxy_level": user.get("proxy_level"),
            "auth_status": user.get("auth_status"),
        }
        token = tool_jwt.jencode(user_id=user.get("id"), jw_type=JWType.AGENT, client_info="h5",
                                 extra=extra,
                                 useful_life=JWType.AGENT.desc)
        login_info = {
            "token": token,
            "id": user.get("id"),
            "proxy_name": user.get("proxy_name"),
            "proxy_level": user.get("proxy_level"),
            "auth_status": user.get("auth_status"),
        }
        self.answer(self.sta_code.PASS, login_info, hint='登陆成功!')


class ProxyRefreshToken(ProxyAuthApi):

    async def post(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        user: ProxyUser = await ProxyUser.get_by_pk(proxy_id)
        if not user:
            self.answer(self.sta_code.FORBID, {}, hint='禁止登陆!')
        extra = {
            "proxy_name": user.get("proxy_name"),
            "proxy_level": user.get("proxy_name"),
        }
        if not user:
            self.answer(self.sta_code.FORBID, {}, hint='无权限登录!')
        token = tool_jwt.jencode(user_id=user.get("id"), jw_type=JWType.AGENT, client_info="h5",
                                 extra=extra,
                                 useful_life=JWType.AGENT.desc)
        login_info = {
            "token": token,
            "proxy_name": user.get("proxy_name"),
            "proxy_level": user.get("proxy_level"),
        }
        self.answer(self.sta_code.PASS, login_info, hint='刷新成功成功!')
