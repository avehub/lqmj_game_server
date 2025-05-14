# coding=utf-8
from sanic import Request
from lucky_admin.base_api import BaseApi


class TestApi(BaseApi):
    async def get(self, req: Request):
        return self.answer(hint="Here is a api for test.")
