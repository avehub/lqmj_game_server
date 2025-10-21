"""
茶馆成员关系管理相关接口
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.club_users import ClubUsersRC
from c_services.const.cs_enum_const import CmdClub, RedDotType
from common.public.enum_const import StaCode, ServiceEnum
from common.public.conf import C_SERVICE_SECRET_KEY
from lucky_game.model_rc.base_clubs import BaseClubRC


class JoinBlack(GameAuthApi):
    """加入小黑屋"""
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        creator = u_info.get("uid")
        uid = self.check_int(req.json.get("uid"), require=True, p_name="用户ID")
        club_id = self.check_int(req.json.get("club_id"), require=True, p_name="茶馆ID")
        behavior_id, e = await ClubUsersRC.join_black(
            uid=uid,
            club_id=club_id,
            check_uid=creator,
        )
        if not behavior_id:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class CancelBlack(GameAuthApi):
    """取消黑名单"""
    async def post(self, req: Request, **kwargs):
        relation_id = self.check_int(req.json.get("relation_id"), require=True, p_name="关系ID")
        behavior, e = await ClubUsersRC.cancel_black(relation_id)
        if not behavior:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class UpdateRelation(GameAuthApi):
    """编辑茶馆与用户关系"""
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        creator = u_info.get("uid")
        relation_id = self.check_int(req.json.get("relation_id"), require=True, p_name="关系ID")
        status = self.check_int(req.json.get("status"), require=False, default=None, minval=0, maxval=1, p_name="成员状态")
        role = self.check_int(req.json.get("role"), require=False, default=None, minval=0, maxval=1, p_name="角色")
        if status == ClubUsersRC.STATUS_BLACK:
            relation, e = await ClubUsersRC.get_club_user_by_id(relation_id)
            if not relation:
                return self.answer(StaCode.FAIL, hint=e)
            sta, e = await ClubUsersRC.join_black(
                uid=relation["uid"],
                club_id=relation["club_id"],
                check_uid=creator,
            )
            if not sta:
                return self.answer(StaCode.FAIL, hint=e)
        sta, e = await ClubUsersRC.update_club_user(
            relation_id=relation_id,
            status=status,
            role=role,
        )
        if not sta:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class KickRelation(GameAuthApi):
    """踢出茶馆"""
    async def post(self, req: Request, **kwargs):
        check_uid = kwargs.get("u_info").get("uid")
        relation_id = self.check_int(req.json.get("relation_id"), require=True, p_name="关系ID")
        relation_info, _ = await ClubUsersRC.get_club_user_by_id(relation_id)
        behavior, e = await ClubUsersRC.delete_club_user(relation_id, check_uid=check_uid)
        if not behavior:
            return self.answer(StaCode.FAIL, hint=e)
        cs_enum = ServiceEnum.find_member_by_val(ServiceEnum.C_CLUB)
        await BaseClubRC.update_club_int_field(relation_info["club_id"], "num", 1, "sub")
        data = {"secret": C_SERVICE_SECRET_KEY, "club_id": relation_info["club_id"], "uid": relation_info["uid"]}
        await self.cs2cs_by_rmq(
            cs_enum,
            CmdClub.QUIT_CLUB,
            data,
            relation_info["uid"],
        )
        await self.send_red_dot(
            relation_info["uid"],
            RedDotType.RD_CLUB_KICK,
        )
        return self.answer()


class GetClubUser(GameAuthApi):
    """获取茶馆用户列表"""
    async def get(self, req: Request, **kwargs):
        club_id = self.check_int(req.args.get("club_id"), require=True, p_name="茶馆ID")
        uid = self.check_int(req.args.get("uid"), require=False, default=None, p_name="用户ID")
        status = self.check_int(req.args.get("status"), require=False, default=ClubUsersRC.STATUS_NORMAL, p_name="成员状态")
        role = self.check_int(req.args.get("role"), require=False, default=None, p_name="角色")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        data, e = await ClubUsersRC.get_club_user_by_filter(
            club_id=club_id,
            uid=uid,
            role=role,
            status=status,
            page=page,
            page_size=page_size,
        )
        if data:
            # 处理用户在线离线状态
            if page and data["total"] > 0:
                data["list"] = await BaseUserRC.handel_online_status(data["list"])
            else:
                data = await BaseUserRC.handel_online_status(data)
        return self.answer(data=data, hint=e)

