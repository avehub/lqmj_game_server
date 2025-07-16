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
    KEY_SESSION = "club_room_template_session_club_id"

    @classmethod
    async def cache_session_set(cls, club_id, value):
        return await cls.conf.rds.set_item(f"{cls.KEY_SESSION}:{club_id}", value)

    @classmethod
    async def cache_session_get(cls, club_id):
        data = await cls.conf.rds.get_item(f"{cls.KEY_SESSION}:{club_id}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data


    @classmethod
    async def cache_session_drop(cls, club_id):
        return await cls.conf.rds.drop_item(f"{cls.KEY_SESSION}:{club_id}")

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
                "total_round": kwargs.get('total_round', 0),
                "cs_type": kwargs.get('cs_type', 0),
                "price": kwargs.get('price', 0),
                "is_friend": kwargs.get('is_friend', 0),
                "is_location": kwargs.get('is_location', 0),
            }

            new_template = await cls.db_model.add_one(template_data)
            if not new_template:
                return False, "模板创建失败"
        except OperationalError as e:
            return False, f"模板创建失败: {str(e)}"
        return new_template.id, "成功"

    @classmethod
    async def delete_template(cls, template_id: int, club_id: int):
        """删除房间模板"""
        try:
            sta = await cls.db_model.filter(id=template_id).delete()
            if not sta:
                return False, "操作失败"
        except OperationalError as e:
            return False, f"模板删除失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def update_template(cls, template_id: int, **kwargs):
        """更新模板信息"""
        try:
            template, e = await cls.get_by_id(template_id)
            if not template:
                return False, e
            valid_fields = ["max_player", "rule_details", "total_round", "price", "cs_type", "play_type", "is_friend", "is_location"]
            update_data = {k: v for k, v in kwargs.items() if k in valid_fields}
            if 'rule_details' in update_data:
                update_data['rule_details'] = json_encode(update_data['rule_details'])
            if update_data:
                await cls.db_model.filter(id=template_id).update(**update_data)
        except OperationalError as e:
            return None, f"模板更新失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def get_by_id(cls, template_id: int):
        """根据ID获取模板详情"""
        try:
            template = await cls.db_model.get_by_pk(template_id)
            if not template:
                return None, "未找到模板"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return template, "成功"

    @classmethod
    async def get_by_club(cls, club_id: int, play_type: any = None):
        """根据茶馆ID获取模板列表"""
        try:
            query = {"club_id": club_id}
            if play_type is not None:
                query["play_type"] = play_type
            templates = await cls.db_model.filter(**query).values()
        except OperationalError as e:
            return [], f"查询失败: {str(e)}"
        return templates, "成功"

    @classmethod
    async def delete_club_all(cls, club_id: int):
        """删除茶馆所有房间模板(解散茶馆)"""
        try:
            query = {
                "club_id": club_id
            }
            data = await cls.db_model.filter(**query).delete()
            if not data:
                return False, "失败"
        except OperationalError as e:
            return False, e
        return True, "成功"
