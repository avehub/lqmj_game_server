from sanic import Request
from common.public.conf import R_UID_THRESHOLD, ROBOT_AVATAR
from common.public.enum_const import Sex, ServiceEnum, CacheKey, GameType
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.base_user import BaseUserRC


class UserInfo(GameAuthApi):
    """ 查询用户信息 """

    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        q_uid = req.args.get("uid")
        if q_uid:
            uid = q_uid
        data = await BaseUserRC.cache_by_uid(uid)
        return self.answer(data=data)

