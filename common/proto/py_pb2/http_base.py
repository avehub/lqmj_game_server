from common.proto.pb2 import http_base_pb2
from google.protobuf.json_format import MessageToDict


class PbBaseRep():
    """ 基础response结构类 """
    __proto = http_base_pb2.S2CBase()

    @classmethod
    def encode(cls, code, msg, _any=None) -> bytes:
        if _any and not hasattr(_any, "DESCRIPTOR"):
            raise ValueError(f"BaseRep _any data error: {_any}")
        cls.__proto.code = code
        cls.__proto.msg = msg
        _any and cls.__proto.data.Pack(_any)  # 装载Any消息
        data = cls.__proto.SerializeToString()
        cls.clear_data()
        return data

    @classmethod
    def decode(cls, proto_data):
        cls.__proto.ParseFromString(proto_data)
        # 解包data
        # any_msg = self.__proto.data
        # if any_msg.Is(Person.DESCRIPTOR):
        #     person = Person()
        #     any_msg.Unpack(person)
        return MessageToDict(cls.__proto, preserving_proto_field_name=True, use_integers_for_enums=True)

    @classmethod
    def clear_data(cls):
        cls.__proto.data.Clear()  # 清空any数据
