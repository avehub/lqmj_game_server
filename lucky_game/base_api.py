# coding=utf-8
from nsanic.orm.rc_model import RCModel
from sanic.request import Request
from nsanic.handler_http import BaseHttpApi
from nsanic.base_ws import BaseWebsocket
from nsanic.libs.manager import WsConnector
from common.public.common_class import CommonApi
from common.public.enum_const import StaCode
from lucky_game.config import conf_srv, ConfSrv
from lucky_game.handler.decorator import GameChecker
from lucky_game.handler.exception import RealJsonFinish
from lucky_game.model_rc.base_user import BaseUserRC


class BaseApi(BaseHttpApi, CommonApi):
    conf: ConfSrv = conf_srv
    RCModel.set_conf(conf)

    async def check_solid_params(self, req: Request):
        """ 检查固有参数 """
        uid = req.json.get("uid")
        self.check_int(uid, require=True)
        user = await BaseUserRC.cache_by_uid(uid)
        not user and self.answer(self.sta_code.FAIL, hint="No player information")
        return user

    @staticmethod
    def real_ip(req: Request):
        """ 与Nginx直接建立TCP连接的客户端的IP地址 """
        return req.headers.get("x-real-ip")

    @classmethod
    def ori_ip(cls, req: Request):
        """
        多级代理最前面那个ip
        X-Forwarded-For: client, proxy1, proxy2
        通常情况下第一个IP地址是最接近用户的，但这并不总是绝对安全或准确的，因为X-Forwarded-For头可以被伪造。
        因此，在处理涉及安全性的事务时，不能仅依赖于X-Forwarded-For来判断用户的真实性。
        """
        ip_list = req.headers.get("x-forwarded-for")
        # cls.log_info("ip_list: ", ip_list, "real_ip: ", cls.real_ip(req), "remote ip: ", req.remote_addr, "ip: ", req.ip)
        if ip_list:
            return ip_list.split(',')[0]
        return cls.real_ip(req) or req.client_ip

    def answer_json(
            self, code: StaCode = None,
            data: (dict, object, list) = None,
            total: int = 0,
            hint: str = '',
            headers: dict = None):
        """
        公共JSON响应函数

        :param code: 响应码,请参照StaCode中取值, 默认响应成功状态
        :param data: 响应数据, 可以是任意符合JSON规范类型的数据模型
        :param total: 针对于分页响应的总数量
        :param hint: 响应消息, 字符串, 设置值后会采取设置的值，否则会使用响应码映射的默认值
        :param headers: 附加响应头
        """
        if not code:
            code = self.sta_code.PASS
        raise RealJsonFinish(code, data, total, hint, headers)


class GameAuthApi(BaseApi):
    decorators = [GameChecker]


class BaseWS(BaseWebsocket):
    conf = conf_srv
    conn_manager = WsConnector

class SpecialApi(BaseApi):
    decorators = []
