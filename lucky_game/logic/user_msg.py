""" 用户消息相关逻辑处理 """
import random
import ast
from typing import Union, Tuple

from nsanic.libs import tool_dt
from lucky_game.const import ActivityType, ActivitySta, AwardType, PayType, ReasonCostGold
from lucky_game.config import conf_srv, ConfSrv
from common.public.common_class import CommonApi
from lucky_game.model_rc.base_award import AwardRC
from lucky_game.model_rc.user_activity import LogUserActivityRC, UserActivityProgressRC, AwardGainsRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from nsanic.libs.mult_log import NLogger
from lucky_game.model_rc.conf_json import ConfJsonRC
from nsanic.libs.tool import json_parse, json_encode

AUTO_ACTIVITY_TYPE = [ActivityType.LUCK_SIGN_IN, ActivityType.PACKAGE, ActivityType.SHARE]


class UserMsg(CommonApi):
    """ 用户消息基础类 """
    async def get_day_msg(self, uid: int):
        """ 获取当日需要发送的消息 """
        club_msg = activity_msg = mail_msg = store_msg = friend_msg = chat_msg = {}
        # 活动

        # 茶馆

        # 邮件

        # 商城

        # 好友

        # 聊天
        uid = self.check_int(req.args.get("uid"), require=True, p_name="用户id")
        data = await UserMsgRC.cache_by_uid(uid)
        return self.answer(data=data)

    async def push_msg(self, uid: int, msg: str):
        """ 推送消息 """
        return await UserMsgRC.push_msg(uid, msg)
