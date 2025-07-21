from typing import Optional

from aio_pika import DeliveryMode
from nsanic.base_conf import BaseConf
from nsanic.libs.component import LogMeta
from nsanic.libs.tool import json_encode, json_parse

from common.proto.py_pb2.ws_base import PbWsBaseRep
from common.public.enum_const import ServiceEnum, Channel, CacheKey, StaCode
from common.utils.utils import UtilsTool


class CommonApi(LogMeta):
    conf: BaseConf

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
            service_type,
            c_code,
            uid=1,
            msg=None,
    ):
        """
        内部调用ws
        目标service: ws_hall
        发给ws服务的，非直接面向用户
        """
        r_key = await cls.__get_routing_key(uid)
        cmd = UtilsTool.packet_command(service_type, c_code)
        await cls.cs2cs_by_rmq(ServiceEnum.WS_HALL, cmd, msg, uid, r_key=r_key)

    @classmethod
    async def __get_routing_key(cls, uid):
        if uid == 1:
            r_key = Channel.CHANNEL_SYSTEM_MSG
        else:
            ws_id = await cls.get_player_ws_id(uid)
            r_key = f"{ServiceEnum.WS_HALL.phrase}_{ServiceEnum.WS_HALL.val}_{ws_id}"
        return r_key

    @classmethod
    async def send_msg_to_player(
            cls,
            c_code,
            uid=1,
            code=StaCode.DEFAULT,
            hint="",
            msg=None,
            req_id="",
            cs_type: ServiceEnum = 0
    ):
        """ 发送消息至玩家 """
        r_key = await cls.__get_routing_key(uid)
        hint = hint or code.msg
        pb_data = PbWsBaseRep.encode(code, hint, msg, req_id)
        cmd = UtilsTool.packet_command(cs_type, c_code)
        await cls.cs2cs_by_rmq(ServiceEnum.WS_HALL, cmd, pb_data, uid, r_key=r_key)

    @classmethod
    async def req_by_rpc(cls, cs_type: ServiceEnum, c_code, uid, msg, r_key=''):
        """ rpc请求 """
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        data = await cls.conf.rmq.req_by_rpc(cs_type, c_code, uid, msg, r_key)
        return json_parse(data, log_fun=cls.log_err)

    @classmethod
    async def rep_by_rpc(cls, cs_type: ServiceEnum, msg, r_key="", correlation_id=None):
        """ rpc响应 """
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        await cls.conf.rmq.rep_by_rpc(cs_type, msg, r_key, correlation_id=correlation_id)

    @classmethod
    async def bytes_by_int_list(cls, bytes_list):
        """批量获取bytes"""
        result = []
        if not bytes_list:
            return result
        data = [p.decode('utf-8') for p in bytes_list]
        result = [int(p) for p in data]
        return result

    @classmethod
    async def merge_by_key(
            cls,
            arr1: list[dict[str, any]],
            arr2: list[dict[str, any]],
            key: str,
            fields: Optional[list[str]] = None
    ):
        """合并两个数组"""
        index = {
            item[key]: {k: v for k, v in item.items() if (not fields or k in fields)}
            for item in arr2
        }

        return [
            {
                **item,
                **{  # 仅合并指定字段
                    k: v
                    for k, v in index.get(item[key], {}).items()
                    if (not fields or k in fields)
                }
            }
            for item in arr1
        ]

    @classmethod
    async def json_by_dict(cls, data: str):
        """ json转dict  """
        if not data:
            return {}
        if "'" in data:
            str_json = data.replace("'", "\"")
        else:
            str_json = data
        return json_parse(str_json)
