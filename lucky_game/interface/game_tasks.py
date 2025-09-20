"""
游戏任务相关接口
"""
from sanic import Request
from c_services.const.cs_enum_const import CmdWorkers
from common.utils.kit_dt import KitDt
from nsanic.libs.tool import json_parse, json_encode
from tortoise.transactions import in_transaction
from common.proto.py_pb2.http_player_vault import PbGoods
from common.public.enum_const import TaskId, DbKey
from lucky_game.base_api import GameAuthApi
from common.proto.py_pb2.http_interaction import PbTask, pack_task_data
from lucky_game.handler.up_assets import UpAssets, StatFlow
from lucky_game.model_rc.base_award import ConfAwardRC
from lucky_game.model_rc.base_game_task import ConfTaskRC, UserTaskRC
from lucky_game.model_rc.goods_manager import GoodsManagerRC
from lucky_game.model_rc.active_behaviors import UserBehaviorsRC
from lucky_game.model_rc.base_interaction import InteractionRC
from lucky_game.const import TaskType, AwardType, CompleteSta, ReasonCostGold, EventTracking


class GameTaskHandler(GameAuthApi):
    """ 获取指定task_type任务配置 / 用户活跃"""

    async def get(self, req: Request, **kwargs):
        task_type = self.check_int(req.args.get("task_type"), require=True, p_name="task_type")
        tt_enum = TaskType.find_member_by_val(task_type)
        (not tt_enum) and self.answer(self.sta_code.ERR_ARG, hint="该任务类型不存在")

        user = kwargs.get("u_info")
        uid = user.get("uid")
        platform = req.args.get('c_platform') or ''

        # 1.获取任务配置 + 用户任务数据
        task_items = await ConfTaskRC.get_task_items(task_type=task_type, platform=platform, is_pack=True)
        (not task_items) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有任务奖励")
        task_conf = await UserTaskRC.check_task_data(uid, task_type, task_items)
        (not task_conf) and self.answer(self.sta_code.ERR_CONF, hint="任务数据不存在")

        return_data = {"task_conf": task_conf}
        if task_type != TaskType.ROOKIE_TASK:
            # 2.获取活跃配置
            active_items = await ConfAwardRC.get_award_items(AwardType.ACTIVE)
            (not active_items) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有活跃奖励")
            active_conf = await InteractionRC.get_conf_daily_active(active_items)
            (not active_conf) and self.answer(self.sta_code.ERR_CONF, hint="活跃值数据不存在")

            # 3.获取用户活跃值 / 计算活跃达成奖励
            active_awards_sta, active_score = await UserBehaviorsRC.stat_active_achieve_award(uid, KitDt.timestamp_today())
            active_data = {
                "cur_active_score": active_score,
                "active_awards_sta": json_encode(active_awards_sta)
            }

            return_data["active_conf"] = active_conf
            return_data["active_data"] = active_data

        pro_data = PbTask.pb_model(return_data)
        self.info_log(uid, f"GameTaskHandler {tt_enum.phrase} 获取任务配置 / 用户日活数据 成功")
        return self.answer(data=pro_data)


class GameTaskUpdateForRookie(GameAuthApi):
    """ 新手引导中更新任务（西行路新手引导中专用） """

    async def post(self, req: Request, **kwargs):
        is_rookie_task = self.check_int(req.json.get("is_rookie_task", 0), require=True, default=0, p_name='is_rookie_task')
        if not is_rookie_task:
            self.answer(self.sta_code.ERR_ARG, hint="任务更新非法调用")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        task_info = {
            "task_id": TaskId.MONOPOLY_ROLL_DICE_1.val,
            "add_val": 1
        }
        finish_flag, task_data = await UserTaskRC.update_user_task_records(uid, task_info)
        if finish_flag:
            data_model = pack_task_data(PbTask.task_model(), **task_data)
            self.answer(data=data_model, hint="ok")
        self.answer(hint="任务更新失败！")


