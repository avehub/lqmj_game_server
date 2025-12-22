"""
用户赛事积分表
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from common.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import TournamentUserPoints
from tortoise.exceptions import OperationalError


class TournamentUserPointRC(BaseCommonRC):
    db_model = TournamentUserPoints
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
    async def add_user_point(cls, cycle_id, uid, score, ticket: int = 0):
        """新增模板"""
        try:
            data = {
                "cycle_id": cycle_id,
                "uid": uid,
                "score": score,
                "ticket": ticket,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, new

    @classmethod
    async def up_user_point(cls, cycle_id, uid, up_data: dict):
        """更新模板"""
        try:
            query = {"cycle_id": cycle_id, "uid": uid}
            has = await cls.db_model.filter(**query).first()
            if not has:
                score = up_data.get("score", 0)
                ticket = up_data.get("ticket", 0)
                await cls.add_user_point(cycle_id, uid, score, ticket)
            else:
                valid_fields = {"score", "ticket", "rank_num", "updated"}
                update_data = {k: v for k, v in up_data.items() if k in valid_fields}
                if update_data:
                    if has.score:
                        update_data["score"] = has.score + update_data["score"]
                    if has.ticket:
                        update_data["ticket"] = has.ticket + update_data["ticket"]
                    await cls.db_model.filter(**query).update(**update_data)
                    await cls.cache_session_del(f"{cycle_id}:{uid}")
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_point_filter(cls, uid: int = None, cycle_id: int = None, page: int = None, page_size: int = None):
        """获取模板记录"""
        try:
            query = {}
            if cycle_id is not None:
                query["cycle_id"] = cycle_id
            if uid is not None:
                query["uid"] = uid
            order_field = "-id"
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
    async def get_user_point(cls, cycle_id: int, uid: int):
        """获取模板信息"""
        try:
            result = await cls.cache_session_get(f"{cycle_id}:{uid}")
            if result:
                return True, result
            query = {"cycle_id": cycle_id, "uid": uid}
            result = data = await cls.db_model.filter(**query).first()
            if not data:
                return False, "用户未报名"
        except OperationalError as e:
            return None, f"查询失败:{e}"
        if data:
            await cls.cache_session_set(f"{cycle_id}:{uid}", result)
        return True if result else False, result

    @classmethod
    async def del_user_point(cls, cycle_id: int, uid: int):
        """删除模板"""
        try:
            await cls.db_model.filter(cycle_id=cycle_id, uid=uid).delete()
            await cls.cache_session_del(f"{cycle_id}:{uid}")
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, "成功"
