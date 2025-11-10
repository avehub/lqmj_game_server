"""
登录相关接口
"""
import jwt
from nsanic.libs import tool_jwt, tool_dt
from sanic import Request, response
from typing import List, Dict


from c_services.const.cs_enum_const import CmdWorkers
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.decorator import LimitTestCall, SysMaintain
from lucky_game.handler.douyin import DouYin
from lucky_game.handler.ios_pay import ios_service
from lucky_game.model_db.log import RecordsGameUserLogin
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.conf_json import ConfJsonRC
# from lucky_game.model_rc.vip_level import UserVipRC
from lucky_game.model_rc.server_addr import ServerAddrRC
from common.public.enum_const import JWType, LoginWay, DbKey, RegionEnum, StaCode
from common.utils.utils import UtilsTool
from nsanic.libs.tool import http_get, json_parse
from lucky_game.handler.wechat import WeChat
from lucky_game.handler.alipay import Alipay
from lucky_game.const import PlatForm, AliGrantType, EventTracking
from lucky_game.handler.ali_verification import AliVerification
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from common.public.conf import ASSET_SERVER_ADDR
import random

class BaseLogin(GameAuthApi):

    async def request_get_ip_geo(self, req, old_ip=None):
        """ 请求ip信息 """
        ip = self.ori_ip(req)
        if old_ip and ip == old_ip:
            return {}
        data = {}
        if not self.conf.DEBUG_MODE:
            ip_info = await UtilsTool.get_ip_geo(ip, self.log_info)  # 获取玩家地址相关
            if not ip_info:
                return data
            data["address"] = ip_info.get("city") or ""
            data["region"] = ip_info.get("region") or RegionEnum.Guizhou.phrase
            data["country"] = ip_info.get("country_id") or "CN"  # 国家域名
            data["isp"] = ip_info.get("isp") or ""
        return data

    async def update_user_login_info(self, req, u_info, login_info, wechat_info: dict = None):
        """ 更新玩家表登录数据 """
        updated = await self.request_get_ip_geo(req)
        updated['valid_key'] = self.rng.mk_str(16)
        if wechat_info:
            updated["unionid"] = wechat_info.get('unionid')
            updated["avatar"] = wechat_info.get('avatar')
            updated["name"] = wechat_info.get('name')
            updated["wechat"] = 1
        u_info = await BaseUserRC.update_info(u_info, updated)
        login_info.update({'uid': u_info.get('uid')})
        await RecordsGameUserLogin.split_add_one(login_info, db_key=DbKey.LOG)
        return u_info

    @classmethod
    async def get_login_info(cls, req, login_way: LoginWay, dev_ident=""):
        """ 获取登录信息：一般指当前登录的独有信息（可变） """
        ip = cls.ori_ip(req)
        login_info = {
            'login_way': login_way,
            'dev_id': dev_ident,
            'login_ip': ip,  # req.remote_addr or req.ip,
            'tst_mark': True if login_way == LoginWay.GUEST else False,
            'platform': req.args.get('platform') or req.json.get('platform') or req.headers.get('platform') or "",
            'dev_name': req.args.get('c_os') or req.json.get('c_os') or req.headers.get('c_os') or ""
        }
        return login_info

    def init_user_info(self, login_info, user_info: dict):
        """
        初始化玩家数据
        login_info: 登录信息
        user_info: 一般指从第三方获取到的用户信息，没有时则为空
        """
        safe_key = self.rng.mk_str(18)
        valid_key = self.rng.mk_str(16)
        dev_ident = login_info.get("dev_id")
        platform = user_info.get("platform")
        name = user_info.get("nickname") or user_info.get("nick_name") or ""
        avatar = user_info.get("avatar", f"avatar/avatar_{random.randint(1, 7)}.png")
        if name:
            name = UtilsTool.filter_emoji(name[:20])
        else:
            name = f"游客{self.rng.mk_str(4, True)}"

        unique = dev_ident
        if platform == PlatForm.NATIVE_APP:
            unique = dev_ident + user_info.get("apple_id", "")

        info = {
            'name': name,
            'safe_key': safe_key,
            'valid_key': valid_key,
            "ip": login_info.get("login_ip"),
            'address': login_info.get("address"),
            'region': login_info.get("region"),
            'country': login_info.get("country") or "CN",
            'tst_mark': login_info.get("tst_mark") or False,
            "dev_ident": dev_ident,
            "platform": platform,
            'wechat': user_info.get("wechat") or 0,
            "unionid": user_info.get("unionid", UtilsTool.get_hash_secrets('guest_unionid', unique)),
            "openid": user_info.get("openid", UtilsTool.get_hash_secrets('guest_openid', unique)),
            "avatar": avatar,
            "phone": user_info.get("phone", ""),
            "apple_id": user_info.get("apple_id", ""),
        }
        return info

    async def format_login_info(self, u_info: dict, server_info: list, jwt_type=JWType.USER, issued=True):
        uid = u_info.get("uid")
        if issued:  # 未签发走这里，签发jwt
            safe_key = u_info.pop('safe_key')
            subject_info = f"{u_info.get('created')}_{uid}"  # client_info
            self.conf.log.info("token 签发：", subject_info)
            token = tool_jwt.jencode(uid, jwt_type, safe_key, subject_info, jwt_type.desc)
            u_info.update({'token': token})

        # vip等级查询
        # vip_info = await UserVipRC.get_vip_conf_by_uid(uid)
        # u_info.update({"vip_level": vip_info.get("level")})

        data = {"user_info": u_info, "server_info": server_info}
        self.log_info("user login: ", uid, u_info.get("token"))

        await self.push_task2worker(CmdWorkers.GET_RED_DOT_LIST, uid=uid)
        await self.push_task2worker(CmdWorkers.LOGIN_SIGN_IN, uid=uid)
        return self.answer(data=data)

    async def create_new_user(
            self,
            req,
            unique_key: str,
            login_info: dict,
            req_user_info=None,
            cache_key="",
            platform=None
    ):
        ip_info = await self.request_get_ip_geo(req)
        login_info.update(ip_info)

        req_user_info = req_user_info or {}
        req_user_info["platform"] = platform
        u_dict = self.init_user_info(login_info, req_user_info)

        # 新用户登录赠送金币
        gift_conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_NEW_USER_GIFT)
        asset_gift = {'gold': gift_conf.get("gold"), 'diamond': gift_conf.get("diamond")}
        if platform == PlatForm.WECHAT_MINI_GAME:
            asset_gift["yellow_diamond"] = gift_conf.get("yellow_diamond")
        else:
            asset_gift["room_card"] = gift_conf.get("room_card")
        u_dict.update(asset_gift)

        # 写入新用户信息
        self.log_info('init user:', u_dict)
        await BaseUserRC.db_model.add_one(u_dict)
        cache_key = cache_key or unique_key
        # 返回新用户信息
        u_info = await BaseUserRC.cache_by_unique({unique_key: u_dict.get(unique_key), "platform": platform}, cache_key)
        if not u_info:
            return

        uid = u_info.get('uid')
        # 写入登陆记录和注册事件
        login_info.update({'uid': uid})
        await RecordsGameUserLogin.split_add_one(login_info, db_key=DbKey.LOG)
        await self.push_task2worker(
            CmdWorkers.USER_EVENT_TRACKING, uid=uid, msg={'event_tracking': EventTracking.AFTER_REGISTER.val})
        # 赠送金币记录入库
        await ExtraUserResourceChangesRC.bulk_register_change_record(uid, asset_gift)
        await self.push_task2worker(CmdWorkers.FETCH_ACTIVE_MAILS, uid=uid)
        u_info["new_user"] = True
        return u_info

    async def whether_through(self) -> List[Dict]:
        """ 是否通过 """
        server_info: List[Dict] = await ServerAddrRC.cache_all()
        if not server_info or not server_info[0].get("status"):
            self.answer(hint="As server maintenance, please visit later, thank you.")
        return server_info


