"""
茶馆和用户关系
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ClubUsers
from lucky_game.model_rc.base_rc import BaseCommonRC
from pprint import pprint
from nsanic.libs.tool import json_encode


class ClubUsersRC(BaseCommonRC):
    db_model = ClubUsers
    tb_name = db_model.sheet_name()

    KEY_CLUB_ID = 'club_id'
    KEY_SESSION_UID = "club_user_session_uid"
    KEY_SESSION_CLUBID = "club_user_session_clubid"

    @classmethod
    async def cache_session_uid_set(cls, uid, value):
        await cls.conf.rds.set_item(f"{cls.KEY_SESSION_UID}:{uid}", value)

    @classmethod
    async def cache_session_uid_get(cls, uid):
        await cls.conf.rds.get_item(f"{cls.KEY_SESSION_UID}:{uid}")

    @classmethod
    async def cache_session_uid_drop(cls, uid):
        await cls.conf.rds.drop_item(f"{cls.KEY_SESSION_UID}:{uid}")

    @classmethod
    async def cache_session_clubid_set(cls, club_id, value):
        await cls.conf.rds.set_item(f"{cls.KEY_SESSION_CLUBID}:{club_id}", value)

    @classmethod
    async def cache_session_clubid_get(cls, club_id):
        await cls.conf.rds.get_item(f"{cls.KEY_SESSION_CLUBID}:{club_id}")

    @classmethod
    async def cache_session_clubid_drop(cls, club_id):
        await cls.conf.rds.drop_item(f"{cls.KEY_SESSION_CLUBID}:{club_id}")

    @classmethod
    async def check_club_user(cls, uid, club_id):
        """检查用户是否在茶馆"""
        try:
            club_user = await cls.db_model.get_or_none(uid=uid, club_id=club_id)
            print(club_user)
            if not club_user:
                return False, "茶馆用户关系不存在"
            if club_user.status != 0:
                return False, "茶馆成员状态异常"
        except OperationalError as e:
            return False, e
        return True, "茶馆用户关系已存在"

    @classmethod
    async def create_club_user(cls, uid: int, club_id: int):
        """添加用户至茶馆"""
        try:
            club_user, e = await cls.check_club_user(uid, club_id)
            if club_user:
                return False, e
            await cls.db_model.add_one({
                "uid": uid,
                "club_id": club_id
            })
        except OperationalError as e:
            return False, e
        return True, "添加成功"

    @classmethod
    async def update_club_user(cls, id: int, **kwargs):
        """更新用户茶馆关系"""
        try:
            data, e = await cls.get_club_user_by_id(id)
            if not data:
                return False, e
            if kwargs:
                up_data = {}
                for k, v in kwargs.items():
                    if k == "role" or k == "status":
                        up_data[k] = v
                if up_data:
                    await cls.db_model.update_from_dict(cls.tb_name, up_data).save()
                    await cls.cache_session_uid_drop(data.uid)
                    await cls.cache_session_clubid_drop(data.club_id)
        except OperationalError as e:
            return False, e
        return True, "更新成功"

    @classmethod
    async def delete_club_user(cls, id: int = 0, uid: int = 0, club_id: int = 0):
        """删除用户茶馆关系"""
        try:
            if id == 0:
                data, e = await cls.get_club_user_by_id(id)
            else:
                data, e = await cls.get_club_user_by_one(uid, club_id)
            if not data:
                return False, e
            await cls.db_model.filter(id=id).delete()
            await cls.cache_session_uid_drop(data.uid)
            await cls.cache_session_clubid_drop(data.club_id)
        except OperationalError as e:
            return False, e
        return True, "删除成功"

    @classmethod
    async def get_club_user_by_id(cls, id: int):
        """根据ID获取用户茶馆关系"""
        try:
            result = await cls.db_model.get_or_none(id=id)
            if not result:
                return result, "茶馆用户关系不存在"
        except OperationalError as e:
            return False, e
        return result, "成功"

    @classmethod
    async def get_club_user_by_club_id(cls, club_id: int):
        """根据茶馆ID获取茶馆下用户列表"""
        try:
            result = await cls.cache_session_clubid_get(club_id)
            if not result:
                result = await cls.db_model.get_by_dict({"club_id": club_id})
                await cls.cache_session_clubid_set(club_id, result)
        except OperationalError as e:
            return False, e
        return result, "成功"

    @classmethod
    async def get_club_user_by_uid(cls, uid: int):
        """根据用户ID获取用户茶馆关系"""
        try:
            result = await cls.cache_session_uid_get(uid)
            if not result:
                result = await cls.db_model.get_by_dict({"uid": uid})
                await cls.cache_session_uid_set(uid, result if result else {})
        except OperationalError as e:
            return False, e
        return result, "成功"

    @classmethod
    async def get_club_user_by_one(cls, uid: int, club_id: int):
        """根据用户ID、茶馆ID获取用户茶馆关系"""
        try:
            result = await cls.db_model.get_or_none(uid=uid, club_id=club_id)
            if not result:
                return result, "茶馆用户关系不存在"
        except OperationalError as e:
            return False, e
        return result, "成功"
