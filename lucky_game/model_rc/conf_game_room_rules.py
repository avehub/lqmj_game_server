"""
游戏房间规则配置
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ConfGameRoomRules
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode, json_parse

class ConfGameRoomRulesRC(BaseCommonRC):
    db_model = ConfGameRoomRules
    tb_name = db_model.sheet_name()

    KEY_RULE_ID = 'rule_id'
    KEY_SESSION = "game_room_rule_session"

    @classmethod
    async def cache_session_set(cls, rule_id, value):
        await cls.conf.rds.set_item(f"{cls.KEY_SESSION}:{rule_id}", value)

    @classmethod
    async def cache_session_get(cls, rule_id):
        return await cls.conf.rds.get_item(f"{cls.KEY_SESSION}:{rule_id}")

    @classmethod
    async def cache_session_drop(cls, rule_id):
        await cls.conf.rds.drop_item(f"{cls.KEY_SESSION}:{rule_id}")

    @classmethod
    async def create_rule(cls, pip: int, rule_type: int, rule_name: str, rule_info: dict):
        """创建房间规则配置"""
        try:
            rule_data = {
                "pip": pip,
                "rule_type": rule_type,
                "rule_name": rule_name,
                "rule_info": json_encode(rule_info)
            }
            
            new_rule = await cls.db_model.add_one(rule_data)
            await cls.cache_session_set(new_rule.id, new_rule)
            return new_rule, None
        except OperationalError as e:
            return None, f"规则创建失败: {str(e)}"

    @classmethod
    async def delete_rule(cls, rule_id: int):
        """删除规则配置"""
        try:
            await cls.db_model.filter(id=rule_id).delete()
            await cls.cache_session_drop(rule_id)
            return True, None
        except OperationalError as e:
            return None, f"规则删除失败: {str(e)}"

    @classmethod
    async def update_rule(cls, rule_id: int, **kwargs):
        """更新规则配置"""
        try:
            valid_fields = ["pip", "rule_type", "rule_name", "rule_info"]
            update_data = {k: v for k, v in kwargs.items() if k in valid_fields}
            
            if 'rule_info' in update_data:
                update_data['rule_info'] = json_encode(update_data['rule_info'])
                
            if update_data:
                await cls.db_model.filter(id=rule_id).update(**update_data)
                await cls.cache_session_drop(rule_id)
            return True, None
        except OperationalError as e:
            return None, f"规则更新失败: {str(e)}"

    @classmethod
    async def get_by_id(cls, rule_id: int):
        """根据ID获取规则详情"""
        try:
            cached = await cls.cache_session_get(rule_id)
            if cached:
                return cached, None
                
            rule = await cls.db_model.get_or_none(id=rule_id)
            if rule:
                await cls.cache_session_set(rule_id, rule)
            return rule, None
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def get_by_parent(cls, pip: int):
        """根据父级ID获取子规则列表"""
        try:
            rules = await cls.db_model.filter(pip=pip).all()
            if not rules:
                return rules, "暂无规则配置"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return rules, "成功"

    @classmethod
    async def get_by_child(cls, ids: list):
        """根据IDS获取配置列表"""
        try:
            rules = await cls.db_model.filter(pip__in=ids).all()
            if not rules:
                return rules, "暂无规则配置"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return rules, "成功"

    @classmethod
    async def _child(cls, rule: list):
        """根据结果自动获取子集配置列表"""
        child_ids = [val['id'] for val in rule]
        children, e = await cls.get_by_child(child_ids)
        if children:
            for val in rule:
                rule["child"] = []
                for child in children:
                    if val['id'] == child['pip']:
                        rule["child"].append(child)
                    await cls._child(child)
        return rule
    @classmethod
    async def get_by_type(cls, rule_type: int):
        """根据规则类型获取配置列表"""
        try:
            rules = await cls.db_model.filter(rule_type=rule_type).all()
            if not rules:
                return rules, "暂无规则配置"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return rules, "成功"


    @classmethod
    async def get_all(cls, pip: int = None, rule_type: int = None):
        """获取所有规则列表"""
        result = []
        try:
            query = {}
            if pip is not None:
                query["pip"] = pip
            if rule_type is not None:
                query["type"] = rule_type
            rules, e = await cls.db_model.filter(**query).values()
            if not rules:
                return result, f"查询失败: {str(e)}"
            result = await cls._child(rules)
        except OperationalError as e:
            return result, f"查询失败: {str(e)}"
        return result, "成功"
