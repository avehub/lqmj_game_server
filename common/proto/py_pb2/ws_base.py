from google.protobuf.json_format import MessageToDict
from common.proto.pb2 import ws_base_pb2
from common.public.enum_const import StaCode


class PbWsBaseRep():
    __proto = ws_base_pb2.S2CWsBase()

    @classmethod
    def encode(cls, code: StaCode, hint="", _any=None, req_id=""):
        cls.__proto.code = code.val
        cls.__proto.hint = hint or code.msg
        _any and cls.__proto.data.Pack(_any)  # 装载Any消息
        cls.__proto.req_id = req_id
        data = cls.__proto.SerializeToString()
        cls.clear_data()
        return data

    @classmethod
    def decode(cls, proto_data):
        cls.__proto.ParseFromString(proto_data)
        # 解包data
        return MessageToDict(cls.__proto, preserving_proto_field_name=True, use_integers_for_enums=True)

    @classmethod
    def clear_data(cls):
        cls.__proto.data.Clear()  # 清空any数据


class PbWsAuth():
    __proto = ws_base_pb2.S2CAuthToken()

    @classmethod
    def pb_model(cls, auth_token: str):
        """ 消息模型 """
        cls.__proto.auth_token = auth_token
        return cls.__proto

    @classmethod
    def encode(cls, auth_token: str):
        cls.__proto.auth_token = auth_token
        return cls.__proto.SerializeToString()
