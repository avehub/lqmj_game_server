"""
法相系统
"""
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from tortoise.transactions import in_transaction
from common.public.conf import R_UID_THRESHOLD
from common.utils.utils import UtilsTool
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.up_assets import StatFlow, UpAssets
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_prop import ItemsPropRC
from lucky_game.model_rc.base_robot import ConfRobotRC
from lucky_game.model_rc.base_skin import ItemsSkinRC, UserSkinRC
from lucky_game.model_rc.base_user import BaseUserRC
from common.public.enum_const import ServiceEnum, MonsterCardType, Switch, DbKey
from lucky_game.const import GotType, GoodsItem, GamePropType, GoodsType, ReasonCostGold
from lucky_game.model_rc.goods_manager import GoodsManagerRC


class SkinDharmaForm(GameAuthApi):
    """法相一级：法相之形"""

    async def get(self, req: Request, **kwargs):
        cs_type = self.check_int(req.args.get("cs_type", 5), require=True, p_name="cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        (not cs_enum) and self.answer(self.sta_code.ERR_ARG, hint="游戏暂未开放法相系统")

        # 0.检查限时皮肤剩余时效
        user = kwargs.get("u_info")
        uid = user.get("uid")

        # await self.push_task2worker(CmdWorkers.CHECK_LIMITED_GOODS, msg={'cs_type': cs_type}, uid=uid)
        await UserSkinRC.deal_expire_skin(uid, cs_type)

        user_skin = await UserSkinRC.get_user_skin_by_game(uid, cs_type)
        (not user_skin) and self.answer(self.sta_code.ERR_CONF, hint="没有用户法相数据，请稍后再试")

        # 1.获取法相配置数据
        all_skins = await ItemsSkinRC.get_skin_items()
        (not all_skins) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有法相配置，请稍后再试")

        # 2.检查法相持有情况
        detail_skin = await UserSkinRC.check_skin_detail_data(all_skins, user_skin)
        (not detail_skin) and self.answer(self.sta_code.ERR_CONF, hint="没有法相数据，请稍后再试")

        # 3.舍利总数 / 新法相 / 可升级 查询
        upgrade_items = await UserBagRC.get_skin_upgrade_items(uid)
        new_skin = await BaseUserRC.deal_user_update_goods(uid, key_name=UserSkinRC.KEY_NEWLY)
        upgrade_skin = await UserSkinRC.deal_upgradable_skin(uid)

        data = {
            "all_skin_general": detail_skin,
            "upgrade_skin": upgrade_skin,
            "new_skin": [] if not new_skin else json_parse(new_skin),
            "cur_relics": upgrade_items.get("cur_relics") or 0
        }
        self.log_info(uid, f"SkinDharmaForm 法相一级：法相之形 {cs_type}>>>")
        return self.answer(data=data)


class SkinDharmaAppear(GameAuthApi):
    """法相二级：法相显现"""

    async def get(self, req: Request, **kwargs):
        cs_type = self.check_int(req.args.get("cs_type", 5), require=True, p_name="cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        (not cs_enum) and self.answer(self.sta_code.ERR_ARG, hint="游戏暂未开放法相系统")

        match_card = self.check_int(req.args.get("match_card"), require=True, p_name="match_card")
        mc_enum = MonsterCardType.find_member_by_val(match_card)
        (not isinstance(mc_enum, MonsterCardType)) and self.answer(self.sta_code.ERR_ARG, hint="该角色暂未发行任何法相")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        user_skin = await UserSkinRC.get_user_skin_by_game(uid, cs_type)
        (not user_skin) and self.answer(self.sta_code.ERR_CONF, hint="没有用户法相数据，请稍后再试")

        # 1.获取对应法相配置
        filter_skin = await ItemsSkinRC.filter_skin_items(cs_type, match_card=match_card)
        (not filter_skin) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有法相配置，请稍后再试")

        # 2.检查法相持有情况
        detail_skin = await UserSkinRC.check_skin_detail_data(filter_skin, user_skin, is_more=True)
        (not detail_skin) and self.answer(self.sta_code.ERR_CONF, hint="没有法相数据，请稍后再试")

        # 3.获取升级素材情况
        for i in detail_skin:
            shard_id = i.get("shard_id")
            if shard_id and i.get("got_type") != GotType.NOT_GOT.val:
                upgrade_items = await UserBagRC.get_skin_upgrade_items(uid, shard_id=shard_id)
                cur_shards = upgrade_items.get("cur_shards") or 0
                next_need_shards = i.get("next_need_shards") or 0
                i['cur_shards'] = cur_shards
                i['next_need_relics'] = next_need_shards - cur_shards

        # 3.新法相 / 可升级 查询
        new_skin = await BaseUserRC.deal_user_update_goods(uid, key_name=UserSkinRC.KEY_NEWLY)
        upgrade_skin = await UserSkinRC.deal_upgradable_skin(uid)

        data = {
            "all_skin": detail_skin,
            "upgrade_skin": upgrade_skin,
            "new_skin": [] if not new_skin else json_parse(new_skin)
        }
        self.log_info(uid, f"SkinDharmaAppear 法相二级：法相显现 {mc_enum.phrase}>>>")
        return self.answer(data=data)


class GetSkinAllStarItems(GameAuthApi):
    """获取所有星级信息"""

    async def get(self, req: Request, **kwargs):
        cs_type = self.check_int(req.args.get("cs_type", 5), require=True, p_name="cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        (not cs_enum) and self.answer(self.sta_code.ERR_ARG, hint="游戏暂未开放法相系统")

        goods_id = self.check_int(req.args.get("goods_id"), require=True, minval=5000, maxval=5999, p_name="goods_id")

        conf_skin = await ItemsSkinRC.get_skin_items_by_id(goods_id)
        (not conf_skin) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="未找到该法相的数据")
        public_id = conf_skin.get("public_id")

        filter_skin = await ItemsSkinRC.filter_skin_items(cs_type, public_id=public_id)
        (not filter_skin) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有法相配置，请稍后再试")

        data = {"all_skin": filter_skin}
        self.log_info(f"GetSkinAllStarItems {public_id}所有星级信息")
        return self.answer(data=data)


class UseSkinItem(GameAuthApi):
    """
    装备法相
    注意：上下篇通用皮肤同时装备，单篇的装备对应篇章
    """

    async def post(self, req: Request, **kwargs):
        # todo:
        # cs_type = self.check_int(req.json.get("cs_type", 0), require=True, p_name="cs_type")
        # cs_enum = ServiceEnum.find_member_by_val(cs_type)
        # (not cs_enum) and self.answer(self.sta_code.ERR_ARG, hint="游戏暂未开放法相系统")

        goods_id = self.check_int(req.json.get("goods_id"), require=True, minval=5000, maxval=5999, p_name="goods_id")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        user_skin = await UserSkinRC.get_user_skin(uid)
        cur_u_skins = [u for u in user_skin if u.get("skin_item_id") == goods_id]
        (not cur_u_skins) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="未获得该法相")

        conf_skin = await ItemsSkinRC.get_skin_items_by_id(goods_id)
        (not conf_skin) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="未找到该法相的数据")
        (conf_skin.get("star_level") == 0) and self.answer(self.sta_code.CONDITION_NOT_MET, hint="法相暂未获得")

        for s in cur_u_skins:
            # todo:
            # if cs_type and cs_type != s.get("cs_type"):
            #     continue
            got_type = s.get("got_type")
            (got_type != GotType.UNUSED) and self.answer(self.sta_code.ALREADY_DO, hint="无需重复装备")

            exp_time = s.get("exp_time")
            if exp_time and exp_time < tool_dt.cur_time():
                self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="法相已过期，不允许装备")

            sta = await UserSkinRC.set_user_skin(uid, goods_id, conf_skin.get("match_card")) # 对应卡牌（例如孙悟空里只能使用一款法相）
            (not sta) and self.answer(self.sta_code.FAIL, hint="装备法相失败，请稍后再试")

        self.log_info(uid, f"UseSkinItem 法相装备成功 {goods_id}")
        return self.answer(hint="装备成功")


