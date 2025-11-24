from common.proto.pb2 import common_pb2
from common.proto.pb2 import http_leisure_pb2

red_dots_opportunity = common_pb2.RedDotsOpportunity  # 红点时机枚举
switch_enum = common_pb2.Switch  # 开关
switch_type_enum = common_pb2.SwitchType  # 开关


def s2c_in_service_model(**kwargs):
    """ 玩家是否在service中判断 """
    in_service_model = http_leisure_pb2.S2CInService()
    in_service_model.tid = str(kwargs.get("tid") or "")
    in_service_model.cs_type = kwargs.get("cs_type") or 0
    in_service_model.timestamp = str(kwargs.get("timestamp") or "")
    uid_list = kwargs.get("uid_list") or []
    if uid_list:
        in_service_model.uid_list.extend(uid_list)
    return in_service_model


def get_one_of_model():
    return common_pb2.S2COneFieldWeb()


def pack_chat_history(chat_list: list):
    obj = common_pb2.ChatMsgList()
    for msg in chat_list:
        m = obj.chat_msg_list.add()
        m.chat_chan = msg.get("chat_channel")
        m.from_uid = msg.get("from_uid")
        m.content = msg.get("content")
        m.created = msg.get("created") or 0
    return obj
