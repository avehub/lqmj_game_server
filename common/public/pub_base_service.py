import asyncio
from common.utils.meta_class import SingleTon


class BasePubService(metaclass=SingleTon):
    """ 公共基础类 """
    conf = None

    def __init__(self, service_type=0):
        self.__service_type = service_type
        self.__cmd2func = {}

    @property
    def service_type(self):
        return self.__service_type

    @service_type.setter
    def service_type(self, s_type):
        self.__service_type = s_type

    @property
    def cmd2func(self):
        return self.__cmd2func

    def __add_handler(self, cmd, func):
        assert cmd and cmd > 0 and func
        assert self.__cmd2func.get(cmd) is None, "duplicate handler"
        self.__cmd2func[cmd] = func

    def add_handlers(self, cmd_handlers: dict):
        for k, v in cmd_handlers.items():
            self.__add_handler(k, v)

    @classmethod
    def register_rc_model(cls, *models):
        """ 注册缓存模型 """
        for model in models:
            model.conf = cls.conf

    async def service(self, cmd, uid, data):
        """
        uid: uid or ws
        注意顺序
        """
        func = self.__cmd2func.get(cmd)
        if not func or not callable(func):
            return
        return await func(uid, data) if asyncio.iscoroutinefunction(func) else func(uid, data)

    @classmethod
    def share_server(cls):
        return cls()
