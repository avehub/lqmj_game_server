"""
赛事周期表 (月度赛事实例)
"""
from datetime import datetime

from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from common.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import TournamentCycle
from tortoise.exceptions import OperationalError


class TournamentCycleRC(BaseCommonRC):
    db_model = TournamentCycle
    tb_name = db_model.sheet_name()
    expired_mode = 0

    CYCLE_STATUS_UNSTART = 0  # 未开始
    CYCLE_STATUS_STARTING = 1  # 进行中
    CYCLE_STATUS_END = 2  # 结束
    CYCLE_STATUS_SETTLE = 3  # 结算



    @classmethod
    async def cache_session_set(cls, query, value):
        # TODO 设置周期赛事积分过期时间
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
    async def add_cycle(cls, cycle_name, template_id, reward_id,cycle_year, cycle_month, cycle_start_date, cycle_end_date, status):
        """新增赛事周期"""
        try:
            data = {
                "cycle_name": cycle_name,
                "template_id": template_id,
                "reward_id": reward_id,
                "cycle_year": cycle_year,
                "cycle_month": cycle_month,
                "cycle_start_date": cycle_start_date,
                "cycle_end_date": cycle_end_date,
                "status": status,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, new

    @classmethod
    async def update_cycle(cls, cycle_id, up_data: dict):
        """更新赛事周期"""
        try:
            query = {"id": cycle_id}
            valid_fields = {"cycle_name", "template_id", "reward_id", "cycle_year", "cycle_month", "updated", "cycle_start_date", "cycle_end_date", "status"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            cls.conf.log.info("赛季更新cycle_id：", cycle_id)
            cls.conf.log.info("赛季更新update_data：", update_data)
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
                await cls.cache_session_del(cycle_id)
                await cls.conf.rds.drop_item("cycle_id")
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_cycle_filter(cls, cycle_id: int = None, status: int = None, cycle_year: int = None, reward_id: int = None,
                                  template_id: int = None, page: int = None, page_size: int = None, cycle_month: int = None):
        """获取赛事周期记录"""
        try:
            query = {}
            if cycle_id is not None:
                query["id"] = cycle_id
            if reward_id is not None:
                query["reward_id"] = reward_id
            if status is not None:
                query["status"] = status
            if template_id is not None:
                query["template_id"] = template_id
            if cycle_year is not None:
                query["cycle_year"] = cycle_year
            if cycle_month is not None:
                query["cycle_month"] = cycle_month
            order_field = "id"
            result = None
            if page and page_size:
                total = await cls.db_model.filter(**query).count()
                data = []
                if total > 0:
                    offset = (page - 1) * page_size
                    data = await cls.db_model.filter(**query).order_by(order_field).offset(
                        offset).limit(page_size).values()
                    data = await cls.serialize_dates(data)
                result = await cls.page_result(page, page_size, total, data)
            else:
                data = await cls.db_model.filter(**query).order_by(order_field).values()
                if data:
                    result = await cls.serialize_dates(data)
            if not data:
                return False, result
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, result

    @classmethod
    async def get_cycle_info(cls, cycle_id: int):
        """获取赛事周期信息"""
        try:
            result = await cls.cache_session_get(cycle_id)
            if result:
                return True, result
            sta, data = await cls.get_cycle_filter(cycle_id=cycle_id)
        except OperationalError as e:
            return None, f"查询失败:{e}"
        if data:
            result = data[0]
            await cls.cache_session_set(cycle_id, result)
        return True if result else False, result

    @classmethod
    async def del_cycle(cls, cycle_id: int):
        """删除赛事周期"""
        try:
            await cls.db_model.filter(id=cycle_id).delete()
            await cls.cache_session_del(cycle_id)
        except OperationalError as e:
            return None, f"操作失败:{e}"
        return True, "成功"

    @classmethod
    async def get_current_cycle_id(cls) -> int:
        """ 获取当前赛事ID """
        cycle_id = await cls.conf.rds.get_item("cycle_id")
        if isinstance(cycle_id, bytes):
            cycle_id = json_parse(cycle_id.decode())
        if not cycle_id:
            sta, data = await cls.get_cycle_filter(status=1)
            cycle_id = data[0]["id"] if data else 0
            ex_time = 86400 - (tool_dt.cur_time()-tool_dt.day_begin())
            await cls.conf.rds.set_item("cycle_id", cycle_id, ex_time=ex_time)
        return cycle_id

    @classmethod
    async def check_cycle_status(cls, cycle_id: int) -> tuple:
        """ 检查当前赛事是否开始 """
        sta, cycle = await cls.get_cycle_info(cycle_id)
        if not sta or not cycle:
            return False, "无该赛事场次"
        now = tool_dt.cur_time()
        start_time = datetime.strptime(cycle["cycle_start_date"] + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(cycle["cycle_end_date"] + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        start_time_tamp = int(start_time.timestamp())
        end_time_tamp = int(end_time.timestamp())
        if start_time_tamp > now or now > end_time_tamp:
            return False, "该赛事未开始"
        return True, "赛事正在进行中"

