"""
游戏战绩相关接口
"""
import ast

from sanic import Request
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.base_records_game import BaseRecordsGameRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from common.public.enum_const import ServiceEnum, StaCode
from datetime import datetime, timedelta
from c_services.cs_mahjong.room_fczj import RoomFCZJ
from c_services.cs_mahjong.const import HuType


class UserRecords(GameAuthApi):
    """用户战绩列表"""

    async def get(self, req: Request, **kwargs):
        uid = self.check_int(req.args.get("uid"), default=None, require=False, p_name="用户ID")
        club_id = self.check_int(req.args.get("club_id"), default=None, require=True, p_name="茶馆ID")
        cs_type = self.check_int(req.args.get("cs_type"), require=False, minval=ServiceEnum.C_WORKERS,p_name="子服务类型")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        data, e = await BaseRecordsGameRC.get_record_list(uid=uid, club_id=club_id, cs_type=cs_type, page=page, page_size=page_size)
        return self.answer(data=data, hint=e)


class TotalRecords(GameAuthApi):
    """总局战绩列表"""

    async def get(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        room_id = self.check_int(req.args.get("room_id"), require=False, p_name="房间ID")
        cs_type = self.check_int(req.args.get("cs_type"), require=False, minval=ServiceEnum.C_WORKERS,
                                 p_name="子服务类型")
        start_time = self.check_int(req.args.get("start_time"), require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), require=False, p_name="结束时间")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        data, e = await BaseRecordsGameRC.get_by_room_id(
            room_id=room_id,
            uid=uid,
            cs_type=cs_type,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )
        total = complete = score = 0
        if data["total"] > 0:
            for item in data["list"]:
                total += 1
                score += item["final_score"]
        result = {
            "data": data,
            "total": total,
            "complete": complete,
            "score": score,
        }
        return self.answer(data=result, hint=e)


class SegmentRecords(GameAuthApi):
    """子局战绩列表"""

    async def get(self, req: Request, **kwargs):
        uid = self.check_int(req.args.get("uid"), require=False, p_name="用户ID")
        record_tid = self.check_int(req.args.get("record_tid"), require=False, p_name="战绩总ID")
        record_rid = self.check_int(req.args.get("record_rid"), require=False, p_name="战绩房间ID")
        start_time = self.check_int(req.args.get("start_time"), require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), require=False, p_name="结束时间")
        data, e = await BaseRecordsGameRC.get_record_segment_list(
            uid=uid,
            record_tid=record_tid,
            record_rid=record_rid,
            start_time=start_time,
            end_time=end_time,
        )
        return self.answer(data=data, hint=e)


class ClubRecords(GameAuthApi):
    """茶馆战绩列表"""

    async def get(self, req: Request, **kwargs):
        uid = self.check_int(req.args.get("uid"), default=None, require=False, p_name="用户ID")
        club_id = self.check_int(req.args.get("club_id"), default=None, require=True, p_name="茶馆ID")
        room_id = self.check_int(req.args.get("room_id"), default=None, require=False, p_name="房间ID")
        cs_type = self.check_int(req.args.get("cs_type"), default=None, require=False, minval=ServiceEnum.C_WORKERS,
                                 p_name="子服务类型")
        start_time = self.check_int(req.args.get("start_time"), default=None, require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), default=None, require=False, p_name="结束时间")
        incomplete = self.check_int(req.args.get("incomplete"), default=None, require=False, p_name="只看完整局")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        data, e = await BaseRecordsGameRC.get_by_club_id(
            uid=uid,
            club_id=club_id,
            room_id=room_id,
            cs_type=cs_type,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )
        total = complete = score = 0
        if data:
            for item in data:
                total += 1
                score += item["final_score"]
        result = {
            "list": data,
            "total": total,
            "complete": complete,
            "score": score,
        }
        return self.answer(data=result, hint=e)


class UserAggregateRanks(GameAuthApi):
    """用户战绩总计"""

    async def get(self, req: Request, **kwargs):
        uid = self.check_int(req.args.get("uid"), require=True, p_name="用户ID")
        club_id = self.check_int(req.args.get("club_id"), require=False, p_name="茶馆ID")
        cs_type = self.check_str(req.args.get("cs_type"), require=False, p_name="子服务类型")
        start_time = self.check_int(req.args.get("start_time"), default=None, require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), default=None, require=False, p_name="结束时间")
        if start_time is None:
            # today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            # start_time = int(today_start.timestamp())
            seven_days_ago = datetime.now() - timedelta(days=7)
            start_time = int(seven_days_ago.timestamp())
        if end_time is None:
            end_time = int(datetime.now().timestamp())
        if cs_type and not isinstance(cs_type, list):
            cs_type = ast.literal_eval(cs_type)
        data, e = await BaseRecordsGameRC.get_by_club_id(
            uid=uid,
            club_id=club_id,
            start_time=start_time,
            end_time=end_time,
            cs_type=cs_type,
        )
        score = 0
        win = 0
        fail = 0
        total = 0
        grade = 0
        max_multiple = 0
        max_hu_type = HuType.PING_HU
        max_hu_name = ""
        if data:
            for item in data:
                total += 1
                score += item["final_score"]
                if item["final_grade"] == 1:
                    grade += 1
                if item["final_status"] == 1:
                    win += 1
                else:
                    fail += 1
                max_multiple = max(max_multiple, item["final_result"].get("max_multiple", 0))
                if item["final_result"].get("max_hu_type"):
                    max_hu_type, max_hu_name = RoomFCZJ.compare_hu_type(max_hu_type, item["final_result"].get("max_hu_type"))
        result = {
            "total": total,
            "score": score,
            "win": win,
            "fail": fail,
            "grade": grade,
            "end_time": end_time,
            "max_multiple": max_multiple,
            "max_hu_type": max_hu_type,
            "max_hu_name": max_hu_name,
        }
        return self.answer(data=result)


