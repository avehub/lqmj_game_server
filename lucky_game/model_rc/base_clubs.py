"""
茶馆相关
"""
import asyncio
from typing import Union, Iterable
from datetime import datetime, date
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from nsanic.orm.rc_model import RCModel
from c_services.const.cs_enum_const import CmdWorkers
from common.public.enum_const import BaseEnum, CacheKey, BanType
from common.utils.kit_dt import KitDt
from tortoise.exceptions import OperationalError
from lucky_game.const import GoodsItem, ReasonCostGold, ReasonCostDiamond
from lucky_game.model_db.log import RecordsUserBan
from lucky_game.model_db.main import Clubs
from lucky_game.model_rc.base_rc import BaseCommonRC
from pprint import pprint

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
        await cls.conf.rds.set_item(f"{cls.KEY_SESSION}:{club_id}", value, ex_time=10 * 86400)

    @classmethod
    async def cache_session_get(cls, club_id):
        return await cls.conf.rds.get_item(f"{cls.KEY_SESSION}:{club_id}")

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
            await cls.db_model.add_one(club_dick)
            # TODO 关系表 insert
        except OperationalError as e:
            # cls.conf.info_log(f"creat club: {name} 茶馆创建失败", e)
            return False, e

        return True, "创建成功"

    @classmethod
    async def get_club_by_id(cls, club_id: int):
        """根据茶馆ID获取茶馆信息"""
        try:
            club = cls.cache_session_get(club_id)
            if not club:
                club = await cls.db_model.get_or_none(id=club_id)
                await cls.cache_session_set(club_id, club)

            return club
        except OperationalError as e:
            # cls.conf.info_log(f"get club: {club_id} 茶馆获取失败", e)
            return None

    @classmethod
    async def get_club_by_uid(cls, club_uid: int):
        """根据馆主ID获取茶馆列表"""
        pass
