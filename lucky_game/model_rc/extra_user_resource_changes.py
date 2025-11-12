"""
用户资源变动记录
"""
import decimal

from tortoise.exceptions import OperationalError

from lucky_game.const import ReasonCostGold
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
    async def create_change_record(cls, uid: int, operation: str, currency: int, num: [int, decimal.Decimal], explain: str = "", reason: int = None):
        """创建资源变动记录"""
        try:
            if num > 0:
                record_data = {
                    "uid": uid,
                    "status": cls.OPERATION_MAP.get(operation),
                    "currency": currency,
                    "num": abs(num),
                    "explain": explain,
                    "reason": reason if reason else 0,
                }
                new_record = await cls.db_model.add_one(record_data)
                cls.conf.log.info(f"创建资源变动记录{new_record}")
                return new_record, "成功"
        except OperationalError as e:
            return None, f"记录创建失败: {str(e)}"
        return {}, "成功"

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
    async def change_user_resource(cls, uid: int, change_field: str, change_value: [int, decimal.Decimal], operation: str = 'add', explain: str = "", reason: int = None):
        """用户资源变更"""
        if change_value <= 0:
            return False, "无效的资源数量"
        if change_field not in cls.CURRENCY_MAP.values():
            return False, "无效的资源类型"
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                u_sta, e = await BaseUserRC.update_user_int_field(uid, change_field, change_value, operation)
                if not u_sta:
                    return False, "资源变更失败"
                currency = next((k for k, v in cls.CURRENCY_MAP.items() if v == change_field), 0)
                if not explain and reason is not None:
                    reason_enum = ReasonCostGold.find_member_by_val(reason)
                    explain = reason_enum.phrase
                c_sta, e = await cls.create_change_record(uid, operation, currency, change_value, explain, reason)
                if not c_sta:
                    return False, "资源变更生成失败"
            cls.conf.log.info(f"资源变更：uid {uid} uid {uid} change_field {change_field} operation {operation} change_value {change_value}")
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

    @classmethod
    async def get_resource_changes_filter(cls, uid: any = None, status: int = None, start_time: int = None, end_time: int = None,
                               currency: int = None, count: bool = False, page: int = None, page_size: int = None):
        """获取订单记录"""
        try:
            query = {}
            if uid is not None:
                if isinstance(uid, list):
                    query["uid__in"] = uid
                else:
                    query["uid"] = uid
            if status is not None:
                query["status"] = status
            if currency is not None:
                query["currency"] = currency
            if start_time is not None:
                query["created__gte"] = start_time
            if end_time is not None:
                query["created__lte"] = end_time
            order_field = "-id"
            if count:
                result = await cls.db_model.filter(**query).count()
            else:
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