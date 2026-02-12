""" 赛事相关逻辑处理 """
import decimal
import random

from lucky_game.model_rc.base_award import AwardRC
from nsanic.libs.mk_random import RngMaker
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from tortoise.transactions import in_transaction

from common.model_rc.tournament_cycle_leaderboard import TournamentCycleLeaderboardRC
from common.model_rc.tournament_rewards import TournamentRewardRC
from common.model_rc.tournament_rules import TournamentRuleRC
from common.public.conf import R_UID_THRESHOLD
from common.public.enum_const import DbKey
from common.public.common_class import CommonApi
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_mails import MailsRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.base_store import GoodRC
from lucky_game.const import ReasonCostGold, CurrencyType, PayMode, OrderStatus, GainStatus, GoodsSku, PlatForm, \
    OperatingSystem, StoreType
from nsanic.libs.mult_log import NLogger

from common.model_rc.tournament_user_point import TournamentUserPointRC
from common.model_rc.tournament_cycle import TournamentCycleRC


class TournamentLogic:

    def __init__(self):
        pass



    async def distribute_order_point(self, order: dict):
        """ 分发订单积分 """
        cycle_id = await TournamentCycleRC.get_current_cycle_id()
        _, rule = await TournamentRuleRC.get_rule_info(is_content=True)
        ticket = order["num"] * rule["unit_point"]
        up_data = {"ticket": ticket}
        return await TournamentUserPointRC.up_user_point(cycle_id, order.get("uid"), up_data)

    async def send_ranking_reward(self, cycle_id: int, ranking_list: list, reward: dict):
        """ 发送排行榜奖励 """
        rank_end = 0
        reward_content = []
        sta, cycle_info = await TournamentCycleRC.get_cycle_info(cycle_id)
        NLogger.info(f"reward: {reward}")
        if sta and reward:
            rank_end = reward.get("rank_end")
            # reward_content = reward.get("reward_content")
            reward_sta, reward_content = await TournamentRewardRC.get_reward_list(reward)
        mail_type = 2
        sender = "1"
        title = "【赛事奖励】" + cycle_info["reward_name"]
        for k, v in enumerate(ranking_list):
            ranking = k + 1
            if ranking > rank_end:
                break
            uid = v.get("uid")
            if uid > R_UID_THRESHOLD:
                award_ids = reward_content[k]["award_ids"]
                content = f"尊敬的选手：{cycle_info['reward_name']}已结束，您在本次赛事中斩获第 {ranking}名的优异成绩！专属奖励已发放至您的邮件中，请及时查收并完成兑换，祝您后续赛事再创佳绩！"
                attachment = '{"award_ids": ' + f"{award_ids}" + '}'
                await MailsRC.create_mail(mail_type, sender, uid, title, content, attachment)
        return True

    async def distribute_order_good(self, order: dict) -> tuple:
        """ 分发订单商品、道具 """
        uid = order.get("uid")
        good = await GoodRC.get_good_info(order.get("sku"))
        # 发送农产品至邮件
        # mail_type = 2
        # sender = "赛事系统"
        # title = "赛事农产品领取"
        # content = f"恭喜您在赛事中获得{order['num']}个{good['name']}"
        # attachment = {"good_ids": [good["good_id"]], "num": order["num"]}
        # return await MailsRC.create_mail(mail_type, sender, uid, title, content, attachment)
        # 发送商品至背包
        express = [{
            "good_id": good["good_id"],
            "count": order["num"],
            "end_time": await GoodRC.get_good_end_time(good["type"]),
        }]
        return await UserBagRC.update_user_bag(uid, express)


    async def up_cycle_status(self, cycle_id: int):
        """ 更新赛事周期状态 """
        sta, _ = await TournamentCycleRC.update_cycle(cycle_id, {"status": TournamentCycleRC.CYCLE_STATUS_END})
        if sta:
            next_cycle_id = 1 + cycle_id
            await TournamentCycleRC.update_cycle(next_cycle_id, {"status": TournamentCycleRC.CYCLE_STATUS_STARTING})
        return True


    async def cycle_settle(self, cycle_id: int, reward_id: int):
        """ 赛事周期结算 """
        # 将用户上赛季积分清空
        # sta, _ = await TournamentUserPointRC.del_user_point(cycle_id)
        # NLogger.info(f"清空赛季积分del_user_point:{sta}")
        # 统计赛季周期获奖用户
        _, reward_info = await TournamentRewardRC.get_reward_info(reward_id)
        reward_sta, reward_user = await TournamentCycleLeaderboardRC.get_leaderboard_filter(cycle_id=cycle_id, page=1, page_size=reward_info["rank_end"])
        NLogger.info(f"reward_user:{reward_user}")
        if reward_sta and reward_user:
            award_u_list = [item for item in reward_user["list"]]
            # 发送榜奖励
            await self.send_ranking_reward(cycle_id, award_u_list, reward_info)

    async def warm_up_cycle(self, cycle_id: int) -> tuple:
        """获取热身赛奖励发放状态及发放赛季ID"""
        status = False
        # 用户热身赛奖励累计发放直到写入下一个周赛
        sta, cycle_info = await TournamentCycleRC.get_cycle_info(cycle_id)
        next_cycle_id = 1 + cycle_id
        if cycle_info and cycle_info["cycle_type"] == 1:
            next_cycle_info = await TournamentCycleRC.get_cycle_info(next_cycle_id)
            if next_cycle_info["cycle_type"] == 0:
                status = True
        return status, next_cycle_id


    @staticmethod
    async def check_uid_white_status(uid: int) -> bool:
        """ 检查用户是否在白名单 """
        status = False
        # 获取赛事白名单
        conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_TOURNAMENT_WHITE)
        if conf_data and conf_data["status"]:
            if uid in conf_data["special_uid"]:
                status = True
        return status
    
    @staticmethod
    async def send_ranking_reward_by_one(cycle_id: int, uid: int, award_id: int, ranked: int):
        """ 发送玩家奖励至邮件 """
        reward_content, _ = await AwardRC.get_award_info(award_id)
        sta, cycle_info = await TournamentCycleRC.get_cycle_info(cycle_id)
        NLogger.info(f"cycle_id: {cycle_id}, uid: {uid}, reward_content: {reward_content}")
        mail_type = 2
        sender = "1"
        title = "【赛事奖励】" + cycle_info["reward_name"]
        if uid > R_UID_THRESHOLD:
                content = f"尊敬的选手：{cycle_info['reward_name']}已结束，您在本次赛事中斩获第 {ranked}名的优异成绩！专属奖励已发放至您的邮件中，请及时查收并完成兑换，祝您后续赛事再创佳绩！"
                attachment = '{"award_ids": ' + f"{award_id}" + '}'
                await MailsRC.create_mail(mail_type, sender, uid, title, content, attachment)
        return True




