# coding=utf-8
from sanic import Request, json
from lucky_game.base_api import GameAuthApi
from common.public.enum_const import StaCode
from lucky_game.model_rc.base_records_game import BaseRecordsGameRC
from lucky_game.model_rc.game_rooms import GameRoomsRC


class TestApi(GameAuthApi):
    decorators = []

    async def get(self, req: Request):
        data = await GameRoomsRC.abnormal_cs_type(22)
        return self.answer(StaCode.DEFAULT, data=data)


class TestCreatGameRecords(GameAuthApi):
    """创建游戏记录(模拟数据)"""
    decorators = []
    async def post(self, req: Request):
        data, _ = await BaseRecordsGameRC.creat_game_records()
        return self.answer(data=data)


