"""
茶馆房间模板
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ClubRoomTemplates
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode, json_parse

class ClubRoomTemplatesRC(BaseCommonRC):
    db_model = ClubRoomTemplates
    tb_name = db_model.sheet_name()

    KEY_TEMPLATE_ID = 'template_id'
    KEY_SESSION = "club_room_template_session"

    @classmethod
    async def cache_session_set(cls, club_id, value):
        await cls.conf.rds.set_item(f"{cls.KEY_SESSION}:{club_id}", value)

    @classmethod
    async def cache_session_get(cls, club_id):
        return await cls.conf.rds.get_item(f"{cls.KEY_SESSION}:{club_id}")

    @classmethod
    async def cache_session_drop(cls, club_id):
        await cls.conf.rds.drop_item(f"{cls.KEY_SESSION}:{club_id}")

    @classmethod
    async def create_template(cls, club_id: int, platform: int, play_type: int, 
                             rule_details: dict, max_player: int, **kwargs):
        """创建茶馆房间模板"""
        try:
            template_data = {
                "club_id": club_id,
                "platform": platform,
                "play_type": play_type,
                "rule_details": json_encode(rule_details),
                "max_player": max_player,
                "current_players": kwargs.get('current_players', 0),
                "cs_type": kwargs.get('cs_type', 0)
            }
            
            new_template = await cls.db_model.add_one(template_data)
            if not new_template:
                return False, "模板创建失败"
        except OperationalError as e:
            return False, f"模板创建失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def delete_template(cls, template_id: int, club_id: int):
        """删除房间模板"""
        try:
            sta = await cls.db_model.filter(id=template_id).delete()
            if not sta:
                return False, "操作失败"
            await cls.cache_session_drop(club_id)
        except OperationalError as e:
            return None, f"模板删除失败: {str(e)}"
        return True, None

    @classmethod
    async def update_template(cls, template_id: int, **kwargs):
        """更新模板信息"""
        try:
            valid_fields = ["max_player", "rule_details", "platform", "current_players"]
            update_data = {k: v for k, v in kwargs.items() if k in valid_fields}
            
            if 'rule_details' in update_data:
                update_data['rule_details'] = json_encode(update_data['rule_details'])
                
            if update_data:
                await cls.db_model.filter(id=template_id).update(**update_data)
                await cls.cache_session_drop(template_id)
            return True, None
        except OperationalError as e:
            return None, f"模板更新失败: {str(e)}"

    @classmethod
    async def get_by_id(cls, template_id: int):
        """根据ID获取模板详情"""
        try:
            cached = await cls.cache_session_get(template_id)
            if cached:
                return cached, None
                
            template = await cls.db_model.get_or_none(id=template_id)
            if template:
                await cls.cache_session_set(template_id, template)
            return template, None
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def get_by_club(cls, club_id: int, play_type: int = None):
        """根据茶馆ID获取模板列表"""
        try:
            query = {"club_id": club_id}
            if play_type is not None:
                query["play_type"] = play_type
                
            templates = await cls.db_model.filter(**query).values()
            if not templates:
                return [], "未找到模板"
        except OperationalError as e:
            return [], f"查询失败: {str(e)}"
        return templates, None
