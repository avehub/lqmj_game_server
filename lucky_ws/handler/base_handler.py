from common.utils.utils import UtilsTool
from common.proto.py_pb2.ws_base import PbWsBaseRep
from common.public.pub_base_service import BasePubService


class BaseService(BasePubService):

    def __init__(self, service_type):
        super().__init__(service_type)

    async def response(self, ws, c_code, code, hint, _any=None, req_id=''):
        """ 回复玩家 """
        data = PbWsBaseRep.encode(code, hint, _any, req_id)
        print("回复玩家：", code, hint, _any, req_id, data)
        await ws.send(UtilsTool.pack_msg_by_bytes(self.service_type, c_code, data))

