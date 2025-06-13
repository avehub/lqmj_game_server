"""
游戏战绩（子局）记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import RecordsGameSegment
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode, json_parse


class RecordsGameSegmentRC(BaseCommonRC):
    db_model = RecordsGameSegment
    tb_name = db_model.sheet_name()

    KEY_GAME_ROOM_ID = 'record_rid'
    KEY_GAME_TOTAL_ID = 'record_tid'
    KEY_GAME_SEGMENT_ID = 'record_sid'