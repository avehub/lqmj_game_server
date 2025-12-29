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
代理提现
"""


class ProxyWithdraw(BaseApi):

    async def post(self, req: Request):
        print("123")

