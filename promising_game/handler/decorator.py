from functools import wraps
from inspect import isawaitable
from nsanic.libs import tool_jwt, tool_dt
from sanic.request import Request
from nsanic.libs.mult_log import NLogger
from nsanic.handler_http import BaseRps

from common.public.conf import LIVE_SERVER
from common.public.enum_const import JWType
from promising_game.model_rc.base_user import BaseUserRC
from promising_game.config import conf_srv, ConfSrv


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


class GameChecker(BaseDecorator):
    """ 游戏检查器 """
    conf: ConfSrv = conf_srv

    def __init__(self, func):
        super().__init__(func)

    def check_required_parameter(self, req: Request):
        """ 检查必要参数 """
        c_os = req.args.get("c_os")
        self.check_str(c_os, require=True, p_name="c_os")
        c_platform = req.args.get("c_platform")
        self.check_str(c_platform, require=True, p_name="c_platform")
        c_uid = req.args.get("c_uid")
        self.check_int(c_uid, require=True, minval=1, p_name="c_uid")
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
        return await self.call_method(req, *args, **kwargs)

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
            self.answer(code=self.sta_code.REQ_FREQUENT)

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


def aio_runtime(log: NLogger = None):
    """协程 时间检查"""

    def out_runtime(fun):
        @wraps(fun)
        async def wrap_fun(*args, **kwargs):
            pass

        return wrap_fun

    return out_runtime
