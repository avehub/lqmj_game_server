"""
游戏战绩基础类
"""
from datetime import datetime, timedelta
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import RecordsGameRoom
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from nsanic.libs.tool import json_encode, json_parse
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey


class BaseRecordsGameRC(BaseCommonRC):

    KEY_GAME_ROOM_ID = 'record_rid'
    KEY_GAME_TOTAL_ID = 'record_tid'
    KEY_GAME_SEGMENT_ID = 'record_sid'

    @classmethod
    async def default_time(cls, days: int = 7):
        """生成默认时间范围"""
        now = datetime.now()
        days_ago = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = int(days_ago.timestamp())
        end_time = int(now.timestamp())
        return start_time, end_time

    @classmethod
    async def creat_game_records(cls, room_id: int = None, club_id: int = None,  start_time: int = None,
                                         end_time: int = None, cs_type: int = None):
        """新增游戏战绩"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                pass
                data = True
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_uid(cls, uid: int, start_time: int = None, end_time: int = None, cs_type: int = None):
        """根据用户ID获取战绩 (默认七日内)"""
        try:
            if start_time is None and end_time is None:
                start_time, end_time = cls.default_time()
            data, e = RecordsGameTotalRC.get_records_total_by_filter(
                uid=uid,
                start_time=start_time,
                end_time=end_time,
                cs_type=cs_type
            )
            if not data:
                return data, e
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_room_id(cls, room_id: int = None, uid: int = None,  start_time: int = None,
                                         end_time: int = None, cs_type: int = None):
        """根据房间号获取战绩 (默认七日内)"""
        try:
            if start_time is None and end_time is None:
                start_time, end_time = cls.default_time()
            data, e = RecordsGameTotalRC.get_records_total_by_filter(
                room_id=room_id,
                uid=uid,
                start_time=start_time,
                end_time=end_time,
                cs_type=cs_type
            )
            if not data:
                return data, e
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_club_id(cls, club_id: int = None, room_id: int = None, start_time: int = None, end_time: int = None,
                             cs_type: int = None, uid: int = None, final_score: int = None, order_field: str = None):
        """根据茶ID馆获取 (默认七日内)战绩"""
        try:
            if start_time is None and end_time is None:
                start_time, end_time = cls.default_time()
            data, e = RecordsGameTotalRC.get_records_total_by_filter(
                club_id=club_id,
                room_id=room_id,
                uid=uid,
                start_time=start_time,
                end_time=end_time,
                cs_type=cs_type,
                final_score=final_score,
                order_field=order_field,
            )
            if not data:
                return data, e
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_club_count(cls, club_id: int = None, room_id: int = None, start_time: int = None, end_time: int = None,
                                cs_type: int = None, final_score: int = None):
        try:
            if start_time is None and end_time is None:
                start_time, end_time = cls.default_time()
            result, e = RecordsGameRoomRC.get_record_room_by_filter(
                club_id=club_id,
                room_id=room_id,
                start_time=start_time,
                end_time=end_time,
                cs_type=cs_type,
                final_score=final_score,
            )
            if not result:
                return None, e
            for item in result:
                pass
            return result, e
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"


    @classmethod
    async def get_record_room_by_filter(cls, club_id: int = None, room_id: int = None, creator: int = None):
        """根据条件获取房间战绩列表"""
        try:
            query = {}
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