class LoginByGuest(BaseLogin):
    """ 游客登陆 """
    decorators = [LimitTestCall]

    async def post(self, req: Request):
        server_info = await self.whether_through()
        platform = self.check_int(req.args.get('platform'), require=True, p_name="平台ID")
        dev_ident = req.json and req.json.get('device_id') or req.headers.get('device_id')
        self.check_str(dev_ident, require=True, minlen=3, maxlen=18, p_name="device_id")
        # platform = PlatForm.WEBPAGE
        q_params = {
            "dev_ident": dev_ident,
            "platform": platform,
        }
        u_info = await BaseUserRC.cache_by_unique(q_params, BaseUserRC.KEY_DEVICE_ID)
        login_info = await self.get_login_info(req, LoginWay.GUEST, dev_ident=dev_ident)
        if not u_info:
            u_info = await self.create_new_user(req, 'dev_ident', login_info, u_info, BaseUserRC.KEY_DEVICE_ID, platform)
        else:
            u_info = await self.update_user_login_info(req, u_info, login_info)

        (not u_info) and self.answer(StaCode.NO_PLAYER_INFO, hint='Failed to login')
        self.log_info('LoginByGuest suc:', u_info.get("uid"))
        return await self.format_login_info(u_info, server_info, JWType.USER)



