"""
游戏房间记录
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ExtraGameRoom
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode, json_parse


class ExtraGameRoomRC(BaseCommonRC):
    db_model = ExtraGameRoom
    tb_name = db_model.sheet_name()

    KEY_RECORD_ID = 'record_id'
    KEY_ROOM_ID = 'room_id'
    KEY_SESSION = "extra_game_room_session"

    @classmethod
    async def cache_session_set(cls, room_id, value):
        await cls.conf.rds.set_item(f"{cls.KEY_SESSION}:{room_id}", value)

    @classmethod
    async def cache_session_get(cls, room_id):
        return await cls.conf.rds.get_item(f"{cls.KEY_SESSION}:{room_id}")

    @classmethod
    async def cache_session_drop(cls, room_id):
        await cls.conf.rds.drop_item(f"{cls.KEY_SESSION}:{room_id}")

    @classmethod
    async def create_extra_game_room(cls, room_id: int, club_id: int, room_rule: dict, 
                                    cs_type: int, play_type: int, **kwargs):
        """创建房间记录"""
        try:
            room_data = {
                "room_id": room_id,
                "club_id": club_id,
                "room_rule": json_encode(room_rule),
                "cs_type": cs_type,
                "play_type": play_type,
                "current_players": 0,
                "room_uids": ""
            }
            # 关联game_rooms表房间
            if 'game_room' in kwargs:
                room_data.update({
                    "current_players": kwargs['game_room'].current_players,
                    "room_uids": kwargs['game_room'].uid
                })
            
            new_record = await cls.db_model.add_one(room_data)
            await cls.cache_session_set(room_id, new_record)
            return new_record, None
        except OperationalError as e:
            return None, f"扩展记录创建失败: {str(e)}"

    @classmethod
    async def delete_by_room_id(cls, room_id: int):
        """根据房间ID删除记录"""
        try:
            await cls.db_model.filter(room_id=room_id).delete()
            await cls.cache_session_drop(room_id)
            return True, None
        except OperationalError as e:
            return None, f"记录删除失败: {str(e)}"

    @classmethod
    async def update_by_room_id(cls, room_id: int, **kwargs):
        """更新房间记录信息"""
        try:
            record = await cls.db_model.get_or_none(room_id=room_id)
            if not record:
                return None, "扩展记录不存在"

            # 处理玩家UID列表
            if 'room_uids' in kwargs:
                if isinstance(kwargs['room_uids'], list):
                    kwargs['room_uids'] = ",".join(map(str, kwargs['room_uids']))
                
            valid_fields = ["current_players", "room_uids", "room_rule"]
            update_data = {k: v for k, v in kwargs.items() if k in valid_fields}
            
            if update_data:
                await cls.db_model.filter(room_id=room_id).update(**update_data)
                await cls.cache_session_drop(room_id)
            return True, None
        except OperationalError as e:
            return None, f"记录更新失败: {str(e)}"

    @classmethod
    async def get_by_room_id(cls, room_id: int):
        """根据房间ID获取扩展记录"""
        try:
            cached = await cls.cache_session_get(room_id)
            if cached:
                return cached, None
                
            record = await cls.db_model.get_or_none(room_id=room_id)
            if record:
                # 转换玩家UID为列表
                if record.room_uids:
                    record.room_uids = [int(uid) for uid in record.room_uids.split(",") if uid]
                await cls.cache_session_set(room_id, record)
            return record, None
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def get_by_club_id(cls, club_id: int):
        """根据茶馆ID获取扩展记录列表"""
        try:
            records = await cls.db_model.filter(club_id=club_id).all()
            # 转换所有记录的玩家UID为列表
            for r in records:
                if r.room_uids:
                    r.room_uids = [int(uid) for uid in r.room_uids.split(",") if uid]
            return records, None
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
