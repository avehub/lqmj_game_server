# coding=utf-8
from nsanic.base_blue import BaseBlue
from nsanic.handler_http import Urls
from lucky_proxy.interface.test_api import TestApi



class MainBp(BaseBlue):
    # 路由请添加在这里
    DEFAULT_APIS = [
        # 结构为: 接口路由地址, 接口视图处理器, 版本号(可选), 接口命名(可选)
        Urls("/testapi", TestApi),

    ]