class LoginByWechat(BaseLogin):
    """ 微信登陆（公众号、小程序、微信APP） """
    decorators = []

    async def post(self, req: Request):
        """ 通过code登录 """
        # 获取客户端code
        server_info = await self.whether_through()
        code = req.json.get('code')
        platform = self.check_int(req.args.get('platform'), require=True, p_name="平台")
        dev_ident = req.json.get('device_id') or req.headers.get('device_id')
        (not code or not dev_ident) and self.answer(StaCode.ERR_ARG, hint='Failed to login')

        errcode, req_data = await WeChat.wechat_login(code, platform)
        self.log_info('Wechat wechat_app_login result:', errcode, req_data)
        if errcode > 0:
            data = {"errcode": errcode, "errmsg": req_data}
            self.answer(StaCode.EXTERNAL_ERR, data, hint=req_data)

        # 通过open_id查询数据库用户信息
        openid = req_data.get('openid')
        q_params = {
            "openid": openid,
            "platform": platform
        }
        unique_key = BaseUserRC.KEY_OPENID
        h5_app = [PlatForm.WECHAT_MP, PlatForm.NATIVE_APP]
        if platform == PlatForm.WECHAT_MP or platform == PlatForm.NATIVE_APP:
            # 微信公众号、微信APP为同一账号
            req_sta, req_data = await WeChat.wechat_userinfo(req_data.get('access_token'), openid)
            if not req_sta:
                self.answer(StaCode.EXTERNAL_ERR, hint=req_data)
            q_params = {
                "unionid": req_data.get('unionid'),
                "platform__in": h5_app,
            }
            unique_key = BaseUserRC.KEY_UNION_ID
        u_info = await BaseUserRC.cache_by_unique(q_params, unique_key)
        maintain, msg = await SysMaintain.sys_verify(req, u_info=u_info)
        if not maintain:
            return self.answer(StaCode.FAIL, hint=msg)
        login_info = await self.get_login_info(req, LoginWay.WECHAT)

        # 新用户 注册
        if not u_info:
            req_data["avatar"] = req_data.get('headimgurl') if platform in h5_app else f"avatar/avatar_{random.randint(1, 7)}.png"
            req_data["wechat"] = 1
            req_data["unionid"] = req_data.get('unionid')
            u_info = await self.create_new_user(
                req, 'openid', login_info, req_data, BaseUserRC.KEY_OPENID, platform=platform)
            self.log_info('Wechat Reg u_info:', u_info)
        # 老用户 登录
        else:
            wechat_info = {
                "unionid": req_data.get('unionid'),
                "name": req_data.get('nickname'),
            }
            if platform in h5_app:
                wechat_info["avatar"] = req_data.get('headimgurl')
            u_info = await self.update_user_login_info(req, u_info, login_info, wechat_info)
            self.log_info('Wechat Login u_info:', u_info)

        (not u_info) and self.answer(StaCode.NO_PLAYER_INFO)
        if platform == PlatForm.WECHAT_MINI_GAME:
            session_key = req_data.get("session_key")
            await BaseUserRC.cache_session_key(u_info.get('uid'), session_key)
        else:
            await BaseUserRC.cache_wechat_access_token_info(u_info.get('uid'), req_data)
        self.log_info('LoginByWechat suc:', u_info.get("uid"))
        return await self.format_login_info(u_info, server_info, JWType.USER)



