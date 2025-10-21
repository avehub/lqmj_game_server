from sanic import Request, HTTPResponse

from nsanic.libs import tool_jwt
from nsanic.libs.tool import json_encode
from nsanic.libs.component import BaseMeta

from lucky_admin.handler.decorator import sensitive_data_handler
from lucky_admin.model_db.main import RecordsAdminOperates


class RepMiddle(BaseMeta):

    @classmethod
    async def main(cls, req: Request, rep: HTTPResponse):
        """通用跨域适配"""
        method = req.method
        if method in ('GET', 'OPTIONS'):
            return
        username, _ = tool_jwt.get_jwinfo(req.token)
        username = username or req.json.get('username') or ''
        route = req.path.strip('/').split('/')[-1]
        op_name = req.args.get('op_name')
        if req.json:
            sensitive_data_handler(req.json)

        params = json_encode(req.json) or "{}"
        status = rep.status
        hint = ''
        if hasattr(rep, 'raw_body'):
            hint = rep.raw_body.get('msg') or ''
        await RecordsAdminOperates.insert_one(username, route, op_name, method, params, status, hint[:32])
        return
