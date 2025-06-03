"""
茶馆相关
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import Clubs
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.club_users import ClubUsersRC


class BaseClubRC(BaseCommonRC):
    db_model = Clubs
    tb_name = db_model.sheet_name()

    KEY_CLUB_ID = 'club_id'
    KEY_CLUB_HOST_ID = 'club_uid'
    KEY_SESSION = "club_session"

    """创建的茶馆要求"""
    KEY_CLUB_CARD_LIMIT = 10  # 房卡数量

    @classmethod
    async def cache_session_set(cls, club_id, value):
        await cls.conf.rds.set_item(f"{cls.KEY_SESSION}:{club_id}", value)

    @classmethod
    async def cache_session_get(cls, club_id):
        return await cls.conf.rds.get_item(f"{cls.KEY_SESSION}:{club_id}")

    @classmethod
    async def cache_session_drop(cls, club_id):
        return await cls.conf.rds.drop_item(f"{cls.KEY_SESSION}:{club_id}")

    @classmethod
    async def create_club(cls, name: str, club_uid: int, room_card: int):
        """创建茶馆"""
        if room_card >= cls.KEY_CLUB_CARD_LIMIT:
            return False, "房卡不足"

        try:
            club = await cls.db_model.get_or_none(name=name)
            if club:
                # cls.conf.info_log(f"creat club: {name} 茶馆已存在")
                return False, "茶馆名已存在"

            club_dick = {
                "name": name,
                "uid": club_uid
            }

            # cls.conf.info_log('creat club:', club_dick)
            row = await cls.db_model.add_one(club_dick)
            club_user, e = await ClubUsersRC.create_club_user(club_uid, row.id)
            if not club_user:
                return False, e
        except OperationalError as e:
            return False, f"失败：{str(e)}"

        return True, "创建成功"

    @classmethod
    async def get_club_by_uid(cls, uid: int):
        """根据用户ID获取已加入茶馆列表"""
        try:
            club_users_data, e = await ClubUsersRC.get_club_user_by_uid(uid)
            if not club_users_data:
                return [], e
            club_ids = [club_user["club_id"] for club_user in club_users_data]
            club_list = await cls.db_model.filter(id__in=club_ids).values()
        except OperationalError as e:
            return [], f"失败：{str(e)}"
        return club_list, "成功"

    @classmethod
    async def get_club_by_id(cls, club_id: int):
        """根据ID获取茶馆信息"""
        try:
            club = await cls.cache_session_get(club_id)
            if not club:
                club = await cls.db_model.get_by_pk(club_id)
                if not club:
                    return None, "茶馆不存在"
                await cls.cache_session_set(club_id, club)
        except OperationalError as e:
            return None, f"失败：{str(e)}"
        return club, "成功"

    @classmethod
    async def update_club(cls, club_id: int, up_data: dict):
        """更新茶馆信息"""
        try:
            club, e = await cls.get_club_by_id(club_id)
            if not club:
                return False, e
            sta = await cls.db_model.update_by_pk(club_id, up_data, old_data=club)
            if sta:
                club.update(up_data)
                await cls.cache_session_set(club_id, club)
                return club, "成功"
        except OperationalError as e:
            return None, f"失败：{str(e)}"

    @classmethod
    async def update_club_int_field(cls, club_id: int, field_name: str, value: int, operation: str = 'add'):
        try:
            # 获取当前值
            club, e = await cls.update_int_field(club_id, field_name, value, operation)
            if not club:
                return False, e
            # 更新缓存
            await cls.cache_session_drop(club_id)
            return True, "更新成功"

        except OperationalError as e:
            return False, f"更新失败：{str(e)}"

