"""
快递员系统
虚拟资产处理
"""
import asyncio
from collections import defaultdict
from common.public.common_class import CommonApi
from common.utils.utils import UtilsTool
from lucky_game.config import conf_srv, ConfSrv
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_cosmetic import UserCosmeticRC
from lucky_game.model_rc.base_skin import UserSkinRC
from lucky_game.model_rc.goods_manager import GoodsManagerRC
from lucky_game.model_rc.base_award import ConfAwardRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.active_behaviors import UserBehaviorsRC
from c_services.const.cs_enum_const import CmdWorkers, RedDotType
from lucky_game.const import GoodsItem, StoreType, ReasonCostDiamond, ActivityType, ReasonCostGold, PutType, \
    GoodsType


class UpAssets(CommonApi):
    """
    更新用户虚拟资产
    """
    conf: ConfSrv = conf_srv

    @classmethod
    async def stat_express(cls, uid: int, express: dict, trade_item: int):
        """
        快递打包 1：统计订单的货物、一般赠品、首单赠品，并打包
        """
        conf_items = express.get("conf_items") or []
        first_gifts = express.get("first_gifts") or []
        common_gifts = express.get("common_gifts") or []

        conf_gifts = []
        # 1.立得商品处理
        if not conf_items:
            return conf_items, ""
        await GoodsManagerRC.pack_goods_list(conf_items)

        # 2.赠品处理
        if first_gifts:
            is_first = await UserBehaviorsRC.query_is_first_buy(uid, trade_item)
            if is_first:  # 是否首单（同个人买过同个商品则不算首单），有首单则不计common_gifts
                conf_gifts.extend(first_gifts)
            else:
                conf_gifts.extend(common_gifts)

        elif common_gifts:
            conf_gifts.extend(first_gifts)

        if conf_gifts:
            await GoodsManagerRC.pack_goods_list(conf_gifts)

        # 3.资产添加流水原因
        StatFlow.stat_transaction_flow(express, trade_item, goods=conf_items, gifts=conf_gifts)

        cls.info_log(uid, "stat_express 得物：", conf_items, "赠品：", conf_gifts)
        return conf_items, conf_gifts

    @classmethod
    async def stat_awards(cls, award_id: int):
        """
        快递打包 2：统计奖励的奖品，并打包
        """
        award_item = await ConfAwardRC.get_award_item_by_id(award_id)
        conf_items = award_item.get("conf_items") or []
        # 奖品处理
        if conf_items:
            await GoodsManagerRC.pack_goods_list(conf_items)

        return conf_items

    @classmethod
    def stat_currency(cls, goods_list: list):
        """
        快递打包 3：多个快递单统计总货币总和，避免多次访问数据库
        """
        if len(goods_list) <= 1:
            return goods_list

        diamond_dict = None
        gold_dict = None
        processed_goods = []
        for item in goods_list:
            goods_item = item.get("goods_id")
            if goods_item == GoodsItem.DIAMOND:
                if diamond_dict is None:
                    diamond_dict = item.copy()
                else:
                    diamond_dict["goods_count"] += item["goods_count"]
            elif goods_item == GoodsItem.GOLD:
                if gold_dict is None:
                    gold_dict = item.copy()
                else:
                    gold_dict["goods_count"] += item["goods_count"]
            else:
                processed_goods.append(item)

        if diamond_dict:
            processed_goods.append(diamond_dict)
        if gold_dict:
            processed_goods.append(gold_dict)
        return processed_goods

    @classmethod
    def stat_goods(cls, goods_list: list):
        """
        快递打包 4：返回之前，把相同的物品 goods_count 和 time_limit 累加
        """
        if len(goods_list) <= 1:
            return goods_list

        # 使用 defaultdict 来存储每个 goods_id 的合计数量
        combined_goods = defaultdict(lambda: {"goods_id": None, "goods_count": 0, "time_limit": 0})

        for item in goods_list:
            goods_id = item.get("goods_id")
            if goods_id is not None:
                combined_goods[goods_id]["goods_id"] = goods_id
                combined_goods[goods_id]["goods_count"] += item.get("goods_count", 0)
                combined_goods[goods_id]["time_limit"] += item.get("time_limit", 0)
                # 保留其他固定字段
                for key in item.keys():
                    if key not in ["goods_id", "goods_count", "time_limit"]:
                        if key not in combined_goods[goods_id]:
                            combined_goods[goods_id][key] = item[key]

        # 将结果转换为列表
        processed_goods = [item for item in combined_goods.values()]

        return processed_goods

    @classmethod
    async def update_assets(cls, uid, goods: list, gifts: list, is_pack=False, is_notice=True):
        """
        物流发货 1：验证订单和商品之后；
        更新任务收集为多个协程对象 update_task 并发执行；
        """
        if not goods:
            cls.info_log(uid, "商品缺货，请联系客服")
            return False
        # 1.统计累加物品
        goods_copy = goods.copy()
        if gifts:
            goods_copy.extend(gifts)

        all_goods = cls.stat_goods(goods_copy)

        # 2.打包物品全部信息
        if is_pack:
            await GoodsManagerRC.pack_goods_list(all_goods, is_all=True)

        # 3.收集写入任务
        map_func = {
            PutType.U_WALLET.val: cls.add_to_wallet,
            PutType.U_BAG.val: cls.add_to_bag,
            PutType.U_COSMETIC.val: cls.add_to_cosmetic,
            PutType.U_SKIN.val: cls.add_to_skin
        }

        # 4.按put_type分组处理
        group_express = {}
        for ag in all_goods:
            put_type = ag.get("put_type")
            pt_enum = PutType.find_member_by_val(put_type)
            if not isinstance(pt_enum, PutType):
                cls.info_log('PutType 不存在', all_goods)
                continue
            group_express.setdefault(put_type, []).append(ag)

        update_task = []
        for put_type, express in group_express.items():
            add_func = map_func.get(put_type)
            if add_func and callable(add_func):
                update_task.append(add_func(uid, express, is_notice))

        # 5.批量执行
        if update_task:
            await asyncio.gather(*update_task)

        return all_goods

    @classmethod
    async def add_to_wallet(cls, uid, express: list, _):
        """
        物流发货 2：资产，发往钱包
        资产可加reason记录流水
        """
        for ac in express:
            reason = ac.get("reason")
            goods_item = ac.get("goods_id")
            goods_item_enum = GoodsItem.find_member_by_val(goods_item)
            if not goods_item_enum:
                return False
            add_key = goods_item_enum.desc
            new_info = {
                add_key: ac.get("goods_count")
            }
            if reason:
                p_info = await BaseUserRC.update_user_asset(uid, new_info, reason)
            else:
                p_info = await BaseUserRC.update_user_asset(uid, new_info)
                cls.info_log('add_to_wallet 捕捉没有加入流水的出处以供解决', uid, new_info)

            if p_info:
                cls.info_log(uid, 'add_to_wallet 添加钱包成功')
        return True

    @classmethod
    async def add_to_bag(cls, uid, express: list, is_notice=True):
        """物流发货 3：道具，发往背包"""
        b_info = await UserBagRC.update_user_bag(uid, express, is_notice=is_notice)
        if b_info:
            cls.info_log(uid, 'add_to_bag 添加背包成功')
            if not is_notice:
                return True

            rd_type_list = [RedDotType.RD_BAG]
            goods_types = set(item.get('goods_type') for item in express)
            # 若只有隐藏物品的话，则不通知
            if all(gt in UserBagRC.HIDDEN_TYPES for gt in goods_types):
                is_notice = False

            if is_notice:
                # 若有精魄的话，则加入可升级通知
                if GoodsType.SKIN_SHARD in goods_types:
                    rd_type_list.append(RedDotType.RD_SKIN)
                await cls.send_express_notice(uid, rd_type_list)
            return True
        return False

    @classmethod
    async def add_to_cosmetic(cls, uid, express: list, is_notice=True):
        """物流发货 4：装扮，发往装扮"""
        p_info = await UserCosmeticRC.update_user_cosmetic(uid, express, is_notice=is_notice)
        if p_info:
            cls.info_log(uid, 'add_to_cosmetic 添加装扮成功')
            if is_notice:
                await cls.send_express_notice(uid, [RedDotType.RD_PERSONAL])
            return True
        return False

    @classmethod
    async def add_to_skin(cls, uid, express: list, is_notice=True):
        """物流发货 5：皮肤，发往法相系统，如果已获得则兑换成精魄"""
        new_skin = await UserSkinRC.update_user_skin(uid, express, is_notice=is_notice)
        if new_skin:
            cls.info_log(uid, 'add_to_skin 添加皮肤成功')
            if is_notice:
                await cls.send_express_notice(uid, [RedDotType.RD_SKIN])
            return True
        return False

    @classmethod
    async def send_express_notice(cls, uid, rd_type_list: list):
        """快递红点通知"""
        await cls.push_task2worker(CmdWorkers.GET_RED_DOT_LIST, msg={"rd_type_list": rd_type_list}, uid=uid)


