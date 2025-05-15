from c_services.const.cs_enum_const import CmdWs
from lucky_ws.base_api import BaseWS
from common.utils.utils import UtilsTool
# from lucky_ws.handler.wsc_match_forward import MatchForward
from common.proto.py_pb2.ws_base import PbWsBaseRep
from lucky_ws.config.conf_start import conf_srv, ConfSrv
from sanic.request import Request


class WsHall(BaseWS):
    conf: ConfSrv = conf_srv

    # _services = {ServiceEnum.WS_HALL: MatchForward(ServiceEnum.WS_HALL)}

    def __init__(self):
        super().__init__()

    async def wsauth(self, req: Request, ws) -> bool:
        user_info = await self.check_ws_req_params(req, ws)
        if not user_info:
            return False
        token = req.args.get("sign")
        valid_key = user_info.get("valid_key")
        s_key = f"{valid_key}_{req.args.get('timestamp')}"
        uid = user_info.get("uid") or 0
        subject_info = f"{uid}_{user_info.get('created')}"
        encrypt_token = UtilsTool.get_hash_secrets(s_key, subject_info)
        # self.info_log(uid, "认证参数：", s_key, subject_info, "sign：", token, encrypt_token)
        if token != encrypt_token:
            data = PbWsBaseRep.encode(self.sta_code.ERR_AUTH, hint="无效认证")
            await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
            return False

        # 在这里签发一个auth_token,在子游戏连接认证时验证
        # auth_token = UtilsTool.get_hash_secrets(
        #     self.conf.SERVER_SECRET_KEY, subject_info, user_info.get("created"), secrets_type="sha1")
        # token_message = PbWsAuth.pb_model(auth_token)
        # data = PbWsBaseRep.encode(self.sta_code.PASS, hint="ok", _any=token_message)
        # self.info_log(f"玩家{uid}连接成功, {token_message}")
        return user_info

    async def client_listen(self, ws, _):
        """ 监听连接 """
        data = PbWsBaseRep.encode(self.sta_code.PASS, hint="ok")
        await ws.send(self.fun_pack_msg(self.dft_type, CmdWs.SUCCEED, data))
        self.info_log(f"玩家上线", ws.ukey, ws.timestamp)
        await super().client_listen(ws, _)