class GameTaskUpdate(GameAuthApi):
    """ 更新任务状态（主动） """

    async def post(self, req: Request, **kwargs):
        task_id = req.json.get("task_id")
        if not TaskId.find_member_by_val(task_id):
            self.answer(self.sta_code.ERR_ARG, hint="该任务不存在")

        if task_id not in UserTaskRC.ALLOW_UPDATE_TASKS:  # 更新任务交由客户端调用时需要进行非法拦截，避免恶意调用
            self.answer(self.sta_code.ERR_ARG, hint="任务更新非法调用")

        add_val = req.json.get("add_val") or 1  # 增加值
        self.check_int(add_val, require=True, minval=1, p_name="add_val")

        is_sum = req.json.get("is_sum") or 0  # 是否已累加
        self.check_int(is_sum, require=True, default=0, p_name="is_sum")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        task_info = {
            "task_id": task_id,
            "add_val": add_val
        }
        finish_flag, task_data = await UserTaskRC.update_user_task_records(uid, task_info, is_sum=is_sum)
        if finish_flag:
            data_model = pack_task_data(PbTask.task_model(), **task_data)
            self.answer(data=data_model, hint="ok")
        self.answer(hint="任务更新失败！")


class GameTaskComplete(GameAuthApi):
    """任务完成领奖 / 加活跃值"""

    async def post(self, req: Request, **kwargs):
        task_id = req.json.get("task_id")
        ti_enum = TaskId.find_member_by_val(task_id)
        (not ti_enum) and self.answer(self.sta_code.ERR_ARG, hint="该任务不存在")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 1.获取任务配置
        task_item = await ConfTaskRC.get_task_item_by_id(task_id)
        (not task_item) and self.answer(self.sta_code.NO_CONFIGURATION, hint="任务配置不存在")
        await GoodsManagerRC.pack_goods_conf([task_item])

        # 2.获取用户任务数据
        task_data = await UserTaskRC.cache_task_record_by_id(uid, task_id)
        (not task_data) and self.answer(self.sta_code.ERR_CONF, hint="暂无任务信息")

        # 3.确定任务统计周期
        task_type = task_item.get("task_type")  # 类型，决定统计周期
        time_node = ConfTaskRC.get_task_time_node(task_type, task_item)

        if (task_data.get("time_node") != time_node or
                task_data.get("task_sta") in (CompleteSta.INCOMPLETE, CompleteSta.CLAIMED)):
            self.answer(self.sta_code.CONDITION_NOT_MET, hint="任务不满足领取条件或已领取奖励")

        # 4.领取任务奖励
        g_reason = None
        event_tracking = None
        match task_type:
            case TaskType.DAILY_TASK:
                g_reason = ReasonCostGold.DAILY_TASK
            case TaskType.ROOKIE_TASK:
                g_reason = ReasonCostGold.ROOKIE_TASK
                # 新手引导任务相对客户端来说领奖才算完成，否则算跳过
                if task_id == TaskId.ROOKIE_PART_FIRST.val:
                    event_tracking = EventTracking.AFTER_ROOKIE_TASK_FIRST
                elif task_id == TaskId.ROOKIE_PART_SECOND_1.val:
                    event_tracking = EventTracking.AFTER_ROOKIE_TASK_SECOND_1
                elif task_id == TaskId.ROOKIE_PART_SECOND_2.val:
                    event_tracking = EventTracking.AFTER_ROOKIE_TASK_SECOND_2
                elif task_id == TaskId.ROOKIE_PART_MONOPOLY.val:
                    event_tracking = EventTracking.AFTER_ROOKIE_TASK_MONOPOLY

        conf_items = task_item.get("conf_items")
        (not conf_items) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="任务完成奖励缺货，请联系客服")
        if g_reason:
            StatFlow.stat_common_flow(awards=conf_items, g_reason=g_reason)

        # 5.更新任务记录/增加活跃值
        new_task = {"task_id": task_id, "task_sta": CompleteSta.CLAIMED}
        active_params = {"uid": uid, "time_node": time_node}
        old_active = await UserBehaviorsRC.cache_user_active_score(active_params)
        active_score = task_item.get("active_score")
        if old_active:
            new_active = {"active_score": old_active.get("active_score") + active_score}
        else:
            new_active = {"uid": uid, "time_node": time_node, "active_score": active_score}
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UserBehaviorsRC.update_user_active_records(active_params, new_active, old_active)
                await UserTaskRC.update_user_task_records(uid, new_task, is_pull=True)
                up_goods = await UpAssets.update_assets(uid, conf_items, [])
                if event_tracking:
                    await self.push_task2worker(CmdWorkers.USER_EVENT_TRACKING, uid=uid, msg={'event_tracking': event_tracking})
        except Exception as e:
            self.error_log(f"GameTaskComplete 事务执行失败，原因：{e}")
            self.answer(self.sta_code.FAIL, hint="任务完成发奖失败，请联系客服")

        pro_data = PbGoods.pb_model(up_goods)
        self.info_log(uid, f"GameTaskComplete {ti_enum.phrase} 任务完成领奖成功")
        return self.answer(data=pro_data)


