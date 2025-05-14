from typing import Optional

from aio_pika import DeliveryMode
from nsanic.base_conf import BaseConf
from nsanic.libs.tool import json_encode, json_parse

from common.public.enum_const import ServiceEnum, Channel, CacheKey
from common.utils.utils import UtilsTool


class CommonApi:
    conf: BaseConf

    @classmethod
    def info_log(cls, *data):
        if cls.conf.DEBUG_MODE:
            return print(*data)
        cls.conf.log.info(*data)

    @classmethod
    def error_log(cls, *data):
        if cls.conf.DEBUG_MODE:
            return print(*data)
        cls.conf.log.error(*data)

    @classmethod
    async def get_player_ws_id(cls, uid):
        ws_id, _ = await cls.get_player_ws_info(uid)
        return ws_id

    @classmethod
    async def get_player_ws_info(cls, uid):
        ws_info = await cls.conf.rds.get_hash(CacheKey.WS_ONLINE_INFO, uid)
        if ws_info:
            ws_id, timestamp = ws_info.split(b'--' if isinstance(ws_info, bytes) else '--')
            return int(ws_id), int(timestamp)
        return 0, 0

    @classmethod
    async def cs2cs_by_rmq(
            cls,
            cs_type: ServiceEnum,
            c_code,
            msg=None,
            uid=1,
            r_key="",
            exp: Optional[int] = 30,
            delivery_mode=DeliveryMode.NOT_PERSISTENT,
    ):
        """
        通过rmq推送消息到网关
        该方法默认消息不持久化
        """
        await cls.conf.rmq.cs2cs_rmp(cs_type, c_code, uid, msg, r_key, exp, delivery_mode)

    @classmethod
    async def push_task2worker(cls, c_code=0, msg=None, uid=1, r_key="", cs_type: ServiceEnum = ServiceEnum.C_WORKERS):
        """
        推送消息到worker服务，该服务的消息不会过期
        """
        msg = msg or {}
        msg["secret"] = cls.conf.SECRET_KEY
        await cls.cs2cs_by_rmq(cs_type, c_code, msg, uid, r_key, exp=None, delivery_mode=DeliveryMode.PERSISTENT)

    @classmethod
    async def push_task2chat(cls, c_code=0, msg=None, uid=1, r_key="", cs_type: ServiceEnum = ServiceEnum.C_CHAT):
        """
        推送消息到chat服务
        """
        msg = msg or {}
        msg["secret"] = cls.conf.SECRET_KEY
        await cls.cs2cs_by_rmq(cs_type, c_code, msg, uid, r_key, exp=None, delivery_mode=DeliveryMode.PERSISTENT)

    @classmethod
    async def inner_cs2ws(
            cls,
            c_code,
            uid=1,
            msg=None,
            s_enum: ServiceEnum = ServiceEnum.WS_HALL
    ):
        """
        内部调用ws
        目标service: ws_hall
        发给ws服务的，非让ws中转
        """
        if uid == 1:
            r_key = Channel.CHANNEL_SYSTEM_MSG
        else:
            ws_id = await cls.get_player_ws_id(uid)
            if not ws_id:
                return
            r_key = f"{ServiceEnum.WS_HALL.phrase}_{ServiceEnum.WS_HALL.val}_{int(ws_id)}"
        cmd = UtilsTool.packet_command(s_enum, c_code)
        await cls.cs2cs_by_rmq(s_enum, cmd, msg, uid, r_key=r_key)

    @classmethod
    async def req_by_rpc(cls, cs_type: ServiceEnum, c_code, uid, msg, r_key=''):
        """ rpc请求 """
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        data = await cls.conf.rmq.req_by_rpc(cs_type, c_code, uid, msg, r_key)
        return json_parse(data, log_fun=cls.error_log)

    @classmethod
    async def rep_by_rpc(cls, cs_type: ServiceEnum, msg, r_key="", correlation_id=None):
        """ rpc响应 """
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        await cls.conf.rmq.rep_by_rpc(cs_type, msg, r_key, correlation_id=correlation_id)