class LoginByToken(BaseLogin):
    """ 通过token登录 """
    async def post(self, req: Request, **kwargs):
        server_info = await self.whether_through()
        u_info = kwargs.get("u_info")
        login_info = await self.get_login_info(req, LoginWay.TOKEN)
        u_info = await self.update_user_login_info(req, u_info, login_info)
        (not u_info) and self.answer(StaCode.NO_PLAYER_INFO)
        maintain, msg = await SysMaintain.sys_verify(req, u_info=u_info)
        if not maintain:
            return self.answer(StaCode.FAIL, hint=msg)
        jwt_info = kwargs.get("jwt_info")
        issued = False
        if jwt_info.get('exp') - tool_dt.cur_time() <= 43200:
            # 有效期小于12小时则重新签发 60 * 60 * 12
            issued = True
        else:
            # 这里不签发新的
            u_info.update({'token': req.headers.get("Authorization")})

        self.log_info('LoginByToken suc:', u_info.get("uid"), issued)
        return await self.format_login_info(u_info, server_info, issued=issued)


class SendCode(BaseLogin):
    """ 发送验证码 """
    decorators = []
    async def post(self, req: Request):
        # 获取客户手机号
        phone_number = self.check_phone_number(req.json.get('phone_number'), require=True)
        scene = self.check_str(req.json.get('scene'), require=False, default="login", p_name="验证码场景")
        sta, e = await AliVerification.send_code(phone_number, scene)
        if sta is False:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class LoginByPhone(BaseLogin):
    """ 通过手机号登录 """
    decorators = []
    async def post(self, req: Request):
        phone_number = self.check_phone_number(req.json.get('phone_number'), require=True)
        scene = self.check_str(req.json.get('scene'), require=False, default="login", p_name="验证码场景")
        platform = self.check_int(req.args.get('platform'), require=True, p_name="平台")
        code = self.check_str(req.json.get('code'), require=True, p_name="验证码")
        dev_ident = req.json and req.json.get('device_id') or req.headers.get('device_id')
        device_id = self.check_str(dev_ident, require=True, minlen=3, maxlen=18, p_name="device_id")
        sta, e = await AliVerification.verify_code(phone_number, code, scene)
        if sta is False:
            return self.answer(StaCode.FAIL, hint=e)
        # 通过手机号查询数据库用户信息
        user_data = {
            "phone": phone_number
        }
        u_info = await BaseUserRC.cache_by_unique(user_data, BaseUserRC.KEY_PHONE_CACHE)
        maintain, msg = await SysMaintain.sys_verify(req, u_info=u_info)
        if not maintain:
            return self.answer(StaCode.FAIL, hint=msg)
        login_info = await self.get_login_info(req, LoginWay.PHONE)
        if not u_info:
            # 手机号注册
            req_user = await BaseUserRC.get_default_user_info("phone", phone=phone_number, device_id=device_id, platform=platform)
            u_info = await self.create_new_user(
                req, 'phone', login_info, req_user, cache_key=BaseUserRC.KEY_PHONE_CACHE, platform=platform)
            self.log_info('phone number Reg u_info:', u_info)
        else:
            u_info = await self.update_user_login_info(req, u_info, login_info)
            self.log_info('DouYinMG Login u_info:', u_info)

        (not u_info) and self.answer(StaCode.NO_PLAYER_INFO)
        server_info = await self.whether_through()
        self.log_info('LoginByPhone suc:', u_info.get("uid"))
        return await self.format_login_info(u_info, server_info, JWType.USER)


