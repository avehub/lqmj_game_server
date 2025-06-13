"""
游戏战绩基础类
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import RecordsGameRoom
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode, json_parse


class BaseRecordsGameRC(BaseCommonRC):

    KEY_GAME_ROOM_ID = 'record_rid'
    KEY_GAME_TOTAL_ID = 'record_tid'
    KEY_GAME_SEGMENT_ID = 'record_sid'
    @classmethod
    async def get_record_game_by_uid(cls, record_rid: int):
        """根据用户ID获取战绩"""
        pass


    @classmethod
    async def get_record_room_by_filter(cls, club_id: int = None, room_id: int = None, creator: int = None):
        """根据条件获取房间战绩列表"""
        try:
            query = cls.db_model.all()
            if club_id is not None:
                query = query.filter(club_id=club_id)
            if room_id is not None:
                query = query.filter(room_id=room_id)
            if creator is not None:
                query = query.filter(creator=creator)

            records = await query
            return records, "成功"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def update_record_game_room(cls, record_rid: int, **kwargs):
        """更新房间战绩信息"""
        try:
            record = await cls.db_model.get_or_none(record_rid=record_rid)
            if not record:
                return False, "战绩不存在"

            await record.update_from_dict(kwargs).save()
            return True, "更新成功"
        except OperationalError as e:
            return False, f"更新失败: {str(e)}"

    @classmethod
    async def delete_record_game_room(cls, record_rid: int):
        """删除房间战绩记录"""
        try:
            record = await cls.db_model.get_or_none(record_rid=record_rid)
            if not record:
                return False, "战绩不存在"

            await record.delete()
            return True, "删除成功"
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"