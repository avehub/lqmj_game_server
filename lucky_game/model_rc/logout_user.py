"""
注销用户记录表
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import LogoutUser
from lucky_game.model_rc.base_rc import BaseCommonRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from datetime import datetime

from lucky_game.model_rc.base_user import BaseUserRC


class LogoutUserRC(BaseCommonRC):
    db_model = LogoutUser
    tb_name = db_model.sheet_name()


    @classmethod
    async def create_logout_user(cls, u_info: dict, **kwargs):
        """创建战绩总局记录"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                data = {
                    "uid": u_info.get("uid"),
                    "name": u_info.get("name"),
                    "avatar": u_info.get("avatar"),
                    "sex": u_info.get("sex"),
                    "phone": u_info.get("phone"),
                    "email": u_info.get("email"),
                    "address": u_info.get("address"),
                    "id_card": u_info.get("id_card"),
                    "real_name": u_info.get("real_name"),
                    "pi": u_info.get("pi"),
                    "discount": u_info.get("discount"),
                    "gold": u_info.get("gold"),
                    "diamond": u_info.get("diamond"),
                    "room_card": u_info.get("room_card"),
                    "yellow_diamond": u_info.get("yellow_diamond"),
                    "vip": u_info.get("vip"),
                    "platform": u_info.get("platform"),
                    "dev_ident": u_info.get("dev_ident"),
                    "ip": u_info.get("ip"),
                    "region": u_info.get("region"),
                    "country": u_info.get("country"),
                    "openid": u_info.get("openid"),
                    "unionid": u_info.get("unionid"),
                    "wechat": u_info.get("wechat"),
                    "apple_id": u_info.get("apple_id"),
                    "future_value": u_info.get("future_value"),
                    "status": kwargs.get("status"),
                }
                new = await cls.db_model.add_one(data)
                if not new:
                    return False, "创建失败"
                new_data = {"status": data["status"]}
                data = await BaseUserRC.update_info(u_info, new_data)
        except OperationalError as e:
            return False, f"失败原因:{str(e)}"
        return True, data

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
            async with in_transaction(connection_name=DbKey.DEFAULT):
                sta = await cls.db_model.filter(uid=uid).update(status=status)
                if not sta:
                    return False, "失败"

                u_info = await BaseUserRC.cache_by_pk(uid)
                new_data = {
                    "phone": "",
                    "openid": f"{uid}_{datetime.now()}",
                    "unionid": f"{uid}_{datetime.now()}",
                    "apple_id": f"{uid}_{datetime.now()}",
                }
                data = await BaseUserRC.update_info(u_info, new_data, True)
        except OperationalError as e:
            return False, f"删除失败: {str(e)}"
        return True, data


