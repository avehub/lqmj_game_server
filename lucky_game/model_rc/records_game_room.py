"""
游戏战绩（房间）记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import RecordsGameRoom
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode, json_parse


class RecordsGameRoomRC(BaseCommonRC):
    db_model = RecordsGameRoom
    tb_name = db_model.sheet_name()

    KEY_GAME_ROOM_ID = 'record_rid'

    @classmethod
    async def get_record_room_by_id(cls, record_rid: int):
        """根据ID获取房间战绩"""
        try:
            record = await cls.db_model.get_by_pk(record_rid)
            if not record:
                return None, "战绩不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return record, "成功"

    @classmethod
    async def get_record_room_by_filter(cls, club_id: any = None, room_id: any = None, start_time: any = None
                                        , ent_time: any = None, play_type: any = None, cs_type: any = None,
                                        creator: any = None, record_rid: any = None):
        """根据条件获取房间战绩列表"""
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
            if record_rid is not None:
                if isinstance(record_rid, list):
                    query["record_rid__in"] = record_rid
                else:
                    query["record_rid"] = record_rid
            if cs_type is not None:
                if isinstance(cs_type, list):
                    query["cs_type__in"] = cs_type
                else:
                    query["cs_type"] = cs_type
            if play_type is not None:
                if isinstance(play_type, list):
                    query["play_type__in"] = play_type
                else:
                    query["play_type"] = play_type
            if creator is not None:
                if isinstance(creator, list):
                    query["creator__in"] = creator
                else:
                    query["creator"] = creator
            if start_time is not None:
                query["start_time__gte"] = start_time
            if ent_time is not None:
                query["ent_time__lte"] = ent_time
            records = await cls.db_model.filter(**query).values()
            if not records:
                return records, "暂无战绩"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return records, "成功"

    @classmethod
    async def update_record_game_room(cls, record_rid: int, **kwargs):
        """更新房间战绩信息"""
        try:
            record = await cls.db_model.get_or_none(record_rid=record_rid)
            if not record:
                return None, "战绩不存在"
            sta = await record.update_by_pk(record_rid, kwargs)
            if not sta:
                return sta, "更新失败"
        except OperationalError as e:
            return None, f"更新失败: {str(e)}"
        return sta, "成功"

    @classmethod
    async def delete_record_game_room(cls, record_rid: int):
        """删除房间战绩记录"""
        try:
            record = await cls.db_model.del_by_pk(record_rid)
            if not record:
                return record, "删除失败"
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"
        return record, "删除成功"
