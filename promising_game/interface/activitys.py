"""
充值活动类接口
"""
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse, json_encode
from tortoise.transactions import in_transaction
from common.proto.py_pb2.http_player_vault import PbGoods
from common.public.enum_const import DbKey
from common.utils.kit_dt import KitDt
from promising_game.base_api import GameAuthApi
from promising_game.handler.up_assets import UpAssets, StatFlow
from promising_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from common.proto.py_pb2.http_trade_center import PbActivityItems, PbVip
from promising_game.model_rc.base_skin import UserSkinRC
from promising_game.model_rc.conf_json import ConfJsonRC
from promising_game.model_rc.vip_level import UserVipRC, ConfVipRC
from promising_game.const import ActivityType, ActivitySta, ConditionType, ReasonCostDiamond, ReasonCostGold


class GetActivityHandler(GameAuthApi):
    """
    获取充值活动配置
    query_param: act_type / act_id
    """

    async def get(self, req: Request, **kwargs):
        act_type = req.args.get("act_type")
        act_id = req.args.get("act_id")
        (not act_type and not act_id) and self.answer(self.sta_code.ERR_ARG, hint='缺少活动查询条件')

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        platform = req.args.get('c_platform') or ''
        os = req.args.get('c_os') or ''

        # 1.获取活动配置
        if act_type:
            act_type = self.check_int(act_type, require=True, p_name="act_type")
            act_enum = ActivityType.find_member_by_val(act_type)
            (not isinstance(act_enum, ActivityType)) and self.answer(self.sta_code.ERR_ARG, hint='暂时没找到活动类型')
            act_conf = await ConfActivityRC.get_activity_items_by_type(act_type, platform, os)
        else:
            act_id = self.check_int(act_id, require=True, minval=3000, maxval=3999, p_name="act_id")
            ac = await ConfActivityRC.get_activity_item_by_id(act_id, platform, os)
            act_conf = [ac]

        (not act_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint='暂时没找到这类型的活动哦')

        # 2.用户充值数据
        act_datas = await UserActivityRC.check_charge_data(uid, act_conf)
        (not act_datas) and self.answer(self.sta_code.ERR_CONF, hint="活动数据不存在")

        # 3.额外配置
        extra_conf = ""
        if act_datas[0].get("act_type") == ActivityType.LIFETIME_CARD:
            conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_LIFETIME_CARD)
            extra_conf = conf_data.get("privilege_show")

        data = {
            "act_conf": act_datas,
            "extra_conf": json_encode(extra_conf)
        }
        proto_data = PbActivityItems.pb_model(data)
        self.info_log(uid, "GetActivityHandler 获取活动配置 / 用户充值数据 成功", act_type, act_id)
        return self.answer(data=proto_data)


