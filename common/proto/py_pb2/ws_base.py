from google.protobuf.json_format import MessageToDict
from common.proto.pb2 import ws_base_pb2
from common.public.enum_const import StaCode


class PbWsBaseRep():

    @classmethod
    def encode(cls, code: StaCode, hint="", _any=None, req_id=""):
        proto = ws_base_pb2.S2CWsBase()
        proto.code = code.val
        proto.hint = hint or code.msg
        _any and proto.data.Pack(_any)  # 装载Any消息
        proto.req_id = req_id
        data = proto.SerializeToString()
        return data

    @classmethod
    def decode(cls, proto_data):
        proto = ws_base_pb2.S2CWsBase()
        proto.ParseFromString(proto_data)
        # 解包data
        return MessageToDict(proto, preserving_proto_field_name=True, use_integers_for_enums=True)


class PbWsAuth():


    @classmethod
    def pb_model(cls, auth_token: str):
        """ 消息模型 """
        proto = ws_base_pb2.S2CAuthToken()
        proto.auth_token = auth_token
        return proto

    @classmethod
    def encode(cls, auth_token: str):
        proto = ws_base_pb2.S2CAuthToken()
        proto.auth_token = auth_token
        return proto.SerializeToString()
