"""
游戏战绩相关接口
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_rc.base_records_game import BaseRecordsGameRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC


class RecordBase(GameAuthApi):
    """游戏战绩基础相关方法"""
    async def base(self, req: Request, **kwargs):
        pid = req.args.get("pid", 0)
        rule_type = req.args.get("type")
        data, e = await BaseRecordsGameRC.get_record_room_by_filter()
        return self.answer(data=data)
