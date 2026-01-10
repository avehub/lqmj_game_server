"""
注销用户记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import LogoutUser
from lucky_game.model_rc.base_rc import BaseCommonRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from datetime import datetime


class LogoutUserRC(BaseCommonRC):
    db_model = LogoutUser
    tb_name = db_model.sheet_name()


    @classmethod
    async def create_logout_user(cls, **kwargs):
        """创建战绩总局记录"""
        try:
            data = {
                "uid": kwargs.get("uid"),
                "name": kwargs.get("name"),
                "avatar": kwargs.get("avatar"),
                "sex": kwargs.get("sex"),
                "phone": kwargs.get("phone"),
                "email": kwargs.get("email"),
                "address": kwargs.get("address"),
                "id_card": kwargs.get("id_card"),
                "real_name": kwargs.get("real_name"),
                "pi": kwargs.get("pi"),
                "discount": kwargs.get("discount"),
                "gold": kwargs.get("gold"),
                "diamond": kwargs.get("diamond"),
                "room_card": kwargs.get("room_card"),
                "yellow_diamond": kwargs.get("yellow_diamond"),
                "vip": kwargs.get("vip"),
                "platform": kwargs.get("platform"),
                "dev_ident": kwargs.get("dev_ident"),
                "ip": kwargs.get("ip"),
                "region": kwargs.get("region"),
                "country": kwargs.get("country"),
                "openid": kwargs.get("openid"),
                "unionid": kwargs.get("unionid"),
                "wechat": kwargs.get("wechat"),
                "apple_id": kwargs.get("apple_id"),
                "future_value": kwargs.get("future_value"),
                "status": kwargs.get("status"),
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "创建失败"
        except OperationalError as e:
            return False, f"失败原因:{str(e)}"
        return True, new

    @classmethod
    async def get_logout_user(cls, uid: int):
        """根据ID获取单条总局战绩"""
        try:
            record = await cls.db_model.filter(uid=uid).first().values()
            if not record:
                return None, "不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return record, "成功"

    @classmethod
    async def get_logout_user_by_filter(cls, uid: any = None, status: int = None, start_time: int = None,
                                         end_time: int = None,):
        """根据条件获取注销用户列表"""
        try:
            query = {}
            if uid is not None:
                if isinstance(uid, list):
                    query["uid__in"] = uid
                else:
                    query["uid"] = uid
            if status is not None:
                query["status"] = status
            if start_time is not None:
                query["created__gte"] = start_time
            if end_time is not None:
                query["created__lt"] = end_time
            result = await cls.db_model.filter(**query).values()
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return True, result



    @classmethod
    async def update_logout_user(cls, uid: int):
        """取消注销"""
        try:
            sta = await cls.db_model.filter(uid=uid).delete()
            if not sta:
                return False, "失败"
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"
        return True, "OK"

    @classmethod
    async def delete_logout_user(cls, uid: int, status: int = 2):
        """ 正式注销 删除User表信息 """
        try:
            sta = await cls.db_model.filter(uid=uid).delete()
            if not sta:
                return False, "失败"
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"
        return True, "OK"


