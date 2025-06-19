"""
茶馆隔离组表
"""
from nsanic.orm.rc_model import RCModel
from lucky_game.model_db.main import ClubGroups
from lucky_game.const import CompleteSta
from nsanic.libs.tool import json_encode, json_parse
from tortoise.exceptions import OperationalError
from lucky_game.model_rc.extra_club_behavior import ExtraClubBehaviorRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey


class ClubGroupRC(RCModel):
    """ 茶馆隔离组表 """
    db_model = ClubGroups
    tb_name = db_model.sheet_name()

    @classmethod
    async def creat_club_group(cls, club_id: int, name: str, u_ids: set, uid: int = None):
        """创建茶馆隔离组"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                group = await cls.db_model.add_one({
                    "club_id": club_id,
                    "name": name,
                    "u_ids": json_encode(list(u_ids)),
                })
                if not group:
                    return group, "创建失败"
                if uid:
                    for u_id in u_ids:
                        await ExtraClubBehaviorRC.create_club_behavior(
                            ExtraClubBehaviorRC.BEHAVIOR_ISOLATION_INDEX,
                            uid=u_id,
                            club_id=club_id,
                            check_uid=uid,
                        )
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
                # 删除原有的用户
                await ExtraClubBehaviorRC.more_delete_club_behavior(
                    behavior_type=ExtraClubBehaviorRC.BEHAVIOR_ISOLATION_INDEX,
                    club_id=group.club_id,
                    uid=json_parse(group.u_ids),
                )

                if name is not None:
                    group.name = name
                if u_ids is not None:
                    group.u_ids = json_encode(list(u_ids))
                await group.save()
                if uid:
                    for u_id in list(u_ids):
                        await ExtraClubBehaviorRC.create_club_behavior(
                            ExtraClubBehaviorRC.BEHAVIOR_ISOLATION_INDEX,
                            uid=u_id,
                            club_id=group.club_id,
                            check_uid=uid,
                        )
        except OperationalError as e:
            return None, f"更新失败: {str(e)}"
        return group.gid, "成功"

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
    async def get_club_group_by_filter(cls, club_id: int, name: str = None):
        """根据条件获取茶馆隔离组列表"""
        try:
            query = {}
            if club_id is not None:
                query["club_id"] = club_id
            if name is not None:
                query["name"] = name
            groups = await cls.db_model.filter(**query).values()
            if not groups:
                return None, "组不存在"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return groups, "成功"

    @classmethod
    async def check_group_by_uid(cls, club_id: int, uid: int, r_uid: int):
        """检测用户是否在茶馆隔离组中"""
        try:
            groups, _ = await cls.get_club_group_by_filter(club_id)
            if groups:
                for item in groups.values():
                    ids = json_parse(item["u_ids"])
                    if uid in ids and r_uid in ids:
                        return True, ids
        except OperationalError as e:
            return None, []
        return False, []
