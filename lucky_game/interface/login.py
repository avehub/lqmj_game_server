"""
登录相关接口
"""
from nsanic.libs import tool_jwt, tool_dt
from sanic import Request
from typing import List, Dict
from c_services.const.cs_enum_const import CmdWorkers
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.decorator import LimitTestCall
from lucky_game.handler.douyin import DouYin
from lucky_game.model_db.log import RecordsGameUserLogin
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.vip_level import UserVipRC
from lucky_game.model_rc.server_addr import ServerAddrRC
from common.public.enum_const import JWType, LoginWay, DbKey, RegionEnum
from common.utils.utils import UtilsTool
from nsanic.libs.tool import http_get, json_parse
from lucky_game.handler.wechat import WeChat
from lucky_game.handler.alipay import Alipay
from lucky_game.const import PlatForm, AliGrantType, EventTracking


class BaseLogin(GameAuthApi):

    async def request_get_ip_geo(self, req, old_ip=None):
        """ 请求ip信息 """
        ip = self.ori_ip(req)
        if old_ip and ip == old_ip:
            return {}
        data = {}
        if not self.conf.DEBUG_MODE:
            ip_info = await UtilsTool.get_ip_geo(ip, self.info_log)  # 获取玩家地址相关
            if not ip_info:
                return data
            data["address"] = ip_info.get("city") or ""
            data["region"] = ip_info.get("region") or RegionEnum.Guizhou.phrase
            data["country"] = ip_info.get("country_id") or "CN"  # 国家域名
            data["isp"] = ip_info.get("isp") or ""
        return data

    async def update_user_login_info(self, req, u_info, login_info):
        """ 更新玩家表登录数据 """
        updated = {'valid_key': self.rng.mk_str(16), 'ip': self.ori_ip(req)}
        # ip_info = await self.request_get_ip_geo(req, u_info.get("ip"))  # 2024/11/19仅在玩家第一次登录游戏获取
        # updated.update(ip_info)
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
            'platform': req.args.get('c_platform') or req.json.get('c_platform') or req.headers.get('c_platform') or "",
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

        name = user_info.get("nickname") or user_info.get("nick_name") or ""
        if name:
            name = UtilsTool.filter_emoji(name[:20])
        else:
            name = f"游客{self.conf.rng.mk_str(8, True)}"

        info = {
            'name': name,
            'safe_key': safe_key,
            'valid_key': valid_key,

            "ip": login_info.get("login_ip"),
            'address': login_info.get("address"),
            'region': login_info.get("region"),
            'country': login_info.get("country") or "CN",
            'tst_mark': login_info.get("tst_mark") or False,
            "dev_ident": login_info.get("dev_id"),

            "platform": user_info.get("platform") or PlatForm.DEFAULT,
            "unionid": user_info.get("unionid"),
            "openid": user_info.get("openid")
        }
        return info

    async def format_login_info(self, u_info: dict, server_info: list, jwt_type=JWType.USER, issued=True):
        uid = u_info.get("uid")
        # -- snip --
        # todo: 临时代码(上线去掉)
        # if LIVE_SERVER:
        #     if tool_dt.cur_time() < ONLINE_TIME:
        #         flag = await self.rds.conn.sismember('white_list', uid)
        #         if not flag:
        #             hint = f"游戏将于{ONLINE_TIME_STR}开启\n请玩家耐心等待……({uid})"
        #             self.answer(code=self.sta_code.FAIL, hint=hint)
        #     else:
        #         await self.rds.drop_item('white_list')
        # -- snip --

        if issued:  # 未签发走这里，签发jwt
            safe_key = u_info.pop('safe_key')
            subject_info = f"{u_info.get('created')}_{uid}"  # client_info
            self.conf.log.info("token 签发：", subject_info)
            token = tool_jwt.jencode(uid, jwt_type, safe_key, subject_info, jwt_type.desc)
            u_info.update({'token': token})

        # vip等级查询
        vip_info = await UserVipRC.get_vip_conf_by_uid(uid)
        u_info.update({"vip_level": vip_info.get("level")})

        data = {"user_info": u_info, "server_info": server_info}
        self.info_log("user login: ", uid, u_info.get("token"))

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
        req_user_info["platform"] = platform or PlatForm.DEFAULT
        u_dict = self.init_user_info(login_info, req_user_info)

        # 新用户登录赠送灵石
        gift_conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_NEW_USER_GIFT)
        asset_gift = {'gold': gift_conf.get("gold"), 'diamond': gift_conf.get("diamond")}
        u_dict.update(asset_gift)

        # 写入新用户信息
        self.info_log('init user:', u_dict)
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
        dev_ident = req.json and req.json.get('device_id') or req.headers.get('device_id')
        self.check_str(dev_ident, require=True, minlen=3, maxlen=18, p_name="device_id")
        platform = PlatForm.TEST
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

        (not u_info) and self.answer(self.sta_code.NO_PLAYER_INFO, hint='Failed to login')
        self.info_log('LoginByGuest suc:', u_info.get("uid"))
        return await self.format_login_info(u_info, server_info, JWType.USER)


