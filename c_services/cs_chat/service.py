from collections import deque
from nsanic.libs import tool_dt
from c_services.base.base_server import JsonBaseServer
from c_services.const.cs_enum_const import CmdChat
from common.proto.pb2 import common_pb2
from common.public.enum_const import ChatChannel
from lucky_game.model_rc.base_chat import ChatRecordRC


class ChatServer(JsonBaseServer):
    """
    聊天服务
    """

    def __init__(self):
        super().__init__()

        self.add_handlers({
            CmdChat.RECEIVE_CHAT_MSG: self.__recv_chat_message,
        })
        self.register_rc_model(ChatRecordRC)

    async def __recv_chat_message(self, to_uid, msg: dict):
        """ 接收聊天消息 """
        # todo:VIP等级、排位等级、装扮等即时性要求不高，可通过web接口查询（可重新封装一个查询聊天信息的借口）
        print("接受聊天消息", msg)
        chat_channel = msg.get("chat_channel")

        # 添加到聊天历史记录 todo: worker写入？
        await ChatRecordRC.save_chat_message(msg)
        # 根据频道选择不同的广播方法
        match chat_channel:
            case ChatChannel.WORLD:
                await self.send_message(msg)
            case ChatChannel.FRIENDS:
                await self.send_message(msg, to_uid)
            case _:
                return

    async def send_message(self, msg: dict, recv_uid=1):
        """
        发送消息
        :param msg:
        :param recv_uid: 1广播所有在线玩家，具体uid则单发
        :return: None
        """
        # todo:model需要重写
        m = common_pb2.ChatMsg()
        m.chat_chan = msg.get("chat_channel")
        m.from_uid = msg.get("from_uid")
        m.content = msg.get("content")
        m.created = msg.get("created") or tool_dt.cur_time()
        await self.chat_ws_by_rmq(CmdChat.RECEIVE_CHAT_MSG, uid=recv_uid, msg=m)
