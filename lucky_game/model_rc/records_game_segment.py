"""
游戏战绩（子局）记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import RecordsGameSegment
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from nsanic.libs.tool import json_encode, json_parse


class RecordsGameSegmentRC(BaseCommonRC):
    db_model = RecordsGameSegment
    tb_name = db_model.sheet_name()

    KEY_GAME_ROOM_ID = 'record_rid'
    KEY_GAME_TOTAL_ID = 'record_sid'
    KEY_GAME_SEGMENT_ID = 'record_sid'

    @classmethod
    async def create_record_game_segment(cls, record_rid: int, uid: int, round_num: int, round_status: int,
                                         round_score: int, round_ranking: int, round_result: str, replay_msg: str):
        """创建战绩子局记录"""
        try:
            record = await RecordsGameRoomRC.get_record_room_by_id(record_rid)
            record_data = {
                "record_rid": record["record_rid"],
                "record_tid": 0,
                "uid": uid,
                "cs_type": record["cs_type"],
                "round_num": round_num,
                "round_status": round_status,
                "round_score": round_score,
                "round_ranking": round_ranking,
                "round_result": round_result,
                "replay_msg": replay_msg,
            }
            new_record = await cls.db_model.add_one(record_data)
            if not new_record:
                return new_record, "创建失败"
        except OperationalError as e:
            return None, f"创建失败: {str(e)}"
        return new_record, "成功"

    @classmethod
    async def update_record_game_segment(cls, record_sid: int, **kwargs):
        """更新子局战绩记录"""
        try:
            record_tid = kwargs.get("record_tid")
            if record_tid:
                up_sta = await cls.db_model.update_by_pk(record_sid, {"record_tid": record_tid})
                if not up_sta:
                    return up_sta, "更新失败"
        except OperationalError as e:
            return None, f"更新失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def get_records_segment_by_id(cls, record_sid: int):
        """根据ID获取单条子局战绩"""
        try:
            record = await cls.db_model.get_by_pk(record_sid)
            if not record:
                return None, "战绩不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return record, "成功"

    @classmethod
    async def get_records_segment_by_rid(cls, record_rid: int):
        """根据ID获取单条子局战绩"""
        try:
            query = {
                "record_rid": record_rid
            }
            record = await cls.db_model.filter(**query).first()
            if not record:
                return None, "战绩不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return record, "成功"

    @classmethod
    async def get_record_segment_by_filter(cls, greater_round_ranking: int = None, greater_round_score: int = None,
                                            uid: any = None, record_rid: any = None, record_tid: any = None,
                                            replay_msg: str = None, record_sid: any = None, page: int = None,
                                            page_size: int = None):
        """根据条件获取子局战绩列表"""
        try:
            query = {}
            if greater_round_ranking is not None:
                query["round_ranking__gte"] = greater_round_ranking
            if greater_round_score is not None:
                query["greater_round_score_gte"] = greater_round_score
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
            if record_sid is not None:
                if isinstance(record_sid, list):
                    query["record_sid__in"] = record_sid
                else:
                    query["record_sid"] = record_sid
            if replay_msg is not None:
                query["replay_msg"] = replay_msg
            if page and page_size:
                total, _ = await cls.count_record_segment(**query)
                records = []
                if total > 0:
                    offset = (page - 1) * page_size
                    records = await cls.db_model.filter(**query).offset(offset).limit(page_size).values()
                result = cls.page_result(page, page_size, total, records)
            else:
                result = records = await cls.db_model.filter(**query).values()
            if not records:
                return result, "暂无战绩"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return result, "成功"

    @classmethod
    async def count_record_segment(cls, **perms):
        """获取房间战绩数量"""
        try:
            count = await cls.db_model.filter(**perms).count()
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return count, "成功",

    @classmethod
    async def delete_record_game_segment(cls, record_sid: int):
        """删除战绩子局记录"""
        try:
            record = await cls.db_model.del_by_pk(record_sid)
            if not record:
                return record, "删除失败"
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"
        return record, "删除成功"
