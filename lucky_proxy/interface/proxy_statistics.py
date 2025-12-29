# coding=utf-8
from nsanic.libs import tool_jwt

from common.public.conf import WeChatConf
from common.public.enum_const import StaCode
from lucky_proxy.base_api import BaseApi
from sanic import Request

from lucky_proxy.const import ProxyLoginType
from lucky_proxy.handler.wechat_mp import WeChatMpLogin
from lucky_proxy.model_db.main import ProxyUser

"""
代理统计相关
"""

"""
代理主页统计图标数据
"""


class ProxyIndexStatistics(BaseApi):

    async def get(self, req: Request):
       pass