class ClubAggregateRanks(GameAuthApi):
    """茶馆战绩总计"""

    async def get(self, req: Request, **kwargs):
        club_id = self.check_int(req.args.get("club_id"), default=None, require=True, p_name="茶馆ID")
        start_time = self.check_int(req.args.get("start_time"), default=None, require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), default=None, require=False, p_name="结束时间")
        if start_time is None:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = int(today_start.timestamp())
        if end_time is None:
            end_time = int(datetime.now().timestamp())
        data, e = await RecordsGameRoomRC.get_record_room_by_filter(
            club_id=club_id,
            start_time=start_time,
            end_time=end_time,
        )
        room_card = total = player = 0
        creator = set()
        if data:
            for item in data:
                total += 1
                creator.add(item["creator"])
                room_card += item["price"]
                player += item["max_player"]
        result = {
            "room_card": room_card,
            "total": total,
            "player": player,
            "creator": len(creator),
            "end_time": end_time,
        }
        return self.answer(data=result)


class ClubRanks(GameAuthApi):
    """茶馆战绩排行榜"""
    async def get(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        club_id = self.check_int(req.args.get("club_id"), default=None, require=True, p_name="茶馆ID")
        cs_type = self.check_int(req.args.get("cs_type"), default=None, require=False, minval=ServiceEnum.C_WORKERS,
                                 p_name="子服务类型")
        play_type = self.check_str(req.args.get("play_type"), default=None, require=False, p_name="玩法类型")
        start_time = self.check_int(req.args.get("start_time"), default=None, require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), default=None, require=False, p_name="结束时间")
        final_score = self.check_int(req.args.get("final_score"), default=None, require=False, p_name="最佳分数")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        order_field = self.check_str(req.args.get("order_field"), require=False, default="total_score", p_name="排序字段")
        order_type_val = self.check_int(req.args.get("order_type"), require=False, minval=1, maxval=2, p_name="排序方式")
        order_type = "DESC"
        if order_type_val == 2:
            order_type = "ASC"

        data, e = await RecordsGameTotalRC.query_record_total_by_sql(
            club_id=club_id,
            final_score=final_score,
            play_type=play_type,
            cs_type=cs_type,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
            order_field=order_field,
            order_type=order_type,
            group_field="uid",
            filtration="uid, record_rid, club_id, COUNT(final_status) AS total_status, SUM(final_score) AS total_score, SUM(final_grade) AS total_grade, SUM(price) AS total_price"
        )
        return self.answer(data=data, hint=e)


class PastRanks(GameAuthApi):
    """茶馆、我的历史战绩"""
    async def get(self, req: Request, **kwargs):
        uid = self.check_int(req.args.get("uid"), default=None, require=False, p_name="用户ID")
        club_id = self.check_int(req.args.get("club_id"), default=None, require=False, p_name="茶馆ID")
        start_time = self.check_int(req.args.get("start_time"), default=None, require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), default=None, require=False, p_name="结束时间")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        play_type = self.check_str(req.args.get("play_type"), default=None, require=False, p_name="玩法类型")
        cs_type = self.check_str(req.args.get("cs_type"), default=None, require=False, p_name="子服务类型")
        final_score = self.check_int(req.args.get("final_score"), default=None, require=False, p_name="最佳分数")
        if cs_type and not isinstance(cs_type, list):
            cs_type = ast.literal_eval(cs_type)
        if play_type and not isinstance(play_type, list):
            play_type = ast.literal_eval(play_type)

        data, e = await BaseRecordsGameRC.get_past_list(
            uid=uid,
            club_id=club_id,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
            play_type=play_type,
            cs_type=cs_type,
            final_score=final_score,
        )
        return self.answer(data=data, hint=e)

class SegmentRecordsByReplayLabel(GameAuthApi):
    """根据回放标签查询战绩子局记录"""
    async def get(self, req: Request, **kwargs):
        replay_label = self.check_str(req.args.get("replay_label"), default=None, require=True, p_name="回放标签")
        data, e = await RecordsGameSegmentRC.record_by_replay_label(replay_label=replay_label)
        if not data:
            return self.answer(StaCode.FAIL, hint="回放标签不存在")
        return self.answer(data=data, hint=e)

