"""
充值活动类接口
"""
import traceback
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse, json_encode
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from common.utils.kit_dt import KitDt
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.up_assets import UpAssets, StatFlow
from lucky_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from lucky_game.model_rc.base_award import AwardRC
# from lucky_game.model_rc.base_skin import UserSkinRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.vip_level import UserVipRC, ConfVipRC
from lucky_game.const import ActivityType, ActivitySta, ConditionType, ReasonCostDiamond, ActivityStatus
from lucky_game.logic.activity import Base, SignIn, Package


class ActivityDetail(GameAuthApi):
    """
    获取活动信息
    query_param: act_type / act_id
    """

    async def get(self, req: Request, **kwargs):
        try:
            act_type = req.args.get("act_type")
            uid = kwargs.get("u_info").get("uid")
            # 1.获取活动配置
            if act_type:
                act_type = self.check_int(act_type, p_name="act_type")
                act_enum = ActivityType.find_member_by_val(act_type)
                (not isinstance(act_enum, ActivityType)) and self.answer(self.sta_code.ERR_ARG, hint='暂时没找到活动类型')
                ac, e = await ConfActivityRC.get_activity_by_once(act_type=act_type)
            else:
                act_id = self.check_int(req.args.get("act_id"), require=True, p_name="活动ID")
                ac, e = await ConfActivityRC.get_activity_by_once(act_id=act_id)
            (not ac) and self.answer(self.sta_code.NO_CONFIGURATION, hint=e)
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

class JoinActivity(GameAuthApi):
    """
    参与活动
    """
    async def post(self, req: Request, **kwargs):
        try:
            sta = False
            uid = kwargs.get("u_info").get("uid")
            act_id = self.check_int(req.json.get("act_id"), require=True, p_name="活动ID")
            award_type = self.check_int(req.json.get("award_type"), require=True, p_name="参与活动方式")
            ac, e = await ConfActivityRC.get_activity_by_once(act_id=act_id)
            # 校验活动
            (not ac or ac.get("status") != ActivityStatus.ACT_UNDER_WAY) and self.answer(self.sta_code.NO_CONFIGURATION, hint="活动不存在或已结束")
            sta, msg, result = await Base().act_handler(ac, uid, award_type)
            if not sta:
                self.answer(self.sta_code.FAIL, hint=msg)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for frame in tb:
                self.logerr(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            self.log_err(f"JoinActivity 执行失败，原因：{e}")
            return self.answer(code=self.sta_code.FAIL, hint="参与活动失败")
        return self.answer(data={"status": sta, "result": result})


class GainActivity(GameAuthApi):
    """
    领取活动奖励
    """
    async def post(self, req: Request, **kwargs):
        try:
            uid = kwargs.get("u_info").get("uid")
            act_id = self.check_int(req.json.get("act_id"), require=True, p_name="活动ID")
            award_id = self.check_str(req.json.get("award_id"), require=True, p_name="奖励ID")
            ac, e = await ConfActivityRC.get_activity_by_once(act_id=act_id)
            # 校验活动
            (not ac or ac.get("status") != ActivityStatus.ACT_UNDER_WAY) and self.answer(self.sta_code.NO_CONFIGURATION,
                                                                                         hint="活动不存在或已结束")
            sta, e = await Base().act_gain(ac, uid, award_id)
            if not sta:
                self.answer(self.sta_code.FAIL, hint=e)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for frame in tb:
                self.logerr(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            self.log_err(f"JoinActivity 执行失败，原因：{e}")
            return self.answer(code=self.sta_code.FAIL, hint="参与活动失败")
        gain_awards, _ = await AwardRC.get_award_by_filter(award_id=award_id)
        return self.answer(data={"status": sta, "gain_awards": gain_awards}, hint=e)


class ProgressActivity(GameAuthApi):
    """
    活动进度
    """
    async def get(self, req: Request, **kwargs):
        try:
            u_info = kwargs.get("u_info")
            uid = u_info.get("uid")
            act_type = self.check_int(req.args.get("act_type"), require=True, p_name="活动类型")
            ac, e = await ConfActivityRC.get_activity_by_once(act_type=act_type)
            # 校验活动
            (not ac or ac.get("status") != ActivityStatus.ACT_UNDER_WAY) and self.answer(self.sta_code.NO_CONFIGURATION,
                                                                                         hint="活动不存在或已结束")
            sta, msg, data = await Base().act_progress(uid, ac.get("act_id"), act_type)
            self.loginfo(f"活动进度数据：{data}")
            if not sta:
                self.answer(self.sta_code.FAIL, hint=msg)
            if data:
                # 剩余签到次数及数据组装, 如果后期接口响应时间长这部分放客户端处理
                if act_type in [ActivityType.LUCK_SIGN_IN, ActivityType.INFINITE_PLAY]:
                    data["progress"]["is_free_signed"] = data["progress"]["today_total"] <= 0
                    data["progress"]["today_surplus"] = ac["join_limit_day"] - data["progress"]["today_total"]
                award_ids = ac.get("condition_awards").get("award_ids")
                gain = []
                if data["gains"]:
                    gains = {}
                    for i in data["gains"]:
                        if gains.get(i["type_id"]):
                            gains[i["type_id"]].append(i)
                        else:
                            gains[i["type_id"]] = [i]
                    for award_id in award_ids:
                        if gains.get(award_id):
                            gain.append({"award_id": award_id, "status": gains.get(award_id)[0]["status"]})
                        else:
                            if act_type == ActivityType.PACKAGE:
                                # 限时登录
                                package_gain = await Package().get_progress(award_id)
                                gain.append(package_gain)
                            else:
                                gain.append({"award_id": award_id, "status": -1})
                else:
                    for award_id in award_ids:
                        if act_type == ActivityType.PACKAGE:
                            # 限时登录
                            package_gain = await Package().get_progress(award_id)
                            gain.append(package_gain)
                        elif act_type == ActivityType.INFINITE_PLAY:
                            # 救济金
                            status = 0 if u_info.get("gold", 0) < ConfActivityRC.RELIEF_THRESHOLD else -1
                            gain.append({"award_id": award_id, "status": status})
                        else:
                            gain.append({"award_id": award_id, "status": -1})
                data["gains"] = gain
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for frame in tb:
                self.logerr(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            self.log_err(f"ProgressActivity 执行失败，原因：{e}")
            return self.answer(code=self.sta_code.FAIL, hint="获取活动进度失败")
        return self.answer(data=data, hint=msg)




