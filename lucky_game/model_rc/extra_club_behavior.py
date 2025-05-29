"""
茶馆行为记录信息
"""

from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ExtraClubBehavior
from lucky_game.model_rc.base_rc import BaseCommonRC


class ExtraClubBehaviorRC(BaseCommonRC):
    db_model = ExtraClubBehavior
    tb_name = db_model.sheet_name()

    TYPE = (1, 2, 3) #类型：1加入茶馆申请 2小黑屋 3隔离
    STATUS = (0, 1, 99) #状态，类型==1：0未审批 1拒绝 99通过，类型==2/3:99成功

    @classmethod
    async def _type_re_status(cls, behavior_type):
        """类型和状态对应关系"""
        status = 0
        if behavior_type == 2 or 3:
            status = 99
        return status

    @classmethod
    async def create_club_behavior(cls, behavior_type: int, uid: int, club_id: int, check_uid: int = 0):
        """新增茶馆行为"""
        try:
            row = await cls.db_model.add_one({
                "uid": uid,
                "club_id": club_id,
                "type": behavior_type,
                "status": await cls._type_re_status(behavior_type),
                "check_uid": check_uid,
            })
            if not row:
                return False, "创建失败"
        except OperationalError as e:
            return False, e
        return row.id, "成功"

    @classmethod
    async def update_club_behavior(cls, behavior_id: int, up_data: dict):
        """更新茶馆行为"""
        try:
            data, e = await cls.get_behavior_by_id(behavior_id)
            if not data:
                return False, e
            sta = await cls.db_model.update_by_pk(behavior_id, up_data, data)
            if not sta:
                return False, "更新失败"
        except OperationalError as e:
            return False, e
        return True, "更新成功"

    @classmethod
    async def get_behavior_by_id(cls, behavior_id: int):
        """根据ID获取茶馆行为"""
        try:
            result = await cls.db_model.get_by_pk(behavior_id)
            if not result:
                return result, "茶馆行为不存在"
        except OperationalError as e:
            return False, e
        return result, "成功"

