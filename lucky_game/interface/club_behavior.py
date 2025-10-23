"""
茶馆用户行为记录相关接口
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.extra_club_behavior import ExtraClubBehaviorRC
from lucky_game.model_rc.club_users import ClubUsersRC
from common.public.common_class import CommonApi


class GetBehaviorExtra(GameAuthApi):
    """获取用户行为记录"""
    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        creator = u_info.get("uid")
        uid = self.check_int(req.args.get("uid"), require=False, p_name="用户ID")
        club_id = self.check_int(req.args.get("club_id"), require=True, p_name="茶馆ID")
        status = self.check_int(req.args.get("status"), require=False, default=99, p_name="行为状态")
        page = self.check_int(req.args.get("page"), require=False, minval=1, p_name="分页页码")
        page_size = self.check_int(req.args.get("amount"), require=False, minval=1, p_name="每页数量")
        data, e = await ExtraClubBehaviorRC.get_behavior_by_filter(
            uid=uid,
            club_id=club_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        if page and data["list"]:
            ids = [item.get("uid") for item in data["list"]]
            role_data, _ = await ClubUsersRC.get_club_user_by_filter(uid=list(set(ids)), club_id=club_id)
            data["list"] = await CommonApi.merge_by_key(data["list"], role_data, "uid", ["role"])
        if not page and data:
            ids = [item.get("uid") for item in data]
            role_data, _ = await ClubUsersRC.get_club_user_by_filter(uid=list(set(ids)), club_id=club_id)
            data = await CommonApi.merge_by_key(data, role_data, "uid", ["role"])
        return self.answer(data=data, hint=e)

