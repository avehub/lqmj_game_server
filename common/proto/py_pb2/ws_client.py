"""
服务端业务与客户端的消息
"""
from common.proto.pb2 import ws_client_pb2
from nsanic.libs.tool import json_encode


class S2CAgainRoomInfo:
    @classmethod
    def pb_model(cls, **kwargs):
        """ 再来一局房间信息 """
        obj = ws_client_pb2.AgainRoomInfo()
        obj.room_id = kwargs.get("room_id") or 0
        obj.play_type = kwargs.get("play_type") or 0
        obj.cs_type = kwargs.get("cs_type") or 0
        obj.creator = kwargs.get("creator") or 0
        obj.status = kwargs.get("status") or 0
        obj.total_round = kwargs.get("total_round") or 0
        obj.max_player = kwargs.get("max_player") or 0
        rule_details = kwargs.get("rule_details") or ""
        if rule_details:
            obj.rule_details = json_encode(rule_details)
        return obj

