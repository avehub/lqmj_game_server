"""
用户互动相关接口
"""
from sanic import Request
from nsanic.libs import tool_dt
from common.proto.py_pb2.ws_leisure import S2CTopAnnouncements
from common.utils.kit_dt import KitDt
from common.utils.utils import UtilsTool
from lucky_game.base_api import GameAuthApi
from c_services.const.cs_enum_const import CmdWorkers
from lucky_game.handler.up_assets import UpAssets, StatFlow
from lucky_game.interface.some_pay import BaseSomePay
from lucky_game.model_db.extra import RecordsAdOrder
from tortoise.transactions import in_transaction
from lucky_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from lucky_game.model_rc.base_award import ConfAwardRC, UserAwardRC
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_prop import ItemsPropRC
from lucky_game.model_rc.base_skin import UserSkinRC
from lucky_game.model_rc.base_store import ConfMonopolyStoreRC
from lucky_game.model_rc.goods_manager import GoodsManagerRC
from lucky_game.model_rc.base_interaction import InteractionRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.active_behaviors import UserBehaviorsRC
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_admin.model_rc.conf_announcements import ConfAnnouncementsRC
from common.public.enum_const import DbKey, TaskId, Switch
from lucky_game.const import AchieveType, AdSlotItem, PlatForm, OrderStatus, DeliverStatus, AwardType, \
    SignInSta, GoodsItem, GoodsType, ReasonCostGold, CompleteSta, GamePropType, ActivityItem


class MakeAdOrder(GameAuthApi):
    """ 创建广告订单 """

    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 检查免广告特权
        check_res = await UserActivityRC.verify_activation(uid, ActivityItem.WEEK_CARD_2)
        if check_res == Switch.CLOSE:
            is_wait, limit_time = await BaseUserRC.check_cool_down(uid)
            if is_wait:
                self.answer(self.sta_code.REQ_FREQUENT, hint=f"抱歉，请稍等{limit_time}秒再观看下一个广告")

        ad_slot_id = self.check_int(req.json.get("ad_slot_id"), require=True, minval=2000, maxval=4999, p_name="ad_slot_id")
        ao_enum = AdSlotItem.find_member_by_val(ad_slot_id)
        (not ao_enum) and self.answer(code=self.sta_code.ERR_ARG, hint="广告失效，请联系客服")

        platform = u_info.get("platform")
        pf_enum = PlatForm.find_member_by_val(platform)
        (not isinstance(pf_enum, PlatForm)) and self.answer(code=self.sta_code.ERR_ARG, hint="设备不支持")

        # 1.检查广告位剩余次数
        item_num, _ = UtilsTool.explode_command(ad_slot_id, digit=3)
        if item_num == 2:
            ad_conf = await ConfMonopolyStoreRC.get_monopoly_store_item_by_id(ad_slot_id)
            buy_limit = json_parse(ad_conf.get("buy_limit")) if ad_conf.get("buy_limit") else {}
            receive_limit = buy_limit.get("times") or 0
        elif item_num == 3:
            ad_conf = await ConfActivityRC.get_activity_item_by_id(act_id=ad_slot_id)
            receive_limit = ad_conf.get("join_limit_day") or 0
        else:
            ad_conf = await ConfAwardRC.get_award_item_by_id(ad_slot_id)
            receive_limit = ad_conf.get("receive_limit") or 0
        (not ad_conf) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="广告奖励失效，请联系客服")

        if receive_limit > 0:
            watch_record = await UserBehaviorsRC.cache_user_ad_times(uid, KitDt.timestamp_today())
            if watch_record and watch_record.get(ao_enum.desc, 0) >= receive_limit:
                self.answer(code=self.sta_code.CONDITION_NOT_MET, hint="今日看广告次数已用完，请明日再来")

        # 2.创建订单，插入订单表
        data = {
            "uid": uid,
            "ad_slot_id": ad_slot_id,
            "ad_achieve_type": AchieveType.TOTAL,
            "ad_achieve_value": req.json.get("count") or 1,
            "ad_order_desc": ao_enum.phrase,
            "order_source": pf_enum.val,
        }
        insert_data = await RecordsAdOrder.gen_insert_data(**data)
        record_trade = await RecordsAdOrder.split_add_one(insert_data)
        if not record_trade:
            return self.answer(self.sta_code.FAIL, hint="广告创建失败，请稍后再试")

        return_data = {
            "order_id": insert_data.get("ad_order_id"),
            "trade_time": tool_dt.cur_time(),
        }
        self.info_log(uid, f"MakeAdOrder 创建{ao_enum.phrase}广告订单 成功")
        return self.answer(data=return_data)