class LoginByApple(BaseLogin):
    """Apple 登录"""
    decorators = []

    async def post(self, req: Request):
        # 1. 获取请求参数
        name = self.check_str(req.json.get('name'), require=False,  p_name="昵称")
        email = self.check_str(req.json.get('email'), require=False,  p_name="邮箱")
        platform = self.check_int(req.args.get('platform'), require=True, p_name="平台")
        device_id = self.check_str(req.json.get('device_id'), require=True, maxlen=18, p_name="设备ID")
        apple_id = self.check_str(req.json.get('apple_id'), require=True, p_name="苹果用户ID")
        if not apple_id:
            return self.answer(StaCode.ERR_ARG, hint="缺少必要参数")
        u_info = await BaseUserRC.cache_by_unique({'apple_id': apple_id, "platform": platform}, BaseUserRC.KEY_APPLE_ID)
        maintain, msg = await SysMaintain.sys_verify(req, u_info=u_info)
        if not maintain:
            return self.answer(StaCode.FAIL, hint=msg)
        # 2. 获取服务器信息
        server_info = await self.whether_through()

        # 3. 使用 code 获取 token 和用户信息
        # success, user_info = await ios_service.get_apple_user_info(code)
        # if not success:
        #     return self.answer(StaCode.TOKEN_INVALID, hint=user_info)

        # 查询用户是否已存在
        # u_info = await BaseUserRC.get_user_by_apple(apple_id)
        login_info = await self.get_login_info(req, LoginWay.APPLE, device_id)

        # 5. 新用户注册或老用户登录
        if not u_info:
            # 新用户注册
            nickname = f"Ios{apple_id[:3]}" if not name else name  # 默认昵称

            # 创建用户
            u_info = await self.create_new_user(
                req,
                'apple_id',
                login_info,
                {
                    'apple_id': apple_id,
                    "device_id": device_id,
                    'email': email,
                    'nickname': nickname,
                },
                'apple_id',
                platform=PlatForm.NATIVE_APP
            )
            self.log_info('Apple Reg u_info:', u_info)
        else:
            # 老用户登录
            u_info = await self.update_user_login_info(req, u_info, login_info)
            self.log_info('Apple Login u_info:', u_info)

        if not u_info:
            return self.answer(StaCode.FAIL, hint="用户登录失败")

        self.log_info('LoginByApple success:', u_info.get("uid"))
        return await self.format_login_info(u_info, server_info, JWType.USER)

class BindByWechat(BaseLogin):
    """ 绑定微信 """
    async def post(self, req: Request, **kwargs):
        code = self.check_str(req.json.get('code'), require=True, p_name="微信code")
        platform = self.check_int(req.args.get('platform'), require=True, p_name="平台")
        user = kwargs.get("u_info")
        if not user or user.get("wechat"):
            return self.answer(StaCode.NO_PLAYER_INFO)
        if user.get("wechat"):
            return self.answer(StaCode.FAIL, hint="微信已绑定")
        errcode, req_data = await WeChat.wechat_login(code, platform)
        self.log_info('Wechat wechat_app_login result:', errcode, req_data)
        if errcode > 0:
            data = {"errcode": errcode, "errmsg": req_data}
            self.answer(StaCode.EXTERNAL_ERR, data, hint=req_data)
        req_sta, data = await WeChat.wechat_userinfo(req_data.get('access_token'), req_data.get('openid'))
        if not req_sta:
            self.answer(StaCode.EXTERNAL_ERR, data=data)
        unionid = data.get('unionid')
        q_params = {
            "unionid": unionid,
        }
        u_info = await BaseUserRC.cache_by_unique(q_params, BaseUserRC.KEY_UNION_ID)
        if u_info:
            return self.answer(StaCode.FAIL, hint="微信已绑定其他账号，请直接使用微信登录")
        updated = {
            'valid_key': self.rng.mk_str(16),
            'ip': self.ori_ip(req),
            'openid': data.get('openid'),
            'unionid': unionid,
            'wechat': 1,
            'name': data.get('nickname'),
        }
        if data.get('nickname'):
            updated['name'] = data.get('nickname')
            updated['sex'] = data.get('sex') or 0
        if data.get('headimgurl'):
            updated['avatar'] = data.get('headimgurl')
        u_info = await BaseUserRC.update_info(user, updated)
        (not u_info) and self.answer(StaCode.FAIL, hint="绑定失败")
        return self.answer()





