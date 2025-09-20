"""
玩家游戏资源
基础物品 / 道具 / 装扮
"""
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from tortoise.transactions import in_transaction
from common.proto.py_pb2.common import get_one_of_model
from common.utils.kit_dt import KitDt
from common.utils.utils import UtilsTool
from lucky_game.base_api import GameAuthApi
from common.public.conf import R_UID_THRESHOLD, ROBOT_BATTLE
from lucky_game.model_rc.base_activity import UserActivityRC
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_game_task import UserTaskRC
from lucky_game.model_rc.base_prop import ItemsPropRC
from lucky_game.model_rc.base_ranking import ConfSeasonRC
from lucky_game.model_rc.base_robot import ConfRobotRC, BaseRobotRC
from lucky_game.model_rc.base_safe_box import UserSafeBoxRC
from lucky_game.model_rc.base_skin import UserSkinRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.goods_manager import GoodsManagerRC
from lucky_game.model_rc.base_cosmetic import ItemsCosmeticRC, UserCosmeticRC
from common.proto.py_pb2.http_player_vault import PbBag, PbCosmetic, PbSafeBox, PbGameProp, PbUsedGoods, PbGoods
from common.public.enum_const import CacheKey, ServiceEnum, GameType, DbKey, Switch, TaskId
from lucky_game.const import SafeBoxOpType, GotType, ReasonCostGold, PutType, GoodsType, SeasonStatus, \
    CompleteSta, JumpTarget, ActivityItem, JumpType


