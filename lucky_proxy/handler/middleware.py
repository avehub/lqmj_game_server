from sanic import Request, HTTPResponse

from nsanic.libs import tool_jwt
from nsanic.libs.tool import json_encode
from nsanic.libs.component import BaseMeta
from lucky_proxy.handler.decorator import sensitive_data_handler


class RepMiddle(BaseMeta):

    @classmethod
    async def main(cls, req: Request, rep: HTTPResponse):
        """通用跨域适配"""
        method = req.method
        if method in ('GET', 'OPTIONS'):
            return
        return
