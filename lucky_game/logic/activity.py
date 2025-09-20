""" 活动、奖品相关逻辑处理 """
import decimal
import random
import ast
import traceback
from datetime import datetime
from typing import Union, Tuple

from nsanic.libs import tool_dt
from tortoise.transactions import in_transaction

from c_services.const.cs_enum_const import CmdRoom
from common.public.conf import C_SERVICE_SECRET_KEY
from common.public.enum_const import ServiceEnum, DbKey, CacheKey
from lucky_game.const import ActivityType, ActivitySta, AwardType, PayType, ReasonCostGold, OrderStatus, GoodsSku, \
    PlatForm
from lucky_game.config import conf_srv, ConfSrv
from common.public.common_class import CommonApi
from lucky_game.model_rc.base_activity import ConfActivityRC
from lucky_game.model_rc.base_award import AwardRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.user_activity import LogUserActivityRC, UserActivityProgressRC, AwardGainsRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from nsanic.libs.mult_log import NLogger
from lucky_game.model_rc.conf_json import ConfJsonRC
from nsanic.libs.tool import json_parse, json_encode
from lucky_game.model_rc.base_store import GoodRC
from lucky_game.model_rc.order import OrderRC
from c_services.base.base_server import BaseServer


async def atc_behavior(uid: int, act_id: int, act_type: int, award_type: int, pay_type: int) -> bool:
    """活动行为记录"""
    # 记录参与活动日志
    log_id, _ = await LogUserActivityRC.add_log(uid, act_id, pay_type=pay_type, award_type=award_type)
    # 用户行为记录
    return True


async def act_count(uid: int, act_id: int, period: str):
    """ 获取用户已参与活动次数 """
    start_time, end_time = await CommonApi.get_time_range(period)
    sta, signed = await LogUserActivityRC.activity_frequency(uid=uid, act_id=act_id, start_time=start_time,
                                                             end_time=end_time, count=True)
    return sta, signed