class GetActivityAwards(GameAuthApi):
    """通过act_id领取活动奖励"""

    async def post(self, req: Request, **kwargs):
        act_id = self.check_int(req.json.get("act_id"), require=True, minval=3000, maxval=3999, p_name="act_id")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        platform = req.args.get('c_platform') or ''
        os = req.args.get('c_os') or ''

        # 1.查询活动记录
        charge_record = await UserActivityRC.get_user_charge_records_by_id(uid, act_id)
        (not charge_record) and self.answer(self.sta_code.ACTIVITY_NOT_EXIST, hint="您未参与任何活动")

        # 2.查询活动
        act_item = await ConfActivityRC.get_activity_item_by_id(act_id, platform, os)
        (not act_item) and self.answer(self.sta_code.ERR_CONF, hint="活动数据不存在")

        # 3.检验活动
        start_time, end_time, cur_time = act_item.get('start_time'), act_item.get('end_time'), tool_dt.cur_time()
        if start_time > 0 and cur_time < start_time:
            self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="活动暂未开始")
        if end_time > 0 and cur_time > end_time:
            self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="活动已经结束")

        # 4.检查活动记录
        deadline = charge_record.get('deadline')
        if deadline and deadline < cur_time:
            self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="活动已到期，请续期之后再来领取")

        if charge_record.get("activity_sta") != ActivitySta.ACT_INCOMPLETE:
            self.answer(self.sta_code.NOT_IN_VALID_STATE, hint="活动状态无法领奖")

        map_func = {
            ConditionType.DAY_REGULAR.val: self.act_pull_day_regular,
            ConditionType.PULL_TOTAL.val: self.act_pull_total
        }
        pull_func = map_func.get(act_item.get('condition_type'))
        if pull_func and callable(pull_func):
            act_awards, new_data = await pull_func(uid, req, act_item, charge_record)
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await UserActivityRC.update_user_charge_records(uid, act_item, new_data)
                    up_goods = await UpAssets.update_assets(uid, act_awards, [], is_pack=True)
            except Exception as e:
                self.error_log(f"GetActivityAwards 事务执行失败，原因：{e}")
                self.answer(code=self.sta_code.FAIL, hint="奖励领取失败，请联系客服")

            pro_data = PbGoods.pb_model(up_goods)
            self.info_log(uid, act_item.get('desc', ''), '活动领取成功')
            return self.answer(data=pro_data)
        return self.answer(code=self.sta_code.FAIL)

    async def act_pull_day_regular(self, _, __, activity_item, charge_record):
        """每天固定数量领取"""
        act_awards = activity_item.get('act_awards')
        (not act_awards) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="没有需要领取的奖励")

        today_time_node = KitDt.timestamp_today()
        new_data = {'id': charge_record.get('id'), 'time_node': today_time_node}
        # 1.检查领取日期记录
        old_awards_achieved = charge_record.get('awards_achieved')
        awards_achieved = [] if not old_awards_achieved else json_parse(old_awards_achieved)
        (today_time_node in awards_achieved) and self.answer(code=self.sta_code.ALREADY_DO, hint="今天的奖励已全部领取，请明天再来哦")

        # 2.检查日奖次数（同一天次数才算）
        join_limit_day = activity_item.get('join_limit_day')
        times_day = charge_record.get('times_day')
        if charge_record.get('time_node', 0) == today_time_node:
            (times_day >= join_limit_day) and self.answer(self.sta_code.ALREADY_DO, hint="今天的奖励已领取，请明天再来哦")
            times_day += 1
        else:
            times_day = 1
        new_data['times_day'] = times_day

        # 3.当天末次处理
        if times_day == join_limit_day:
            awards_achieved.append(today_time_node)
            new_data['awards_achieved'] = json_encode(awards_achieved)

        # 4.日奖奖品
        goods = []
        for aw in act_awards:
            if aw.get('day') == 0:  # 0为每天都可领取
                goods.append(aw)

        # 5.验货发货
        (not goods) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="奖励缺货，请联系客服")
        StatFlow.stat_activity_flow(activity_item.get('act_type'), act_awards)

        return goods, new_data

    async def act_pull_total(self, uid, req, activity_item, charge_record):
        act_awards = activity_item.get('act_awards')
        (not act_awards) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="没有需要领取的奖励")
        join_limit_total = activity_item.get('join_limit_total') or 3

        target = self.check_int(req.json.get('target'), require=True, minval=1, maxval=join_limit_total, p_name="target")

        new_data = {'id': charge_record.get('id')}
        # 1.检查领取记录
        old_awards_achieved = charge_record.get('awards_achieved')
        awards_achieved = [] if not old_awards_achieved else json_parse(old_awards_achieved)
        (target in awards_achieved) and self.answer(code=self.sta_code.ALREADY_DO, hint="该奖励已经领取")

        # 2.检查总领奖次数
        if len(awards_achieved) >= join_limit_total:
            self.answer(self.sta_code.ALREADY_DO, hint="所有的奖励已经领取")

        # 3.检查解锁奖励：目前只有首充逻辑
        awards_unlocked = UserActivityRC.cal_awards_unlocked(charge_record.get("join_time"))
        (target not in awards_unlocked) and self.answer(code=self.sta_code.ALREADY_DO, hint="今天的奖励还未解锁，请明天再来哦")

        # 4.提取对应的奖励/更新领奖记录
        awards_achieved.append(target)
        new_data['awards_achieved'] = json_encode(awards_achieved)

        goods = [aw for aw in act_awards if aw.get('day') == target]
        (not goods) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="奖励缺货，请联系客服")

        for g in goods:
            await UserSkinRC.deal_hold_skin(uid, g)
        StatFlow.stat_activity_flow(activity_item.get('act_type'), act_awards)

        return goods, new_data


