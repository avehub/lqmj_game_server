"""
代理初始化

"""
from lucky_proxy.model_db.main import ProxyUser


class ProxyCreator:
    async def init_proxy(self, proxyUser: ProxyUser):
        ProxyUser.create()
        pass