class UpgradeSkinItem(GameAuthApi):
    """
    法相升星
    注意：星级是通用的，例如上篇升级，下篇共用星级
    """

    async def post(self, req: Request, **kwargs):
        cs_type = self.check_int(req.json.get("cs_type", 0), require=True, p_name="cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        (not cs_enum) and self.answer(self.sta_code.ERR_ARG, hint="游戏暂未开放法相系统")

        goods_id = self.check_int(req.json.get("goods_id"), require=True, minval=5000, maxval=5999, p_name="goods_id")

        use_relic = self.check_int(req.json.get("use_relic"), require=True, minval=0, maxval=2, p_name="use_relic")
        (use_relic is None) and self.answer(self.sta_code.ERR_ARG, hint="万能舍利补足设置错误")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 1.验证用户法相数据
        user_data = await UserSkinRC.cache_user_skin(uid) or []
        cur_skins = [u for u in user_data if u.get("skin_item_id") == goods_id and u.get("exp_time") == 0]
        (not cur_skins) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="未获得该永久法相")

        # 2.获取法相配置和同款配置
        skins_conf = await ItemsSkinRC.get_skin_items_by_id(goods_id)
        (not skins_conf) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没有找到当前法相数据")

        filter_skins = await ItemsSkinRC.filter_skin_items(cs_type, public_id=skins_conf.get("public_id"))
        (not filter_skins) and self.answer(self.sta_code.CONDITION_NOT_MET, hint="没有找到该款法相配置")

        # 3.本款法相各星级数据 / 加载下级数据
        detail_skins = ItemsSkinRC.load_next_skin_items(filter_skins)
        (not detail_skins) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没有找到该款法相")

        detail_conf = next((s for s in detail_skins if s.get("goods_id") == goods_id), None)
        (not detail_conf) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没有该法相配置")

        star_level = detail_conf.get("star_level")
        if star_level == detail_conf.get("top_star", 1) or star_level == 0:
            self.answer(self.sta_code.CONDITION_NOT_MET, hint="法相已是最高星级或不支持升星")

        # 4.获取升级素材情况
        shard_id = skins_conf.get("shard_id")
        upgrade_items = await UserBagRC.get_skin_upgrade_items(uid, shard_id=shard_id)
        cur_shards = upgrade_items.get("cur_shards") or 0  # 精魄数
        cur_relics = upgrade_items.get("cur_relics") or 0  # 万能精魄数
        next_need_shards = detail_conf.get("next_need_shards")  # 下一级需要精魄数
        next_goods_id = detail_conf.get("next_goods_id")  # 下一级ID

        # 4.计算消耗精魄：使用万能精魄补全 / 不使用
        cost_items = []
        if use_relic == Switch.OPEN:
            if cur_shards + cur_relics < next_need_shards:
                self.answer(self.sta_code.CONDITION_NOT_MET, hint="升星所需法相精魄或舍利不足")

            # 计算需要使用的精魄和万能精魄
            need_shards = min(cur_shards, next_need_shards)
            need_relics = max(0, next_need_shards - need_shards)

            if need_shards > 0:
                cost_items.append({"goods_id": shard_id, "goods_count": -need_shards})
            if need_relics > 0:
                cost_items.append({"goods_id": GoodsItem.RELICS.val, "goods_count": -need_relics})
        else:
            if cur_shards < next_need_shards:
                self.answer(self.sta_code.CONDITION_NOT_MET, hint="升星所需法相精魄不足")
            if next_need_shards > 0:
                cost_items.append({"goods_id": shard_id, "goods_count": -next_need_shards})

        # 5.扣除升星道具
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                update_skin = {"goods_id": goods_id, "next_goods_id": next_goods_id}
                await UserSkinRC.update_user_skin(uid, update_skin, is_upgrade=True, user_skin=user_data)  # 更新到升级后的ID
                await UserBagRC.update_user_bag(uid, cost_items)  # 更新剩余升级材料
                await UserSkinRC.deal_upgradable_skin(uid, cs_type, id_list=[goods_id], is_del=True)  # 去除可升级名单
        except Exception as e:
            self.log_err(f"UpgradeSkinItem 事务执行失败，原因：{e}")
            self.answer(self.sta_code.FAIL, hint="升星错误，请稍后再试")

        # 6.返回最新配置，使用状态不变
        new_skin = next((s for s in detail_skins if s.get("goods_id") == next_goods_id), {})
        for s in cur_skins:
            if s.get("cs_type") == cs_type:
                new_skin['got_type'] = s.get("got_type")

        self.log_info(uid, f"UpgradeSkinItem 法相升星成功，使用万能：{use_relic}")
        return self.answer(data=new_skin, hint="升星成功")


