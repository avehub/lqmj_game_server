"""
茶馆和用户关系
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ClubUsers
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_parse

from lucky_game.model_rc.club_user_group import ClubUserGroupRC
from lucky_game.model_rc.extra_club_behavior import ExtraClubBehaviorRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey



class ClubUsersRC(BaseCommonRC):
    db_model = ClubUsers
    tb_name = db_model.sheet_name()

    KEY_CLUB_ID = 'club_id'
    KEY_SESSION_UID = "club_user_session_uid"
    KEY_SESSION_CLUBID = "club_user_session_clubid"

    ROLE_MANAGE = 1  # 管理员
    ROLE_HOST = 9  # 茶馆主

    STATUS_NORMAL = 0  # 正常
    STATUS_BLACK = 1  # 小黑屋

    @classmethod
    async def cache_session_uid_set(cls, uid, value):
        """根据用户ID缓存用户茶馆关系列表"""
        return await cls.conf.rds.set_item(f"{cls.KEY_SESSION_UID}:{uid}", value)

    @classmethod
    async def cache_session_uid_get(cls, uid):
        """根据用户ID获取用户茶馆关系列表"""
        data = await cls.conf.rds.get_item(f"{cls.KEY_SESSION_UID}:{uid}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_session_uid_drop(cls, uid):
        """根据用户ID删除用户茶馆关系列表"""
        return await cls.conf.rds.drop_item(f"{cls.KEY_SESSION_UID}:{uid}")

    @classmethod
    async def cache_session_clubid_set(cls, club_id, value):
        """根据茶馆ID缓存用户茶馆关系列表"""
        return await cls.conf.rds.set_item(f"{cls.KEY_SESSION_CLUBID}:{club_id}", value)

    @classmethod
    async def cache_session_clubid_get(cls, club_id):
        """根据茶馆ID缓存用户茶馆关系列表"""
        data = await cls.conf.rds.get_item(f"{cls.KEY_SESSION_CLUBID}:{club_id}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_session_clubid_drop(cls, club_id):
        """根据茶馆ID缓存用户茶馆关系列表"""
        return await cls.conf.rds.drop_item(f"{cls.KEY_SESSION_CLUBID}:{club_id}")

    @classmethod
    async def create_club_user(cls, uid: int, club_id: int, role: int = 0, status: int = 0):
        """添加用户至茶馆"""
        try:
            club_user, e = await cls.get_club_user_by_one(uid, club_id)
            if club_user:
                return False, e
            await cls.db_model.add_one({
                "uid": uid,
                "club_id": club_id,
                "role": role,
                "status": status
            })
        except OperationalError as e:
            return False, e
        return True, "添加成功"

    @classmethod
    async def update_club_user(cls, relation_id: int, role: int = None, status: int = None, check_uid: int = None):
        """更新用户茶馆关系"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                data, e = await cls.get_club_user_by_id(relation_id)
                if not data:
                    return False, e
                up_data = {}
                if role is not None:
                    up_data["role"] = role
                if status is not None:
                    up_data["status"] = status
                if up_data:
                    await cls.db_model.update_by_pk(relation_id, up_data)
                    await cls.cache_session_uid_drop(data["uid"])
                    await cls.cache_session_clubid_drop(data["club_id"])
                # 管理员变更写入行为记录
                if role is not None and role != data["role"]:
                    # 管理员->普通成员
                    status = ExtraClubBehaviorRC.BEHAVIOR_STATUS_CANCEL
                    group_status = ClubUserGroupRC.GROUP_STATUS_NORMAL
                    if role == cls.ROLE_MANAGE:
                        # 普通成员->管理员
                        status = ExtraClubBehaviorRC.BEHAVIOR_STATUS_SUCCEED
                        group_status = ClubUserGroupRC.GROUP_STATUS_DISABLE
                    # 写入行为记录
                    sta, msg = await ExtraClubBehaviorRC.create_club_behavior(
                        ExtraClubBehaviorRC.BEHAVIOR_MANAGE_INDEX,
                        data["uid"],
                        data["club_id"],
                        check_uid=check_uid,
                        status=status
                    )
                    if not sta:
                        return False, msg
                    # 更新禁止同桌状态
                    groups, e = await ClubUserGroupRC.get_club_user_group_by_filter(
                        data["club_id"],
                        uid=data["uid"]
                    )
                    if groups and groups[0]["u_ids"]:
                        group_id, e = await ClubUserGroupRC.update_club_user_group(
                            groups[0]["gid"],
                            status=group_status
                        )
                        if not group_id:
                            return False, msg
        except OperationalError as e:
            return False, e
        return True, "更新成功"

    @classmethod
    async def delete_club_user(cls, relation_id: int = None, uid: int = None, club_id: int = None,
                               check_uid: int = None):
        """删除用户茶馆关系"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                query = {}
                if relation_id is not None:
                    query["id"] = relation_id
                if uid is not None:
                    query["uid"] = uid
                if club_id is not None:
                    query["club_id"] = club_id
                data = await cls.db_model.filter(**query).first()
                if data:
                    if data.role == cls.ROLE_HOST:
                        return False, "无法删除茶馆主"
                    from lucky_game.model_rc.game_rooms import GameRoomsRC
                    check, _ = await GameRoomsRC.check_uid_room_user(data.uid)
                    if check:
                        return False, "用户已在游戏中，无法退出"
                    await cls.db_model.del_by_pk(data.id)
                    await cls.cache_session_uid_drop(data.uid)
                    await cls.cache_session_clubid_drop(data.club_id)
                sta, e = await ExtraClubBehaviorRC.create_club_behavior(
                    ExtraClubBehaviorRC.BEHAVIOR_OUT_INDEX,
                    data.uid,
                    data.club_id,
                    check_uid=0 if check_uid == data.uid else check_uid,  # 主动离开check_id=0
                    status=ExtraClubBehaviorRC.BEHAVIOR_STATUS_SUCCEED,
                )
                if not sta:
                    return False, e
        except OperationalError as e:
            return False, e
        return True, "删除成功"

    @classmethod
    async def get_club_user_by_id(cls, relation_id: int):
        """根据ID获取用户茶馆关系"""
        try:
            result = await cls.db_model.get_by_pk(relation_id)
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
    async def get_club_user_by_uid(cls, uid: int, in_role: list = None):
        """根据用户ID获取用户茶馆关系"""
        try:
            result = await cls.cache_session_uid_get(uid)
            if not result:
                result = await cls.db_model.get_by_dict({"uid": uid, "role__in": in_role})
                await cls.cache_session_uid_set(uid, result)
        except OperationalError as e:
            return False, e
        return result, "成功"

    @classmethod
    async def get_club_user_by_uid_club_ids(cls, uid: int, in_role: list = None, club_id: any = None):
        """根据用户ID获取用户加入、管理茶馆IDS"""
        result = []
        try:
            where = {"uid": uid}
            if in_role:
                where["role__in"] = in_role
            if club_id:
                if isinstance(club_id, list):
                    where["club_id__in"] = club_id
                else:
                    where["club_id"] = club_id
            club_users_data = await cls.db_model.get_by_dict(where)
            if club_users_data:
                result = [club_user["club_id"] for club_user in club_users_data]
        except OperationalError as e:
            return False, e
        return result, "成功"

    @classmethod
    async def get_club_user_by_one(cls, uid: int, club_id: int):
        """根据用户ID、茶馆ID获取用户茶馆关系"""
        try:
            result = await cls.db_model.filter(uid=uid, club_id=club_id).first().values()
            if not result:
                return result, "茶馆用户关系不存在"
        except OperationalError as e:
            return False, e
        return result, "成功"

    @classmethod
    async def get_club_user_by_filter(cls, uid: any = None, club_id: int = None, role: any = None, status: int = None,
                                      page: int = None, page_size: int = None):
        """获取用户茶馆关系"""
        try:
            query = {}
            if uid is not None:
                if isinstance(uid, list):
                    query["uid__in"] = uid
                else:
                    query["uid"] = uid
            if club_id is not None:
                query["club_id"] = club_id
            if role is not None:
                if isinstance(role, list):
                    query["role__in"] = role
                else:
                    query["role"] = role
            if status is not None:
                query["status"] = status
            if page and page_size:
                data = []
                count = await cls.db_model.get_count(query)
                if count > 0:
                    offset = (page - 1) * page_size
                    data = await cls.db_model.filter(**query).order_by("-role").offset(offset).limit(page_size).values()
                result = await cls.page_result(page, page_size, count, data)
            else:
                result = data = await cls.db_model.filter(**query).order_by("-role").values()
            if not data:
                return result, "暂无数据"
        except OperationalError as e:
            return False, e
        return result, "成功"

    @classmethod
    async def count_club_user(cls, uid: int = None, club_id: int = None, role: int = None, status: int = None):
        """获取符合条件的用户数量"""
        count = 0
        try:
            query = {}
            if uid is not None:
                query["uid"] = uid
            if club_id is not None:
                query["club_id"] = club_id
            if role is not None:
                query["role"] = role
            if status is not None:
                query["status"] = status
            if query:
                count = await cls.db_model.get_count(query)
        except OperationalError as e:
            return count, f"{str(e)}"
        return count, "成功"

    @classmethod
    async def join_black(cls, club_id: int, uid: int, check_uid: int = 0):
        """加入小黑屋"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                club_user, e = await cls.get_club_user_by_one(uid, club_id)
                if not club_user:
                    return False, e
                if club_user["status"] == cls.STATUS_BLACK:
                    return False, "用户已在黑名单中"
                sta = await cls.update_club_user(club_user["id"], status=cls.STATUS_BLACK)
                if not sta:
                    return False, "加入黑名单失败"
                if check_uid:
                    sta, e = await ExtraClubBehaviorRC.create_club_behavior(
                        ExtraClubBehaviorRC.BEHAVIOR_BLACK_INDEX,
                        uid,
                        club_id,
                        check_uid=check_uid,
                        status=ExtraClubBehaviorRC.BEHAVIOR_STATUS_SUCCEED
                    )
                    if not sta:
                        return False, e
        except OperationalError as e:
            return False, e
        return True, "成功"

    @classmethod
    async def cancel_black(cls, relation_id: int, check_uid: int = 0):
        """取消小黑屋"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                club_user, e = await cls.get_club_user_by_id(relation_id)
                if not club_user:
                    return False, e
                if club_user["status"] == cls.STATUS_NORMAL:
                    return False, "用户不在黑名单中"
                sta = await cls.update_club_user(club_user["id"], status=cls.STATUS_NORMAL)
                if not sta:
                    return False, "移除黑名单失败"
                sta, e = await ExtraClubBehaviorRC.create_club_behavior(
                    ExtraClubBehaviorRC.BEHAVIOR_BLACK_INDEX,
                    club_user["uid"],
                    club_user["club_id"],
                    check_uid=check_uid,
                    status=ExtraClubBehaviorRC.BEHAVIOR_STATUS_CANCEL,
                )
                if not sta:
                    return False, e
        except OperationalError as e:
            return False, e
        return True, "成功"

    @classmethod
    async def delete_club_all(cls, club_id: int):
        """删除茶馆所有用户关系(解散茶馆)"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                query = {
                    "club_id": club_id
                }
                data = await cls.db_model.filter(**query).values()
                if data:
                    for item in data:
                        await cls.cache_session_uid_drop(item["uid"])
                    await cls.cache_session_clubid_drop(club_id)
                    await cls.db_model.filter(**query).delete()
        except OperationalError as e:
            return False, e
        return True, "成功"

    @classmethod
    async def is_club_user_black(cls, uid: int, club_id: int):
        """判断用户是否在茶馆黑名单中"""
        club_user, e = await cls.get_club_user_by_one(uid, club_id)
        if not club_user:
            return True, e
        if club_user["status"] == cls.STATUS_BLACK:
            return True, "用户在黑名单中"
        return False, "用户不在黑名单中"