class GameActiveComplete(GameAuthApi):
    """活跃值达成领奖"""

    async def post(self, req: Request, **kwargs):
        target = self.check_int(req.json.get('achieve_value'), require=True, minval=10, maxval=100, p_name="achieve_value")

        user = kwargs.get("u_info")
        uid = user.get("uid")
        today_time_node = KitDt.timestamp_today()

        # 1.获取活跃达成记录
        active_params = {"uid": uid, "time_node": today_time_node}
        old_active = await UserBehaviorsRC.cache_user_active_score(active_params)
        (not old_active) and self.answer(self.sta_code.ERR_CONF, hint="亲，您目前的活跃值不足，请再接再厉")

        # 2.活跃达成计算
        cur_score = old_active.get('active_score')
        (cur_score < target) and self.answer(self.sta_code.CONDITION_NOT_MET, hint="亲，您目前的活跃值不足，请再接再厉")

        # 3.活跃达成奖励配置
        active_items = await ConfAwardRC.get_award_items(AwardType.ACTIVE)
        (not active_items) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有活跃达成奖励")
        active_conf = await InteractionRC.get_conf_daily_active(active_items)
        (not active_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="活跃达成配置不存在")

        # 4.满足的所有活跃奖统计
        awards = []
        old_active_achieved = old_active.get('active_achieved')
        active_achieved = [] if not old_active_achieved else json_parse(old_active_achieved)
        for a_conf in active_conf:
            achieve_value = a_conf.get("achieve_value")
            if achieve_value <= cur_score:
                if active_achieved and achieve_value in active_achieved:
                    continue
                active_awards = a_conf.get("conf_items")
                if active_awards:
                    active_achieved.append(achieve_value)
                    awards.extend(active_awards)

        # 5.更新活跃领奖记录 / 发奖
        (not awards) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="活跃达成奖励缺货，请联系客服")
        StatFlow.stat_common_flow(awards=awards, g_reason=ReasonCostGold.DAILY_ACTIVE)
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                pull_info = {"uid": uid, "active_achieved": json_encode(active_achieved)}
                await UserBehaviorsRC.update_user_active_records(active_params, pull_info, old_active)
                up_goods = await UpAssets.update_assets(uid, awards, [])
        except Exception as e:
            self.error_log(f"GameActiveComplete 事务执行失败，原因：{e}")
            return self.answer(self.sta_code.FAIL, hint="活跃达成发奖失败，请联系客服")

        pro_data = PbGoods.pb_model(up_goods)
        self.info_log(uid, f"GameActiveComplete 活跃{cur_score}达成领奖成功 {active_achieved}")
        return self.answer(data=pro_data)