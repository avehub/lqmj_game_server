import tortoise
from sanic import Request
from common.public.conf import R_UID_THRESHOLD, ROBOT_AVATAR
from common.public.enum_const import Sex, ServiceEnum
from lucky_game.base_api import GameAuthApi
from lucky_game.model_db.extra import RecordsGameGrade
from lucky_game.model_rc.game_rooms import GameRoomsRC
from common.public.enum_const import ServiceEnum, CacheKey


class RefreshAssets(GameAuthApi):
    """ 刷新玩家资产 """

    async def get(self, _: Request, **kwargs):
        u_info = kwargs.get("u_info")
        data = {
            "gold": u_info.get("gold"),
            "diamond": u_info.get("diamond")
        }
        return self.answer(data=data)


class QueryUserGameGrade(GameAuthApi):
    """查询玩家游戏战绩 """
    async def get(self, req: Request, **kwargs):
        cs_type = self.check_int(req.args.get("cs_type"), require=True, minval=ServiceEnum.C_WORKERS, p_name="cs_type")
        if not ServiceEnum.find_member_by_val(cs_type):
            self.answer(self.sta_code.ERR_ARG, hint="参数错误")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        query_params = {"uid": uid, "cs_type": cs_type}
        try:
            data = await RecordsGameGrade.get_by_dict(query_params, limit=15)
        except tortoise.exceptions.OperationalError:
            data = {}
        if not data:
            self.answer(self.sta_code.PASS, hint="无数据")

        data_model = {"games_info": data}
        self.answer(data={"games_info": data})


class QueryUserIsInCService(GameAuthApi):
    """ 查询玩家是否在子服务中（游戏中） """
    async def get(self, _: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        cs_info = await self.conf.rds.get_hash(CacheKey.IN_SERVICE, uid, jsparse=True)
        if not cs_info:
            self.answer(self.sta_code.FAIL, hint="不在游戏中")
        self.answer(data=cs_info)


class QueryChatUserInfo(GameAuthApi):
    """ 查询聊天用户信息 """

    # todo:VIP等级、排位等级、装扮等即时性要求不高，可通过web接口查询（可重新封装一个查询聊天信息的借口）

    async def get(self, req: Request, **_b):
        uid = self.check_int(req.args.get("uid"), require=True, minval=1000, p_name="uid")

        pass
