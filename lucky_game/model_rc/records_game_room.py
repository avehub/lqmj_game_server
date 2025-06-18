"""
游戏战绩（房间）记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import RecordsGameRoom
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.game_rooms import GameRoomsRC
from nsanic.libs.tool import json_encode, json_parse


class RecordsGameRoomRC(BaseCommonRC):
    db_model = RecordsGameRoom
    tb_name = db_model.sheet_name()

    KEY_GAME_ROOM_ID = 'record_rid'

    @classmethod
    async def create_record_game_room(cls, room_id: int, start_time: int, end_time: int = 0):
        """创建房间战绩记录"""
        try:
            game_room, _ = await GameRoomsRC.get_game_room_by_room_id(room_id)
            record_data = {
                "room_id": room_id,
                "club_id": game_room["club_id"],
                "play_type": game_room["play_type"],
                "cs_type": game_room["cs_type"],
                "pay_type": game_room["pay_type"],
                "creator": game_room["creator"],
                "total_round": game_room["total_round"],
                "max_player": game_room["max_player"],
                "rule_details": game_room["rule_details"],
                "price": game_room["price"],
                "start_time": start_time,
                "end_time": end_time,
            }
            new_record = await cls.db_model.add_one(record_data)
            if not new_record:
                return new_record, "创建失败"
        except OperationalError as e:
            return None, f"创建失败: {str(e)}"
        return new_record, "成功"

    @classmethod
    async def update_record_game_room(cls, record_rid: int, **kwargs):
        """更新房间战绩记录"""
        try:
            record, _ = await cls.get_record_room_by_id(record_rid)
            if not record:
                return None, "战绩不存在"
            end_time = kwargs.get("end_time")
            if end_time:
                up_sta = await cls.db_model.update_by_pk(record_rid, {"end_time": end_time}, old_data=record)
                if not up_sta:
                    return up_sta, "更新失败"
        except OperationalError as e:
            return None, f"更新失败: {str(e)}"
        return True, "成功"

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
                                        , end_time: any = None, play_type: any = None, cs_type: any = None,
                                        creator: any = None, record_rid: any = None, order_field: any = None,
                                        page: int = None, page_size: int = None):
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
            if end_time is not None:
                query["end_time__lt"] = end_time
            if order_field is None:
                order_field = "record_rid"
            if page and page_size:
                total, _ = await cls.count_record_room(**query)
                records = []
                if total > 0:
                    offset = (page - 1) * page_size
                    records = await cls.db_model.filter(**query).order_by(order_field).limit(page_size).offset(offset).values()
                result = await cls.page_result(page, page_size, total, records)
            else:
                result = records = await cls.db_model.filter(**query).order_by(order_field).values()
            if not records:
                return result, "暂无战绩"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return result, "成功"

    @classmethod
    async def count_record_room(cls, **perms):
        """获取房间战绩数量"""
        try:
            count = await cls.db_model.filter(**perms).count()
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return count, "成功",

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
