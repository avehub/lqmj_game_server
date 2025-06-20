# coding=utf-8
from sanic import Request, json
from lucky_game.base_api import GameAuthApi
from common.public.enum_const import StaCode
from lucky_game.model_rc.base_records_game import RecordsGameTotalRC
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
        new_data = [
            {
                "record_rid": 12,
                "room_id": 961365,
                "club_id": 100003,
                "uid": 100000,
                "cs_type": 22,
                "final_status": 1,
                "final_score": 1,
                "final_ranking": 1,
                "final_grade": 1,
                "final_result": 1,
            },
            {
                "record_rid": 12,
                "room_id": 961365,
                "club_id": 100003,
                "uid": 100001,
                "cs_type": 22,
                "final_status": 0,
                "final_score": 0,
                "final_ranking": 0,
                "final_grade": 0,
                "final_result": 0,
            }
        ]
        data, _ = await RecordsGameTotalRC.bulk_create_record_game_total(new_data)
        return self.answer(data=data)