class StatFlow():
    """
    统计资产流水
    """

    @classmethod
    def stat_transaction_flow(cls, express: dict, trade_item: int, goods=None, gifts=None):
        """
        添加流水 1：交易支付用，统计资产类物品流水原因，得物和赠品分开统计
        """
        if not express:
            return
        item_num, _ = UtilsTool.explode_command(trade_item, digit=3)
        diamond_reason = gold_reason = gift_reason = None
        if item_num == 3:
            act_type = express.get("act_type")
            if act_type == ActivityType.FIRST_CHARGE:
                gold_reason = ReasonCostGold.ACT_FIRST_CHARGE
                diamond_reason = ReasonCostDiamond.ACT_FIRST_CHARGE

            elif act_type == ActivityType.WEEK_CARD:
                gold_reason = ReasonCostGold.ACT_WEEK_CARD

            elif act_type == ActivityType.PACKAGE:
                gold_reason = ReasonCostGold.ACT_FIRST_CHARGE

            elif act_type == ActivityType.LIFETIME_CARD:
                gold_reason = ReasonCostGold.ACT_LIFETIME_CARD
                diamond_reason = ReasonCostDiamond.ACT_LIFETIME_CARD
        else:
            store_type = express.get("store_type")
            if store_type == StoreType.DIAMOND:
                gift_reason = ReasonCostGold.STORE_SHOPPING_GIFT
                diamond_reason = ReasonCostDiamond.STORE_BUY_DIAMOND

        cls.set_reason(goods, GoodsItem.DIAMOND, diamond_reason)
        cls.set_reason(goods, GoodsItem.GOLD, gold_reason)
        cls.set_reason(gifts, GoodsItem.DIAMOND, gift_reason)
        cls.set_reason(gifts, GoodsItem.GOLD, gift_reason)

    @classmethod
    def stat_activity_flow(cls, act_type: ActivityType, awards=None):
        """
        添加流水 2：活动领取用，统计资产类物品流水原因
        """
        if not awards:
            return
        diamond_reason = gold_reason = None

        if act_type == ActivityType.WEEK_CARD:
            gold_reason = ReasonCostGold.WEEK_CARD_AWARDS
        elif act_type == ActivityType.LIFETIME_CARD:
            gold_reason = ReasonCostGold.LIFETIME_CARD_AWARDS
            diamond_reason = ReasonCostDiamond.LIFETIME_CARD_AWARDS
        elif act_type == ActivityType.FIRST_CHARGE:
            gold_reason = ReasonCostGold.ACT_FIRST_CHARGE
            diamond_reason = ReasonCostDiamond.ACT_FIRST_CHARGE

        cls.set_reason(awards, GoodsItem.DIAMOND, diamond_reason)
        cls.set_reason(awards, GoodsItem.GOLD, gold_reason)

    @classmethod
    def stat_common_flow(cls, awards=None, d_reason=None, g_reason=None):
        """
        添加流水 3：通用，外部能确定原因，统计资产类物品流水原因
        """
        if not awards:
            return
        cls.set_reason(awards, GoodsItem.DIAMOND, d_reason)
        cls.set_reason(awards, GoodsItem.GOLD, g_reason)

    @classmethod
    def set_reason(cls, goods_list: list, goods_item, reason):
        """设置流水"""
        if goods_list and reason:
            for item in goods_list:
                if item.get("goods_id") == goods_item:
                    item["reason"] = reason
