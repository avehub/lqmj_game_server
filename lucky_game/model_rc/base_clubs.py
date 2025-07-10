"""
茶馆相关
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import Clubs
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.club_users import ClubUsersRC
from nsanic.libs.tool import json_parse
from c_services.const.cs_enum_const import RoomStatus


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
        return await cls.conf.rds.set_item(f"{cls.KEY_SESSION}:{club_id}", value)

    @classmethod
    async def cache_session_get(cls, club_id):
        data = await cls.conf.rds.get_item(f"{cls.KEY_SESSION}:{club_id}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_session_drop(cls, club_id):
        return await cls.conf.rds.drop_item(f"{cls.KEY_SESSION}:{club_id}")

    @classmethod
    async def check_club_name(cls, name: str, club_id: int = None):
        """检查茶馆名称是否存在"""
        try:
            has = cls.conf.sw.contain_sensitive_words(name)
            if has:
                return False, "茶馆名包含敏感词"
            club = await cls.db_model.get_or_none(name=name)
            if club_id is not None:
                if club and club.id != club_id:
                    return False, "茶馆名已存在"
            else:
                if club:
                    return False, "茶馆名已存在"
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return True, "校验成功"


    @classmethod
    async def create_club(cls, name: str, club_uid: int, room_card: int):
        """创建茶馆"""
        try:
            club_dick = {
                "name": name,
                "uid": club_uid,
                "other": {"pay_type": 1, "host_power_room": 3}
            }
            # cls.conf.info_log('creat club:', club_dick)
            row = await cls.db_model.add_one(club_dick)
            club_user, e = await ClubUsersRC.create_club_user(club_uid, row.id, role=ClubUsersRC.ROLE_HOST)
            if not club_user:
                return False, e
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return row, "创建成功"

    @classmethod
    async def get_club_by_uid(cls, uid: int, in_role: list = None):
        """根据用户ID获取已加入茶馆列表"""
        try:
            club_ids, _ = await ClubUsersRC.get_club_user_by_uid_club_ids(uid, in_role=in_role)
            club_list = await cls.db_model.filter(id__in=club_ids).values()
        except OperationalError as e:
            return False, f"失败：{str(e)}"
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
    async def update_club(cls, club_id: int, name: str = None, other: dict = None, status: int = None):
        """更新茶馆信息"""
        try:
            club, e = await cls.get_club_by_id(club_id)
            if not club:
                return False, e
            up_data = {}
            if name:
                up_data["name"] = name
            if other:
                up_data["other"] = other
            if status:
                up_data["status"] = status
            if up_data:
                sta = await cls.db_model.update_by_pk(club_id, up_data, old_data=club)
                if not sta:
                    return None, "失败"
                club.update(up_data)
                await cls.cache_session_set(club_id, club)
        except OperationalError as e:
            return None, f"失败：{str(e)}"
        return club, "成功"

    @classmethod
    async def delete_club(cls, club_id: int):
        """删除茶馆信息"""
        try:
            club, e = await cls.get_club_by_id(club_id)
            # 茶馆基金
            if club["room_card"] > 0:
                return None, "无法解散，还有未消耗的房卡基金"
            # 存在游戏中的房间则无法解散
            from lucky_game.model_rc.game_rooms import GameRoomsRC
            rooms, _ = await GameRoomsRC.get_game_rooms_by_filter(
                club_id=club_id,
                status=[
                    RoomStatus.T_IDLE,
                    RoomStatus.T_READY,
                    RoomStatus.T_PLAYING,
                    RoomStatus.T_RECHARGE_ING,
                    RoomStatus.T_CHECK_OUT,
                    RoomStatus.T_DISMISS,
                ]
            )
            if rooms:
                return None, "无法解散，还有未结束的游戏房间"
            await cls.db_model.update_by_pk(club_id, {"status": 1})
            await cls.cache_session_drop(club_id)
        except OperationalError as e:
            return None, f"失败：{str(e)}"
        return True, "成功"

    @classmethod
    async def update_club_int_field(cls, club_id: int, field_name: str, value: int, operation: str = 'add'):
        try:
            club, e = await cls.update_int_field(club_id, field_name, value, operation)
            if not club:
                return False, e
            # 更新缓存
            await cls.cache_session_drop(club_id)
        except OperationalError as e:
            return False, f"更新失败：{str(e)}"
        return True, "更新成功"

