""" 茶馆相关逻辑处理 """
import decimal
import random

from nsanic.libs.mk_random import RngMaker
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from tortoise.transactions import in_transaction

from c_services.const.cs_enum_const import RedDotType
from common.public.enum_const import DbKey, ServiceEnum
from common.public.common_class import CommonApi
from lucky_game.handler.vivo_pay import vivo_payment
from lucky_game.logic.activity import FirstCharge
from lucky_game.model_rc.base_clubs import BaseClubRC
from lucky_game.model_rc.club_users import ClubUsersRC
from lucky_game.model_rc.extra_club_behavior import ExtraClubBehaviorRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.base_store import GoodRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import ReasonCostGold, CurrencyType, PayMode, OrderStatus, GainStatus, GoodsSku, PlatForm, \
    OperatingSystem, StoreType
from nsanic.libs.mult_log import NLogger
from common.public.conf import ENV, C_SERVICE_SECRET_KEY
from common.public.conf import LIVE_SERVER
from lucky_game.handler.huifu import DouGongPay
from lucky_game.handler.wechat import WeChat
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from common.aliyun.pay_service import AlipayPayment
from lucky_game.model_rc.vip_level import UserVipRC


class ClubLogic(CommonApi):


    @classmethod
    async def send_club_rmq_by_game(cls, msg_cmd: int, club_id: int, uid: int):
        """ 发送茶馆消息到游戏服务 """
        cs_enum = ServiceEnum.find_member_by_val(ServiceEnum.C_CLUB)
        data = {"secret": C_SERVICE_SECRET_KEY, "club_id": club_id, "uid": uid}
        await cls.cs2cs_by_rmq(
            cs_enum,
            msg_cmd,
            data,
            uid,
        )

    @classmethod
    async def leave_club_before(cls, uid: int, club_id: int, check_uid: int = None):
        """ 离开茶馆前业务处理 """
        sta, e = await ExtraClubBehaviorRC.create_club_behavior(
            ExtraClubBehaviorRC.BEHAVIOR_OUT_INDEX,
            uid,
            club_id,
            check_uid=0 if check_uid == uid else check_uid,  # 主动离开check_id=0
            status=ExtraClubBehaviorRC.BEHAVIOR_STATUS_DEFAULT,
        )
        if not sta:
            return False, e

        return True, "OK"

    @classmethod
    async def leave_club_after(cls, relation_info: dict, check_uid: int = None):
        """ 离开茶馆后业务处理 """
        behavior, e = await ClubUsersRC.delete_club_user(relation_info["id"], check_uid=check_uid)
        if not behavior:
            return False, e
        await BaseClubRC.update_club_int_field(relation_info["club_id"], "num", 1, "sub")

        await cls.send_red_dot(
            relation_info["uid"],
            RedDotType.RD_CLUB_KICK,
        )

    @classmethod
    async def kick_club(cls, uid: int, club_id: int):
        """ 踢出茶馆业务处理 """
        pass
