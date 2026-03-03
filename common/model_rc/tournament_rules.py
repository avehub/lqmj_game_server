"""
赛事规则表
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from common.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import TournamentRules
from tortoise.exceptions import OperationalError


class TournamentRuleRC(BaseCommonRC):
    db_model = TournamentRules
    tb_name = db_model.sheet_name()
    expired_mode = 0


    @classmethod
    async def cache_session_set(cls, query, value):
        return await cls.conf.rds.set_item(f"{cls.tb_name}:{query}", value)

    @classmethod
    async def cache_session_get(cls, query):
        data = await cls.conf.rds.get_item(f"{cls.tb_name}:{query}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_session_del(cls, query):
        return await cls.conf.rds.del_item(f"{cls.tb_name}:{query}")

    @classmethod
    async def add_rule(cls, rule_content, template_id, rule_type):
        """新增赛事规则"""
        try:
            data = {
                "rule_content": rule_content,
                "template_id": template_id,
                "rule_type": rule_type,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, new

    @classmethod
    async def update_rule(cls, rule_id, up_data: dict):
        """更新赛事规则"""
        try:
            query = {"id": rule_id}
            valid_fields = {"rule_content", "template_id", "rule_type", "updated"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
                await cls.cache_session_del(rule_id)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_rule_filter(cls, rule_id: int = None, template_id: int = None, rule_type: int = None):
        """获取赛事规则"""
        try:
            query = {}
            if rule_id is not None:
                query["id"] = rule_id
            if template_id is not None:
                query["template_id"] = template_id
            if rule_type is not None:
                query["rule_type"] = rule_type
            data = await cls.db_model.filter(**query).values()
            if not data:
                return False, data
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, data

    @classmethod
    async def get_rule_info(cls, rule_id: int = 1, is_content: bool = False):
        """获取赛事规则信息"""
        try:
            result = await cls.cache_session_get(rule_id)
            if not result:
                sta, data = await cls.get_rule_filter(rule_id=rule_id)
                if sta and data:
                    result = data[0]
                    await cls.cache_session_set(rule_id, result)
        except OperationalError as e:
            return None, f"查询失败:{e}"
        if is_content:
            result = result["rule_content"]
        return True if result else False, result

    @classmethod
    async def del_rule(cls, rule_id: int):
        """删除赛事规则"""
        try:
            await cls.db_model.filter(id=rule_id).delete()
            await cls.cache_session_del(rule_id)
        except OperationalError as e:
            return None, f"操作失败:{e}"
        return True, "成功"