class VipLevelHandler(GameAuthApi):
    """获取VIP等级配置"""

    async def get(self, _, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 1.获取vip配置 / 用户vip数据
        vip_items = await ConfVipRC.get_all_vip_items()
        (not vip_items) and self.answer(self.sta_code.NO_CONFIGURATION, hint="vip配置数据不存在")
        u_vip_info = await UserVipRC.cache_by_pk(uid)

        # 2.获取等级和领奖状态
        today_time_node = KitDt.timestamp_today()
        pull_time_node = u_vip_info.get("time_node", 0)
        vip_id = u_vip_info.get("vip_id")

        old_level_achieved = u_vip_info.get("level_achieved")
        level_achieved = [] if not old_level_achieved else json_parse(old_level_achieved)

        old_daily_achieved = [] if pull_time_node != today_time_node else u_vip_info.get("daily_achieved")
        daily_achieved = [] if not old_daily_achieved else json_parse(old_daily_achieved)

        level = 0
        next_need_amount = 0
        for v_conf in vip_items:
            if v_conf.get("id") == vip_id:
                level = v_conf.get("level")
                # 立即检查并计算下一个等级所需的金额
                next_v_conf = next((vi for vi in vip_items if vi.get("level") == level + 1), None)
                if next_v_conf:
                    next_need_exp = next_v_conf.get("need_exp")
                    cal_exp = next_need_exp - u_vip_info.get("cur_exp", 0)
                    conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_VIP)
                    next_need_amount = cal_exp / conf_data.get("exp_rate", 10)
                break

        # 3.计算vip等级奖/日奖 领奖情况
        conf_vip = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_VIP)
        level_targets = conf_vip.get("targets") or []
        level_awards_sta = ConfJsonRC.stat_of_completion(level, level_achieved, level_targets)
        daily_awards_sta = ConfJsonRC.stat_of_completion(level, daily_achieved, level_targets)

        vip_data = {
            "cur_level": level,
            "cur_exp": u_vip_info.get("cur_exp") or 0,
            "daily_awards_sta": json_encode(daily_awards_sta),
            "level_awards_sta": json_encode(level_awards_sta),
            "next_need_amount": round(next_need_amount)
        }
        return_data = {
            "vip_conf": vip_items,
            "vip_data": vip_data
        }
        proto_data = PbVip.pb_model(return_data)
        self.info_log(uid, "VipLevelHandler 获取VIP配置 / 用户VIP数据 成功")
        return self.answer(data=proto_data)


class VipLevelPullAwards(GameAuthApi):
    """
    VIP用户领取奖励
    level:对应等级奖，为0则每日奖
    """

    async def post(self, req: Request, **kwargs):
        level = self.check_int(req.json.get('level', 0), require=True, minval=0, maxval=10, p_name="level")
        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 1.获取vip配置 / 用户vip数据
        vip_items = await ConfVipRC.get_all_vip_items(is_all=True)
        (not vip_items) and self.answer(self.sta_code.NO_CONFIGURATION, hint="vip配置数据不存在")
        u_vip_info = await UserVipRC.cache_by_pk(uid)
        (not u_vip_info or u_vip_info.get("default_cache")) and self.answer(self.sta_code.CONDITION_NOT_MET, hint='用户vip等级还未达成，请继续加油吧')

        vip_id = u_vip_info.get("vip_id")
        cur_level = 0
        for v_conf in vip_items:
            if v_conf.get("id") == vip_id:
                cur_level = v_conf.get("level")

        awards = []
        # 3.等级奖统计
        if level:
            (level > cur_level) and self.answer(self.sta_code.FAIL, hint='该vip等级还未达成，请继续加油吧')
            old_level_achieved = u_vip_info.get("level_achieved")
            level_achieved = [] if not old_level_achieved else json_parse(old_level_achieved)
            if level_achieved and level in level_achieved:
                self.answer(self.sta_code.ALREADY_DO, hint='该vip等级奖励已经领取')

            for v_conf in vip_items:
                if v_conf.get("level") == level:
                    level_awards = v_conf.get("level_awards")
                    level_achieved.append(level)
                    if level_awards:
                        awards = level_awards
                        break
            StatFlow.stat_common_flow(awards=awards, d_reason=ReasonCostDiamond.VIP_LEVEL_AWARDS, g_reason=ReasonCostGold.VIP_LEVEL_AWARDS)
            pull_info = {"level_achieved": json_encode(level_achieved)}

        # 4.日奖统计
        else:
            today_time_node = KitDt.timestamp_today()
            pull_time_node = u_vip_info.get("time_node", 0)

            old_daily_achieved = [] if pull_time_node != today_time_node else u_vip_info.get("daily_achieved")
            daily_achieved = [] if not old_daily_achieved else json_parse(old_daily_achieved)
            for v_conf in vip_items:
                v_level = v_conf.get("level")
                if v_level <= cur_level:
                    if daily_achieved and v_level in daily_achieved:
                            continue
                    daily_awards = v_conf.get("daily_awards")
                    if daily_awards:
                        daily_achieved.append(v_level)
                        awards.extend(daily_awards)
            StatFlow.stat_common_flow(awards=awards, g_reason=ReasonCostGold.VIP_DAILY_AWARDS)
            pull_info = {"daily_achieved": json_encode(daily_achieved), "time_node": today_time_node}

        # 5.发奖/改写记录
        (not awards) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="vip奖励缺货，请联系客服")
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UserVipRC.update_user_vip(uid, pull_info, u_vip_info)
                up_goods = await UpAssets.update_assets(uid, awards, [], is_pack=True)
        except Exception as e:
            self.error_log(f"VipLevelPullAwards 事务执行失败，原因：{e}")
            self.answer(code=self.sta_code.FAIL, hint="vip奖励领取失败，请联系客服")

        pro_data = PbGoods.pb_model(up_goods)
        self.info_log(uid, f"VipLevelPullAwards vip领取{level}奖成功")
        return self.answer(data=pro_data)
