"""
游戏战绩（总局）记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import RecordsGameTotal
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from nsanic.libs.tool import json_encode, json_parse
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from datetime import datetime, timedelta


class RecordsGameTotalRC(BaseCommonRC):
    db_model = RecordsGameTotal
    tb_name = db_model.sheet_name()

    KEY_GAME_ROOM_ID = 'record_rid'
    KEY_GAME_TOTAL_ID = 'record_tid'

    @classmethod
    async def create_record_game_total(cls, record_rid: int, uid: int, final_status: int, final_score: int, final_ranking: int,
                                       final_grade: int, final_result: dict, ):
        """创建战绩总局记录"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                record, _ = await RecordsGameRoomRC.get_record_room_by_id(record_rid)
                record_data = {
                    "record_rid": record["record_rid"],
                    "room_id": record["room_id"],
                    "club_id": record["club_id"],
                    "uid": uid,
                    "cs_type": record["cs_type"],
                    "final_status": final_status,
                    "final_score": final_score,
                    "final_ranking": final_ranking,
                    "final_grade": final_grade,
                    "final_result": final_result,
                }
                new_record = await cls.db_model.add_one(record_data)
                if not new_record:
                    return new_record, "创建失败"
                up_segment_sta, _ = await RecordsGameSegmentRC.update_record_game_segment(record_rid, record_tid=new_record.record_tid)
                up_room_sta, _ = await RecordsGameRoomRC.update_record_game_room(
                    record_rid,
                    end_time=int(datetime.now().timestamp())
                )
                if not up_room_sta or not up_segment_sta:
                    return new_record, "创建失败"
        except OperationalError as e:
            return None, f"创建失败: {str(e)}"
        return new_record, "成功"

    @classmethod
    async def bulk_create_record_game_total(cls, new_data: list):
        """批量写入战绩总局记录"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                instances = [cls.db_model(**data) for data in new_data]
                await cls.db_model.bulk_create(instances)
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return True, "成功"

    @classmethod
    async def get_record_total_by_id(cls, record_tid: int):
        """根据ID获取单条总局战绩"""
        try:
            record = await cls.db_model.get_by_pk(record_tid)
            if not record:
                return None, "战绩不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return record, "成功"

    @classmethod
    async def get_record_total_by_filter(cls, club_id: any = None, room_id: any = None, uid: any = None,
                                          record_rid: any = None, record_tid: any = None, start_time: int = None,
                                          end_time: int = None, cs_type: int = None, final_score: int = None,
                                          order_field: str = None, page: int = None, page_size: int = None):
        """根据条件获取总局战绩列表"""
        try:
            query = {}
            if club_id is not None:
                if isinstance(club_id, list):
                    query["club_id__in"] = club_id
                else:
                    query["club_id"] = club_id
            if room_id is not None:
                if isinstance(room_id, list):
                    query["room_id__in"] = room_id
                else:
                    query["room_id"] = room_id
            if uid is not None:
                if isinstance(uid, list):
                    query["uid__in"] = uid
                else:
                    query["uid"] = uid
            if record_rid is not None:
                if isinstance(record_rid, list):
                    query["record_rid__in"] = record_rid
                else:
                    query["record_rid"] = record_rid
            if record_tid is not None:
                if isinstance(record_tid, list):
                    query["record_tid__in"] = record_tid
                else:
                    query["record_tid"] = record_tid
            if start_time is not None:
                query["created__gte"] = start_time
            if end_time is not None:
                query["created__lt"] = end_time
            if cs_type is not None:
                query["cs_type"] = cs_type
            if final_score is not None:
                query["final_score__gte"] = final_score
            if order_field is None:
                order_field = "record_tid"
            if page and page_size:
                total, _ = await cls.count_record_total(**query)
                records = []
                if total > 0:
                    offset = (page - 1) * page_size
                    records = await cls.db_model.filter(**query).order_by(order_field).offset(offset).limit(page_size).values()
                result = await cls.page_result(page, page_size, total, records)
            else:
                result = records = await cls.db_model.filter(**query).order_by(order_field).values()
            if not records:
                return result, "暂无战绩"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return result, "成功"

    @classmethod
    async def count_record_total(cls, **perms):
        """获取房间战绩数量"""
        try:
            count = await cls.db_model.filter(**perms).count()
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return count, "成功",


    @classmethod
    async def delete_record_game_total(cls, record_tid: int):
        """删除战绩总局记录"""
        try:
            record = await cls.db_model.del_by_pk(record_tid)
            if not record:
                return record, "删除失败"
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"
        return record, "删除成功"
