"""
茶馆用户行为记录相关接口
"""
from sanic import Request
from common.public.enum_const import StaCode
from datetime import datetime, timedelta
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.club_users import ExtraClubBehaviorRC
from lucky_game.model_rc.base_user import BaseUserRC
from nsanic.libs.tool import json_encode, json_parse


class GetBehaviorExtra(GameAuthApi):
    """获取用户行为记录"""
    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        creator = u_info.get("uid")
        uid = self.check_int(req.json.get("uid"), require=False, p_name="用户ID")
        club_id = self.check_int(req.json.get("club_id"), require=True, p_name="茶馆ID")
        data, e = await ExtraClubBehaviorRC.get_behavior_by_filter(
            uid=uid,
            club_id=club_id,
        )
        return self.answer(data=data, hint=e)