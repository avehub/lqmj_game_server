from functools import wraps
from inspect import isawaitable
from nsanic.libs import tool_jwt, tool_dt
from sanic.request import Request
from nsanic.libs.mult_log import NLogger
from nsanic.handler_http import BaseRps
from common.public.conf import LIVE_SERVER
from common.public.enum_const import JWType
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.config import conf_srv, ConfSrv
from nsanic.libs.consts import StaCode
from nsanic.exception import JsonFinish
from nsanic.libs.consts import Code
from ..model_rc.conf_json import ConfJsonRC


class BaseDecorator(BaseRps):
    def __init__(self, func):
        super().__init__()
        self.__func = func

    def check_method(self, req: Request):
        if req.method in ('POST', 'PUT',) and req.json is None:
            return self.answer(self.sta_code.FAIL, hint="Missing body parameter")

    async def call_method(self, req, *args, **kwargs):
        response = self.__func(req, *args, **kwargs)

        if isawaitable(response):
            response = await response
        return response

    async def check_inner(
            self,
            val: any,
            require: bool = False,
            default: any = None,
            inner_dick: tuple = (),
            p_name='') -> int or str:
        """
        内部指定参数校验
        :param val: 待校验对象
        :param require: 是否必要参数 默认非必要
        :param default: 非必要状态下的默认值
        :param inner_dick: 校验范围列表
        :param p_name: 参数名
        :return 转换的值--int
        """
        if not require:
            return default
        if val is None:
            return self.answer(
                code=StaCode.ERR_ARG,
                hint=f"The parameter {p_name} is required"
            )
        if val in inner_dick:
            return val
        else:
            return self.answer(
                code=StaCode.ERR_ARG,
                hint=f"The parameter {p_name} is not within the range of parameter values"
            )



class GameChecker(BaseDecorator):
    """ 游戏检查器 """
    conf: ConfSrv = conf_srv

    def __init__(self, func):
        super().__init__(func)

    def check_required_parameter(self, req: Request):
        """ 检查必要参数 """
        c_os = req.args.get("c_os")
        self.check_str(c_os, require=True, p_name="c_os")
        platform = req.args.get("platform")
        self.check_str(platform, require=True, p_name="platform")
        c_uid = req.args.get("c_uid")
        self.check_int(c_uid, require=True, p_name="c_uid")
        c_ver = req.args.get("c_ver")
        self.check_str(c_ver, require=True, p_name="c_ver")

    async def __call__(self, req: Request, *args, **kwargs):
        # self.check_method(req)
        LIVE_SERVER and self.check_required_parameter(req)
        u_info, data = await self.verify_token(req)
        if not u_info:
            self.answer(self.sta_code.FAIL, hint=data)
        ban_time = u_info.get("ban_time") or 0
        if ban_time == -1 or ban_time > tool_dt.cur_time():
            self.answer(self.sta_code.FAIL, hint="玩家已处于被封禁中！")

        kwargs.update({"u_info": u_info})
        kwargs.update({"jwt_info": data})
        result = await self.call_method(req, *args, **kwargs)
        self.loginfo(f"出参:", result)
        return result

    @classmethod
    async def verify_token(cls, req):
        """ 验证token """
        token = req.headers.get("Authorization") or (req.json and req.json.get("token")) or ""
        if not token:
            return False, "缺少必要参数（token）"
        # 1.获取载荷信息
        uid, _ = tool_jwt.get_jwinfo(token)
        if not isinstance(uid, int):
            return False, "uid错误"
        # 2.通过载荷信息获取玩家信息：safe_key
        u_info = await BaseUserRC.cache_by_uid(uid)
        if not u_info:
            return False, "没有玩家信息"
        # 3.通过safe_key验签token合法性
        safe_key = u_info.get("safe_key")
        subject_info = f"{u_info.get('created')}_{uid}"
        # self.conf.log.info("token 验证：", subject_info)
        data, hint = tool_jwt.jdecode(token, JWType.USER, safe_key, subject_info)
        if not data:
            return False, "Invalid authorization."
        return u_info, data


class CurrentLimiting(BaseDecorator):
    """ 限流处理 """
    conf: ConfSrv = conf_srv
    exp = 60
    limit_times = 5

    def __init__(self, func):
        super().__init__(func)

    async def __call__(self, req: Request, *args, **kwargs):
        u_info = kwargs.get("u_info") or {}
        u_key = u_info.get('uid')  # or BaseApi.ori_ip(req)
        cache_key = f"req_limit:{u_key}:{req.server_path}"

        incr_value = await self.conf.rds.conn.incr(cache_key)
        await self.conf.rds.expired(cache_key, self.exp)  # 设置键过期时间

        if incr_value > self.limit_times:
            return self.answer(code=self.sta_code.REQ_FREQUENT)

        return await self.call_method(req, *args, **kwargs)


class LimitTestCall(BaseDecorator):
    """ 限制测试调用 """
    conf: ConfSrv = conf_srv

    def __init__(self, func):
        super().__init__(func)

    async def __call__(self, req: Request, *args, **kwargs):
        if LIVE_SERVER:
            self.answer(self.sta_code.FAIL, hint="该接口仅测试用")
        return await self.call_method(req, *args, **kwargs)

class SysMaintain(BaseDecorator):
    """ 系统维护性特用 """
    conf: ConfSrv = conf_srv
    def __init__(self, func):
        super().__init__(func)

    @classmethod
    async def sys_verify(cls, req: Request, **kwargs):
        uid = 0
        verify_status = True
        u_info = kwargs.get("u_info")
        if u_info and isinstance(u_info, dict):
            uid = u_info.get("uid")
        maintain = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_MAINTAIN)
        cls.conf.log.info("系统维护性检查:", type(maintain), maintain)
        if maintain.get("status"):
            verify_status = False
            if uid in maintain.get("special_uid"):
                verify_status = True
        return verify_status, "游戏维护中，暂时无法进入！详情请联系客服"



def aio_runtime(log: NLogger = None):
    """协程 时间检查"""

    def out_runtime(fun):
        @wraps(fun)
        async def wrap_fun(*args, **kwargs):
            pass

        return wrap_fun

    return out_runtime
