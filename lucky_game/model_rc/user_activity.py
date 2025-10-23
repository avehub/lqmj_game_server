"""用户参与活动相关"""
from datetime import datetime
import random
from typing import Type, Union, Tuple, List, Dict, Any
from tortoise.exceptions import OperationalError
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import LogUserActivity
from lucky_game.model_db.main import UserActivityProgress
from lucky_game.model_db.main import AwardGains


class LogUserActivityRC(BaseCommonRC):
    db_model = LogUserActivity
    tb_name = db_model.sheet_name()

    @classmethod
    async def add_log(cls, uid, act_id, join_time: int = None, pay_type: int = None, award_type: int = None):
        """添加用户活动记录"""
        try:
            new = await cls.db_model.add_one({
                "uid": uid,
                "join_time": join_time if join_time else int(datetime.now().timestamp()),
                "act_id": act_id,
                "pay_type": pay_type if pay_type else 0,
                "award_type": award_type if award_type else 0
            })
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"添加失败:{e}"
        return new, "添加成功"

    @classmethod
    async def activity_frequency(cls, uid: int = None, act_id: int = None, pay_type: int = None, start_time: int = None,
                                 end_time: int = None, award_type: int = None, count: bool = False) -> Union[
        Tuple[None, str], Tuple[bool, Any]]:
        """获取用户参与活动次数"""
        try:
            query = {}
            if uid is not None:
                query["uid"] = uid
            if act_id is not None:
                query["act_id"] = act_id
            if pay_type is not None:
                query["pay_type"] = pay_type
            if start_time is not None:
                query["join_time__gte"] = start_time
            if end_time is not None:
                query["join_time__lte"] = end_time
            if count:
                data = await cls.db_model.filter(**query).count()
            else:
                data = await cls.db_model.filter(**query).order_by("-id").values("id", "uid", "activity_id",
                                                                                 "join_time", "pay_type")
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, data


class UserActivityProgressRC(BaseCommonRC):
    db_model = UserActivityProgress
    tb_name = db_model.sheet_name()
    STATUS_FINISH = 99

    @classmethod
    async def add_progress(cls, uid: int, act_id: int, current_value: int, deadline: int, status: int = None,
                           time_node: int = None, join_time: int = None):
        """新增活动进度"""
        try:
            new = await cls.db_model.add_one({
                "uid": uid,
                "act_id": act_id,
                "current_value": current_value,
                "deadline": deadline,
                "join_time": join_time if join_time else int(datetime.now().timestamp()),
                "time_node": time_node if time_node else 0,
                "status": status if status else 0
            })
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return new, "成功"

    @classmethod
    async def up_progress(cls, up_data: dict, progress_id: int = None, uid: int = None, act_id: int = None,
                          status: int = None,
                          ):
        """更新活动进度"""
        try:
            query = {}
            if uid is not None:
                query["uid"] = uid
            if act_id is not None:
                query["activity_id"] = act_id
            if status is not None:
                query["status"] = status
            if progress_id is not None:
                query["progress_id"] = progress_id
            valid_fields = {"current_value", "deadline", "status", "time_node", "join_time", "created"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_activity_progress(cls, uid: int = None, act_id: int = None, status: int = None,
                                    start_time: int = None, end_time: int = None, count: bool = False):
        """获取用户参与活动次数"""
        try:
            query = {}
            if uid is not None:
                query["uid"] = uid
            if act_id is not None:
                query["act_id"] = act_id
            if status is not None:
                query["status"] = status
            if start_time is not None:
                query["created__gte"] = start_time
            if end_time is not None:
                query["created__lte"] = end_time
            if count:
                data = await cls.db_model.filter(**query).count()
            else:
                data = await cls.db_model.filter(**query).order_by("-progress_id").values()
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, data

    @classmethod
    async def get_activity_progress_once(cls, uid: int = None, act_id: int = None, status: int = None,
                                    start_time: int = None, end_time: int = None, deadline: int = None):
        """获取用户参与活动一次"""
        try:
            query = {}
            if uid is not None:
                query["uid"] = uid
            if act_id is not None:
                query["act_id"] = act_id
            if status is not None:
                query["status"] = status
            if deadline is not None:
                query["deadline"] = deadline
            if start_time is not None:
                query["created__gte"] = start_time
            if end_time is not None:
                query["created__lte"] = end_time
            data = await cls.db_model.filter(**query).first().values()
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, data

class AwardGainsRC(BaseCommonRC):
    db_model = AwardGains
    tb_name = db_model.sheet_name()

    @classmethod
    async def add_gains(cls, uid: int, act_id: int, type_id: int, reward_type: int, status: int = None,
                           remark: dict = None):
        """新增活动进度"""
        try:
            new = await cls.db_model.add_one({
                "uid": uid,
                "act_id": act_id,
                "reward_type": reward_type,
                "type_id": type_id,
                "remark": remark if remark else "",
                "status": status if status else 0
            })
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return new, "成功"

    @classmethod
    async def up_gains(cls, up_data: dict, gain_id: any = None, uid: int = None, act_id: int = None,
                          status: int = None, type_id: int = None,
                          ):
        """更新活动进度"""
        try:
            query = {}
            if uid is not None:
                query["uid"] = uid
            if act_id is not None:
                query["act_id"] = act_id
            if status is not None:
                query["status"] = status
            if type_id is not None:
                query["type_id"] = type_id
            if gain_id is not None:
                if isinstance(gain_id, list):
                    query["id__in"] = gain_id
                else:
                    query["id"] = gain_id
            valid_fields = {"status", "remark", "updated"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_award_gains(cls, uid: int = None, act_id: int = None, status: int = None, type_id: any = None,
                                    start_time: int = None, end_time: int = None, count: bool = False):
        """获取用户参与活动次数"""
        try:
            query = {}
            if uid is not None:
                query["uid"] = uid
            if act_id is not None:
                query["act_id"] = act_id
            if type_id is not None:
                if isinstance(type_id, list):
                    query["type_id__in"] = type_id
                else:
                    query["type_id"] = type_id
            if status is not None:
                query["status"] = status
            if start_time is not None:
                query["created__gte"] = start_time
            if end_time is not None:
                query["created__lte"] = end_time
            if count:
                data = await cls.db_model.filter(**query).count()
            else:
                data = await cls.db_model.filter(**query).order_by("-id").values()
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, data
