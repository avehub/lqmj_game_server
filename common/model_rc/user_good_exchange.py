"""
用户兑换记录表
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from common.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import UserGoodExchange
from tortoise.exceptions import OperationalError


class UserGoodExchangeRC(BaseCommonRC):
    db_model = UserGoodExchange
    tb_name = db_model.sheet_name()

    @classmethod
    async def add_exchange(cls, uid: int, phone: str, real_name: str, good_id: int, good_type: int, platform: int, region: str,
                           address: str, num: int = 1, check_status: int = 0, status: int = 0):
        """新增兑换信息"""
        try:
            data = {
                "uid": uid,
                "good_id": good_id,
                "good_type": good_type,
                "platform": platform,
                "phone": phone,
                "real_name": real_name,
                "region": region,
                "address": address,
                "num": num,
                "check_status": check_status,
                "status": status,
                "express_id": 0,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, new

    @classmethod
    async def up_exchange(cls, exchange_id, up_data: dict):
        """更新兑换信息"""
        try:
            query = {"exchange_id": exchange_id}
            valid_fields = {"region", "address", "phone", "real_name", "updated", "express_no"
                            "check_status", "exchange_no", "express_id", "status"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_exchange_filter(cls, uid: int = None, phone: int = None, check_status: int = None, status: int = None,
                                  page: int = None, page_size: int = None):
        """获取兑换信息记录"""
        try:
            query = {}
            if phone is not None:
                query["phone"] = phone
            if uid is not None:
                query["uid"] = uid
            if check_status is not None:
                query["check_status"] = check_status
            if status is not None:
                query["status"] = status
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