class CompleteAdOrder(GameAuthApi):
    """完成广告订单 / 发奖 / 统计次数"""

    async def post(self, req: Request, **kwargs):
        ad_slot_id = self.check_int(req.json.get("ad_slot_id"), require=True, minval=2000, maxval=4999, p_name="ad_slot_id")
        ao_enum = AdSlotItem.find_member_by_val(ad_slot_id)
        (not ao_enum) and self.answer(code=self.sta_code.ERR_ARG, hint="广告失效，请联系客服")

        ad_order_id = self.check_str(req.json.get("ad_order_id"), require=True, p_name="ad_order_id")
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 2.查询订单
        ad_order_info = await RecordsAdOrder.query_order(ad_order_id=ad_order_id)
        (not ad_order_info) and self.answer(self.sta_code.ORDER_NOT_FOUND, hint="广告创建失败，请重新进入")

        if ad_order_info.get("status") != OrderStatus.PAID:
            map_func = {
                AdSlotItem.DY_RAFFLE_LUCK.val: self.deal_ad_sign_in,
                AdSlotItem.DY_AWARD.val: self.deal_ad_award,
                AdSlotItem.DY_RELIEF.val: self.deal_ad_relief,
                AdSlotItem.DY_DICE.val: self.deal_ad_pay,
                AdSlotItem.DY_GOLD_NOT_ENOUGH_FIRST.val: self.deal_ad_pay,
                AdSlotItem.DY_GOLD_NOT_ENOUGH_SECOND.val: self.deal_ad_pay,
                AdSlotItem.DY_SIGN_WK.val: self.deal_ad_sign_in
            }
            deal_func = map_func.get(ad_slot_id)
            if deal_func and callable(deal_func):
                res = await deal_func(ad_slot_id, u_info, req)
                self.info_log(uid, f"CompleteAdOrder {ao_enum.phrase} 领奖完成")
                (not res) and self.answer(self.sta_code.FAIL, hint="看广告失败，请联系客服")
                # 暂用支付状态表示完成情况
                update_done = {
                    "status": OrderStatus.PAID,
                    "deliver_status": DeliverStatus.SHIPPED,
                    "finish_time": tool_dt.cur_time(),
                }
                try:
                    async with in_transaction(connection_name=DbKey.DEFAULT):
                        await RecordsAdOrder.update_by_pk(ad_order_id, update_done, ad_order_info)
                        await UserBehaviorsRC.update_user_ad_times(uid, KitDt.timestamp_today(), ao_enum.desc,
                                                                   ad_order_info.get("ad_achieve_value"))
                        # 检查免广告特权
                        check_res = await UserActivityRC.verify_activation(uid, ActivityItem.WEEK_CARD_2)
                        if check_res == Switch.CLOSE:
                            await BaseUserRC.set_cool_down(uid)
                except Exception as e:
                    self.error_log(f"CompleteAdOrder 事务执行失败，原因：{e}")
                    self.answer(self.sta_code.FAIL, hint="广告发奖失败，请联系客服")
                return self.answer(data=res)
            return self.answer(self.sta_code.FAIL, hint="看广告失败，请联系客服")
        return self.answer(self.sta_code.FAIL, hint="广告已经完成观看")

    async def deal_ad_sign_in(self, ad_slot_id, u_info, req: Request):
        """每日看广告抽奖/补签"""
        uid = u_info.get("uid")
        sta, res_info = None, ""

        if ad_slot_id == AdSlotItem.DY_RAFFLE_LUCK:
            sta, res_info = await SignInComplete.complete_sign_in(uid, AwardType.SIGN_IN_RF, is_free=True)

        elif ad_slot_id == AdSlotItem.DY_SIGN_WK:
            backdate_sign_date = self.check_int(req.json.get("backdate_sign_date") or None, minval=0, maxval=31, p_name="backdate_sign_date 补签必填")
            is_free = True if backdate_sign_date else False  # 补签则backdate_sign_date和is_free都为真，正常签则都为假
            sta, res_info = await SignInComplete.complete_sign_in(uid, AwardType.SIGN_IN_WK, is_free=is_free, backdate_sign_date=backdate_sign_date)

        if not sta:
            return self.answer(self.sta_code.FAIL, hint=res_info)
        return res_info

    async def deal_ad_relief(self, _, u_info, __):
        """每日看广告随机翻倍救济金"""
        sta, res_info = await GetReliefHandler.start_the_relief(u_info.get("uid"), u_info.get("gold"), is_free=True)
        if not sta:
            return self.answer(self.sta_code.FAIL, hint=res_info)
        return res_info

    async def deal_ad_award(self, ad_slot_id, u_info, _):
        """每日看广告获得金币"""
        awards = {}
        if ad_slot_id == AdSlotItem.DY_AWARD:
            conf_odds = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_ADS_AWARDS)
            result = UtilsTool.select_element_by_prob(conf_odds, size=100)
            (not result) and self.answer(self.sta_code.FAIL, hint="随机奖励加载错误")

            awards = {
                "goods_id": GoodsItem.GOLD.val,
                "goods_type": GoodsType.V_ASSET.val,
                "goods_count": int(result)
            }
            StatFlow.stat_common_flow(awards=[awards], g_reason=ReasonCostGold.AD_FREE_GOLD)

        (not awards) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="商品缺货，请联系客服")
        up_goods = await UpAssets.update_assets(u_info.get("uid"), [awards], [], is_pack=True)
        return up_goods

    async def deal_ad_pay(self, ad_slot_id, u_info, _):
        """每日看广告商店兑换"""
        buy_record = {}
        uid = u_info.get("uid")
        item_num, _ = UtilsTool.explode_command(ad_slot_id, digit=3)
        if item_num == 3:
            express, _, buy_record, _, _ = await BaseSomePay.verify_goods(uid, ad_slot_id)
        else:
            express = await ConfMonopolyStoreRC.get_monopoly_store_item_by_id(store_id=ad_slot_id)
        (not express) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="商品缺货，请联系客服")

        conf_items = express.get("conf_items")
        (not conf_items) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="广告商品缺货，请联系客服")

        up_goods = await UpAssets.update_assets(u_info.get("uid"), conf_items, [], is_pack=True)
        if buy_record:  # 更新购买次数（仅充值礼包促销）
            await BaseUserRC.cache_count_buy_limit(uid, ad_slot_id, buy_record)
        return up_goods


