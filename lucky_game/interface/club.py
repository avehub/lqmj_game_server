"""
茶馆
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.base_clubs import BaseClubRC
from lucky_game.model_rc.base_user import BaseUserRC
from common.public.enum_const import StaCode


class BaseClub(GameAuthApi):
    async def check_solid_params(self, req: Request):
        """ 检查固有参数 """
        pass


class ClubCreate(BaseClub):
    """创建茶馆"""

    async def post(self, req: Request, **kwargs):
        # 参数校验
        name = req.json.get("name")
        self.check_str(name, require=True, minlen=2, maxlen=10, p_name="茶馆名称")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        room_card = u_info.get("room_card")
        # 保存到数据库
        suc, e = await BaseClubRC.create_club(name, uid, room_card)
        if not suc:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class ClubList(BaseClub):
    """获取茶馆列表"""
    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        result, e = await BaseClubRC.get_club_by_uid(uid)
        if not result:
            return self.answer(StaCode.FAIL, hint=e)

        # 处理茶馆主头像
        for club in result:
            user = await BaseUserRC.get_session_key(club['uid'])
            club["avatar"] = user["avatar"] if user else ""
        return self.answer(data=result)


class ClubHall(BaseClub):
    """茶馆大厅"""
    async def get(self, req: Request, **kwargs):
        club_id = req.json.get("id")
        result, e = await BaseClubRC.get_club_by_id(club_id)
        if not result:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer(data=result)


class ClubJoin(BaseClub):
    """加入茶馆"""
    async def post(self, req: Request, **kwargs):
        pass


class ClubLeave(BaseClub):
    """离开茶馆"""
    async def post(self, req: Request, **kwargs):
        pass


class ClubInfo(BaseClub):
    """茶馆详情"""
    pass