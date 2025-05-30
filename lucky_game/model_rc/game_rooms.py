"""
游戏房间模型
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import GameRooms
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode


class GameRoomsRC(BaseCommonRC):
    db_model = GameRooms
    tb_name = db_model.sheet_name()

    KEY_ROOM_ID = 'room_id'
    KEY_CLUB_ID = 'club_id'

    @classmethod
    async def create_game_room(cls, platform: int, creator: int, rule_details: dict,
                               cs_type: int, club_id: int = 0, **kwargs):
        total_round = kwargs.get("total_round", 0)
        if club_id > 0:
            # TODO 茶馆创建房间规则校验
            pass

        """创建游戏房间"""
        try:
            room_data = {
                "club_id": club_id,
                "creator": creator,
                "platform": platform,
                "cs_type": cs_type,
                "total_round": total_round,
                "rule_details": json_encode(rule_details) if rule_details else "{}",
                "max_players": 1,
                "current_players": 0,
            }

            new_room = await cls.db_model.add_one(room_data)
            if not new_room:
                return None, "房间创建失败"
        except OperationalError as e:
            return None, f"房间创建失败: {str(e)}"
        return new_room.id, "成功"

    @classmethod
    async def delete_game_room(cls, room_id: int):
        """删除游戏房间"""
        try:
            room = await cls.db_model.get_or_none(id=room_id)
            if not room:
                return None, "房间不存在"

            await cls.db_model.filter(id=room_id).delete()
        except OperationalError as e:
            return False, f"房间删除失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def update_game_room(cls, room_id: int, **kwargs):
        """更新房间信息"""
        try:
            room = await cls.db_model.get_or_none(id=room_id)
            if not room:
                return None, "房间不存在"

            valid_fields = ["status", "player_count", "rule_details"]
            update_data = {k: v for k, v in kwargs.items() if k in valid_fields}

            if update_data:
                await cls.db_model.filter(id=room_id).update(**update_data)
        except OperationalError as e:
            return False, f"房间更新失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def get_game_room_by_id(cls, room_id: int):
        """根据ID获取房间详情"""
        try:
            room = await cls.db_model.get_or_none(id=room_id)
            if not room:
                return None, "房间不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return room, "成功"

    @classmethod
    async def get_game_rooms_by_filter(cls, club_id: int = None, status: int = None, creator: int = None):
        """多条件查询房间列表"""
        try:
            query = {}
            if club_id is not None:
                query["club_id"] = club_id
            if status is not None:
                query["status"] = status
            if creator is not None:
                query["creator"] = creator

            rooms = await cls.db_model.filter(**query).order_by("status").values()
            if not rooms:
                return [], "未找到符合条件的房间"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return rooms, "成功"