"""
赛事场次表 (周赛/总决赛)
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from common.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import TournamentRound
from tortoise.exceptions import OperationalError


class TournamentRoundRC(BaseCommonRC):
    db_model = TournamentRound
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
    async def add_round(cls, round_name, cycle_id, round_number, start_time, end_time, register_start_time, \
                        max_participants, current_participants, register_end_time, point_weight, status):
        """新增赛事场次"""
        try:
            data = {
                "round_name": round_name,
                "cycle_id": cycle_id,
                "round_number": round_number,
                "start_time": start_time,
                "end_time": end_time,
                "register_start_time": register_start_time,
                "register_end_time": register_end_time,
                "status": status,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, new

    @classmethod
    async def update_round(cls, round_id, up_data: dict):
        """更新赛事场次"""
        try:
            query = {"id": round_id}
            valid_fields = {"round_name", "cycle_id", "round_number", "start_time", "updated", "end_time", "register_start_time", "register_end_time", "status"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
                await cls.cache_session_del(round_id)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_round_filter(cls, cycle_id: int = None, status: int = None, round_number: int = None,
                                  count: bool = False, round_id: int = None, page: int = None, page_size: int = None):
        """获取赛事场次记录"""
        try:
            query = {}
            if round_id is not None:
                query["id"] = round_id
            if status is not None:
                query["status"] = status
            if cycle_id is not None:
                query["cycle_id"] = cycle_id
            if round_number is not None:
                query["round_number"] = round_number
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
    async def get_round_info(cls, round_id: int):
        """获取赛事场次信息"""
        try:
            result = await cls.cache_session_get(round_id)
            if result:
                return True, result
            data, msg = await cls.get_round_filter(round_id=round_id)
            if data:
                result = data[0]
                await cls.cache_session_set(round_id, result)
        except OperationalError as e:
            return None, f"操作失败:{e}"
        return True if result else False, result

    @classmethod
    async def del_round(cls, round_id: int):
        """删除赛事场次"""
        try:
            await cls.db_model.filter(id=round_id).delete()
            await cls.cache_session_del(round_id)
        except OperationalError as e:
            return None, f"操作失败:{e}"
        return True, "成功"
