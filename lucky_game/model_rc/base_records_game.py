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
    async def get_record_game_by_uid(cls, uid: int, start_time: int = None, end_time: int = None, cs_type: int = None):
        """根据用户ID获取战绩 (默认七日内)"""
        pass


    @classmethod
    async def get_record_game_by_room_id(cls, room_id: int = None,  start_time: int = None, end_time: int = None, cs_type: int = None):
        """根据条件获取单条战绩 (默认七日内)"""
        try:
            query = {}
            if room_id is not None:
                query["room_id"] = room_id
            # if start_time is not None:
            #     query["start_time"] = start_time
            # if end_time is not None:
            #     query["end_time"] = end_time
            # if cs_type is not None:
            #     query["cs_type"] = cs_type
            record = await cls.db_model.filter(**query).values()
            if not record:
                return None, "战绩不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return record, "成功"

    @classmethod
    async def get_record_game_by_club_id(cls, club_id: int = None, start_time: int = None, end_time: int = None,
                                         cs_type: int = None):
        """根据条件获取单条战绩 (默认七日内)"""
        try:
            query = {}
            if club_id is not None:
                query["club_id"] = club_id
            # if start_time is not None:
            #     query["start_time"] = start_time
            # if end_time is not None:
            #     query["end_time"] = end_time
            # if cs_type is not None:
            #     query["cs_type"] = cs_type
            record = await cls.db_model.filter(**query).values()
            if not record:
                return None, "战绩不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return record, "成功"

    @classmethod
    async def get_record_game_by_filter(cls, club_id: int = None, room_id: int = None, uid: int = None,
                                        start_time: int = None, end_time: int = None,):
    @classmethod
    async def get_record_room_by_filter(cls, club_id: int = None, room_id: int = None, creator: int = None):
        """根据条件获取房间战绩列表"""
        try:

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