class SignInHandler(GameAuthApi):
    """
    通用获取签到配置
    签到奖励：签到立即获取；
    累计奖励：累计签到天数获取；
    """

    async def get(self, req: Request, **kwargs):
        award_type = self.check_int(req.args.get("award_type"), require=True, p_name="award_type")
        at_enum = AwardType.find_member_by_val(award_type)
        (not isinstance(at_enum, AwardType)) and self.answer(self.sta_code.ERR_ARG, hint="签到奖励类型错误")

        user = kwargs.get("u_info")
        uid = user.get("uid")
        should_sign_date = UserBehaviorsRC.cal_should_sign_date(award_type)  # 应该签到的日期格式（周一、26号等）

        # 1.按奖励类型获取签到配置
        map_func = {
            AwardType.SIGN_IN_RF.val: self.get_raffle_sign_conf,
            AwardType.SIGN_IN_WK.val: self.get_week_sign_conf,
            AwardType.SIGN_IN.val: self.get_seven_sign_conf
        }
        deal_func = map_func.get(award_type)
        if not deal_func and not callable(deal_func):
            self.answer(self.sta_code.ERR_CONF, hint="签到配置或类型错误")

        return_data, targets_key = await deal_func(uid)
        (not return_data) and self.answer(self.sta_code.FAIL, hint="获取签到配置失败，请稍后再试")

        # 2.获取用户签到统计数据
        sign_info = await UserBehaviorsRC.get_sign_in_records(uid, award_type) or {}
        sign_in_date, sign_in_achieved = UserBehaviorsRC.parse_sign_in_info(sign_info)

        # 3.计算累计奖励（使用到目标列表targets）
        achieved_days = len(sign_in_date)
        sign_targets = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_SING_IN)
        sign_awards_sta = ConfJsonRC.stat_of_completion(achieved_days, sign_in_achieved, sign_targets.get(targets_key, []))

        sign_data = {
            "sign_achieved": achieved_days,  # 已签到次数
            "sign_status": SignInSta.UN_SIGN if should_sign_date not in sign_in_date else SignInSta.SIGNED,  # 当下签到状态
            "sign_awards_sta": json_encode(sign_awards_sta),  # 总领奖状态
            "sign_in_date": json_encode(sign_in_date)  # 总签到日期
        }
        return_data["sign_data"] = sign_data

        self.info_log(uid, f"SignInHandler {at_enum.phrase}配置 / 用户签到数据 成功")
        return self.answer(data=return_data)

    async def get_raffle_sign_conf(self, uid):
        """运势抽奖签到配置"""
        today_time_node = KitDt.timestamp_today()
        # 抽奖配置
        raffle_awards = await ConfAwardRC.get_award_items(AwardType.RAFFLE_LUCK)
        (not raffle_awards) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有运势抽奖奖品")
        raffle_conf = await InteractionRC.get_conf_raffle_luck(raffle_awards, today_time_node)
        (not raffle_conf) and self.answer(self.sta_code.ERR_CONF, hint="运势抽奖配置不存在")

        # 运势文案
        luck = await UserBehaviorsRC.cache_user_luck_number(uid, today_time_node, AwardType.LUCK)
        (not luck) and self.answer(self.sta_code.ERR_CONF, hint="运势正忙呢，请稍后再试")
        luck_data = {"yun_shi": luck.get('luck'), "yun_shi_desc": luck.get('desc')}

        # 累计抽奖签到配置
        sign_awards = await ConfAwardRC.get_award_items(AwardType.SIGN_IN_RF)
        (not sign_awards) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有签到奖励")
        sign_conf = await InteractionRC.get_conf_sign_in(sign_awards, InteractionRC.CONF_RAFFLE_SIGN_IN)
        (not sign_conf) and self.answer(self.sta_code.ERR_CONF, hint="签到配置不存在")

        return_data = {
            "raffle_conf": raffle_conf,  # 抽奖配置
            "luck_data": luck_data,  # 运势文案
            "sign_conf": sign_conf  # 累计配置
        }
        return return_data, InteractionRC.SING_TARGET_R

    async def get_week_sign_conf(self, _):
        """每周七日签到配置"""
        # 立得奖励/累计奖励
        week_awards = await ConfAwardRC.get_award_items(AwardType.SIGN_IN_WK)
        (not week_awards) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有每周七日签到奖品")

        sign_awards = await InteractionRC.get_conf_sign_in(week_awards, InteractionRC.CONF_WEEK_SIGN_IN)
        (not sign_awards) and self.answer(self.sta_code.ERR_CONF, hint="每周七日签到配置不存在")

        sign_item, sign_conf = [], []
        for w in sign_awards or []:
            if w.get('achieve_type') == AchieveType.DONE:
                sign_item.append(w)
            elif w.get('achieve_type') == AchieveType.DURATION:
                sign_conf.append(w)

        return_data = {
            "sign_item": sign_item,  # 立得配置
            "sign_conf": sign_conf  # 累计配置
        }
        return return_data, InteractionRC.SING_TARGET_W

    async def get_seven_sign_conf(self, _):
        """七日抽奖签到配置"""
        # 获取七日签到配置
        seven_awards = await ConfAwardRC.get_award_items(AwardType.SIGN_IN)
        (not seven_awards) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有七日签到奖励")

        sign_conf = await InteractionRC.get_conf_sign_in(seven_awards, InteractionRC.CONF_SEVEN_SIGN_IN)
        (not sign_conf) and self.answer(self.sta_code.ERR_CONF, hint="七日签到配置不存在")

        return_data = {"sign_conf": sign_conf}  # 累计配置
        return return_data, InteractionRC.SING_TARGET_S


