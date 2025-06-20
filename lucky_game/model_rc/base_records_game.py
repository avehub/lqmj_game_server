"""
游戏战绩基础类
"""
from datetime import datetime, timedelta
from tortoise.exceptions import OperationalError
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
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
                # 测试数据
                room_id = 961365
                start_time = 1722756800
                end_time = 1722856800
                uid = 100000
                r_record, _ = await RecordsGameRoomRC.create_record_game_room(room_id, start_time, end_time)
                s_record, _ = await RecordsGameSegmentRC.create_record_game_segment(r_record.record_rid, uid, 1, 1, 1, 0, {"gold":100, "other":456}, "http://123.cc")
                t_record, _ = await RecordsGameTotalRC.create_record_game_total(r_record.record_rid, uid, 1, 1, 1, 1, {"gold":100, "other":456})
                data = True
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_uid(cls, uid: int, start_time: int = None, end_time: int = None, cs_type: int = None,
                         page_size: int = None, page: int = None):
        """根据用户ID获取战绩 (默认七日内)"""
        try:
            if start_time is None and end_time is None:
                start_time, end_time = await cls.default_time()
            data, e = await RecordsGameTotalRC.get_record_total_by_filter(
                uid=uid,
                start_time=start_time,
                end_time=end_time,
                cs_type=cs_type,
                page_size=page_size,
                page=page,
            )
            # TODO 暂时注释 根据前端联调数据需要做调整
            # if data.get("total") > 0:
            #     ids = [item["record_rid"] for item in data["list"]]
            #     room_data, _ = await RecordsGameRoomRC.get_record_room_by_filter(
            #         record_rid=ids,
            #     )
            #     data["list"] = CommonApi.merge_by_key(data["list"], room_data, "record_rid")
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_room_id(cls, room_id: int = None, uid: int = None,  start_time: int = None,
                             end_time: int = None, cs_type: int = None, page_size: int = None,
                             page: int = None):
        """根据房间号获取战绩 (默认七日内)"""
        try:
            if start_time is None and end_time is None:
                start_time, end_time = await cls.default_time()
            data, e = await RecordsGameTotalRC.get_record_total_by_filter(
                room_id=room_id,
                uid=uid,
                start_time=start_time,
                end_time=end_time,
                cs_type=cs_type,
                page_size=page_size,
                page=page,
            )
            if not data:
                return data, e
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_club_id(cls, club_id: int = None, room_id: int = None, start_time: int = None, end_time: int = None,
                             cs_type: int = None, uid: int = None, final_score: int = None, order_field: str = None,
                             page_size: int = None, page: int = None):
        """根据茶ID馆获取 (默认七日内)战绩"""
        try:
            if start_time is None and end_time is None:
                start_time, end_time = await cls.default_time()
            data, e = await RecordsGameTotalRC.get_record_total_by_filter(
                club_id=club_id,
                room_id=room_id,
                uid=uid,
                start_time=start_time,
                end_time=end_time,
                cs_type=cs_type,
                final_score=final_score,
                order_field=order_field,
                page_size=page_size,
                page=page,
            )
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_club_count(cls, club_id: int = None, room_id: int = None, start_time: int = None, end_time: int = None,
                                uid: int = None, cs_type: int = None, final_score: int = None):
        try:
            if start_time is None and end_time is None:
                start_time, end_time = await cls.default_time()
            result, e = await RecordsGameTotalRC.get_record_total_by_filter(
                uid=uid,
                club_id=club_id,
                room_id=room_id,
                start_time=start_time,
                end_time=end_time,
                cs_type=cs_type,
            )
            if not result:
                return None, e
            for item in result:
                pass
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return result, "成功"


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