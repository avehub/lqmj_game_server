"""
游戏战绩相关接口
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_rc.base_records_game import BaseRecordsGameRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from common.public.enum_const import ServiceEnum


class RecordBase(GameAuthApi):
    """游戏战绩基础相关方法"""


class UserRecords(RecordBase):
    """用户战绩列表"""

    async def get(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        self.check_int(uid, require=True, p_name="用户ID")
        cs_type = self.check_int(req.args.get("cs_type"), require=False, minval=ServiceEnum.C_WORKERS,
                                 p_name="子服务类型")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        data, e = await BaseRecordsGameRC.get_by_uid(uid=uid, cs_type=cs_type, page=page, page_size=page_size)
        return self.answer(data=data, hint=e)


class TotalRecords(RecordBase):
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


class SegmentRecords(RecordBase):
    """子局战绩列表"""

    async def get(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        record_tid = self.check_int(req.args.get("record_tid"), require=False, p_name="战绩总ID")
        record_rid = self.check_int(req.args.get("record_rid"), require=False, p_name="战绩房间ID")
        replay_msg = self.check_int(req.args.get("replay_msg"), require=False, p_name="视频回看码")
        data, e = await RecordsGameSegmentRC.get_record_segment_by_filter(
            uid=uid,
            record_tid=record_tid,
            record_rid=record_rid,
            replay_msg=replay_msg,
        )
        return self.answer(data=data, hint=e)


class ClubRecords(RecordBase):
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


class UserAggregateRanks(RecordBase):
    """用户战绩总计"""

    async def get(self, req: Request, **kwargs):
        uid = self.check_int(req.args.get("uid"), require=True, p_name="用户ID")
        start_time = self.check_int(req.args.get("start_time"), default=None, require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), default=None, require=False, p_name="结束时间")
        data, e = await BaseRecordsGameRC.get_by_club_id(
            uid=uid,
            start_time=start_time,
            end_time=end_time,
        )
        win = fail = total = grade = 0
        if data:
            for item in data:
                total += 1
                if item["final_grade"] == 1:
                    grade += 1
                if item["final_status"] == 1:
                    win += 1
                else:
                    fail += 1
        result = {
            "total": total,
            "win": win,
            "fail": fail,
            "grade": grade,
        }
        return self.answer(data=result)


class ClubAggregateRanks(RecordBase):
    """茶馆战绩总计"""

    async def get(self, req: Request, **kwargs):
        club_id = self.check_int(req.args.get("club_id"), default=None, require=True, p_name="茶馆ID")
        start_time = self.check_int(req.args.get("start_time"), default=None, require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), default=None, require=False, p_name="结束时间")
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
        }
        return self.answer(data=result)


class ClubRanks(RecordBase):
    """茶馆战绩排行榜"""
    async def get(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        club_id = self.check_int(req.args.get("club_id"), default=None, require=True, p_name="茶馆ID")
        cs_type = self.check_int(req.args.get("cs_type"), default=None, require=False, minval=ServiceEnum.C_WORKERS,
                                 p_name="子服务类型")
        start_time = self.check_int(req.args.get("start_time"), default=None, require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), default=None, require=False, p_name="结束时间")
        final_score = self.check_int(req.args.get("final_score"), default=None, require=False, p_name="最佳分数")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        data, e = await BaseRecordsGameRC.get_by_club_id(
            uid=uid,
            club_id=club_id,
            final_score=final_score,
            cs_type=cs_type,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )
        return self.answer(data=data, hint=e)


class PastRanks(RecordBase):
    """茶馆、我的历史战绩"""
    async def get(self, req: Request, **kwargs):
        uid = self.check_int(req.args.get("uid"), default=None, require=False, p_name="用户ID")
        club_id = self.check_int(req.args.get("club_id"), default=None, require=True, p_name="茶馆ID")
        start_time = self.check_int(req.args.get("start_time"), default=None, require=False, p_name="开始时间")
        end_time = self.check_int(req.args.get("end_time"), default=None, require=False, p_name="结束时间")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        data, e = await BaseRecordsGameRC.get_by_club_id(
            uid=uid,
            club_id=club_id,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )
        return self.answer(data=data, hint=e)