class BagHandler(GameAuthApi):
    """获取背包全部"""

    async def get(self, _: Request, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")

        all_bag = await UserBagRC.get_user_bag_by_type(uid=uid)
        if all_bag:
            await GoodsManagerRC.pack_goods_list(all_bag, is_all=True)
            UserBagRC.organize_bag_data(all_bag)
            # 排序逻辑
            all_bag = sorted(all_bag, key=lambda x: (
                x.get('goods_type', 0),
                -(x.get('game_prop_type', 0)),
                x.get('goods_id', 0)
            ))

        new_bag = await BaseUserRC.deal_user_update_goods(uid, key_name=UserBagRC.KEY_NEWLY)
        data = {
            "all_bag": all_bag,
            "new_bag": [] if not new_bag else json_parse(new_bag)
        }
        proto_data = PbBag.pb_model(data)
        self.info_log(uid, "BagHandler 背包加载成功")
        return self.answer(data=proto_data)


class DropBagItem(GameAuthApi):
    """通过bag_id删除背包过期项目"""

    async def post(self, req: Request, **kwargs):
        bag_id = self.check_int(req.json.get("bag_id"), require=True, minval=1, p_name="bag_id")
        user = kwargs.get("u_info")
        uid = user.get("uid")

        bag_item = await UserBagRC.get_user_bag_by_id(uid, bag_id)
        (not bag_item) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没找到物品")

        exp_time = bag_item.get("exp_time")
        (exp_time > tool_dt.cur_time()) and self.answer(self.sta_code.CONDITION_NOT_MET, hint="物品没有过期，不允许删除")

        all_bag = await UserBagRC.drop_user_bag_by_id(uid, bag_id)
        (not all_bag) and self.answer(self.sta_code.FAIL, hint="删除物品失败")

        new_bag = await BaseUserRC.deal_user_update_goods(uid, key_name=UserBagRC.KEY_NEWLY)
        data = {
            "all_bag": all_bag,
            "new_bag": [] if not new_bag else json_parse(new_bag)
        }
        proto_data = PbBag.pb_model(data)
        self.info_log(uid, f"DropBagItem 背包删除物品{bag_id}成功")
        return self.answer(data=proto_data)


class GetGamePropHandler(GameAuthApi):
    """获取游戏道具（准备界面使用）"""

    async def get(self, _, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")

        prop_conf = await ItemsPropRC.get_game_prop_items()
        (not prop_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有道具配置，请稍后再试")

        season_conf = await ConfSeasonRC.get_current_season()
        season_sta = True if season_conf.get("status", 0) == SeasonStatus.ACTIVE_SEASON else False

        user_bag = await UserBagRC.get_user_bag_by_type(uid, goods_types=[GoodsType.GAME_PROP.val])
        all_prop = UserBagRC.check_bag_data(user_bag, prop_conf, is_ready=True, season_sta=season_sta)
        (not all_prop) and self.answer(self.sta_code.ERR_CONF, hint="没有道具数据，请稍后再试")

        proto_data = PbGameProp.pb_model(all_prop)
        self.info_log(uid, f"GetGamePropHandler 玩家持有道具加载成功 赛季状态 {season_sta}")
        return self.answer(data=proto_data)


class GetCosmeticHandler(GameAuthApi):
    """获取游戏装扮"""

    async def get(self, _: Request, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")

        cos_conf = await ItemsCosmeticRC.get_cosmetic_items()
        (not cos_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有装扮配置，请稍后再试")

        user_cos = await UserCosmeticRC.check_cosmetic_data(uid, cos_conf)
        (not user_cos) and self.answer(self.sta_code.ERR_CONF, hint="没有装扮数据，请稍后再试")

        new_cos = await BaseUserRC.deal_user_update_goods(uid, key_name=UserCosmeticRC.KEY_NEWLY)
        data = {
            "all_cos": user_cos,
            "new_cos": [] if not new_cos else json_parse(new_cos)
        }
        proto_data = PbCosmetic.pb_model(data)
        self.info_log(uid, "GetCosmeticHandler 游戏装扮加载成功")
        return self.answer(data=proto_data)


class GetCosmeticUsedItems(GameAuthApi):
    """
    装扮使用项查询， 只返回cosmetic_item_id
    隐性需求：随机给机器人装扮道具
    """

    async def get(self, req: Request, **kwargs):
        query_uid_list = req.args.get("query_uid_list")
        query_uid_list = json_parse(query_uid_list) if query_uid_list else []
        if not query_uid_list:
            user = kwargs.get("u_info")
            query_uid_list.append(user.get("uid", 0))

        for uid in query_uid_list:
            if not isinstance(uid, int):
                self.info_log(f"Invalid UID detected: {uid}, UIDs: {query_uid_list}")
                return self.answer(self.sta_code.ERR_ARG, hint=f"非法的用户ID: {uid}")

        result_list = []
        for uid in query_uid_list:
            if uid > R_UID_THRESHOLD:  # 真人
                used_list = await UserCosmeticRC.get_user_used_cosmetic(uid)
                if not used_list:
                    continue

            elif ROBOT_BATTLE[0] <= uid <= ROBOT_BATTLE[1]:  # 战斗机器人需要按场次配置
                leisure_id = self.check_int(req.args.get("leisure_id"), require=True, default=1, p_name="leisure_id")
                robot_conf = await ConfRobotRC.get_robot_conf_by_id(leisure_id)
                used_list = []
                if robot_conf:
                    for key in ["avatar_frame", "chat_bubble"]:
                        config = robot_conf.get(key)
                        if config:
                            res = UtilsTool.select_element_by_prob(config, size=100)
                            if res != "default":
                                used_list.append(int(res))

            else:  # 社交机器人需要真实配置好的
                robot_conf = await BaseRobotRC.cache_by_pk(uid)
                used_list = []
                extra_info = robot_conf.get("extra_info")
                if not extra_info:
                    continue
                avatar_frame = extra_info.get("avatar_frame")
                if avatar_frame:
                    used_list = [avatar_frame]

            result_list.append({"uid": uid, "used_goods": used_list})

        proto_data = PbUsedGoods.pb_model(result_list)
        self.info_log(query_uid_list, "GetCosmeticUsedItems 正在使用的装扮查询成功")
        return self.answer(data=proto_data)


class UseCosmeticItem(GameAuthApi):
    """使用游戏装扮"""

    async def post(self, req: Request, **kwargs):
        goods_id = self.check_int(req.json.get("goods_id"), require=True, minval=1000, maxval=1999, p_name="goods_id")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        data_model = await UserCosmeticRC.get_cosmetic_with_items(uid, goods_id)
        (not data_model) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没找到该装扮或道具")

        got_type = data_model.got_type
        (got_type != GotType.UNUSED) and self.answer(self.sta_code.ALREADY_DO, hint="无需重复使用")

        exp_time = data_model.exp_time
        if exp_time and exp_time < tool_dt.cur_time():
            self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="装扮或道具已过期，不允许使用")

        cosmetic_type = data_model.cosmetic_item.cosmetic_type
        sta = await UserCosmeticRC.set_user_cosmetic(uid, goods_id, cosmetic_type)
        (not sta) and self.answer(self.sta_code.FAIL, hint="切换使用失败，请稍后再试")

        self.info_log(uid, f"UseCosmeticItem 装扮道具{goods_id}使用成功")
        return self.answer(hint="使用成功")


class ClickNewGoodsItem(GameAuthApi):
    """新获得物品点击"""

    async def post(self, req: Request, **kwargs):
        id_list = req.json.get("id_list")
        id_list = [] if not id_list else json_parse(id_list)
        (not isinstance(id_list, list)) and self.answer(self.sta_code.ERR_ARG, hint='没有识别到需要点击的物品ID')

        put_type = self.check_int(req.json.get("put_type"), require=True, p_name="put_type")
        act_enum = PutType.find_member_by_val(put_type)
        (not isinstance(act_enum, PutType)) and self.answer(self.sta_code.ERR_ARG, hint='未知的存放物品来源')

        user = kwargs.get("u_info")
        uid = user.get("uid")

        match put_type:
            case PutType.U_BAG:
                key_name = UserBagRC.KEY_NEWLY
            case PutType.U_SKIN:
                key_name = UserSkinRC.KEY_NEWLY
            case _:
                key_name = UserCosmeticRC.KEY_NEWLY

        sta = await BaseUserRC.deal_user_update_goods(uid, id_list=id_list, is_del=True, key_name=key_name)
        (not sta) and self.answer(hint="重复点击或失败")

        self.info_log(uid, f"ClickNewGoodsItem 新物品点击成功 {id_list}")
        return self.answer(hint="点击成功")


class SafeBoxHandler(GameAuthApi):
    """获取保险箱配置"""

    async def get(self, _: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        # 1.获取保险箱配置
        conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_SAFE_BOX)
        (not conf_data) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有相关配置")

        # 2.查询玩家保险箱信息
        safe_box_info = await UserSafeBoxRC.cache_by_pk(uid)
        user_data = {
            "amount": safe_box_info.get("amount") or 0,
            "complement_sta": safe_box_info.get("complement_sta") or Switch.CLOSE,
            "complement_count": safe_box_info.get("complement_count") or 0,
            "space": safe_box_info.get("space") or 0,
            "times_limit": safe_box_info.get("times_limit") or 0,
            "exp_time": safe_box_info.get("exp_time") or 0,
        }
        # 3.每日使用次数获取
        used_record = await BaseUserRC.get_safe_box_count(uid)
        used_times = 0
        if used_record:
            if KitDt.timestamp_today() == used_record.get("time_node", 0):
                used_times = used_record.get("used_times")
        user_data["used_times"] = used_times

        data = {
            "safe_box_conf": conf_data,
            "safe_box_data": user_data
        }
        proto_data = PbSafeBox.pb_model(data)
        self.info_log(uid, "SafeBoxHandler 加载保险箱成功")
        return self.answer(data=proto_data)


class SafeBoxOperateUser(GameAuthApi):
    """
    保险箱操作
    存 / 取 / 设置自动补足 / 领取补足金
    """

    async def post(self, req: Request, **kwargs):
        # 1.操作类型核验
        opt_type = self.check_int(req.json.get("opt_type"), require=True, p_name="opt_type")
        ot_enum = SafeBoxOpType.find_member_by_val(opt_type)
        (not ot_enum) and self.answer(code=self.sta_code.ERR_ARG, hint="不支持的操作类型")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 2.查询玩家保险箱信息
        safe_box_info = await UserSafeBoxRC.cache_by_pk(uid)
        if not safe_box_info or safe_box_info.get("default_cache"):
            self.answer(self.sta_code.CONDITION_NOT_MET, hint="未激活保险箱，请开通终生卡获得使用权限")

        map_func = {
            SafeBoxOpType.SAVE.val: self.safe_box_save,
            SafeBoxOpType.DRAW.val: self.safe_box_draw,
            SafeBoxOpType.SET_COMPLEMENT.val: self.safe_box_set_complement,
            SafeBoxOpType.USE_COMPLEMENT.val: self.safe_box_use_complement
        }
        opt_func = map_func.get(opt_type)
        if opt_func and callable(opt_func):
            sta = await opt_func(u_info, req, safe_box_info)
            self.info_log(uid, f"SafeBoxOperateUser {ot_enum.phrase}保险箱操作结果 {sta}")
            if sta:
                return self.answer(hint='保险箱操作成功')
            return self.answer(code=self.sta_code.FAIL)

    async def safe_box_save(self, u_info, req: Request, safe_box_info):
        """存入"""
        exp_time = safe_box_info.get("exp_time") or 0
        if exp_time and exp_time > tool_dt.cur_time():
            self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="保险箱已过期，请重新激活再存入")

        amount = req.json.get("amount")  # 数量
        (amount < 1) and self.answer(self.sta_code.ERR_ARG, hint="不能存入小于1的金额，请重新输入")
        uid = u_info.get("uid")

        # 1.该限制主要避免玩家游戏中要输时退出游戏来将灵石存入保险箱
        cs_info = await self.conf.rds.get_hash(CacheKey.IN_SERVICE, uid, jsparse=True)
        if cs_info:
            cs_enum = ServiceEnum.find_member_by_val(cs_info.get("cs_type"))
            (cs_enum.desc == GameType.LEISURE) and self.answer(self.sta_code.FORBID,
                                                               hint="当前在休闲场游戏中，不能使用保险箱")
        # 3.验证钱包余额
        (amount > u_info.get("gold", 0)) and self.answer(self.sta_code.GOLD_NOT_ENOUGH,
                                                         hint="对不起，您的灵石不足，请注意灵石余额！")
        # 2.验证使用次数
        used_record = await BaseUserRC.get_safe_box_count(uid)
        time_node = used_record.get("time_node")
        used_times = used_record.get("used_times")

        today_midnight = KitDt.timestamp_today()
        if time_node == today_midnight:
            (used_times >= safe_box_info.get("times_limit")) and self.answer(self.sta_code.ALREADY_DO,
                                                                             hint="今日存入次数已达上限")
            used_times += 1
        else:
            used_times = 1

        # 3.验证保险箱余量
        space = safe_box_info.get("space", 0)  # 容量
        cur_amount = safe_box_info.get("amount", 0)  # 当前已存入的总量
        box_amount = cur_amount + amount

        if space != -1 and box_amount > space:
            self.answer(self.sta_code.FAIL, hint="您的保险箱容量已达上限")

        box_data = {"amount": box_amount}
        user_data = {"gold": -amount}
        cache_data = {"used_times": used_times, "time_node": today_midnight}
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UserSafeBoxRC.update_safe_box(uid, box_data, safe_box_info)
                await BaseUserRC.update_user_asset(uid, user_data, ReasonCostGold.SAFE_BOX_SAVE)
        except Exception as e:
            self.error_log(f"safe_box_save 事务执行失败，原因：{e}")
            self.answer(self.sta_code.FAIL, hint="保险箱存入失败，请稍后重试")
        await BaseUserRC.cache_safe_box_count(uid, cache_data)

        return True

    async def safe_box_draw(self, u_info, req: Request, safe_box_info):
        """取出"""
        amount = req.json.get("amount")  # 数量
        (amount < 1) and self.answer(self.sta_code.ERR_ARG, hint="不能取出小于1的金额，请重新输入")

        cur_amount = safe_box_info.get("amount", 0)  # 当前已存入的总量
        (amount > cur_amount) and self.answer(self.sta_code.GOLD_NOT_ENOUGH, hint="对不起，您的保险箱余额不足！")

        uid = u_info.get("uid")
        box_data = {"amount": cur_amount - amount}
        user_data = {"gold": amount}
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UserSafeBoxRC.update_safe_box(uid, box_data, safe_box_info)
                await BaseUserRC.update_user_asset(uid, user_data, ReasonCostGold.SAFE_BOX_DRAW)
        except Exception as e:
            self.error_log(f"safe_box_draw 事务执行失败，原因：{e}")
            self.answer(self.sta_code.FAIL, hint="保险箱取出失败，请稍后重试")

        return True

    async def safe_box_set_complement(self, u_info, req: Request, safe_box_info):
        """设置自动补足"""
        exp_time = safe_box_info.get("exp_time") or 0
        if exp_time and exp_time > tool_dt.cur_time():
            self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="保险箱已过期，请重新激活再设置")

        complement_sta = self.check_int(req.json.get("complement_sta"), require=True, minval=0, maxval=2,
                                        p_name="complement_sta")
        (complement_sta is None) and self.answer(self.sta_code.ERR_ARG, hint="自动补足设置参数错误")

        amount = self.check_int(req.json.get("amount"), require=True, p_name="amount")
        if complement_sta == Switch.CLOSE:
            (amount > 0) and self.answer(self.sta_code.ERR_ARG, hint="请先勾选开启补足，再设置金额")
        elif complement_sta == Switch.OPEN:
            (amount < 1000000000) and self.answer(self.sta_code.ERR_ARG, hint="设置自动补足金额不能低于10亿")

        cur_complement_sta = safe_box_info.get("complement_sta")
        cur_complement_count = safe_box_info.get("complement_count")
        if cur_complement_sta == complement_sta and cur_complement_count == amount:
            self.answer(self.sta_code.ALREADY_DO, hint="无需重复设置")

        box_data = {"complement_sta": complement_sta, "complement_count": amount}
        sta = await UserSafeBoxRC.update_safe_box(u_info.get("uid"), box_data, safe_box_info)
        (not sta) and self.answer(self.sta_code.FAIL, hint="自动补足设置失败，请稍后重试")

        return True

    async def safe_box_use_complement(self, u_info, _, safe_box_info):
        """领取自动补足"""
        sta_code, hint = await UserSafeBoxRC.safe_box_use_complement(u_info, safe_box_info)
        if sta_code != self.sta_code.PASS:
            self.answer(sta_code, hint=hint)

        return True


class GetDetailShardInfo(GameAuthApi):
    """
    获取碎片详细信息
    暂时只适用于舍利、精魄等查询跳转信息
    """

    async def get(self, req: Request, **kwargs):
        goods_id = self.check_int(req.args.get("goods_id"), require=True, minval=1000, maxval=1999, p_name="goods_id")
        goods = [{
            "goods_id": goods_id,
            "goods_type": GoodsType.SKIN_SHARD.val
        }]
        await GoodsManagerRC.pack_goods_list(goods)
        (not goods) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="未找到物品配置")

        proto_data = PbGoods.pb_model(goods)
        self.info_log(f"GetDetailShardInfo 查询{goods_id}详细信息成功")
        return self.answer(data=proto_data)


class GetGoodsJumpChance(GameAuthApi):
    """获取跳转机会"""

    async def get(self, req: Request, **kwargs):
        jump_type = self.check_int(req.args.get("jump_type"), require=True, p_name="jump_type")
        tp_enum = JumpType.find_member_by_val(jump_type)
        (not isinstance(tp_enum, JumpType)) and self.answer(self.sta_code.ERR_ARG, hint='未知的前往类型')

        jump_target = req.args.get("jump_target")
        if jump_type == JumpType.GO_LIMITED:
            jump_target = self.check_int(jump_target, p_name="jump_target")
            tt_enum = JumpTarget.find_member_by_val(jump_target)
            (not isinstance(tt_enum, JumpTarget)) and self.answer(self.sta_code.ERR_ARG, hint='未知的前往目标')

        season_id = req.args.get("season_id", 0)
        if jump_type == JumpType.GO_SEASON:
            season_id = self.check_int(season_id, p_name="season_id")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        if jump_type == JumpType.GO_FOREVER:
            jump_sta = 1
        else:
            jump_sta = await self.verify_jump_status(uid, jump_type, jump_target=jump_target, season_id=season_id)

        one_of_model = get_one_of_model()
        one_of_model.jump_sta = jump_sta
        self.info_log(uid, f"GetGoodsJumpChance 获取{tp_enum.phrase}类型跳转机会：{jump_sta}")
        self.answer(self.sta_code.PASS, data=one_of_model)

    @classmethod
    async def verify_jump_status(cls, uid, jump_type: JumpType, jump_target=0, season_id=0):
        """验证跳转目标是否有效"""
        jump_sta = 1
        # 活动限时
        if jump_type == JumpType.GO_LIMITED:
            if jump_target == JumpTarget.GO_FIRST_CHARGE:
                charge_record = await UserActivityRC.get_user_charge_records_by_id(uid, ActivityItem.FIRST_CHARGE)
                if charge_record:
                    awards_achieved = charge_record.get("awards_achieved")
                    awards_achieved = json_parse(awards_achieved) if awards_achieved else []
                    if len(awards_achieved) >= 3:
                        jump_sta = 0

            elif jump_target == JumpTarget.GO_SIGN_IN_SEVEN:
                task_info = await UserTaskRC.cache_task_record_by_id(uid, TaskId.ROOKIE_SEVEN_SIGN_IN.val)
                if task_info.get('task_sta') == CompleteSta.COMPLETED and task_info.get('cur_value', 0) >= 7:
                    jump_sta = 0
        # 赛季限时
        elif jump_type == JumpType.GO_SEASON:
            season_conf = await ConfSeasonRC.db_model.get_by_pk(season_id, field=['status'])
            if season_conf and season_conf.get("status", 0) == SeasonStatus.OUT_OF_TIME:
                jump_sta = 0

        return jump_sta