class LoginByWechatMiniProgram(BaseLogin):
    """ 微信MG登陆 """
    decorators = []

    async def post(self, req: Request):
        """ 通过code登录 """
        # 获取客户端code
        server_info = await self.whether_through()
        code = req.json.get('code')
        (not code) and self.answer(self.sta_code.ERR_ARG, hint='Failed to login')

        errcode, req_data = await WeChat.wechat_mini_game_login(code)
        self.info_log('Wechat mini_program_login result:', errcode, req_data)
        if errcode > 0:
            data = {"errcode": errcode, "errmsg": req_data}
            self.answer(self.sta_code.EXTERNAL_ERR, data, hint=req_data)

        # 通过union_id查询数据库用户信息
        openid = req_data.get('openid')
        platform = PlatForm.WECHAT_MINI_GAME
        q_params = {
            "openid": openid,
            "platform": platform
        }
        u_info = await BaseUserRC.cache_by_unique(q_params, BaseUserRC.KEY_OPENID)
        login_info = await self.get_login_info(req, LoginWay.WECHAT)

        # 新用户 注册
        if not u_info:
            u_info = await self.create_new_user(
                req, 'openid', login_info, req_data, BaseUserRC.KEY_OPENID, platform=platform)
            self.info_log('WechatMG Reg u_info:', u_info)
        # 老用户 登录
        else:
            u_info = await self.update_user_login_info(req, u_info, login_info)
            self.info_log('WechatMG Login u_info:', u_info)

        (not u_info) and self.answer(self.sta_code.NO_PLAYER_INFO, hint='Failed to login')
        # 保存session key (有效期不知) 用户登录态凭证
        session_key = req_data.get("session_key")
        await BaseUserRC.cache_session_key(u_info.get('uid'), session_key)
        self.info_log('LoginByWechatMiniProgram suc:', u_info.get('uid'))
        return await self.format_login_info(u_info, server_info, JWType.USER)


class LoginByWechat(BaseLogin):
    """ 微信登陆 """
    decorators = []

    async def post(self, req: Request):
        """ 通过code登录 """
        # 获取客户端code
        server_info = await self.whether_through()
        code = req.json.get('code')
        dev_ident = req.json.get('device_id') or req.headers.get('device_id')
        (not code or not dev_ident) and self.answer(self.sta_code.ERR_ARG, hint='Failed to login')

        errcode, req_data = await WeChat.wechat_app_login(code)
        self.info_log('Wechat wechat_app_login result:', errcode, req_data)
        if errcode > 0:
            data = {"errcode": errcode, "errmsg": req_data}
            self.answer(self.sta_code.EXTERNAL_ERR, data, hint=req_data)

        return await self.__after_get_token_by_code(req, req_data, server_info, dev_ident)

    async def __after_get_token_by_code(self, req, data, server_info, dev_ident):
        # 获取access_token、open_id等信息
        access_token = data.get('access_token')
        open_id = data.get('openid')
        url = "https://api.weixin.qq.com/sns/userinfo?access_token={0}&openid={1}&connect_redirect=1"
        url = url.format(access_token, open_id)

        # 通过access_token和open_id获取用户个人信息（UnionID机制）
        req_get = await http_get(url)
        req_data = json_parse(req_get)
        self.info_log('Wechat userinfo result:', req_data)
        errcode = req_data.get("errcode", 0)
        if errcode > 0:
            data = {"errcode": errcode, "errmsg": req_data}
            self.answer(self.sta_code.EXTERNAL_ERR, data, hint=req_data)

        # 通过union_id查询数据库用户信息
        union_id = req_data.get('unionid')
        platform = PlatForm.WECHAT_MINI_GAME
        q_params = {
            "unionid": union_id,
            "platform": platform
        }
        u_info = await BaseUserRC.cache_by_unique(q_params, BaseUserRC.KEY_UNION_ID)
        login_info = await self.get_login_info(req_get, LoginWay.WECHAT)

        # 新用户 注册
        if not u_info:
            u_info = await self.create_new_user(
                req, 'unionid', login_info, req_data, BaseUserRC.KEY_UNION_ID, platform=platform)
            self.info_log('Wechat Reg u_info:', u_info)
        # 老用户 登录
        else:
            u_info = await self.update_user_login_info(req, u_info, login_info)
            self.info_log('Wechat Login u_info:', u_info)

        (not u_info) and self.answer(self.sta_code.NO_PLAYER_INFO)
        self.info_log('LoginByWechat suc:', u_info.get("uid"))
        return await self.format_login_info(u_info, server_info, JWType.USER)


