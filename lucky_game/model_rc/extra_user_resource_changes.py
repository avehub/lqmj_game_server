"""
用户资源变动记录
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ExtraUserResourceChanges
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.base_user import BaseUserRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from datetime import datetime


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
    OPERATION_MAP = {
        "sub": 0,
        "add": 1,
    }

    @classmethod
    async def change_field(cls):
        """获取变更字段"""
        return list(cls.CURRENCY_MAP.values())

    @classmethod
    async def change_operation(cls):
        """获取变更方式"""
        return list(cls.OPERATION_MAP.keys())

    @classmethod
    async def check_change_field(cls, val: str = None):
        """变更字段校验"""
        return val in await cls.change_field()

    @classmethod
    async def check_change_operation(cls, val: str = None):
        """变更方式校验"""
        return val in await cls.change_operation()

    @classmethod
    async def create_change_record(cls, uid: int, operation: str, currency: int, num: int, explain: str = ""):
        """创建资源变动记录"""
        try:
            record_data = {
                "uid": uid,
                "status": cls.OPERATION_MAP.get(operation),
                "currency": currency,
                "num": abs(num),
                "explain": explain
            }
            new_record = await cls.db_model.add_one(record_data)
            return new_record, None
        except OperationalError as e:
            return None, f"记录创建失败: {str(e)}"

    @classmethod
    async def bulk_register_change_record(cls, uid: int, gifts: dict, register_type: int = 0, explain: str = "注册奖励"):
        """用户注册批量创建资源变动记录"""
        try:
            if not gifts:
                return True, None
            tmp = {v: k for k, v in cls.CURRENCY_MAP.items()}
            record_data = []
            date_time = int(datetime.now().timestamp())
            for currency, num in gifts.items():
                if num == 0:
                    continue
                record_data.append(
                    {
                        "uid": uid,
                        "status": 1,
                        "currency": tmp[currency],
                        "num": abs(num),
                        "explain": explain,
                        "created": date_time,
                    }
                )
            await cls.db_model.bulk_create([cls.db_model(**r) for r in record_data])
        except OperationalError as e:
            return None, f"记录创建失败: {str(e)}"
        return True, "成功"


    @classmethod
    async def get_records_by_uid(cls, uid: int, limit: int = 50):
        """根据用户ID获取最近记录"""
        try:
            records = await cls.db_model.filter(uid=uid).order_by('-id').limit(limit).all()
            return records, None
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"

    @classmethod
    async def change_user_resource(cls, uid: int, change_field: str, change_value: int, operation: str = 'add', explain: str = ""):
        """用户资源变更"""
        print("change_field", change_field)
        print("values", cls.CURRENCY_MAP.values())
        if change_field not in cls.CURRENCY_MAP.values():
            return False, "无效的资源类型"
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                u_sta, e = await BaseUserRC.update_user_int_field(uid, change_field, change_value, operation)
                if not u_sta:
                    return False, "资源变更失败"
                currency = next((k for k, v in cls.CURRENCY_MAP.items() if v == change_field), 0)
                c_sta, e = await cls.create_change_record(uid, operation, currency, change_value, explain)
                if not c_sta:
                    return False, "资源变更生成失败"
        except OperationalError as e:
            return False, f"操作失败: {str(e)}"
        return True, "成功"

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

