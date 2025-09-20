from common.proto.pb2 import http_friend_pb2


class PbFriendship():

    @classmethod
    def pb_model(cls, data: list):
        __proto = http_friend_pb2.S2CFriendshipList()

        for i in data or []:
            if i:
                obj = __proto.friend_list.add()
                pack_friend_data(obj, **i)
        return __proto


def pack_friend_data(obj, **kwargs):
    obj.uid = kwargs.get("uid") or 0
    obj.friend_uid = kwargs.get("friend_uid") or 0
    obj.friend_status = kwargs.get("status") or 0