class GetGameSkinUsedItems(GameAuthApi):
    """
    法相使用项查询， 只返回skin_item_id（此处暂未使用，在游戏WS查询）
    隐性需求：给机器人法相
    """

    async def get(self, req: Request, **kwargs):
        cs_type = self.check_int(req.args.get("cs_type", 5), require=True, p_name="cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        (not cs_enum) and self.answer(self.sta_code.ERR_ARG, hint="游戏暂未开放法相系统")

        query_uid_list = req.args.get("query_uid_list")
        query_uid_list = json_parse(query_uid_list) if query_uid_list else []
        if not query_uid_list:
            user = kwargs.get("u_info")
            query_uid_list.append(user.get("uid", 0))

        for uid in query_uid_list:
            if not isinstance(uid, int):
                self.log_info(f"Invalid UID detected: {uid}, UIDs: {query_uid_list}")
                return self.answer(self.sta_code.ERR_ARG, hint=f"非法的用户ID: {uid}")

        result_list = []
        for uid in query_uid_list:
            if uid > R_UID_THRESHOLD:
                used_list = await UserSkinRC.get_user_used_skin(uid, cs_type)
                if not used_list:
                    continue

                result_list.append({"uid": uid, "used_goods": used_list})
            else:
                leisure_id = self.check_int(req.args.get("leisure_id"), require=True, default=1, p_name="leisure_id")

                robot_conf = await ConfRobotRC.get_robot_conf_by_id(leisure_id)
                if robot_conf:
                    skin_count = robot_conf.get("skin_count")
                    count = int(UtilsTool.select_element_by_prob(skin_count, size=100))
                    if count > 0:
                        used_list = []
                        config = robot_conf.get("card_skin")
                        if config:
                            used_skins = set()  # 用于记录已抽取的法相 ID
                            while len(used_list) < count:
                                res = UtilsTool.select_element_by_prob(config, size=410)
                                if res and res not in used_skins:
                                    used_skins.add(res)
                                    used_list.append(int(res))
                        result_list.append({"uid": uid, "used_goods": used_list})

        self.log_info(query_uid_list, "GetGameSkinUsedItems 正在使用的法相查询成功")
        return self.answer(data=result_list)


class UseLimitedTimeSkin(GameAuthApi):
    """使用限时皮肤"""

    async def post(self, req: Request, **kwargs):
        goods_id = self.check_int(req.json.get("goods_id"), require=True, minval=1000, maxval=1999, p_name="goods_id")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 1.通过goods_id查询背包
        bag_item = await UserBagRC.get_user_bag_by_id(uid, goods_id=goods_id)
        (not bag_item) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没有找到限时法相")

        # 2.验证宝盒
        goods_count = bag_item.get("goods_count")
        (not goods_count) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="限时法相不足哦，请先获取再使用吧")

        prop_item = await ItemsPropRC.cache_conf_by_pk(goods_id)
        (not prop_item) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="限时法相配置不存在")

        game_prop_type = prop_item.get("game_prop_type")
        (game_prop_type != GamePropType.LIMITED_TIME_SKIN) and self.answer(self.sta_code.FAIL, hint="该物品无法使用")

        # 3.获取奖励配置 和 构建限时法相数据
        target_data = prop_item.get("target_data")
        skin_item_id = target_data.get("goods_id")
        extra_info = prop_item.get("extra_info")
        days = extra_info.get("days", 1)
        time_limit = int(days * 86400)

        # 4.获取法相配置，检查是否拥有
        skins_conf = await ItemsSkinRC.get_skin_items_by_id(skin_item_id)
        (not skins_conf) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没有找到当前法相数据")

        user_datas = await UserSkinRC.cache_user_skin(uid)
        cur_skin = next((i for i in user_datas if i.get('skin_public_id') == skins_conf.get('public_id')), None)

        convert_goods = {"goods_id": skin_item_id, "goods_type": GoodsType.CARD_SKIN.val, "time_limit": time_limit}
        to_updated = False
        if cur_skin:
            exp_time = cur_skin.get("exp_time", 0)
            if exp_time == 0:
                s_e_info = skins_conf.get("extra_info", {})
                convert_gold = s_e_info.get("convert_gold", 0)
                if convert_gold > 0:
                    convert_goods = {
                        'goods_id': GoodsItem.GOLD.val,
                        'goods_type': GoodsType.V_ASSET.val,
                        'goods_count': convert_gold * days
                    }
                    await GoodsManagerRC.pack_goods_list([convert_goods])
                    StatFlow.stat_common_flow(awards=[convert_goods], g_reason=ReasonCostGold.CONVERT_AWARDS)
            else:
                convert_goods.update(skins_conf)
                to_updated = True
        else:
            convert_goods.update(skins_conf)

        # 5.消耗道具统计
        cost_item = {
            "goods_id": goods_id,
            "goods_count": -1
        }
        # 7.发奖 / 更新背包
        (not convert_goods) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="使用限时法相失败，请联系客服")
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                if to_updated:
                    await UserSkinRC.update_user_skin(uid, [convert_goods], user_skin=user_datas)
                else:
                    up_goods = await UpAssets.update_assets(uid, [convert_goods], [])
                await UserBagRC.update_user_bag(uid, [cost_item])
        except Exception as e:
            self.log_err(f"UseLimitedTimeSkin 事务执行失败，原因：{e}")
            self.answer(self.sta_code.FAIL, hint="使用限时法相失败，请联系客服")

        pro_data = [convert_goods] if to_updated else up_goods
        self.log_info(uid, f"UseLimitedTimeSkin 使用限时法相成功，获得{days}天使用时间", skin_item_id)
        return self.answer(data=pro_data)

