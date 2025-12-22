"""
赛事相关接口
"""
import hashlib
import os
from datetime import datetime
from urllib import parse
from urllib.parse import urlparse, urlunparse

from sanic import Request, response

from c_services.const.cs_enum_const import CmdRoom
from lucky_game.base_api import GameAuthApi
from nsanic.libs.tool import read_file, json_parse
from common.public.enum_const import StaCode, ServiceEnum
from lucky_game.handler.random_utils import generate_random_string
from lucky_game.handler.wechat import WeChat
from common.public.conf import WeChatConf, C_SERVICE_SECRET_KEY
from common.model_rc.tournament_rules import TournamentRuleRC
from common.model_rc.tournament_cycle import TournamentCycleRC
from common.model_rc.tournament_rewards import TournamentRewardRC
from common.model_rc.tournament_registration import TournamentRegistrationRC
from common.model_rc.tournament_cycle_leaderboard import TournamentCycleLeaderboardRC
from common.model_rc.tournament_user_point import TournamentUserPointRC
from lucky_game.model_rc.base_award import AwardRC


class TournamentConfig(GameAuthApi):
    CACHE_KEY = "tournament_config"
    async def get(self, req: Request, **kwargs):
        """
        获取赛事配置
        """
        data = await self.conf.rds.get_item(self.CACHE_KEY)
        if not data:
            # 获取赛事规则
            sta, rule = await TournamentRuleRC.get_rule_info(rule_id=1)
            # 获取赛事周期
            sta, cycle = await TournamentCycleRC.get_cycle_filter()
            if cycle:
                for item in cycle:
                    # 获取赛事奖励
                    _, item["cycle_reward"] = await TournamentRewardRC.get_reward_info(item["reward_id"])
            data = {
                'rule': rule,
                'cycle': cycle,
            }
            await self.conf.rds.set_item(self.CACHE_KEY, data, ex_time=3600) if data else None
        else:
            if isinstance(data, bytes):
                data = json_parse(data.decode())
        return self.answer(data=data)

class TournamentUserPoint(GameAuthApi):
    async def get(self, req: Request, **kwargs):
        """
        获取用户赛事积分
        """
        uid = kwargs.get("u_info").get("uid")
        cycle_id = self.check_int(req.args.get("cycle_id"), require=False, p_name="赛事周期ID")
        sta, user_point = await TournamentUserPointRC.get_user_point(cycle_id=cycle_id, uid=uid)
        if not sta:
            user_point = {"cycle_id": cycle_id, "uid": uid, "score": 0, "rank_num": 0, "ticket": 0}
        return self.answer(data=user_point)

class TournamentLeaderboard (GameAuthApi):
    async def get(self, req: Request, **kwargs):
        """
        获取赛事排行榜
        """
        uid = kwargs.get("u_info").get("uid")
        cycle_id = self.check_int(req.args.get("cycle_id"), require=True, p_name="赛事周期ID")
        page = self.check_int(req.args.get("page"), require=False, default=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, default=10, p_name="每页数量")
        sta, data = await TournamentCycleLeaderboardRC.get_leaderboard_filter(cycle_id=cycle_id, page=page, page_size=page_size)
        return self.answer(data=data)

class JoinTournament(GameAuthApi):
    async def post(self, req: Request, **kwargs):
        """
        加入赛事
        """
        cycle_id = self.check_int(req.json.get("cycle_id"), require=False, p_name="场次ID")
        pid = self.check_int(req.json.get("pid"), require=True, p_name="邀请用户ID")
        uid = kwargs.get("u_info").get("uid")
        has_registered = await TournamentRegistrationRC.get_uid_registration(uid, cycle_id)
        if has_registered:
            return self.answer(StaCode.FAIL, hint="已报名")
        sta, new = await TournamentRegistrationRC.add_registration(round_id, uid, TournamentRegistrationRC.REGISTER_TYPE_SINGLE, pid=pid)
        if not new:
            return self.answer(StaCode.FAIL)
        return self.answer()
