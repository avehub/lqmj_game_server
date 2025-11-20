"""
茶馆禁止同桌相关接口
"""
from sanic import Request
from common.public.enum_const import StaCode
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.club_user_group import ClubUserGroupRC
from common.public.common_class import CommonApi


class AlterUserGroup(GameAuthApi):
    """创建用户禁止同桌"""
    async def post(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        u_ids = self.check_str(req.json.get("u_ids"), require=False, p_name="被隔离用户ID")
        club_id = self.check_int(req.json.get("club_id"), require=True, p_name="茶馆ID")
        gid, e = await ClubUserGroupRC.alter_club_user_group(
            uid=uid,
            u_ids=await CommonApi.json_by_dict(u_ids),
            club_id=club_id,
        )
        if not gid:
            return self.answer(StaCode.FAIL, hint=e)

        return self.answer(data={"gid": gid})


class GetUserGroup(GameAuthApi):
    """获取用户禁止同桌"""
    async def get(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        club_id = self.check_int(req.args.get("club_id"), require=False, p_name="茶馆ID")
        data, e = await ClubUserGroupRC.get_club_user_group_by_filter(
            uid=uid,
            club_id=club_id,
        )
        return self.answer(data=data, hint=e)
