"""
用户赛事积分表
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse

from c_services.const.cs_enum_const import CmdWorkers
from common.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import TournamentCycle, TournamentUserPoints
from tortoise.exceptions import OperationalError
from common.public.conf import ENV
from common.model_rc.tournament_cycle import TournamentCycleRC


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
            if ENV != "prod":
                ticket = 100
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
        """更新赛事积分"""
        try:
            query = {"cycle_id": cycle_id, "uid": uid}
            has = await cls.db_model.filter(**query).first()
            score = up_data.get("score", 0)
            ticket = up_data.get("ticket", 0)
            if not has:
                await cls.add_user_point(cycle_id, uid, score, ticket)
                replay_msg_data = {
                    "uid": uid,
                    "cycle_id": cycle_id,
                    "total_points": score,
                }
            else:
                valid_fields = {"score", "ticket", "updated"}
                update_data = {k: v for k, v in up_data.items() if k in valid_fields}
                if update_data:
                    if score:
                        update_data["score"] = has.score + score
                    if ticket:
                        if has.ticket < 0:
                            has.ticket = 0
                        update_data["ticket"] = has.ticket + ticket
                    await cls.db_model.filter(**query).update(**update_data)
                    await cls.cache_session_del(f"{cycle_id}:{uid}")

                replay_msg_data = {
                    "uid": uid,
                    "cycle_id": cycle_id,
                    "total_points": update_data.get("score", 0),
                }
            # 更新排行榜
            await cls.push_task2worker(CmdWorkers.UPDATE_CYCLE_POINT_LEADERBOARD, replay_msg_data)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_point_filter(cls, uid: int = None, cycle_id: int = None, page: int = None, page_size: int = None):
        """获取赛事用户积分列表"""
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
            result = data = await cls.db_model.filter(**query).first().values()
            if not data:
                return False, "用户未报名"
        except OperationalError as e:
            return None, f"查询失败:{e}"
        if data:
            await cls.cache_session_set(f"{cycle_id}:{uid}", result)
        return True if result else False, result

    @classmethod
    async def get_user_ticket(cls, uid: int):
        """获取模板信息"""
        try:
            query = {"uid": uid}
            data = await cls.db_model.filter(**query).order_by("-id").values()
            if not data:
                return False, "用户未报名"
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, data[0]

    @classmethod
    async def del_user_point(cls, cycle_id: int, uid: int = None):
        """删除模板"""
        try:
            await cls.db_model.filter(cycle_id=cycle_id, uid=uid).delete()
            await cls.cache_session_del(f"{cycle_id}:{uid}")
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, "成功"

    @classmethod
    async def update_int_field(cls, uid: int, field_name: str, value: int, operation: str = 'add'):
        """
        门票积分变更

        Args:
            uid (int): 用户ID
            field_name (str): 要修改的字段名
            value (int | Decimal): 修改的值
            operation (str): 操作类型，'add' 或 'sub'，默认为'add'

        Returns:
            tuple: (bool, str) - (操作结果, 消息)
        """
        if operation not in ['add', 'sub']:
            return False, "无效的操作类型，只支持'add'或'sub'"
        try:
            # 获取当前赛季周期ID
            cycle_id = await TournamentCycleRC.get_current_cycle_id()
            sta, data = await cls.get_user_point(cycle_id, uid)
            if not data:
                return False, "数据不存在"

            # 获取当前字段值
            current_value = data[field_name]
            # 计算新值
            if operation == 'add':
                new_value = current_value + value
            else:
                new_value = current_value - value
            if new_value < 0:
                new_value = 0
            # 更新数据
            update_data = {field_name: new_value}
            up = await cls.db_model.update_by_pk(data["id"], update_data)
            if not up:
                return False, "更新失败"
            if field_name == "score":
                replay_msg_data = {
                    "uid": uid,
                    "cycle_id": cycle_id,
                    "total_points": new_value,
                }
                # 更新排行榜
                await cls.push_task2worker(CmdWorkers.UPDATE_CYCLE_POINT_LEADERBOARD, replay_msg_data)
            await cls.cache_session_del(f"{cycle_id}:{uid}")
        except OperationalError as e:
            return False, f"更新失败：{str(e)}"
        return True, "更新成功"