class SignInTotalComplete(GameAuthApi):
    """通用累计签到领奖"""

    async def post(self, req: Request, **kwargs):
        # 目标领奖累计数，例如想领取累计3天奖励，achieved=3
        achieved = self.check_int(req.json.get('sign_achieved'), require=True, minval=1, maxval=31, p_name="sign_achieved")

        award_type = self.check_int(req.json.get("award_type"), require=True, p_name="award_type")
        at_enum = AwardType.find_member_by_val(award_type)
        (not isinstance(at_enum, AwardType)) and self.answer(self.sta_code.ERR_ARG, hint="签到奖励类型错误")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        sta, res_info = await self.complete_sign_in_total(uid, achieved, award_type)
        (not sta) and self.answer(code=self.sta_code.FAIL, hint=res_info)

        return self.answer(data=res_info)

    @classmethod
    async def complete_sign_in_total(cls, uid, achieved: int, award_type: AwardType):
        """
        通用的完成签到方法
        achieved:目标领奖累计数，例如：想领取累计3天奖励，achieved=3
        """
        # 1.获取用户签到记录
        sign_info = await UserBehaviorsRC.get_sign_in_records(uid, award_type) or {}
        if not sign_info:
            return False, "您目前的签到天数不足，请再接再厉"
        sign_in_date, sign_in_achieved = UserBehaviorsRC.parse_sign_in_info(sign_info)

        # 2.签到对应奖励计算
        if len(sign_in_date) < achieved:
            return False, "您目前的签到天数不足，请再接再厉"
        if sign_in_achieved and achieved in sign_in_achieved:
            return False, "您已领取过奖励"

        # 3.累计奖励配置
        sign_awards = await ConfAwardRC.get_award_items(award_type)
        match award_type:
            case AwardType.SIGN_IN_RF:
                sign_key_name = InteractionRC.CONF_RAFFLE_SIGN_IN
            case AwardType.SIGN_IN_WK:
                sign_key_name = InteractionRC.CONF_WEEK_SIGN_IN
            case _:
                sign_key_name = InteractionRC.CONF_SEVEN_SIGN_IN

        sign_conf = await InteractionRC.get_conf_sign_in(sign_awards, sign_key_name)
        if not sign_conf:
            return False, "没有累计签到奖励"

        # 找到对应累计奖
        awards = next((award.get("conf_items") for award in sign_conf if award.get("achieve_value") == achieved), None)
        if not awards:
            return False, "累计签到奖励缺货，请联系客服"
        StatFlow.stat_common_flow(awards=awards, g_reason=ReasonCostGold.SIGN_IN_TOTAL, d_reason=ReasonCostGold.SIGN_IN_TOTAL)

        # 5.更新领奖记录
        new_achieved = sign_in_achieved + [achieved]
        new_sign_info = {
            "uid": uid,
            "sign_in_date": json_encode(sign_in_date) if sign_in_date else [],
            "sign_in_achieved": json_encode(new_achieved) if new_achieved else []
        }
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                if award_type == AwardType.SIGN_IN:
                    for a in awards:
                        await UserSkinRC.deal_hold_skin(uid, a)
                    if len(new_achieved) >= 7:
                        await cls.push_task2worker(CmdWorkers.UPDATE_GAME_TASK, {"task_id": TaskId.ROOKIE_SEVEN_SIGN_IN, "add_val": 7}, uid)

                await UserBehaviorsRC.update_user_sign_in_records({"uid": uid, "award_type": award_type}, new_sign_info, sign_info)
                up_goods = await UpAssets.update_assets(uid, awards, [], is_pack=True)
        except Exception as e:
            cls.error_log(f"complete_sign_in_total {award_type}事务执行失败，原因：{e}")
            return False, f"{award_type}签到累计{achieved}发奖失败，请联系客服"

        cls.info_log(uid, f"complete_sign_in_total {award_type}签到累计{achieved}发奖成功")
        return True, up_goods


