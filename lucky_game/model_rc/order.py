"""用户参与活动相关"""
import decimal
from datetime import datetime
import random
from typing import Type, Union, Tuple, List, Dict, Any
from tortoise.exceptions import OperationalError

from lucky_game.const import OrderStatus
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import Orders


class OrderRC(BaseCommonRC):
    db_model = Orders
    tb_name = db_model.sheet_name()

    @classmethod
    async def add_order(cls, uid: int, good_id: int, sku: str, platform: int, amount: decimal.Decimal, currency: int,
                        pay_mode: int, order_no: str, num: int, out_order_no: str = '',
                        status: int = OrderStatus.WAIT_PAY, prepay_id: str = "", explain: str = ""):
        """新增订单"""
        try:
            data = {
                "uid": uid,
                "good_id": good_id,
                "sku": sku,
                "platform": platform,
                "amount": amount,
                "currency": currency,
                "pay_mode": pay_mode,
                "order_no": order_no,
                "num": num,
                "out_order_no": out_order_no if out_order_no else "",
                "status": status if status else 0,
                "prepay_id": prepay_id if prepay_id else "",
                "explain": explain if explain else "",
            }
            cls.conf.log.info("插入订单表信息: ", data)
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return new, "成功"

    @classmethod
    async def up_order(cls, up_data: dict, order_no: str):
        """更新订单"""
        try:
            query = {"order_no": order_no}
            valid_fields = {"out_order_no", "prepay_id", "status", "explain", "updated"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_order_filter(cls, uid: any = None, sku: any = None, good_id: any = None, status: int = None,
                               platform: any = None, start_time: int = None, end_time: int = None,
                               order_no: str = False, count: bool = False):
        """获取订单记录"""
        try:
            query = {}
            if uid is not None:
                if isinstance(uid, list):
                    query["uid__in"] = uid
                else:
                    query["uid"] = uid
            if good_id is not None:
                if isinstance(good_id, list):
                    query["good_id__in"] = good_id
                else:
                    query["good_id"] = good_id
            if sku is not None:
                if isinstance(sku, list):
                    query["sku__in"] = sku
                else:
                    query["sku"] = sku
            if platform is not None:
                if isinstance(platform, list):
                    query["platform__in"] = platform
                else:
                    query["platform"] = platform
            if status is not None:
                query["status"] = status
            if start_time is not None:
                query["created__gte"] = start_time
            if end_time is not None:
                query["created__lte"] = end_time
            if order_no is not None:
                query["order_no"] = order_no
            if count:
                data = await cls.db_model.filter(**query).count()
            else:
                data = await cls.db_model.filter(**query).order_by("-id").values()
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return data, "成功"

    @classmethod
    async def get_order_info(cls, order_no: str):
        """获取订单信息"""
        try:
            data, msg = await cls.get_order_filter(order_no=order_no)
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return data[0], msg
