"""
游戏战绩（总局）记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import RecordsGameTotal
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode, json_parse


class RecordsGameTotalRC(BaseCommonRC):
    db_model = RecordsGameTotal
    tb_name = db_model.sheet_name()

    KEY_GAME_ROOM_ID = 'record_rid'
    KEY_GAME_TOTAL_ID = 'record_tid'

    @classmethod
    async def get_records_total_by_id(cls, record_tid: int):
        """根据ID获取房间战绩"""
        try:
            record = await cls.db_model.get_or_none(record_tid=record_tid).values()
            if not record:
                return None, "战绩不存在"
            return record, "成功"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def get_records_total_by_filter(cls, club_id: int = None, room_id: int = None, creator: int = None):
        """根据条件获取房间战绩列表"""
        try:
            return records, "成功"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def delete_record_game_total(cls, record_tid: int):
        """删除房间战绩记录"""
        try:
            record = await cls.db_model.get_or_none(record_tid=record_tid)
            if not record:
                return False, "战绩不存在"

            await record.delete()
            return True, "删除成功"
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"