class SignInComplete(GameAuthApi):
    """通用完成签到"""

    async def post(self, req: Request, **kwargs):
        award_type = self.check_int(req.json.get("award_type"), require=True, p_name="award_type")
        at_enum = AwardType.find_member_by_val(award_type)
        (not isinstance(at_enum, AwardType)) and self.answer(self.sta_code.ERR_ARG, hint="签到奖励类型错误")

        user = kwargs.get("u_info")
        uid = user.get("uid")
        sta, res_info = await self.complete_sign_in(uid, award_type)
        (not sta) and self.answer(code=self.sta_code.FAIL, hint=res_info)

        data = {"task_id": TaskId.RAFFLE_SIGN_IN, "add_val": 1}
        await self.push_task2worker(CmdWorkers.UPDATE_GAME_TASK, msg=data, uid=uid)
        return self.answer(data=res_info)

    @classmethod
    async def complete_sign_in(cls, uid, award_type, is_free=False, backdate_sign_date=None):
        """
        通用的完成签到方法
        签到：is_free=False 正常签到 / is_free=True 免费签到（无条件签到或者再签到一次）
        补签：is_free=True + backdate_sign_date 免费补签（只能补签一次）
        """
        today_time_node = KitDt.timestamp_today()
        if backdate_sign_date:
            should_sign_date = backdate_sign_date  # 应该补签的日期（目前只用于每周七日签到）
        else:
            should_sign_date = UserBehaviorsRC.cal_should_sign_date(award_type)  # 应该签到的日期格式（周一、26号等）

        # 1.获取签到奖励配置
        awards_conf = None
        if award_type == AwardType.SIGN_IN_RF:
            raffle_awards = await ConfAwardRC.get_award_items(AwardType.RAFFLE_LUCK)
            awards_conf = await InteractionRC.get_conf_raffle_luck(raffle_awards, today_time_node)  # 奖池刷新或打包
        elif award_type == AwardType.SIGN_IN_WK:
            awards_conf = await ConfAwardRC.get_award_items(award_type, is_pack=True)
        if not awards_conf:
            return False, f"没有{award_type}签到类型的奖励配置"

        # 2.获取用户签到记录和验证机会
        sign_info = await UserBehaviorsRC.get_sign_in_records(uid, award_type) or {}
        sign_in_date, sign_in_achieved = UserBehaviorsRC.parse_sign_in_info(sign_info)

        chance, chance_desc = cls.check_sign_in_chance(is_free, should_sign_date, backdate_sign_date, sign_in_date)
        if not chance:
            return chance, chance_desc

        # 3.寻找对应奖励（抽奖获得/指定位置获得）
        sign_conf = None
        g_reason = None
        if award_type == AwardType.SIGN_IN_RF:
            conf_odds = {str(i['award_level']): i['weight'] for i in raffle_awards}
            result = UtilsTool.select_element_by_prob(conf_odds, size=1000)
            sign_conf = next((i for i in awards_conf if int(result) == i.get("award_level")), {})
            g_reason = ReasonCostGold.RAFFLE_LUCK

        elif award_type == AwardType.SIGN_IN_WK:
            # 获取所有类型的签到配置
            sign_confs, sign_total_confs = [], []
            for a in awards_conf or []:
                if a.get('achieve_type') == AchieveType.DONE:
                    sign_confs.append(a)
                elif a.get('achieve_type') == AchieveType.DURATION:
                    sign_total_confs.append(a)

            # 寻找当天的签到奖励配置
            sign_conf = next((i for i in sign_confs if should_sign_date == i.get("award_level")), {})
            g_reason = ReasonCostGold.SIGN_IN_AWARDS

        sign_awards = sign_conf.get("conf_items") or []
        if not sign_awards:
            return False, f"签到{award_type}奖励缺货，请联系客服"
        StatFlow.stat_common_flow(awards=sign_awards, g_reason=g_reason)

        # 4.更新签到记录/发奖
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UpAssets.update_assets(uid, sign_awards, [])

                # 只有在非免费签到或需要补签的情况下才更新签到记录
                if not is_free or (is_free and backdate_sign_date):
                    sign_in_date.append(should_sign_date)
                    new_sign_info = {
                        "uid": uid,
                        "time_node": today_time_node,
                        "award_type": award_type,
                        "sign_in_date": json_encode(sign_in_date) if sign_in_date else '[]',
                        "sign_in_achieved": json_encode(sign_in_achieved) if sign_in_achieved else '[]'
                    }
                    await UserBehaviorsRC.update_user_sign_in_records({"uid": uid, "award_type": award_type}, new_sign_info, sign_info)
        except Exception as e:
            cls.error_log(f"complete_sign_in {award_type}事务执行失败，原因：{e}")
            return False, f"签到{award_type}发奖失败，请联系客服"

        # 5.处理奖励返回，特殊情况需要同时发累计奖
        pro_data = None
        if award_type == AwardType.SIGN_IN_WK:
            # 检查是否达到任何累计奖励条件，并发放相应的奖励
            achieved_days = 0
            for s in sign_total_confs or []:
                achieve_value = s.get('achieve_value')
                if len(sign_in_date) == achieve_value and achieve_value not in sign_in_achieved:
                    achieved_days = achieve_value

            if achieved_days:
                sta, res_info = await SignInTotalComplete.complete_sign_in_total(uid, achieved_days, award_type)
                if sta:
                    sign_awards.extend(res_info)
            pro_data = sign_awards

        elif award_type == AwardType.SIGN_IN_RF:
            pro_data = sign_conf

        cls.info_log(uid, f"签到{award_type}成功，是否免费：{is_free}，是否补签：{backdate_sign_date}")
        return True, pro_data

    @classmethod
    def check_sign_in_chance(cls, is_free, should_sign_date, backdate_sign_date, sign_in_date):
        """
        验证签到机会（暂时用于签到，非累计签到）
        :param is_free: 是否免费签到
        :param should_sign_date: 应该签到的日期
        :param backdate_sign_date: 补签日期，只有补签必填
        :param sign_in_date: 已签到的日期列表
        """
        # 如果是补签请求
        if backdate_sign_date:
            if backdate_sign_date in sign_in_date:
                return False, "亲，已经补签过啦"
            elif not is_free:
                return False, "亲，可以通过看广告补签哦"
        else:  # 正常签到请求
            # 只有当不是免费且今天已签到时才返回失败
            if not is_free and should_sign_date in sign_in_date:
                return False, "亲，今天没有签到机会啦"
        return True, "签到成功"


