"""
用户资产相关
"""
from sanic import Request
from nsanic.libs import tool_dt
from common.proto.py_pb2.ws_leisure import S2CTopAnnouncements
from common.utils.kit_dt import KitDt
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.up_assets import UpAssets, StatFlow
from tortoise.transactions import in_transaction
from lucky_game.model_rc.base_interaction import InteractionRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.active_behaviors import UserBehaviorsRC
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_admin.model_rc.conf_announcements import ConfAnnouncementsRC
from common.public.enum_const import DbKey, TaskId, Switch
from lucky_game.const import AchieveType, AdSlotItem, PlatForm, OrderStatus, DeliverStatus, AwardType, \
    SignInSta, GoodsItem, GoodsType, ReasonCostGold, CompleteSta, GamePropType, ActivityItem

class GetReliefHandler(GameAuthApi):
    """ 领取救济金 """

    async def get(self, _, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        cur_gold = u_info.get("gold")

        sta, res_info = await self.start_the_relief(uid, cur_gold)
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=res_info)
        return self.answer(data=res_info)

    @classmethod
    async def start_the_relief(cls, uid, cur_gold, is_free=False):
        # 获取计算后的次数和额度
        relief_json = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_RELIEF) or {}
        if cur_gold >= relief_json.get("limit_count", 0):
            return False, "金币少于1千时才可以领取"

        # 剩余次数
        relief_record = await BaseUserRC.get_relief_count(uid)
        used_times = relief_record.get("used_times")

        # 计算额度和次数
        today_midnight = KitDt.timestamp_today()
        relief_conf = await InteractionRC.stat_relief_with_additions(uid, relief_json, is_free) or {}
        if relief_record.get("time_node") == today_midnight:
            relief_times = relief_conf.get("times") or 2
            if used_times >= relief_times:
                return False, "当天已无救济金领取次数"
            used_times += 1
        else:
            used_times = 1

        relief_data = {
            "goods_id": GoodsItem.GOLD.val,
            "goods_type": GoodsType.V_ASSET.val,
            "goods_count": relief_conf.get("count"),
            "reason": ReasonCostGold.RELIEF_GET
        }
        awards = [relief_data]
        new_relief = {"used_times": used_times, "time_node": today_midnight}
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                up_goods = await UpAssets.update_assets(uid, awards, [], is_pack=True)
                await BaseUserRC.cache_relief_count(uid, new_relief)
        except Exception as e:
            cls.log_err(f"GetReliefHandler 事务执行失败，原因：{e}")
            return False, "抽奖签到发奖失败，请联系客服"

        cls.log_info(uid, f"GetReliefHandler 领取{relief_conf.get('count')}救济金成功")
        return True, up_goods
