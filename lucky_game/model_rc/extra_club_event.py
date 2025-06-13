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
    KEY_SESSION = "club_event_session"

    EVENT_TYPE = {
        'FUND_RECHARGE': 1,  # 基金充值
        'FUND_CONSUME': 2,   # 基金消耗
        'APPROVAL_LOG': 3    # 入馆审批
    }

    @classmethod
    async def cache_session_set(cls, event_id, value):
        return await cls.conf.rds.set_item(f"{cls.KEY_SESSION}:{event_id}", value)

    @classmethod
    async def cache_session_get(cls, event_id):
        data = await cls.conf.rds.get_item(f"{cls.KEY_SESSION}:{event_id}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_session_drop(cls, event_id):
        return await cls.conf.rds.drop_item(f"{cls.KEY_SESSION}:{event_id}")

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
            await cls.cache_session_set(new_event.id, new_event)
            return new_event, None
        except OperationalError as e:
            return None, f"事件记录创建失败: {str(e)}"

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
