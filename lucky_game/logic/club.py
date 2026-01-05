""" 茶馆相关逻辑处理 """

from c_services.const.cs_enum_const import RedDotType, CmdWorkers
from common.public.enum_const import DbKey, ServiceEnum
from common.public.common_class import CommonApi
from lucky_game.model_rc.club_users import ClubUsersRC
from lucky_game.model_rc.extra_club_behavior import ExtraClubBehaviorRC
from lucky_game.model_rc.extra_club_event import ExtraClubEventRC
from common.public.conf import ENV, C_SERVICE_SECRET_KEY

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
    async def leave_club_before(cls, uid: int, club_id: int, check_uid: int = None,
                                status: int = ExtraClubBehaviorRC.BEHAVIOR_STATUS_DEFAULT):
        """ 离开茶馆前业务处理 """
        has, msg = await ExtraClubBehaviorRC.get_behavior_by_filter(uid=uid, club_id=club_id, status=status, type=ExtraClubBehaviorRC.BEHAVIOR_OUT_INDEX)
        if not has:
            sta, e = await ExtraClubBehaviorRC.create_club_behavior(
                ExtraClubBehaviorRC.BEHAVIOR_OUT_INDEX,
                uid,
                club_id,
                check_uid=0 if check_uid == uid else check_uid,  # 主动离开check_id=0
                status=status,
            )
            if not sta:
                return False, e
        return True, "OK"

    @classmethod
    async def leave_club_check(cls, behavior_info: dict, check_uid: int = None,
                               status: int = ExtraClubBehaviorRC.BEHAVIOR_STATUS_SUCCEED):
        """ 离开茶馆审批处理 """
        sta, e = await ExtraClubBehaviorRC.update_club_behavior(behavior_info["id"],
                                                                {"status": status, "check_uid": check_uid})
        if not sta:
            return False, e
        return True, "OK"

    @classmethod
    async def leave_club_check(cls, behavior_info: dict, check_uid: int = None,
                               status: int = ExtraClubBehaviorRC.BEHAVIOR_STATUS_SUCCEED):
        """ 离开茶馆审批处理 """
        sta, e = await ExtraClubBehaviorRC.update_club_behavior(behavior_info["id"],
                                                                {"status": status, "check_uid": check_uid})
        if not sta:
            return False, e

        return True, "OK"

    @classmethod
    async def leave_club_after(cls, relation_info: dict, check_uid: int = None):
        """ 离开茶馆后业务处理 """
        await ClubUsersRC.delete_club_user(relation_info["id"], check_uid=check_uid)
        from lucky_game.model_rc.base_clubs import BaseClubRC
        sta, msg = await BaseClubRC.update_club_int_field(relation_info["club_id"], "num", 1, "sub")
        await cls.send_red_dot(
            relation_info["uid"],
            RedDotType.RD_CLUB_KICK,
        )
        return True, "OK"

    @classmethod
    async def kick_club(cls, relation_info: dict, check_uid: int):
        """ 踢出茶馆业务处理 """
        await cls.leave_club_before(relation_info["uid"], relation_info["club_id"], check_uid=check_uid,
                                    status=ExtraClubBehaviorRC.BEHAVIOR_STATUS_SUCCEED)
        await cls.leave_club_after(relation_info, check_uid=check_uid)

        return True, "OK"

    @classmethod
    async def send_red_dot_manager(cls, club_id: int, check_uid: int = None, cmd: int = RedDotType.RD_CLUB_APPLY):
        """ 红点通知茶馆管理员 """
        club_manage, e = await ClubUsersRC.get_club_user_by_filter(role=[1, 9], club_id=club_id)
        if club_manage:
            for manage in club_manage:
                if check_uid != manage.get("uid"):
                    await cls.send_red_dot(
                        manage.get("uid"),
                        cmd,
                    )
        return True, "OK"

    @classmethod
    async def club_event(cls, club_id, event_type, uid, num: int = None, room_id: int = None, check_uid: int = None):
        """ 茶馆日常事件Worker """
        msg = {
            "club_id": club_id,
            "event_type": event_type,
            "uid": uid,
            "num": num,
            "room_id": room_id,
            "check_uid": check_uid,
        }
        await cls.push_task2worker(CmdWorkers.CLUB_EVENT_LOG, msg, uid)

    @classmethod
    async def insert_club_event(cls, club_id, event_type, uid, num: int = None, room_id: int = None, check_uid: int = None):
        """ 茶馆日常事件写入 """
        event_msg = ""
        if num and event_type in [ExtraClubEventRC.EVENT_TYPE["FUND_RECHARGE"],
                                  ExtraClubEventRC.EVENT_TYPE["CLOSE_LOG"],
                                  ExtraClubEventRC.EVENT_TYPE["FUND_RECHARGE"],
                                  ExtraClubEventRC.EVENT_TYPE["CLOSE_LOG"]]:
            event_msg = ExtraClubEventRC.EVENT_MSG[event_type].format(price=num)
        if num and room_id and event_type == ExtraClubEventRC.EVENT_TYPE["FUND_CONSUME"]:
            event_msg = ExtraClubEventRC.EVENT_MSG[event_type].format(
                price=num,
                room_id=room_id,
            )
        if event_type in (ExtraClubEventRC.EVENT_TYPE["APPROVAL_LOG"], ExtraClubEventRC.EVENT_TYPE["OUT_CLUB"],
                          ExtraClubEventRC.EVENT_TYPE["KICK_CLUB"]):
            event_msg = ExtraClubEventRC.EVENT_MSG[event_type].format(
                check_uid=check_uid,
                uid=uid,
            )
        sta, _ = await ExtraClubEventRC.create_event(club_id, event_type, uid, event_msg)
        if not sta:
            return False, "写入事件记录失败"
        return True, "OK"