class LoginByToken(BaseLogin):
    """ 通过token登录 """

    async def post(self, req: Request, **kwargs):
        server_info = await self.whether_through()
        u_info = kwargs.get("u_info")
        login_info = await self.get_login_info(req, LoginWay.TOKEN)
        u_info = await self.update_user_login_info(req, u_info, login_info)
        (not u_info) and self.answer(self.sta_code.NO_PLAYER_INFO)
        jwt_info = kwargs.get("jwt_info")
        issued = False
        if jwt_info.get('exp') - tool_dt.cur_time() <= 43200:
            # 有效期小于12小时则重新签发 60 * 60 * 12
            issued = True
        else:
            # 这里不签发新的
            u_info.update({'token': req.headers.get("Authorization")})

        self.info_log('LoginByToken suc:', u_info.get("uid"), issued)
        return await self.format_login_info(u_info, server_info, issued=issued)


class LoginByAlipayGame(BaseLogin):
    """ 支付宝MG登录 """
    decorators = []

    async def post(self, req: Request):
        """ 通过code登录 """
        # 获取客户端code
        server_info = await self.whether_through()
        code = req.json.get('code')
        (not code) and self.answer(self.sta_code.ERR_ARG, hint='Failed to login')

        results, req_data = await Alipay.ali_get_access_token(code, AliGrantType.GET_TOKEN)
        self.info_log('Ali get_access_token result:', results, req_data)
        if not results:
            data = {"errcode": int(req_data.get('code')), "errmsg": req_data.get('sub_msg')}
            self.answer(self.sta_code.EXTERNAL_ERR, data)

        return await self.__after_get_token_by_code(req, req_data, server_info)

    async def __after_get_token_by_code(self, req, at_data, server_info):
        """非静默授权"""
        open_id = at_data.get('open_id')
        # 通过access_token、open_id获取授权和个人信息（非静默授权再用）
        # results, req_data = await Alipay.ali_get_user_auth_info(open_id, access_token)
        # self.info_log('Ali login_by_code results:', results, 'req_data:', req_data)
        # if not results:
        #     data = PbS2CExternalReturn.pb_model(
        #         **{"errcode": int(req_data.get('code')), "errmsg": req_data.get('sub_msg')})
        #     self.answer(self.sta_code.EXTERNAL_ERR, data)
        """静默授权"""
        platform = PlatForm.ALI_MINI_GAME
        req_data = {
            "openid": open_id,
            "platform": platform
        }

        # 通过open_id和platform 查询数据库用户信息
        u_info = await BaseUserRC.cache_by_unique(req_data, BaseUserRC.KEY_OPENID)
        login_info = await self.get_login_info(req, LoginWay.ALIPAY)

        # 新用户 注册
        if not u_info:
            u_info = await self.create_new_user(
                req, 'openid', login_info, req_data, BaseUserRC.KEY_OPENID, platform=platform)
            self.info_log('Ali Reg u_info:', u_info)
        # 老用户 登录
        else:
            u_info = await self.update_user_login_info(req, u_info, login_info)
            self.info_log('Ali Login u_info:', u_info)

        (not u_info) and self.answer(self.sta_code.NO_PLAYER_INFO)
        self.info_log('LoginByAlipayGame suc:', u_info.get("uid"))
        return await self.format_login_info(u_info, server_info, JWType.USER)


class LoginByDouYinGame(BaseLogin):
    """ 抖音MG登录 """
    decorators = []

    async def post(self, req: Request):
        """ 通过code登录 """
        # 获取客户端code
        server_info = await self.whether_through()
        code = req.json.get('code')
        (not code) and self.answer(self.sta_code.ERR_ARG, hint='Failed to login')

        errcode, req_data = await DouYin.douyin_mini_game_login(code)
        self.info_log('DouYin mini_game_login result:', code, req_data)
        if errcode > 0:
            data = {"errcode": errcode, "errmsg": req_data}
            self.answer(self.sta_code.EXTERNAL_ERR, data, hint=req_data)

        # 通过union_id查询数据库用户信息
        union_id = req_data.get('unionid')
        platform = PlatForm.DOUYIN_MINI_GAME
        user_data = {
            "unionid": union_id,
            "platform": platform
        }
        u_info = await BaseUserRC.cache_by_unique(user_data, BaseUserRC.KEY_UNION_ID)
        login_info = await self.get_login_info(req, LoginWay.WECHAT)

        # 新用户 注册
        if not u_info:
            u_info = await self.create_new_user(
                req, 'unionid', login_info, req_data, BaseUserRC.KEY_UNION_ID, platform=platform)
            self.info_log('DouYinMG Reg u_info:', u_info)
        # 老用户 登录
        else:
            u_info = await self.update_user_login_info(req, u_info, login_info)
            self.info_log('DouYinMG Login u_info:', u_info)

        (not u_info) and self.answer(self.sta_code.NO_PLAYER_INFO)
        # 保存会话密钥，如果请求时有 code 参数才会返回
        session_key = req_data.get('session_key')
        await BaseUserRC.cache_session_key(u_info.get('uid'), session_key)
        self.info_log('LoginByDouYinGame suc:', u_info.get("uid"))
        return await self.format_login_info(u_info, server_info, JWType.USER)
