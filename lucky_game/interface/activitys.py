"""
充值活动类接口
"""
import traceback
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse, json_encode
from tortoise.transactions import in_transaction

from c_services.base.base_server import BaseServer
from common.public.common_class import CommonApi
from common.public.enum_const import DbKey, CacheKey
from common.utils.kit_dt import KitDt
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.up_assets import UpAssets, StatFlow
from lucky_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from lucky_game.model_rc.base_award import AwardRC
# from lucky_game.model_rc.base_skin import UserSkinRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.vip_level import UserVipRC, ConfVipRC
from lucky_game.const import ActivityType, ActivitySta, ConditionType, AwardType, ActivityStatus, PayMode, \
    ReasonCostGold
from lucky_game.logic.activity import Base, SignIn, Package, InfinitePlay, FirstCharge


class ActivityDetail(GameAuthApi):
    """
    获取活动信息
    query_param: act_type / act_id
    """

    async def get(self, req: Request, **kwargs):
        platform = self.check_str(req.args.get("platform"), require=True, p_name="平台ID")
        act_type = req.args.get("act_type")
        uid = kwargs.get("u_info").get("uid")
        # 1.获取活动配置
        if act_type:
            act_type = self.check_int(act_type, p_name="act_type")
            act_enum = ActivityType.find_member_by_val(act_type)
            (not isinstance(act_enum, ActivityType)) and self.answer(self.sta_code.ERR_ARG, hint='暂时没找到活动类型')
            ac, e = await ConfActivityRC.get_activity_by_once(act_type=act_type, platform=platform)
        else:
            act_id = self.check_int(req.args.get("act_id"), require=True, p_name="活动ID")
            ac, e = await ConfActivityRC.get_activity_by_once(act_id=act_id)
        (not ac) and self.answer(self.sta_code.NO_CONFIGURATION, hint=e)
        try:
            # 2.奖励内容
            once_awards, condition_awards = await Base().act_by_awards(uid, ac)
            ac["once_awards"] = once_awards
            ac["condition_awards"] = condition_awards
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for frame in tb:
                self.logerr(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            self.logerr(f"原因：{e}")
            return self.answer(code=self.sta_code.FAIL, hint="获取活动信息失败")
        return self.answer(data=ac)

class ActivityList(GameAuthApi):
    """
    获取活动列表
    query_param: act_type
    """

    async def get(self, req: Request, **kwargs):
        platform = self.check_str(req.args.get("platform"), require=True, p_name="平台ID")
        act_type = req.args.get("act_type")
        uid = kwargs.get("u_info").get("uid")
        # 1.获取活动配置
        act_type = self.check_int(act_type, p_name="act_type", default=None, require=True)
        act_enum = ActivityType.find_member_by_val(act_type)
        (not isinstance(act_enum, ActivityType)) and self.answer(self.sta_code.ERR_ARG, hint='暂时没找到活动类型')
        ac_list, e = await ConfActivityRC.get_activity_filter(act_type=act_type, platform=platform)
        (not ac_list) and self.answer(self.sta_code.NO_CONFIGURATION, hint=e)
        try:
            # 2.奖励内容
            for ac in ac_list:
                once_awards, condition_awards = await Base().act_by_awards(uid, ac)
                ac["once_awards"] = once_awards
                ac["condition_awards"] = condition_awards
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for frame in tb:
                self.logerr(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            self.logerr(f"原因：{e}")
            return self.answer(code=self.sta_code.FAIL, hint="获取活动信息失败")
        return self.answer(data=ac_list)

class JoinActivity(GameAuthApi):
    """
    参与活动
    """
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        act_id = self.check_int(req.json.get("act_id"), require=True, p_name="活动ID")
        award_type = self.check_int(req.json.get("award_type"), require=True, p_name="参与活动方式")
        pay_mode = self.check_int(req.json.get("pay_mode"), require=False, p_name="支付方式")
        pay_platform = self.check_int(req.json.get("pay_platform"), require=False, p_name="支付平台")
        platform = self.check_int(req.args.get("platform"), require=True, p_name="平台")
        return_url = self.check_str(req.json.get("return_url"), require=False, default="", p_name="返回地址")
        pay_enum = PayMode.find_member_by_val(pay_mode)
        award_enum = AwardType.find_member_by_val(award_type)
        if pay_mode and not isinstance(pay_enum, PayMode):
            self.answer(self.sta_code.ERR_ARG, hint="支付方式错误")
        if award_type and not isinstance(award_enum, AwardType):
            self.answer(self.sta_code.ERR_ARG, hint="参与活动方式错误")
        ac, e = await ConfActivityRC.get_activity_by_once(act_id=act_id)
        # 校验活动
        (not ac or ac.get("status") != ActivityStatus.ACT_UNDER_WAY) and self.answer(self.sta_code.NO_CONFIGURATION,
                                                                                     hint="活动不存在或已结束")

        sta, msg, result = await Base().act_handler(ac, u_info, award_type, pay_mode, platform, return_url=return_url)
        if not sta:
            self.answer(self.sta_code.FAIL, hint=msg)
        return self.answer(data={"status": sta, "result": result})


class GainActivity(GameAuthApi):
    """
    领取活动奖励
    """
    async def post(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        act_id = self.check_int(req.json.get("act_id"), require=True, p_name="活动ID")
        award_id = self.check_str(req.json.get("award_id"), require=True, p_name="奖励ID")
        ac, e = await ConfActivityRC.get_activity_by_once(act_id=act_id)
        # 校验活动
        (not ac or ac.get("status") != ActivityStatus.ACT_UNDER_WAY) and self.answer(self.sta_code.NO_CONFIGURATION,
                                                                                     hint="活动不存在或已结束")
        sta, e = await Base().give_awards(uid, award_id, act_id, reason=ReasonCostGold.ACTIVITY_GIFT)
        if not sta:
            self.answer(self.sta_code.FAIL, hint=e)
        award_content, _ = await AwardRC.get_award_info(award_id=award_id)
        result = {
            "award": {"gain_awards": award_content["rewards"]},
            "pay_info": {}
        }
        return self.answer(data={"status": sta, "result": result}, hint="领取成功")


class ProgressActivity(GameAuthApi):
    """
    活动进度
    """
    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        act_type = self.check_int(req.args.get("act_type"), require=True, p_name="活动类型")
        platform = self.check_str(req.args.get("platform"), require=True, p_name="平台ID")
        ac, e = await ConfActivityRC.get_activity_by_once(act_type=act_type, platform=platform)
        # 校验活动
        (not ac or ac.get("status") != ActivityStatus.ACT_UNDER_WAY) and self.answer(self.sta_code.NO_CONFIGURATION,
                                                                                     hint="活动不存在或已结束")
        sta, msg, progress, gains = await Base().act_progress(ac, u_info)
        self.loginfo(f"活动进度数据：progress {progress} gains {gains}")
        if not sta:
            return self.answer(self.sta_code.FAIL, hint=msg)
        try:
            if act_type == ActivityType.LUCK_SIGN_IN:
                result = await SignIn().progress_data(uid, ac, progress, gains)
            elif act_type == ActivityType.PACKAGE:
                result = await Package().progress_data(uid, ac, gains)
            elif act_type == ActivityType.INFINITE_PLAY:
                result = await InfinitePlay().progress_data(ac, progress, u_info)
            else:
                result = {
                    "progress": progress,
                    "gains": gains,
                }
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for frame in tb:
                self.logerr(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            self.log_err(f"ProgressActivity 执行失败，原因：{e}")
            return self.answer(code=self.sta_code.FAIL, hint="获取活动进度失败")
        return self.answer(data=result, hint=msg)


class ActivityReturnGold(GameAuthApi):
    """
    获取活动返金币
    """
    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        return_gold = await CommonApi.get_player_join_gold(uid)
        sta = return_gold.get('gold', None)
        return self.answer(data={"return_gold": return_gold.get("gold") if sta and return_gold.get("gold") > 0 else 0})




