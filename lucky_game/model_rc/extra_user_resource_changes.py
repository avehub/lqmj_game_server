"""
用户资源变动记录
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ExtraUserResourceChanges
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.const import GoodsItem


class ExtraUserResourceChangesRC(BaseCommonRC):
    db_model = ExtraUserResourceChanges
    tb_name = db_model.sheet_name()

    # 资源类型映射（与User表字段对应）
    CURRENCY_MAP = {
        1: "gold",           # 金币
        2: "diamond",        # 钻石
        3: "room_card",      # 房卡
        4: "yellow_diamond"  # 黄钻
    }

    @classmethod
    async def create_change_record(cls, uid: int, status: int, currency: int, 
                                  num: int, explain: str = ""):
        """创建资源变动记录"""
        try:
            record_data = {
                "uid": uid,
                "status": 1 if status > 0 else 0,  # 1=充值 0=消耗
                "currency": currency,
                "num": abs(num),
                "explain": explain
            }
            
            new_record = await cls.db_model.add_one(record_data)
            return new_record, None
        except OperationalError as e:
            return None, f"记录创建失败: {str(e)}"

    @classmethod
    async def get_records_by_uid(cls, uid: int, limit: int = 50):
        """根据用户ID获取最近记录"""
        try:
            records = await cls.db_model.filter(uid=uid).order_by('-id').limit(limit).all()
            return records, None
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def batch_create_from_asset_change(cls, uid: int, asset_changes: dict, 
                                            status: int, explain: str = ""):
        """批量创建资产变动记录"""
        try:
            records = []
            for field, delta in asset_changes.items():
                # 反向查找对应的currency类型
                currency_type = next((k for k, v in cls.CURRENCY_MAP.items() if v == field), 0)
                if currency_type == 0 or delta == 0:
                    continue
                
                records.append({
                    "uid": uid,
                    "status": status,
                    "currency": currency_type,
                    "num": abs(delta),
                    "explain": explain
                })
            
            if records:
                await cls.db_model.bulk_create([cls.db_model(**r) for r in records])
            return True, None
        except OperationalError as e:
            return None, f"批量创建失败: {str(e)}"