class GetReliefConf(GameAuthApi):
    """救济金配置"""

    async def get(self, _: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        relief_record = await BaseUserRC.get_relief_count(uid)
        used_times = 0
        if relief_record.get("time_node") == KitDt.timestamp_today():
            used_times = relief_record.get("used_times") or 0

        relief_conf = await InteractionRC.stat_relief_with_additions(uid) or {}
        relief_data = {
            "relief_count": relief_conf.get("count") or 1000,
            "relief_limit_count": relief_conf.get("limit_count") or 1000,
            "relief_multiple": relief_conf.get("multiple") or 1,
            "relief_times": relief_conf.get("times") or 2,
            "relief_used_times": used_times
        }
        self.info_log(uid, "GetReliefConf 加载救济金配置", relief_data)
        return self.answer(data=relief_data)


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
            cls.error_log(f"GetReliefHandler 事务执行失败，原因：{e}")
            return False, "抽奖签到发奖失败，请联系客服"

        cls.info_log(uid, f"GetReliefHandler 领取{relief_conf.get('count')}救济金成功")
        return True, up_goods


class GetCommonAwardsConf(GameAuthApi):
    """通用奖励配置"""

    async def get(self, req: Request, **kwargs):
        ad_slot_id = self.check_int(
            req.args.get("ad_slot_id"), require=True, minval=2000, maxval=4999, p_name="ad_slot_id")
        ao_enum = AdSlotItem.find_member_by_val(ad_slot_id)
        (not ao_enum) and self.answer(code=self.sta_code.ERR_ARG, hint="广告失效，请联系客服")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 1.获取奖励配置
        common_awards = await ConfAwardRC.cache_conf_by_pk(ad_slot_id)
        (not common_awards) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有找到奖励")

        # 2.查询领奖次数
        watch_record = await UserBehaviorsRC.cache_user_ad_times(uid, KitDt.timestamp_today())
        common_awards['receive_times'] = watch_record.get(ao_enum.desc, 0) if watch_record else 0

        await GoodsManagerRC.pack_goods_conf([common_awards])
        self.info_log(uid, "GetCommonAwardsConf 加载通用奖励配置", ad_slot_id)
        return self.answer(data=common_awards)


class PullCommonAwards(GameAuthApi):
    """
    通用奖励领取
    泛指限量的单奖，例如：抖音侧边栏访问奖励
    """

    async def post(self, req: Request, **kwargs):
        award_id = self.check_int(req.json.get("award_id"), require=True, minval=4000, p_name="award_id")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 1.验证是否有对应的奖励
        common_award = await ConfAwardRC.cache_conf_by_pk(award_id)
        (not common_award) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有找到奖励")

        # 2.验证领取次数
        query_params = {'uid': uid, 'award_id': award_id}
        pull_info = await UserAwardRC.cache_user_award_records(query_params)
        receive_limit = common_award.get('receive_limit') or 0
        receive_times = pull_info.get('receive_times') if pull_info else 0
        if receive_limit and receive_limit <= receive_times:
            self.answer(self.sta_code.CONDITION_NOT_MET, hint="领取次数已用尽")

        awards = await UpAssets.stat_awards(award_id)
        (not awards) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="奖品缺货，请联系客服")
        StatFlow.stat_common_flow(awards=awards, g_reason=ReasonCostGold.AD_FREE_GOLD)

        receive_times += 1
        new_pull_info = {
            'uid': uid,
            'award_id': award_id,
            'time_node': tool_dt.cur_time(),
            'award_sta': CompleteSta.CLAIMED,
            'receive_times': receive_times
        }
        # 3.发奖
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UserAwardRC.update_user_award_records(query_params, new_pull_info, pull_info)
                up_goods = await UpAssets.update_assets(uid, awards, [])
        except Exception as e:
            self.error_log(f"PullCommonAwards 事务执行失败，原因：{e}")
            self.answer(self.sta_code.FAIL, hint="奖励领取失败，请联系客服")

        self.info_log(uid, "PullCommonAwards 已领取奖励", award_id)
        return self.answer(data=up_goods)


