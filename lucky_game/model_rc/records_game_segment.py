"""
游戏战绩（子局）记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import RecordsGameSegment
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from lucky_game.handler.random_utils import generate_random_string


class RecordsGameSegmentRC(BaseCommonRC):
    db_model = RecordsGameSegment
    tb_name = db_model.sheet_name()

    KEY_GAME_ROOM_ID = 'record_rid'
    KEY_GAME_TOTAL_ID = 'record_sid'
    KEY_GAME_SEGMENT_ID = 'record_sid'

    @classmethod
    async def make_replay_label(cls, length: int = 6) -> str:
        """生成回放标签"""
        while True:
            replay_label = generate_random_string(length)
            count, _ = await cls.count_record_segment(replay_label=replay_label)
            if not count:
                return replay_label

    @classmethod
    async def create_record_game_segment(cls, record_rid: int, uid: int, round_num: int, round_status: int,
                                         round_score: int, round_ranking: int, round_result: dict, replay_msg: str):
        """创建战绩子局记录"""
        try:
            record, _ = await RecordsGameRoomRC.get_record_room_by_id(record_rid)
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
                "replay_label": await cls.make_replay_label(),
                "replay_msg": replay_msg,
            }
            new_record = await cls.db_model.add_one(record_data)
            if not new_record:
                return new_record, "创建失败"
        except OperationalError as e:
            return None, f"创建失败: {str(e)}"
        return new_record, "成功"

    @classmethod
    async def bulk_create_record_game_segment(cls, new_data: list):
        """批量写入战绩子局记录"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                instances = [cls.db_model(**data) for data in new_data]
                await cls.db_model.bulk_create(instances)
        except OperationalError as e:
            return False, f"子战绩入库失败, 原数据: {new_data}, 失败原因:{str(e)}"
        return True, "成功"

    @classmethod
    async def update_record_game_segment(cls, record_rid: int, uid: int, **kwargs):
        """更新子局战绩记录"""
        try:
            up_data = {}
            record_tid = kwargs.get("record_tid")
            replay_label = kwargs.get("replay_label")
            replay_msg = kwargs.get("replay_msg")
            if record_tid:
                up_data["record_tid"] = record_tid
            if replay_label:
                up_data["replay_label"] = replay_label
            if replay_msg:
                up_data["replay_msg"] = replay_msg
            query = {
                "record_rid": record_rid,
                "uid": uid,
            }
            if up_data:
                count, _ = await cls.count_record_segment(**query)
                up_sta = await cls.db_model.update_by_cond(
                    query,
                    up_data,
                    count,
                )
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
            record = await cls.db_model.filter(**query).first().values()
            if not record:
                return None, "战绩不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return record, "成功"

    @classmethod
    async def get_record_segment_by_filter(cls, greater_round_ranking: int = None, greater_round_score: int = None,
                                           uid: any = None, record_rid: any = None, record_tid: any = None,
                                           replay_msg: str = None, record_sid: any = None, page: int = None,
                                           page_size: int = None, group_field: str = None):
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
            if group_field is None:
                group_field = "record_sid"
            if page and page_size:
                total, _ = await cls.count_record_segment(**query)
                records = []
                if total > 0:
                    offset = (page - 1) * page_size
                    records = await cls.db_model.filter(**query).offset(offset).limit(page_size).group_by(group_field).values()
                result = await cls.page_result(page, page_size, total, records)
            else:
                result = records = await cls.db_model.filter(**query).group_by(group_field).values()
            if not records:
                return result, "暂无战绩"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return result, "成功"

    @classmethod
    async def count_record_segment(cls, group_field: str = None, **perms):
        """获取房间战绩数量"""
        try:
            if group_field:
                count = await cls.db_model.filter(**perms).group_by(group_field).count()
            else:
                count = await cls.db_model.filter(**perms).count()
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return count, "成功",

    @classmethod
    async def delete_record_game_segment(cls, record_sid: int = None, record_rid: int = None):
        """删除战绩子局记录"""
        try:
            record = None
            if record_sid:
                record = await cls.db_model.del_by_pk(record_sid)
            if record_rid:
                await cls.db_model.filter(**{"record_rid": record_rid}).delete()
                record = True
            if not record:
                return record, "删除失败"
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"
        return True, "删除成功"

    @classmethod
    async def query_record_segment_by_sql(cls, record_sid: any = None, uid: any = None, cs_type: int = None,
                                         record_rid: any = None, record_tid: any = None, start_time: int = None,
                                         end_time: int = None, final_score: int = None, group_field: str = None,
                                         page: int = None, page_size: int = None, order_field: str = None,
                                          order_type: str = None, filtration: str = "*"):
        """排行榜查询SQL"""
        try:
            where = " 1=1 "
            if record_sid is not None:
                if isinstance(record_sid, list):
                    where += f" AND record_sid in ({','.join(map(str, record_sid))})"
                else:
                    where += f" AND record_sid = {record_sid}"
            if uid is not None:
                if isinstance(uid, list):
                    where += f" AND uid in ({','.join(map(str, uid))})"
                else:
                    where += f" AND uid = {uid}"
            if record_rid is not None:
                if isinstance(record_rid, list):
                    where += f" AND record_rid in ({','.join(map(str, record_rid))})"
                else:
                    where += f" AND record_rid = {record_rid}"
            if record_tid is not None:
                if isinstance(record_tid, list):
                    where += f" AND record_tid in ({','.join(map(str, record_tid))})"
                else:
                    where += f" AND record_tid = {record_tid}"
            if start_time is not None:
                where += f" AND created >= {start_time}"
            if end_time is not None:
                where += f" AND created < {end_time}"
            if cs_type is not None:
                where += f" AND cs_type = {cs_type}"
            if final_score is not None:
                where += f" AND final_score >= {final_score}"
            if order_field is None:
                order_field = "record_sid"
            if order_type is None:
                order_type = "DESC"
            if group_field is None:
                group_field = "record_sid"
            total = 0
            sql = f"SELECT {filtration} FROM {cls.tb_name} WHERE {where} GROUP BY {group_field} ORDER BY {order_field} {order_type}"
            if page and page_size:
                total = await cls.db_model.exec_query(
                    f"SELECT COUNT(*) as total FROM {cls.tb_name} WHERE {where} GROUP BY {group_field}")
                if total > 0:
                    offset = (page - 1) * page_size
                    sql += f" LIMIT {page_size} OFFSET {offset}"
            result = await cls.db_model.exec_query(sql)
            if page and page_size and result:
                result = await cls.page_result(page, page_size, total, result)
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return result, "成功"

    @classmethod
    async def record_by_replay_label(cls, replay_label: str = None, record_sid: str = None):
        """根据回放标签查询战绩子局记录"""
        try:
            record = None
            if record_sid:
                record = await cls.db_model.del_by_pk(record_sid)
            if replay_label:
                record = await cls.db_model.filter(**{"replay_label": replay_label}).first().values()
        except OperationalError as e:
            return False, f"查询失败: {str(e)}"
        return record, "成功"
