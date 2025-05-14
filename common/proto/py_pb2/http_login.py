from google.protobuf.json_format import ParseDict

from common.proto.pb2 import http_login_pb2
from common.utils.utils import UtilsTool


class PbLogin():
    __proto = http_login_pb2.S2CLogin()

    @classmethod
    def pb_model_old(cls, data: dict):
        """ 消息模型 """
        return ParseDict(data, cls.__proto)

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        cls.__proto = http_login_pb2.S2CLogin()
        server_info = data.get("server_info")
        for one_data in server_info:
            sd = cls.__proto.server_info.add()
            PbServerAddr.pb_model(sd, **one_data)

        user_info = data.get("user_info")
        PbUser.pb_model(user_obj=cls.__proto.user_info, **user_info)
        return cls.__proto

    @classmethod
    def decode(cls, msg: bytes):
        cls.__proto.ParseFromString(msg)
        return cls.__proto


class PbUser():
    __proto = http_login_pb2.Person()

    @classmethod
    def pb_model(cls, user_obj=None, **kwargs):
        """ 消息模型 """
        user_obj = user_obj or cls.__proto
        user_obj.created = kwargs.get("created") or 0
        user_obj.uid = kwargs.get("uid") or 0
        user_obj.name = kwargs.get("name") or ''
        user_obj.sex = kwargs.get("sex") or 0
        user_obj.phone = kwargs.get("phone") or ''
        user_obj.email = kwargs.get("email") or ''
        user_obj.address = kwargs.get("address") or ''
        user_obj.id_card = UtilsTool.mask_id_card(kwargs.get("id_card") or '')
        user_obj.gold = str(kwargs.get("gold") or '')
        user_obj.diamond = kwargs.get("diamond") or 0
        user_obj.avatar = kwargs.get("avatar") or ''
        user_obj.updated = kwargs.get("updated") or 0
        user_obj.dev_ident = kwargs.get("dev_ident") or ''
        user_obj.valid_key = kwargs.get("valid_key") or ''
        user_obj.new_user = kwargs.get("new_user") or False
        user_obj.ip = kwargs.get("ip") or ''
        user_obj.region = kwargs.get("region") or ''
        user_obj.token = kwargs.get("token") or ''
        user_obj.vip_level = kwargs.get("vip_level") or 0
        user_obj.open_id = kwargs.get("openid") or ''
        return user_obj


class PbServerAddr():
    __proto = http_login_pb2.ServerAddr()

    @classmethod
    def pb_model(cls, server_addr_obj=None, **kwargs):
        """ 消息模型 """
        obj = server_addr_obj or cls.__proto
        obj.id = kwargs.get("id") or 0
        obj.created = kwargs.get("created") or 0
        obj.sid = kwargs.get("sid") or 0
        obj.addr = kwargs.get("addr") or ''
        obj.path = kwargs.get("path") or ''
        obj.status = kwargs.get("status") or 0
        return obj


class PbS2CExternalReturn():
    """ 外部返回 """
    __proto = http_login_pb2.S2CExternalReturn()  # todo: 修改名字

    @classmethod
    def pb_model(cls, **kwargs):
        """ 消息模型 """
        obj = cls.__proto
        obj.errcode = kwargs.get("errcode") or 0
        obj.errmsg = kwargs.get("errmsg") or ""
        return obj
