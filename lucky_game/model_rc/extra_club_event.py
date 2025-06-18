"""
茶馆日常事件记录
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ExtraClubEvent
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_parse


class ExtraClubEventRC(BaseCommonRC):
    db_model = ExtraClubEvent
    tb_name = db_model.sheet_name()

    KEY_EVENT_ID = 'event_id'

    EVENT_TYPE = {
        'FUND_RECHARGE': 1,  # 基金充值
        'FUND_CONSUME': 2,   # 基金消耗
        'APPROVAL_LOG': 3    # 入馆审批
    }
    EVENT_MSG = {
        1: "{name}玩家（ID：{uid}）为茶馆充值基金{price}",
        2: "{name}玩家（ID：{uid}）消耗{price}基金创建了{cs_type}玩法（房间号：{room_id}）",
        3: "记录{check_name}管理员（ID：{check_uid}）通过{name}玩家（ID：{uid}）加入茶馆",
    }

    @classmethod
    async def create_event(cls, club_id: int, event_type: int, uid: int, explain: str):
        """创建茶馆事件记录"""
        try:
            event_data = {
                "club_id": club_id,
                "type": event_type,
                "uid": uid,
                "explain": explain
            }
            
            new_event = await cls.db_model.add_one(event_data)
            return new_event, None
        except OperationalError as e:
            return None, f"事件记录创建失败: {str(e)}"

    @classmethod
    async def delete_event(cls, club_id: int, event_type: int, uid: int):
        """删除茶馆事件记录"""
        try:
            query = {
                "club_id": club_id,
                "type": event_type,
                "uid": uid,
            }
            event = await cls.db_model.filter(**query).order_by("id").first()
            if not event:
                return True, "未找到相关事件"
            return await cls.delete_event_by_id(event.id)
        except OperationalError as e:
            return None, f"事件记录创建失败: {str(e)}"

    @classmethod
    async def delete_event_by_id(cls, event_id: int):
        """通过ID删除茶馆事件记录"""
        try:
            sta = await cls.db_model.del_by_pk(event_id)
            if not sta:
                return sta, "删除失败"
        except OperationalError as e:
            return None, f"事件记录创建失败: {str(e)}"
        return sta, "成功"

    @classmethod
    async def get_by_club(cls, club_id: int, limit: int = 50):
        """根据茶馆ID查询事件"""
        try:
            events = await cls.db_model.filter(club_id=club_id).order_by('-id').limit(limit).all()
            return events, None
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def get_by_type(cls, event_type: int, limit: int = 100):
        """根据事件类型查询"""
        try:
            events = await cls.db_model.filter(type=event_type).order_by('-id').limit(limit).all()
            return events, None
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def get_by_user(cls, uid: int, limit: int = 50):
        """根据用户ID查询相关事件"""
        try:
            events = await cls.db_model.filter(uid=uid).order_by('-id').limit(limit).all()
            return events, None
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
