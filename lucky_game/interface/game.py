from sanic import Request
from c_services.const.cs_enum_const import CmdWorkers
from common.public.conf import R_UID_THRESHOLD, ROBOT_AVATAR
from common.public.enum_const import Sex, ServiceEnum, CacheKey, GameType
from lucky_game.base_api import GameAuthApi
from lucky_game.const import RED_DOTS_OPPORTUNITY_MAP, ActivityItem
from lucky_game.model_db.extra import RecordsGameGrade
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.conf_leisure import LeisureConfRC


class GetLeisureList(GameAuthApi):
    """ 休闲场列表 """

    async def get(self, req: Request, **kwargs):
        cs_type = self.check_int(req.args.get("cs_type"), require=True, p_name="cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        not cs_enum and self.answer(self.sta_code.ERR_ARG)
        if not isinstance(cs_enum.desc, GameType) or cs_enum.desc != GameType.LEISURE:
            self.answer(self.sta_code.ERR_ARG, hint="非休闲场")

        data = await LeisureConfRC.cache_all_by_cs_type(cs_type=cs_type)
        return self.answer(data=data)


class LeisureMatching(GameAuthApi):
    """ 休闲场-快速匹配 """

    async def get(self, req: Request, **kwargs):
        cs_type = self.check_int(req.args.get("cs_type"), require=True, p_name="子服务类型")
        play_type = self.check_int(req.args.get("play_type"), require=True, p_name="玩法类型")
        level = self.check_int(req.args.get("level"), require=True, p_name="级别")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        not cs_enum and self.answer(self.sta_code.ERR_ARG)
        if not isinstance(cs_enum.desc, GameType) or cs_enum.desc != GameType.LEISURE:
            self.answer(self.sta_code.ERR_ARG, hint="非休闲场")

        data = await LeisureConfRC.cache_all_by_cs_type(cs_type=cs_type)
        return self.answer(data=data)

