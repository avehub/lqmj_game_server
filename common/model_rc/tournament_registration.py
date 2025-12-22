"""
用户报名表
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from common.model_rc.base_rc import BaseCommonRC
from common.model_rc.tournament_cycle import TournamentCycleRC
from lucky_game.model_db.main import TournamentRegistration
from tortoise.exceptions import OperationalError


class TournamentRegistrationRC(BaseCommonRC):
    db_model = TournamentRegistration
    tb_name = db_model.sheet_name()
    expired_mode = 0

    # 报名状态: 1 - 已报名, 2 - 已取消, 3 - 已确认参赛
    REGISTER_STATUS_WAIT = 1
    REGISTER_STATUS_CANCEL = 2
    REGISTER_STATUS_CONFIRM = 3

    # 报名类型: 1 - 个人报名, 2 - 邀请报名
    REGISTER_TYPE_SINGLE = 1
    REGISTER_TYPE_INVITE = 2



    @classmethod
    async def cache_session_add(cls, query, value):
        return await cls.conf.rds.sadd(f"{cls.tb_name}:{query}", value)

    @classmethod
    async def cache_session_get(cls, query):
        """查看当前赛季报名用户IDS"""
        data = await cls.conf.rds.smembers(f"{cls.tb_name}:{query}")
        return [p.decode('utf-8') for p in data]

    @classmethod
    async def cache_session_del(cls, query, value):
        return await cls.conf.rds.srem(f"{cls.tb_name}:{query}", value)

    @classmethod
    async def get_uid_registration(cls, uid: int, cycle_id: int = None) -> bool:
        """查看用户是否报名当前赛季"""
        if cycle_id is None:
            cycle_id = await TournamentCycleRC.get_current_cycle_id()
        return await cls.conf.rds.sismember(f"{cls.tb_name}:{cycle_id}", uid)

    @classmethod
    async def add_registration(cls, cycle_id, uid, register_type, register_time: int = None, pid: int = 0,
                               register_status: int = None):
        """新增报名用户"""
        try:
            data = {
                "cycle_id": cycle_id,
                "uid": uid,
                "register_type": register_type,
                "register_time": register_time if register_time else tool_dt.cur_time(),
                "pid": pid,
                "register_status": cls.REGISTER_STATUS_WAIT,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
            await cls.cache_session_add(cycle_id, uid)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, new

    @classmethod
    async def update_registration(cls, registration_id, up_data: dict):
        """更新报名用户"""
        try:
            query = {"id": registration_id}
            valid_fields = {"cycle_id", "uid", "pid", "register_type", "register_time", "updated", "register_status"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_registration_filter(cls, uid: int = None, register_status: int = None, register_type: int = None,
                                      pid: int = None,
                                      cycle_id: int = None, registration_id: int = None):
        """获取报名用户记录"""
        try:
            query = {}
            if registration_id is not None:
                query["id"] = registration_id
            if register_status is not None:
                query["register_status"] = register_status
            if uid is not None:
                query["uid"] = uid
            if pid is not None:
                query["pid"] = pid
            if cycle_id is not None:
                query["cycle_id"] = cycle_id
            if register_type is not None:
                query["register_type"] = register_type
            order_field = "-id"
            result = data = await cls.db_model.filter(**query).order_by(order_field).values()
            if not data:
                return False, result
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, result

    @classmethod
    async def get_registration_info(cls, cycle_id: int):
        """获取报名用户列表"""
        try:
            result = await cls.cache_session_get(cycle_id)
            if result:
                return True, result
            data, msg = await cls.get_registration_filter(cycle_id=cycle_id)
        except OperationalError as e:
            return None, f"查询失败:{e}"
        if data:
            result = data[0]
        return True if result else False, result

    @classmethod
    async def del_registration(cls, cycle_id: int, uid: int):
        """删除报名用户"""
        try:
            await cls.db_model.filter(cycle_id=cycle_id, uid=uid).update(register_status=cls.REGISTER_STATUS_CANCEL)
            await cls.cache_session_del(cycle_id, uid)
        except OperationalError as e:
            return None, f"操作失败:{e}"
        return True, "成功"
