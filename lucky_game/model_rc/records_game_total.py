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
        """根据ID获取单条总局战绩"""
        try:
            record = await cls.db_model.get_by_pk(record_tid)
            if not record:
                return None, "战绩不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return record, "成功"

    @classmethod
    async def get_records_total_by_filter(cls, club_id: any = None, room_id: any = None, uid: any = None,
                                          record_rid: any = None, record_tid: any = None):
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

            records = await cls.db_model.filter(**query).values()
            if not records:
                return records, "暂无战绩"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return records, "成功"

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
