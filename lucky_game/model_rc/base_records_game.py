"""
游戏战绩基础类
"""
from collections import defaultdict
from datetime import datetime, timedelta
from tortoise.exceptions import OperationalError
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey


class BaseRecordsGameRC(BaseCommonRC):

    # 隐藏战绩缓存KEY
    KEY_SESSION_GAME_RECORD_HIDDEN = 'record_hidden_uid'

    @classmethod
    async def hidden_game_record(cls, uid: int):
        """隐藏战绩"""
        try:
            await cls.conf.rds.sadd(f"{cls.KEY_SESSION_GAME_RECORD_HIDDEN}", uid)
        except OperationalError as e:
            return None, f"失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def cancel_hidden_game_record(cls, uid: int):
        """取消隐藏战绩"""
        try:
            await cls.conf.rds.srem(f"{cls.KEY_SESSION_GAME_RECORD_HIDDEN}", uid)
        except OperationalError as e:
            return None, f"失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def is_hidden_game_record(cls, uid: int):
        """查询是否隐藏战绩"""
        try:
            result = await cls.conf.rds.sismember(f"{cls.KEY_SESSION_GAME_RECORD_HIDDEN}", uid)
        except OperationalError as e:
            return None, f"失败: {str(e)}"
        return result, "成功"

    @classmethod
    async def default_time(cls, days: int = 7):
        """生成默认时间范围"""
        now = datetime.now()
        days_ago = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = int(days_ago.timestamp())
        end_time = int(now.timestamp())
        return start_time, end_time

    @classmethod
    async def get_record_list(cls, uid: int = None, club_id: int = None, start_time: int = None, end_time: int = None, cs_type: int = None,
                         page_size: int = None, page: int = None, room_id: int = None):
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
                room_id=room_id,
                club_id=club_id,
            )
            if data.get("total") > 0:
                room_data, _ = await RecordsGameRoomRC.get_record_room_by_filter(
                    record_rid=[item["record_rid"] for item in data["list"]],
                )
                data["list"] = await cls.merge_by_key(data["list"], room_data, "record_rid", ["total_round", "max_player", "start_time", "end_time"])
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_record_segment_list(cls, uid: int, record_rid: int, record_tid: int, start_time: int = None, end_time: int = None):
        """根据条件信息获取战绩详情列表"""
        try:
            record_segment, _ = await RecordsGameSegmentRC.query_record_segment_by_sql(
                record_rid=record_rid,
                record_tid=record_tid,
                start_time=start_time,
                end_time=end_time,
                uid=uid,
                order_field="round_num",
                order_type="ASC",
            )
            data = []
            # 根据当前局数进行数据重组
            if record_segment:
                data = await cls.list_by_group(record_segment, "round_num")
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_game_record(cls, room_id: int = None, uid: int = None,  start_time: int = None,
                             end_time: int = None, cs_type: int = None):
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
            )
            if not data:
                return data, e
            t_ids = []
            data_dict = {}
            for item in data:
                t_ids.append(item["record_tid"])
                data_dict[item["record_tid"]] = item
            segment_data, _ = await RecordsGameSegmentRC.get_record_segment_by_filter(
                record_tid=t_ids,
            )
            for item in data:
                item["segment"] = []
                for segment in segment_data:
                    if item["record_tid"] in data_dict:
                        item["segment"].append(segment)
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return data, "成功"

    @classmethod
    async def get_by_club_id(cls, club_id: int = None, room_id: int = None, start_time: int = None, end_time: int = None,
                             cs_type: any = None, uid: int = None, final_score: int = None, order_field: str = None,
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
                group_field="uid"
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
    async def get_past_list(cls, club_id: int = None, room_id: int = None, start_time: int = None, end_time: int = None,
                                uid: int = None, cs_type: any = None, play_type: any = None, page_size: int = None,
                                final_score: int = None, page: int = None):
        try:
            if start_time is None and end_time is None:
                start_time, end_time = await cls.default_time()
            # 当前用户所在的房间及用户
            result_temp, e = await RecordsGameTotalRC.query_record_total_by_sql(
                uid=uid,
                club_id=club_id,
                room_id=room_id,
                start_time=start_time,
                end_time=end_time,
                cs_type=cs_type,
                play_type=play_type,
                final_score=final_score,
                group_field="record_rid",
                filtration="record_rid"
            )
            if not result_temp:
                return None, e
            record_rids = [item["record_rid"] for item in result_temp]
            result_total, e = await RecordsGameTotalRC.query_record_total_by_sql(
                record_rid=record_rids,
                filtration="uid, record_tid, record_rid, final_score, final_grade, final_ranking, final_status, final_result"
            )
            result_room, e = await RecordsGameRoomRC.get_record_room_by_filter(
                record_rid=record_rids,
                page_size=page_size,
                page=page,
            )
            seat_groups = defaultdict(list)
            for seat in result_total:
                seat_groups[seat["record_rid"]].append(seat)
            for item in result_room["list"] if page else result_room:
                item["room_seat"] = seat_groups.get(item["record_rid"], [])
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return result_room, "成功"

    @classmethod
    async def delete_record_by_rid(cls, record_rid: int):
        """删除游戏战绩记录"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                record = await RecordsGameRoomRC.delete_record_game_room(record_rid)
                if not record:
                    return False, "房间战绩删除失败"
                record = await RecordsGameTotalRC.delete_record_game_total(record_rid=record_rid)
                if not record:
                    return False, "总局战绩删除失败"
                record = await RecordsGameSegmentRC.delete_record_game_segment(record_rid=record_rid)
                if not record:
                    return False, "子局战绩删除失败"
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"
        return True, "删除成功"

    @classmethod
    async def refurbish_game_record(cls, date_time: int = None):
        """刷新(完善)游戏战绩 对date_time时间之前的战绩进行刷新"""
        try:
            # 默认刷新1小时前的数据
            if date_time is None:
                date_time = int((datetime.now() - timedelta(hours=1)).timestamp())
            # 查询1小时前未完善的战绩
            async with in_transaction(connection_name=DbKey.DEFAULT):
                record_room, _ = await RecordsGameRoomRC.get_record_room_by_filter(end_time=date_time)
                if record_room:
                    record_rid = [item["record_rid"] for item in record_room]
                    record_segment, _ = await RecordsGameSegmentRC.query_record_segment_by_sql(
                        record_rid=record_rid,
                        group_field="record_rid, uid",
                        filtration="record_rid, uid, MAX(round_num) AS round_num, MAX(create_time) AS create_time, SUM(round_score) AS total_score, round_result"
                    )
                    for item in record_segment:
                        sta, _ = await RecordsGameRoomRC.update_record_game_room(item["record_rid"], end_time=item["create_time"], round_num=item["round_num"])
                        if not sta:
                            cls.log_info(f"房间战绩更新失败record_rid:{item['record_rid']}")
                        sta, _ = await RecordsGameTotalRC.create_record_game_total(
                            item["record_rid"],
                            item["uid"],
                            0,
                            item["total_score"],
                            0,
                            0,
                            {"uid": item["uid"], "seat_id": item["round_result"]["seat_id"], "total_score": item["total_score"], "zi_mo_count": 0, "an_gang_count": 0,
                             "jie_pao_count": 0, "dian_pao_count": 0, "dian_gang_count": 0, "ming_gang_count": 0,
                             "zhuan_wan_gang_count": 0}
                        )
                        if not sta:
                            cls.log_info(f"总局战绩更新失败record_rid:{item['record_rid']}, uid:{item['uid']}")
        except OperationalError as e:
            return None, f"失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def del_history_game_record(cls, date_time: int = None):
        """删除历史游戏战绩数据"""
        try:
            # 默认删除7天前的数据
            if date_time is None:
                date_time = int((datetime.now() - timedelta(days=7)).timestamp())
            record_room, _ = await RecordsGameRoomRC.get_record_room_by_filter(end_time=date_time)
            if record_room:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    record_rids = [item["record_rid"] for item in record_room]
                    record = await RecordsGameSegmentRC.delete_many_record(record_rids)
                    if not record:
                        return False, "子局战绩删除失败"
                    record = await RecordsGameTotalRC.delete_many_record(record_rids)
                    if not record:
                        return False, "总局战绩删除失败"
                    record_room, msg = await RecordsGameRoomRC.delete_many_record(record_rids)
                    if not record_room:
                        return False, "房间战绩删除失败"
        except OperationalError as e:
            return None, f"失败: {str(e)}"
        return True, "成功"
