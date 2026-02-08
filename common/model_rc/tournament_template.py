"""
赛事模板表 (支持多赛事并行)
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from common.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import TournamentTemplate
from tortoise.exceptions import OperationalError


class TournamentTemplateRC(BaseCommonRC):
    db_model = TournamentTemplate
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
    async def add_template(cls, template_name, template_type, cycle_type, rounds_per_cycle, online_rounds, final_round_offline, qualifier_count, status):
        """新增模板"""
        try:
            data = {
                "template_name": template_name,
                "template_type": template_type,
                "cycle_type": cycle_type,
                "rounds_per_cycle": rounds_per_cycle,
                "online_rounds": online_rounds,
                "final_round_offline": final_round_offline,
                "qualifier_count": qualifier_count,
                "status": status,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, new

    @classmethod
    async def update_template(cls, template_id, up_data: dict):
        """更新模板"""
        try:
            query = {"id": template_id}
            valid_fields = {"template_name", "template_type", "cycle_type", "rounds_per_cycle", "updated", "online_rounds", "final_round_offline", "qualifier_count", "status"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
                await cls.cache_session_del(template_id)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_template_filter(cls, template_type: int = None, status: int = None, cycle_type: int = None,
                                  count: bool = False, template_id: int = None, page: int = None, page_size: int = None):
        """获取模板记录"""
        try:
            query = {}
            if template_id is not None:
                query["template_id"] = template_id
            if status is not None:
                query["status"] = status
            if template_type is not None:
                query["template_type"] = template_type
            if cycle_type is not None:
                query["cycle_type"] = cycle_type
            order_field = "-id"
            if count:
                result = await cls.db_model.filter(**query).count()
            else:
                if page and page_size:
                    total = await cls.db_model.filter(**query).count()
                    data = []
                    if total > 0:
                        offset = (page - 1) * page_size
                        data = await cls.db_model.filter(**query).order_by(order_field).offset(
                            offset).limit(page_size).values()
                    result = await cls.page_result(page, page_size, total, data)
                else:
                    result = data = await cls.db_model.filter(**query).order_by(order_field).values()
                if not data:
                    return False, result
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, result

    @classmethod
    async def get_template_info(cls, template_id: int):
        """获取模板信息"""
        try:
            result = await cls.cache_session_get(template_id)
            if result:
                return True, result
            data, msg = await cls.get_template_filter(template_id=template_id)
        except OperationalError as e:
            return None, f"查询失败:{e}"
        if data:
            result = data[0]
            await cls.cache_session_set(template_id, result)
        return True if result else False, result

    @classmethod
    async def del_template(cls, template_id: int):
        """删除模板"""
        try:
            await cls.db_model.filter(template_id=template_id).delete()
            await cls.cache_session_del(template_id)
        except OperationalError as e:
            return None, f"操作失败:{e}"
        return True, "成功"