class Base:
    conf: ConfSrv = conf_srv

    async def act_handler(self, activity: dict, u_info: dict, award_type: int, pay_mode: int = None,
                          platform: int = None, return_url: str = None):
        """ 根据活动类型获取活动操作 """
        uid = u_info.get("uid")
        act_type = activity.get("act_type")
        act_id = activity.get("act_id")
        if act_type == ActivityType.FIRST_CHARGE:
            act_total = await FirstCharge().pay_count(uid)
        else:
            _, act_total = await act_count(uid, act_id, period="day")
        NLogger.info(f"act_count:{act_total}")
        join_limit_day = activity.get("join_limit_day")
        if join_limit_day > 0:
            if act_total > 0 and act_total + 1 > join_limit_day:
                return False, "已达最大参与次数", {}
        if act_type == ActivityType.LUCK_SIGN_IN:
            sta, msg, data = await SignIn().handler(activity, uid, award_type)
            return sta, msg, {"award": data, "pay_info": {}}
        elif act_type == ActivityType.PACKAGE:
            sta, msg, data = await Package().handler(activity, uid, award_type, platform)
            return sta, msg, {"award": data, "pay_info": {}}
        elif act_type == ActivityType.SHARE:
            sta, msg, data = await Common().handler(activity, uid, award_type)
            return sta, msg, {"award": data, "pay_info": {}}
        elif act_type == ActivityType.INFINITE_PLAY:
            conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_RELIEF)
            NLogger.info(f"conf_data:{conf_data} u_info {u_info}")
            if u_info.get("gold") > conf_data.get("min_gold"):
                return False, "暂不符合领取条件", {}
            sta, msg, data = await Common().handler(activity, uid, award_type)
            return sta, msg, {"award": data, "pay_info": {}}
        elif act_type in [ActivityType.FIRST_CHARGE, ActivityType.REPLENISH_GIFT, ActivityType.REVIVE_GIFT,
                          ActivityType.RETURN_GIFT]:
            sta, msg, data = await FirstCharge().handler(uid, activity, award_type, pay_mode, platform, return_url)
            return sta, msg, {"award": [], "pay_info": data}
        elif act_type == ActivityType.AUTHENTICATION:
            pi = u_info.get("pi")
            if not pi:
                return False, "请先认证", {}
            sta, msg, data = await Common().handler(activity, uid, award_type)
            return sta, msg, {"award": data, "pay_info": {}}


    async def act_by_awards(self, uid: int, activity: dict):
        """ 按活动配置获取奖励信息 """
        act_type = activity.get("act_type")
        once_awards = activity.get("once_awards")
        condition_awards = activity.get("condition_awards")
        once_item, condition_item = await self.atc_awards(once_awards=once_awards, condition_awards=condition_awards)
        if not once_item and not condition_item:
            return once_item, condition_item
        if act_type == ActivityType.LUCK_SIGN_IN:
            once_awards = await SignIn().get_random_rewards(uid, act_type, once_item, True)
        else:
            once_awards = once_item

        return once_awards, condition_item

    async def atc_awards(self, once_awards: dict = None, condition_awards: dict = None):
        """ 获取奖励内容 """
        once_items = condition_items = []
        if once_awards:
            ids = once_awards["award_ids"]
            once_items, _ = await AwardRC.get_award_by_filter(award_id=ids)
        if condition_awards:
            ids = condition_awards["award_ids"]
            condition_items, _ = await AwardRC.get_award_by_filter(award_id=ids, order_field="award_id")
            # if act_type == ActivityType.LUCK_SIGN_IN:
        return once_items, condition_items

    async def act_awards_other(self, act_type):
        """
        根据活动类型获取活动信息
        """
        other_awards = {}
        if act_type == ActivityType.LUCK_SIGN_IN:
            conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_LUCK)
            if conf_data:
                other_awards = conf_data[random.randint(0, len(conf_data) - 1)]
        return other_awards

    async def gain_awards(self, uid: int, awards: any = None, act_id: int = 0, award_id: int = 0,
                          explain: str = "参加活动",
                          reward_type: int = 0) -> bool:
        """ 发放奖励 """
        sta = False
        field_values = await ExtraUserResourceChangesRC.change_field()
        # 奖励内容解析
        if awards is None:
            if award_id:
                award_content, _ = await AwardRC.get_award_info(award_id=award_id)
                NLogger.info(f"发放奖励完整数据：award_content={award_content}")
                awards = award_content["rewards"]
        NLogger.info(f"发放奖励内容解析：awards={awards}")
        if awards and isinstance(awards, list):
            for award in awards:
                award_type = award.get("type")
                award_amount = award.get("amount")
                if award_type in field_values:
                    NLogger.info(f"发放奖励：uid={uid}，award_type={award_type}，award_amount={award_amount}")
                    sta, e = await AwardGainsRC.add_gains(
                        uid,
                        act_id,
                        award_id if award_id else award.get("award_id"),
                        reward_type,
                        remark={"type": award_type, "amount": award_amount}
                    )
                    NLogger.info(f"发放奖励入库结果：sta={sta}，e={e}")
        else:
            NLogger.info(f"发放奖励：uid={uid}，reward_type={awards['type']}，reward_amount={awards['amount']}")
            sta, e = await AwardGainsRC.add_gains(
                uid,
                act_id,
                award_id if award_id else awards["award_id"],
                reward_type,
                remark={"type": awards['type'], "amount": awards['amount']}
            )
        return sta

    async def give_awards(self, uid: int, award_id: int, act_id: int = None, reason: int = None) -> Tuple[bool, str]:
        """ 领取奖励 """
        sta, await_gain = await AwardGainsRC.get_award_gains(uid=uid, act_id=act_id, type_id=award_id, status=0)
        if not sta:
            return False, "暂无可领取奖励"
        async with in_transaction(connection_name=DbKey.DEFAULT):
            gain_sta, e = await AwardGainsRC.up_gains(
                up_data={"status": 99},
                uid=uid,
                act_id=act_id,
                type_id=award_id,
                status=0,
            )
            if gain_sta:
                NLogger.info(f"自动领取奖励：await_gain={await_gain}")
                for award in await_gain:
                    remark = award.get("remark")
                    NLogger.info(f"自动领取奖励：award={remark}")
                    if remark:

                        NLogger.info(f"自动领取奖励remark转化前：remark={type(remark)} {remark}")
                        remark = ast.literal_eval(remark)
                        NLogger.info(f"自动领取奖励remark转化后：remark={type(remark)} {remark}")
                        reward_type = remark.get("type")
                        reward_amount = remark.get("amount")
                        if reason is None:
                            reason = ReasonCostGold.ACTIVITY_GIFT
                        sta, e = await ExtraUserResourceChangesRC.change_user_resource(uid, reward_type, reward_amount,
                                                                                       reason=reason)
                        NLogger.info(f"领取奖励：sta={sta}, e={e}")
        return sta, e

    async def act_progress(self, ac: dict, u_info: dict):
        """ 查询当前用户参与活动进度 """
        try:
            act_type = ac.get("act_type")
            act_id = ac.get("act_id")
            uid = u_info.get("uid")
            progress = {}
            gains = []
            # 根据活动类型判断是否需要查询进度或奖励
            query_progress = query_gains = True
            if act_type == ActivityType.LUCK_SIGN_IN:
                start_time, end_time = await CommonApi.get_time_range()
            elif act_type in [ActivityType.PACKAGE, ActivityType.INFINITE_PLAY]:
                start_time, end_time = await CommonApi.get_time_range("day")
            else:
                start_time = end_time = None
                query_progress = query_gains = False
            # 查询进度
            if query_progress:
                progres_sta, progress = await UserActivityProgressRC.get_activity_progress_once(
                    uid=uid,
                    act_id=act_id,
                    start_time=start_time,
                    end_time=end_time,
                )
                if not progres_sta:
                    return False, "活动进度异常", progress, {}
            # 查询奖励
            if query_gains:
                gain_sta, gains = await AwardGainsRC.get_award_gains(
                    uid=uid,
                    act_id=act_id,
                    start_time=start_time,
                    end_time=end_time,
                )
                if not gain_sta:
                    return False, "获取领取奖励内容异常", {}, gains

            return True, "成功", progress, gains
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for frame in tb:
                NLogger.error(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            NLogger.error(f"获取活动进度异常：e={e}")

    async def up_act_progress(self, uid: int, act_id: int, act_type: int, status: int = 0):
        result = {}
        current_value = 1
        # 活动类型时间维度（默认）：永久、单次
        period = "perpetual"
        if act_type == ActivityType.LUCK_SIGN_IN:
            # 活动类型时间维度：月度
            period = "month"
        elif act_type in [ActivityType.PACKAGE, ActivityType.SHARE, ActivityType.INFINITE_PLAY]:
            # 活动类型时间维度：每天
            period = "day"
        start_time, end_time = await CommonApi.get_time_range(period)
        progres_sta, progress = await UserActivityProgressRC.get_activity_progress_once(
            uid=uid,
            act_id=act_id,
            start_time=start_time,
            end_time=end_time,
        )
        NLogger.info(f"参与活动进度查询：uid {uid} act_id {act_id} progres_sta {progres_sta} progress {progress}")
        if progres_sta and progress:
            if act_type in [ActivityType.PACKAGE, ActivityType.SHARE, ActivityType.INFINITE_PLAY,
                            ActivityType.LUCK_SIGN_IN]:
                current_value += progress.get("current_value", 0)
            await UserActivityProgressRC.up_progress(
                up_data={
                    "status": status,
                    "current_value": current_value,
                },
                progress_id=progress["progress_id"],
            )
        else:
            end_date = 0
            await UserActivityProgressRC.add_progress(
                uid=uid,
                act_id=act_id,
                current_value=current_value,
                deadline=end_date,
                status=ActivitySta.ACT_INCOMPLETE
            )
        return True, "成功", result

    async def __user_box(self, uid: int, amount: [int, decimal.Decimal], field="gold", explain: str = ""):
        """背包性资源奖励发放"""
        sta, e = ExtraUserResourceChangesRC.change_user_resource(uid, field, amount,
                                                                 reason=ReasonCostGold.OPEN_TREASURE_BOX)
        return sta, e


class SignIn(Base):
    """ 签到活动 """
    SESSION_SIGNED_KEY = "signed"

    async def handler(self, activity: dict, uid: int, award_type: int):
        """ 处理签到活动 """
        # 检查用户今日是否已签到
        act_type = activity.get("act_type")
        act_id = activity.get("act_id")
        pay_type = PayType.BY_FREE
        NLogger.info(f"act_type={act_type},act_id={act_id},award_type={award_type}")
        if award_type == AwardType.SIGN_IN_RF:
            sta, signed = await act_count(uid, act_id, "day")
            if sta and signed:
                return False, "今日已签到", {}
        else:
            # 广告签到
            pay_type = PayType.BY_WATCH_AD

        # 获取返给用户签到奖励
        rewards = await self.cache_get_signed(uid)
        NLogger.info(f"rewards={rewards}")
        if not rewards:
            return False, "奖励配置错误", {}
        awards = await self.draw_reward(rewards["rewards"])
        NLogger.info(f"awards={awards}")
        # 发放奖励
        gain_sta = await self.gain_awards(uid, awards=awards, act_id=act_id, explain=activity.get("act_name"))
        if not gain_sta:
            return False, "奖励发放失败", {}
        # 自动领取
        await self.give_awards(uid, awards["award_id"], act_id, reason=ReasonCostGold.RAFFLE_LUCK)
        # 累计签到检查并发放奖励
        if award_type == AwardType.SIGN_IN_RF:
            sta, current_value = await self.sign_progress(uid, act_id)
            _, condition_awards = await self.atc_awards(condition_awards=activity["condition_awards"])
            await self.gain_condition_awards(condition_awards, uid, act_id, current_value)
        # 更新记录
        await atc_behavior(uid, act_id, act_type, award_type, pay_type)
        once_item, _ = await self.act_by_awards(uid, activity)
        return True, "成功", {"gain_awards": [awards], "once_awards": once_item}

    async def check_today_sign(self, uid: int) -> dict:
        """ 检查用户今日是否已签到 """
        signed = await self.cache_get_signed(uid)
        NLogger.info(f"signed={signed}")
        return signed if signed else {}

    async def cache_set_signed(self, uid, data):
        """缓存用户签到信息"""
        key = f"{self.SESSION_SIGNED_KEY}:{uid}"
        sta = await self.conf.rds.set_item(key, data)
        expire_num = await CommonApi.seconds_since_midnight()
        await self.conf.rds.expired(f"{self.SESSION_SIGNED_KEY}", expire_num)
        return sta

    async def cache_get_signed(self, uid):
        """查看用户签到信息"""
        data = await self.conf.rds.get_item(f"{self.SESSION_SIGNED_KEY}:{uid}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    async def get_random_rewards(self, uid, act_type, awards, refresh: bool = False):
        """ 根据奖励类型随机获取奖励列表 """
        rewards = await self.check_today_sign(uid)
        if not refresh and rewards:
            return rewards
        rewards = {
            "luck": rewards["luck"] if rewards else await self.act_awards_other(act_type),
            "rewards": []
        }
        for award in awards:
            content = award["content"]
            random_num = random.randint(0, len(content["rewards"]) - 1)
            # 从该类型中随机选择一个奖励
            reward = content["rewards"][random_num]
            reward["award_id"] = award["award_id"]
            reward["probability"] = content["probability"]
            rewards["rewards"].append(reward)

        # 将返回的奖励进行缓存
        await self.cache_set_signed(uid, rewards)
        return rewards

    async def draw_reward(self, rewards: list) -> dict:
        """ 从奖励列表中抽取一个奖励 """
        if not rewards:
            raise ValueError("奖励列表不能为空")
        weights = []
        new_rewards = []
        for reward in rewards:
            if reward["probability"] > 0:
                weights.append(reward["probability"])
                new_rewards.append(reward)
        return random.choices(new_rewards, weights=weights)[0]

    async def gain_condition_awards(self, act_awards: dict, uid: int, act_id: int, current_value: int = 0):
        """ 根据条件获取奖励 """
        sta = False
        # 获取签到奖励及规则
        NLogger.info(f"act_awards={act_awards}")
        for rule in act_awards:
            NLogger.info(f"rule={rule}")
            # 检查是否满足条件
            if rule["content"]["day"] != current_value:
                continue
            if rule["content"]["day"] == current_value:
                # 发放奖励
                sta = await self.gain_awards(uid, awards=rule["content"]["rewards"], act_id=act_id,
                                             award_id=rule["award_id"])
                break
        return sta

    async def sign_progress(self, uid: int, act_id: int):
        """签到进度更新"""
        # 只有每日免费签到才可更新进度
        start_date, end_date = await CommonApi.get_time_range("month")
        sta, progress = await UserActivityProgressRC.get_activity_progress_once(uid=uid, act_id=act_id)
        NLogger.info(f"更新累计签到进度前 查询当前进度：uid {uid} act_id {act_id} progres_sta {sta} progress {progress}")
        current_value = 1
        now = int(datetime.now().timestamp())
        if sta and progress:
            if progress["deadline"] != end_date:
                await UserActivityProgressRC.up_progress(
                    up_data={
                        "current_value": current_value,
                        "deadline": end_date,
                        "join_time": now,
                        "created": now,
                    },
                    progress_id=progress["progress_id"],
                )
            else:
                current_value += progress.get("current_value", 0)
                await UserActivityProgressRC.up_progress(
                    up_data={
                        "current_value": current_value,
                    },
                    progress_id=progress["progress_id"],
                )
        else:
            await UserActivityProgressRC.add_progress(
                uid=uid,
                act_id=act_id,
                current_value=current_value,
                deadline=end_date,
                status=ActivitySta.ACT_COMPLETED,
                time_node=now,
            )

        return True, current_value

    async def progress_data(self, uid: int, ac: dict, progress: dict, award_gains: list) -> dict:
        if not progress:
            progress = {}
        progress["today_total"] = 0
        sta, signed = await act_count(uid, ac.get("act_id"), "day")
        if sta and signed:
            progress["today_total"] = signed
        progress["is_free_signed"] = progress["today_total"] <= 0
        progress["today_surplus"] = ac["join_limit_day"] - progress["today_total"]
        award_ids = ac.get("condition_awards").get("award_ids")
        gain = []
        if award_gains:
            gains = {}
            for i in award_gains:
                # 只获取累计签到奖励
                if i.get("type_id") < 7:
                    continue
                if gains.get(i["type_id"]):
                    gains[i["type_id"]].append(i)
                else:
                    gains[i["type_id"]] = [i]
            for award_id in award_ids:
                if gains.get(award_id):
                    gain.append({"award_id": award_id, "status": gains.get(award_id)[0]["status"]})
                else:
                    gain.append({"award_id": award_id, "status": -1})
        else:
            for award_id in award_ids:
                gain.append({"award_id": award_id, "status": -1})
        data = {
            "progress": progress,
            "gains": gain
        }
        return data


class Package(Base):
    """ 限时登录 """
    AM_AWARD_ID = 14
    PM_AWARD_ID = 15
    WECHAT_MG_AM_AWARD_ID = 44
    WECHAT_MG_PM_AWARD_ID = 45
    # 上午领取时间12：00-13:59
    GAIN_AM_START = 12
    GAIN_AM_END = 13
    # 下午领取时间18：00-20:59
    GAIN_PM_START = 18
    GAIN_PM_END = 20

    async def handler(self, activity: dict, uid: int, award_type: int, platform: int):
        """ 处理限时登录活动 """
        act_type = activity.get("act_type")
        act_id = activity.get("act_id")
        pay_type = PayType.BY_FREE
        award_id = await self.now_award_id(platform)
        if not award_id:
            return False, "当前时间不在活动时间内", {}
        rewards, _ = await AwardRC.get_award_info(award_id)
        NLogger.info(f"rewards={rewards}")
        if not rewards:
            return False, "奖励配置错误", {}
        awards = rewards["rewards"]
        NLogger.info(f"awards={awards}")
        # 发放奖励
        gain_sta = await self.gain_awards(uid, awards=awards, act_id=act_id, award_id=award_id,
                                          explain=activity.get("act_name"))
        if not gain_sta:
            return False, "奖励发放失败", {}
        # 自动领取
        await self.give_awards(uid, award_id, act_id, reason=ReasonCostGold.ACTIVITY_PACKAGE)
        # 更新记录
        await self.up_act_progress(uid, act_id, act_type, UserActivityProgressRC.STATUS_FINISH)
        await atc_behavior(uid, act_id, act_type, award_type, pay_type)
        return True, "成功", {"gain_awards": awards}

    async def now_award_id(self, platform: int) -> int:
        """返回当前时间下的奖励ID"""
        award_id = 0
        now = tool_dt.cur_time()
        am_range_start, am_range_end = await CommonApi.get_time_range(period="day", start_hour=self.GAIN_AM_START,
                                                                      end_hour=self.GAIN_AM_END)
        pm_range_start, pm_range_end = await CommonApi.get_time_range(period="day", start_hour=self.GAIN_PM_START,
                                                                      end_hour=self.GAIN_PM_END)
        if pm_range_start <= now <= pm_range_end:
            award_id = self.PM_AWARD_ID if platform != PlatForm.WECHAT_MINI_GAME else self.WECHAT_MG_AM_AWARD_ID
        if am_range_start <= now <= am_range_end:
            award_id = self.AM_AWARD_ID if platform != PlatForm.WECHAT_MINI_GAME else self.WECHAT_MG_PM_AWARD_ID
        return award_id

    async def get_progress(self, award_id: int, uid: int, ac: dict):
        status = -1
        time_status = -1
        am_range_start, am_range_end = await CommonApi.get_time_range(period="day", start_hour=self.GAIN_AM_START,
                                                                      end_hour=self.GAIN_AM_END)
        pm_range_start, pm_range_end = await CommonApi.get_time_range(period="day", start_hour=self.GAIN_PM_START,
                                                                      end_hour=self.GAIN_PM_END)
        now = tool_dt.cur_time()
        start_time = None
        end_time = None
        if award_id == self.AM_AWARD_ID or award_id == self.WECHAT_MG_AM_AWARD_ID:
            if am_range_start <= now <= am_range_end:
                time_status = status = ActivitySta.ACT_NOT_JOIN
                start_time = am_range_start
                end_time = am_range_end
            if am_range_end < now:
                time_status = 1
        else:
            if pm_range_start <= now <= pm_range_end:
                time_status = status = ActivitySta.ACT_NOT_JOIN
                start_time = pm_range_start
                end_time = pm_range_end
            elif now > pm_range_end:
                time_status = 1
        if uid and status == ActivitySta.ACT_NOT_JOIN:
            count = await self.get_package_count(uid, start_time, end_time, ac.get("act_id"))
            if count:
                status = ActivitySta.ACT_COMPLETED
        return {"award_id": award_id, "status": status, "time_status": time_status}

    async def get_package_count(self, uid: int, start_time: int, end_time: int, act_id: int) -> int:
        sta, count = await LogUserActivityRC.activity_frequency(uid=uid, act_id=act_id,
                                                                start_time=start_time,
                                                                end_time=end_time, count=True)
        return count

    async def progress_data(self, uid: int, ac: dict, award_gains: list) -> dict:
        award_ids = ac.get("condition_awards").get("award_ids")
        gain = []
        if award_gains:
            gains = {}
            for i in award_gains:
                if gains.get(i["type_id"]):
                    gains[i["type_id"]].append(i)
                else:
                    gains[i["type_id"]] = [i]
            for award_id in award_ids:
                if gains.get(award_id):
                    gain.append({"award_id": award_id, "status": gains.get(award_id)[0]["status"]})
                else:
                    package_gain = await self.get_progress(award_id, uid, ac)
                    gain.append(package_gain)
        else:
            for award_id in award_ids:
                package_gain = await self.get_progress(award_id, uid, ac)
                gain.append(package_gain)

        return {"gains": gain}


class Common(Base):
    """ 参与可直接领取奖励的活动(分享、救济金) """

    async def handler(self, activity: dict, uid: int, award_type: int):
        act_type = activity.get("act_type")
        act_id = activity.get("act_id")
        pay_type = PayType.BY_FREE
        _, condition_awards = await self.act_by_awards(uid, activity)
        NLogger.info(f"rewards={condition_awards}")
        rewards = condition_awards[0].get("content") or {}
        if not rewards:
            return False, "奖励配置错误", {}
        awards = rewards["rewards"]
        NLogger.info(f"awards={awards}")
        # 发放奖励
        gain_sta = await self.gain_awards(uid, awards=awards, act_id=act_id,
                                          award_id=condition_awards[0].get("award_id"),
                                          explain=activity.get("act_name"))
        if not gain_sta:
            return False, "奖励发放失败", {}
        # 自动领取
        award_id = condition_awards[0].get("award_id")
        reason = None
        if act_type == ActivityType.SHARE:
            reason = ReasonCostGold.ACTIVITY_SHARE
        if act_type == ActivityType.INFINITE_PLAY:
            reason = ReasonCostGold.RELIEF_GET
        await self.give_awards(uid, award_id, act_id, reason=reason)
        # 更新记录
        await self.up_act_progress(uid, act_id, act_type, UserActivityProgressRC.STATUS_FINISH)
        await atc_behavior(uid, act_id, act_type, award_type, pay_type)
        awards = condition_awards[0]["content"]["rewards"]
        return True, "成功", {"gain_awards": awards}


class InfinitePlay(Base):
    """ 救济金 """

    async def progress_data(self, ac: dict, progress: dict, u_info: dict) -> dict:
        if not progress:
            progress = {}
        progress["today_total"] = 0
        sta, count = await act_count(u_info.get("uid"), ac.get("act_id"), "day")
        if sta and count:
            progress["today_total"] = count
        progress["today_surplus"] = ac["join_limit_day"] - progress["today_total"]
        award_ids = ac.get("condition_awards").get("award_ids")
        gain = []
        conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_RELIEF)
        for award_id in award_ids:
            status = 0 if u_info.get("gold", 0) < conf_data.get("min_gold") else -1
            gain.append({"award_id": award_id, "status": status if progress["today_surplus"] > 0 else -1})
        data = {
            "gains": gain,
            "progress": progress,
        }
        return data


class FirstCharge(Base):
    """ 首充 (充值类活动均适用)"""

    async def handler(self, uid: int, activity: dict, award_type: int, pay_mode: int, platform: int = None,
                      return_url: str = None):
        if award_type != AwardType.TOP_UP:
            return False, "活动参与类型错误", {}
        _, condition_awards = await self.act_by_awards(uid, activity)
        NLogger.info(f"rewards={condition_awards}")
        rewards = condition_awards[0].get("content") or {}
        if not rewards:
            return False, "奖励配置错误", {}
        awards = rewards["rewards"]
        NLogger.info(f"awards={awards}")
        # 生成订单
        good_sku = rewards.get("good_suk")
        if not good_sku:
            return False, "首充商品SKU配置错误", {}
        good = await GoodRC.get_good_info(good_sku)
        if not good:
            return False, "首充商品信息配置错误", {}
        express = {
            "price": good["price"],
            "good_id": good["good_id"],
            "currency": good["currency"],
            "desc": good["desc"],
            "sku": good_sku,
        }

        from lucky_game.logic.payment import PaymentLogic
        explain = ""
        if activity.get("act_type") == ActivityType.RETURN_GIFT:
            # 返还礼包额外金币
            return_gold = await self.conf.rds.get_hash(CacheKey.PLAYER_GOLD, str(uid), jsparse=True)
            # return_gold = await BaseServer.get_play_gold(uid)
            extra = {'return_gold': return_gold.get("gold", 0)}
            explain = json_encode(extra)
        act_order, msg = await PaymentLogic().create_order(uid, express, pay_mode, platform, explain=explain,
                                                           return_url=return_url)
        NLogger.info(f"首充活动订单信息：{act_order}")
        if not act_order:
            return False, msg, act_order
        await self.up_act_progress(uid, activity.get("act_id"), activity.get("act_type"))
        await atc_behavior(uid, activity.get("act_id"), activity.get("act_type"), award_type, PayType.BY_RMB)
        return True, msg, act_order

    async def pay_count(self, uid: int):
        act_total, msg = await OrderRC.get_order_filter(uid=uid, status=OrderStatus.PAID, currency=PayType.BY_RMB,
                                                        count=True)
        return act_total

    async def charge_order(self, order_info: dict):
        sta = False
        msg = ""
        result = {}
        act_type = None
        u_info = await BaseUserRC.cache_by_pk(order_info["uid"])
        if order_info["sku"] == GoodsSku.SKU_FIRST:
            # 首充
            act_type = ActivityType.FIRST_CHARGE
        elif order_info["sku"] in [GoodsSku.SKU_REPLENISH_1, GoodsSku.SKU_REPLENISH_2, GoodsSku.SKU_REPLENISH_3,
                                   GoodsSku.SKU_REPLENISH_4]:
            # 金币补足
            act_type = ActivityType.REPLENISH_GIFT
        elif order_info["sku"] in [GoodsSku.SKU_REVIVE_1, GoodsSku.SKU_REVIVE_2, GoodsSku.SKU_REVIVE_3,
                                   GoodsSku.SKU_REVIVE_4]:
            # 复活
            act_type = ActivityType.REVIVE_GIFT
            # 复活礼包直接领取奖励
            from lucky_game.logic.payment import PaymentLogic
            good = await GoodRC.get_good_info(order_info["sku"])
            sta, msg = await PaymentLogic().pay_after(u_info, good, order_info["order_no"])
            NLogger.info(f"复活礼包领取奖励结果：{sta}--{msg}")
            # 通知游戏复活成功
            data = {
                "secret": C_SERVICE_SECRET_KEY,
                "uid": order_info["uid"],
            }
            await CommonApi.cs2cs_by_rmq(
                ServiceEnum.C_MAHJONG_FC,
                CmdRoom.RECHARGE,
                data,
                order_info["uid"],
            )
        elif order_info["sku"] in [GoodsSku.SKU_RETURN_1, GoodsSku.SKU_RETURN_2, GoodsSku.SKU_RETURN_3,
                                   GoodsSku.SKU_RETURN_4]:
            # 返还
            act_type = ActivityType.RETURN_GIFT
        if act_type:
            activity, _ = await ConfActivityRC.get_activity_by_once(act_type=act_type, platform=u_info.get("platform"))
            sta, msg, result = await self.up_act_progress(order_info["uid"], activity["act_id"], activity["act_type"],
                                                          UserActivityProgressRC.STATUS_FINISH)

        return sta, msg, result


class ReturnGift(Base):
    """ 返还礼包 """
    act_type = ActivityType.RETURN_GIFT
    async def act_award(self, act_level: int):
        """ 获取活动奖励 """
        result = []
        activity, _ = await ConfActivityRC.get_activity_by_once(self.act_type, act_level=act_level)
        if not activity:
            return False, result
        condition_awards = activity.get("condition_awards")
        _, result = await self.atc_awards(condition_awards=condition_awards)
        return True, result
