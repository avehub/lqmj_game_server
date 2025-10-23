"""
广告事件记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.log import RecordsAdEvent
from lucky_game.model_rc.base_rc import BaseCommonRC


class RecordsAdEventRC(BaseCommonRC):
    db_model = RecordsAdEvent
    tb_name = db_model.sheet_name()

    @classmethod
    async def create_record_ad(cls, uid: int, campaign_type: int, type_id: int, platform: int, os: str, ip: str, status: int = 99, ):
        """创建广告事件记录"""
        try:
            record_data = {
                "uid": uid,
                "campaign_type": campaign_type,
                "type_id": type_id,
                "platform": platform,
                "os": os,
                "ip": ip,
                "status": status,
            }
            new_record = await cls.db_model.add_one(record_data)
        except OperationalError as e:
            return None, f"创建失败: {str(e)}"
        return new_record, "成功"