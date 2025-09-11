"""
茶馆隔离组表
"""
from nsanic.orm.rc_model import RCModel
from lucky_game.model_db.main import ClubGroups
from nsanic.libs.tool import json_encode, json_parse
from tortoise.exceptions import OperationalError
from lucky_game.model_rc.extra_club_behavior import ExtraClubBehaviorRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from datetime import datetime


class ClubGroupRC(RCModel):
    """ 茶馆隔离组表 """
    db_model = ClubGroups
    tb_name = db_model.sheet_name()

    @classmethod
    async def _bulk_behavior(cls, club_id: int, uid: int, u_ids: list):
        """批量将茶馆隔离组数据写入行为表"""
        rows = []
        date_time = int(datetime.now().timestamp())
        for u_id in u_ids:
            rows.append(
                {
                    "type": ExtraClubBehaviorRC.BEHAVIOR_ISOLATION_INDEX,
                    "uid": u_id,
                    "club_id": club_id,
                    "check_uid": uid,
                    "status": ExtraClubBehaviorRC.BEHAVIOR_STATUS_SUCCEED,
                    "created": date_time,
                }
            )
        sta, e = await ExtraClubBehaviorRC.bulk_create_club_behavior(rows)
        return sta, e

    @classmethod
    async def creat_club_group(cls, club_id: int, name: str, u_ids: set, uid: int = None):
        """创建茶馆隔离组"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                has, e = await cls.get_club_group_by_filter(club_id=club_id, name=name)
                if has:
                    return None, "组名已存在"
                group = await cls.db_model.add_one({
                    "club_id": club_id,
                    "name": name,
                    "u_ids": json_encode(u_ids),
                })
                if not group:
                    return group, "创建失败"
                if uid:
                    sta, e = await cls._bulk_behavior(club_id=club_id, uid=uid, u_ids=list(u_ids))
                    if not sta:
                        return None, e
        except OperationalError as e:
            return None, f"创建失败: {str(e)}"
        return group.gid, "成功"

    @classmethod
    async def update_club_group(cls, gid: int, name: str = None, u_ids: set = None, uid: int = None):
        """更新茶馆隔离组"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                group = await cls.db_model.get_by_pk(gid)
                if not group:
                    return None, "组不存在"
                up_data = {}
                if name is not None:
                    has, e = await cls.get_club_group_by_filter(club_id=group["club_id"], name=name)
                    if has and gid not in [item["gid"] for item in has]:
                        return None, "组名已存在"
                    up_data["name"] = name
                if u_ids is not None:
                    up_data["u_ids"] = json_encode(u_ids)
                if up_data:
                    await cls.db_model.update_by_pk(gid, up_data)
                if uid:
                    sta, e = await cls._bulk_behavior(club_id=group["club_id"], uid=uid, u_ids=list(u_ids))
                    if not sta:
                        return None, e
        except OperationalError as e:
            return None, f"更新失败: {str(e)}"
        return gid, "成功"

    @classmethod
    async def delete_group(cls, gid: int):
        """删除茶馆隔离组"""
        try:
            sta = await cls.db_model.del_by_pk(gid)
            if not sta:
                return sta, "删除失败"
        except OperationalError as e:
            return None, f"删除失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def get_club_group_by_id(cls, gid: int):
        """根据ID获取茶馆隔离组"""
        try:
            group = await cls.db_model.get_by_pk(gid)
            if not group:
                return None, "组不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return group, "成功"

    @classmethod
    async def get_club_group_by_filter(cls, club_id: int, name: str = None, uid: int = None):
        """根据条件获取茶馆隔离组列表"""
        try:
            query = {}
            if club_id is not None:
                query["club_id"] = club_id
            if name is not None:
                query["name"] = name
            if uid is not None:
                query["u_ids__contains"] = uid
            groups = await cls.db_model.filter(**query).values()
            if groups:
                #将u_ids转化为列表
                for item in groups:
                    item["u_ids"] = json_parse(item["u_ids"]) if item["u_ids"] else []
            else:
                return None, "组不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return groups, "成功"

    @classmethod
    async def check_uid_by_club(cls, club_id: int, uid: int):
        """检测用户是否在茶馆隔离组中"""
        try:
            group_uid = set()
            groups, _ = await cls.get_club_group_by_filter(club_id, uid=uid)
            if groups:
                for item in groups:
                    ids = json_parse(item["u_ids"])
                    if uid in ids:
                        group_uid.update(ids)
        except OperationalError as e:
            return None, []
        sta = False
        if group_uid:
            sta = True
        return sta, group_uid

    @classmethod
    async def check_uid_by_room(cls, club_id: int, room_uid: list, uid: int) -> bool:
        """检测用户是否与房间内用户在同一隔离组中"""
        all_exist = False
        groups, _ = await cls.get_club_group_by_filter(club_id, uid=uid)
        if groups:
            for item in groups:
                values_to_check = [uid]
                target_array = json_parse(item["u_ids"])
                for check_uid in room_uid:
                    values_to_check.append(check_uid)
                    all_exist = all(value in target_array for value in values_to_check)
                    if all_exist:
                        break
        return all_exist

    @classmethod
    async def delete_club_all(cls, club_id: int):
        """删除茶馆所有隔离组(解散茶馆)"""
        try:
            query = {
                "club_id": club_id
            }
            await cls.db_model.filter(**query).delete()
        except OperationalError as e:
            return False, e
        return True, "成功"
