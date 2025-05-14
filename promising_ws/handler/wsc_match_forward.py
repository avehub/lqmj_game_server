from .base_handler import BaseService


class MatchForward(BaseService):
    """ 子网关接收匹配前的处理 """

    def __init__(self, service_type):
        super().__init__(service_type)
        self.add_handlers({

        })