class OpenTreasureBox(GameAuthApi):
    """开启宝盒"""

    async def post(self, req: Request, **kwargs):
        goods_id = self.check_int(req.json.get("goods_id"), require=True, minval=1000, maxval=1999, p_name="goods_id")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 1.通过goods_id查询背包
        bag_item = await UserBagRC.get_user_bag_by_id(uid, goods_id=goods_id)
        (not bag_item) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没有找到物品")

        # 2.验证宝盒
        goods_count = bag_item.get("goods_count")
        (not goods_count) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="宝盒不足哦，请先购买再来开启吧")

        prop_item = await ItemsPropRC.cache_conf_by_pk(goods_id)
        (not prop_item) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="道具配置不存在")

        game_prop_type = prop_item.get("game_prop_type")
        (game_prop_type != GamePropType.TREASURE_BOX) and self.answer(self.sta_code.FAIL, hint="该物品无法开启")

        # 3.获取奖励配置
        prop_level = prop_item.get("prop_level")
        award_confs = await ConfAwardRC.get_award_items(award_type=AwardType.OPEN_TREASURE_BOX)
        open_awards = next((i.get("conf_items") for i in award_confs if prop_level == i.get("award_level")), None)
        (not open_awards) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有抽奖的奖励")

        # 4.获取宝盒机率配置并开启
        conf_odds = prop_item.get("extra_info")
        result = UtilsTool.select_element_by_prob(conf_odds, size=100)
        (not result) and self.answer(self.sta_code.REQ_FREQUENT, hint="系统开小差了，请稍后再试")

        # 5.消耗宝盒统计
        cost_item = {
            "goods_id": goods_id,
            "goods_count": -1,
            "goods_type": GoodsType.GAME_PROP.val
        }
        # 6.兑奖
        open_items = next((i for i in open_awards if int(result) == i.get("level")), None)
        (not open_items) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="开启了空宝盒，请联系客服")
        StatFlow.stat_common_flow(awards=[open_items], g_reason=ReasonCostGold.OPEN_TREASURE_BOX)

        # 7.发奖 / 更新背包
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                up_goods = await UpAssets.update_assets(uid, [open_items], [], is_pack=True)
                await UserBagRC.update_user_bag(uid, [cost_item])  # 更新剩余宝盒
                await BaseUserRC.deal_user_update_goods(uid, id_list=[bag_item.get('bag_id')], is_del=True,
                                                        key_name=UserBagRC.KEY_NEWLY)
        except Exception as e:
            self.error_log(f"OpenTreasureBox 事务执行失败，原因：{e}")
            self.answer(self.sta_code.FAIL, hint="宝盒开启失败，请联系客服")

        self.info_log(uid, "OpenTreasureBox 宝盒开启成功")
        return self.answer(data=up_goods)


class AnnouncementsHandler(GameAuthApi):
    """ 公告相关 """

    async def get(self, _a: Request, **_b):
        data = await ConfAnnouncementsRC.get_current_announcement()
        pb_data = S2CTopAnnouncements.pb_model(data)
        self.answer(data=pb_data)
