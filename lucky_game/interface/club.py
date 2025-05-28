"""
茶馆
"""
from nsanic.libs import tool_jwt, tool_dt
from sanic import Request
from typing import List, Dict
from c_services.const.cs_enum_const import CmdWorkers
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.base_clubs import BaseClubRC
from common.public.enum_const import StaCode
from common.utils.utils import UtilsTool


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

        # TODO 我的茶馆列表
        return self.answer()


# class ClubList(BaseClub):
#     """获取茶馆列表"""
#     async def get(self, req: Request, **kwargs):
#         u_info = kwargs.get("u_info")
#         uid = u_info.get("uid")
#         # TODO 我的茶馆列表
