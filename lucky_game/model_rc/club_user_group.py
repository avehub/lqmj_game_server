"""
茶馆禁止同桌表
"""
from nsanic.orm.rc_model import RCModel
from lucky_game.model_db.main import ClubUserGroups
from nsanic.libs.tool import json_encode, json_parse
from tortoise.exceptions import OperationalError
from lucky_game.model_rc.extra_club_behavior import ExtraClubBehaviorRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from datetime import datetime


class ClubUserGroupRC(RCModel):
    """ 茶馆用户禁止同桌表 """
    db_model = ClubUserGroups
    tb_name = db_model.sheet_name()

    GROUP_STATUS_NORMAL = 1  # 生效
    GROUP_STATUS_DISABLE = 0  # 失效

    @classmethod
    async def alter_club_user_group(cls, club_id: int, uid: int, u_ids: set, status: int = None):
        """更新茶馆禁止同桌"""
        try:
            has, e = await cls.get_club_user_group_by_filter(club_id=club_id, uid=uid)
            if has:
                return await cls.update_club_user_group(has[0]["gid"], u_ids=u_ids, status=status)
            group = await cls.db_model.add_one({
                "club_id": club_id,
                "uid": uid,
                "u_ids": json_encode(u_ids),
                "status": status,
            })
            if not group:
                return group, "创建失败"
        except OperationalError as e:
            return None, f"创建失败: {str(e)}"
        return group.gid, "成功"

    @classmethod
    async def update_club_user_group(cls, gid: int, u_ids: set = None, status: int = None):
        """更新茶馆禁止同桌"""
        try:
            up_data = {}
            if u_ids is not None:
                up_data["u_ids"] = json_encode(u_ids)
            if status is not None:
                up_data["status"] = status
            if up_data:
                await cls.db_model.update_by_pk(gid, up_data)
        except OperationalError as e:
            return None, f"更新失败: {str(e)}"
        return gid, "成功"

    @classmethod
    async def delete_group(cls, club_id: int, uid: int):
        """删除茶馆禁止同桌"""
        try:
            has, e = await cls.get_club_user_group_by_filter(club_id=club_id, uid=uid)
            if not has:
                return None, "禁止同桌不存在"
            sta = await cls.db_model.del_by_pk(has[0]["gid"])
            if not sta:
                return sta, "删除失败"
        except OperationalError as e:
            return None, f"删除失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def get_club_user_group_by_id(cls, gid: int):
        """根据ID获取茶馆禁止同桌"""
        try:
            group = await cls.db_model.get_by_pk(gid)
            if not group:
                return None, "数据不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return group, "成功"

    @classmethod
    async def get_club_user_group_by_filter(cls, club_id: int, uid: int = None, status: int = None, u_ids: int = None):
        """根据条件获取茶馆禁止同桌列表"""
        try:
            query = {}
            if club_id is not None:
                query["club_id"] = club_id
            if uid is not None:
                query["uid"] = uid
            if status is not None:
                query["status"] = status
            if u_ids is not None:
                query["u_ids__contains"] = u_ids
            groups = await cls.db_model.filter(**query).values()
            if groups:
                #将u_ids转化为列表
                for item in groups:
                    item["u_ids"] = json_parse(item["u_ids"]) if item["u_ids"] else []
            else:
                return None, "数据不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return groups, "成功"

    @classmethod
    async def check_uid_by_room(cls, club_id: int, uid: int, room_uid: list) -> bool:
        """检测用户是否与房间内用户在同一禁止同桌中"""
        try:
            sta = room_u_sta = False
            groups, _ = await cls.get_club_user_group_by_filter(club_id, uid=uid)
            cls.conf.log.info(f"groups_1: {groups}, 待加入uid: {uid}, 房间内room_uid: {room_uid}")
            if groups:
                sta = await cls.__check_in_group(groups[0], uid, room_uid)
            if not sta:
                group_list, _ = await cls.get_club_user_group_by_filter(club_id, u_ids=uid)
                if group_list:
                    for group in group_list:
                        cls.conf.log.info(f"group_2: {group}, 待加入uid: {uid}, 房间内room_uid: {room_uid}")
                        cls.conf.log.info(f"group_2:禁止同桌uid: {type(uid)} {uid}")
                        cls.conf.log.info(f"group_2:禁止同桌room_uid: {type(room_uid)} {room_uid}")
                        if group["status"] == 1 and str(group["uid"]) in room_uid:
                            room_u_sta = True
                            break
        except OperationalError as e:
            return False
        return True if sta or room_u_sta else False

    @classmethod
    async def delete_club_all(cls, club_id: int):
        """删除茶馆所有禁止同桌(解散茶馆)"""
        try:
            query = {
                "club_id": club_id
            }
            await cls.db_model.filter(**query).delete()
        except OperationalError as e:
            return False, e
        return True, "成功"

    @classmethod
    async def __check_in_group(cls, group, uid, room_uid) -> bool:
        """检查用户是否在禁止同桌组中"""
        exist = False
        if group and group["status"] == 1:
            if group["u_ids"]:
                for u_id in group["u_ids"]:
                    if str(u_id) in room_uid:
                        exist = True
                        break
        return exist
