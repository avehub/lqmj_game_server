# coding=utf-8
from sanic import Request, json
from lucky_game.base_api import GameAuthApi
from common.public.enum_const import StaCode
from lucky_game.model_rc.base_records_game import BaseRecordsGameRC


class TestApi(GameAuthApi):
    decorators = []

    async def get(self, req: Request):
        # cache_key = f"req_limit:look_ads:{100030}"
        # await self.conf.rds.set_item(cache_key, 1, 30)  # 设置键过期时间
        #
        # await asyncio.sleep(2)
        #
        # limit_time = await self.conf.rds.conn.ttl(cache_key)  # 设置键过期时间
        #
        # return json(body={"limit_time": limit_time})
        data = {
            "x-forwarded-for": req.headers.get("x-forwarded-for"),
            "x-real-ip": req.headers.get("x-real-ip"),
            "remote_addr": req.remote_addr,
            "req_ip": req.ip,
        }

        res = await self.conf.rds.get_item("test")

        return self.answer(StaCode.DEFAULT, data=data)

class TestCreatGameRecords(GameAuthApi):
    """创建游戏记录(模拟数据)"""
    decorators = []
    async def post(self, req: Request):
        data, _ = await BaseRecordsGameRC.creat_game_records()
        return self.answer(data=data)


