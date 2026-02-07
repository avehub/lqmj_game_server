"""
赛事相关接口
"""
import hashlib
import os
from datetime import datetime
from urllib import parse
from urllib.parse import urlparse, urlunparse
from lucky_game.model_rc.conf_json import ConfJsonRC
from nsanic.libs import tool_dt

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
from lucky_game.model_rc.conf_competition import ConfCompetitionRC


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
            # today = datetime.now()
            # current_month = today.month
            # 因为真实赛事跨月所以直接配置一个
            cycle_month = rule["rule_content"]["cycle_month"]
            sta, cycle = await TournamentCycleRC.get_cycle_filter(cycle_month=cycle_month)
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
        if not cycle_id:
            cycle_id = await TournamentCycleRC.get_current_cycle_id()
        sta, user_point = await TournamentUserPointRC.get_user_point(cycle_id=cycle_id, uid=uid)
        if not sta:
            has_sta, user_ticket = await TournamentUserPointRC.get_user_ticket(uid=uid)
            if has_sta:
                up_data = {
                    "ticket": user_ticket["ticket"],
                    "cycle_id": cycle_id,
                    "score": 0,
                }
                await TournamentUserPointRC.up_user_point(cycle_id, uid, up_data)
            else:
                await TournamentUserPointRC.add_user_point(cycle_id, uid, 0)
            _, user_point = await TournamentUserPointRC.get_user_point(cycle_id=cycle_id, uid=uid)
        # 计算用户排名
        rank_position = await TournamentCycleLeaderboardRC.get_uid_rank_and_difference(cycle_id, uid)
        if rank_position:
            user_point.update(rank_position)
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
        has = False
        if sta and data["total"] > 0:
            has = True
        # 获取白名单状态
        conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_TOURNAMENT_WHITE)
        if has and conf and conf["status"] and uid not in conf["special_uid"]:
            # 如果有测试数据对非白名单用户隐藏
            data["total"] = 0 
            data["list"] = [] 
        rank_position = await TournamentCycleLeaderboardRC.get_uid_rank_and_difference(cycle_id, uid, True if data["total"] == 0 else False)
        data["rank_position"] = rank_position
        return self.answer(data=data)

class JoinTournament(GameAuthApi):
    async def post(self, req: Request, **kwargs):
        """
        加入赛事
        """
        cycle_id = self.check_int(req.json.get("cycle_id"), require=False, p_name="场次ID")
        pid = self.check_int(req.json.get("pid"), require=False, default=0, p_name="邀请用户ID")
        uid = kwargs.get("u_info").get("uid")
        sta, rule = await TournamentRuleRC.get_rule_info(is_content=True)
        range_time = rule["range_time"].split("-")
        current_hour = datetime.now().hour
        if current_hour < int(range_time[0].split(":")[0]) or current_hour > int(range_time[1].split(":")[0]):
            return self.answer(StaCode.FAIL, hint=f"比赛时间为每日{rule['range_time']}点")
        if cycle_id:
            sta, msg = await TournamentCycleRC.check_cycle_status(cycle_id)
            if not sta:
                return self.answer(StaCode.FAIL, hint=msg)
        has_registered = await TournamentRegistrationRC.get_uid_registration(uid, cycle_id)
        if has_registered:
            return self.answer(StaCode.FAIL, hint="已报名")
        sta, new = await TournamentRegistrationRC.add_registration(cycle_id, uid, TournamentRegistrationRC.REGISTER_TYPE_SINGLE, pid=pid)
        if not new:
            return self.answer(StaCode.FAIL)
        return self.answer()

class CompetitionConfig(GameAuthApi):
    async def get(self, req: Request, **kwargs):
        """
        获取赛事玩法配置
        """
        competition_id = self.check_int(req.args.get("competition_id"), require=False, default=1, p_name="赛事玩法ID")
        data = await ConfCompetitionRC.cache_conf_data_by_pk(competition_id)
        return self.answer(data=data)
