"""
商店相关接口
"""
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from tortoise.transactions import in_transaction
from common.proto.py_pb2.common import switch_enum, get_one_of_model, switch_type_enum
from common.public.enum_const import DbKey, ServiceEnum
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.up_assets import UpAssets
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.base_store import ConfStoreRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import PayType, GoodsItem, ReasonCostDiamond, ReasonCostGold, GoodsType, StoreType, \
    BossType, HeldSta, PlatForm


class StoreHandler(GameAuthApi):
    """ 加载各类型商店 """

    async def get(self, req: Request, **kwargs):
        boss_type = self.check_int(req.args.get("boss_type") or 0, require=True, p_name="boss_type")
        bs_enum = BossType.find_member_by_val(boss_type)
        (not isinstance(bs_enum, BossType)) and self.answer(self.sta_code.ERR_ARG, hint='该商店类型不存在')

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        match boss_type:
            # case BossType.MONOPOLY_STORE:
            #     cs_type = self.check_int(req.args.get("cs_type", 5), p_name="cs_type")
            #     cs_enum = ServiceEnum.find_member_by_val(cs_type)
            #     (not cs_enum) and self.answer(self.sta_code.ERR_ARG, hint="游戏暂未开放法相系统")
            #
            #     items_lists = await ConfMonopolyStoreRC.get_monopoly_store_items(uid)
            #     (not items_lists) and self.answer(self.sta_code.NO_CONFIGURATION, hint='大富翁商店加载失败，请稍后再试')
            case _:
                platform = req.args.get('platform') or ''
                os = req.args.get('c_os') or ''

                items_lists = await ConfStoreRC.get_store_items(uid, platform=platform, os=os)
                (not items_lists) and self.answer(self.sta_code.NO_CONFIGURATION,
                                                  hint='游戏商店加载失败，请稍后再试')

        self.log_info(uid, f"StoreHandler {bs_enum.phrase}加载成功")
        return self.answer(data=items_lists)


class PayByRedemption(GameAuthApi):
    """ 商店兑换购物 """

    async def post(self, req: Request, **kwargs):
        is_notice = self.check_int(req.json.get("is_notice", 1), default=1, p_name='is_notice')
        trade_item = self.check_int(req.json.get("trade_item"), require=True, minval=2000, maxval=2999,
                                    p_name="trade_item")
        trade_item_count = self.check_int(req.json.get("trade_item_count", 1), default=1, minval=1, maxval=999,
                                          p_name="trade_item_count")

        boss_type = self.check_int(req.json.get("boss_type") or 0, require=True, p_name="boss_type")
        bs_enum = BossType.find_member_by_val(boss_type)
        (not isinstance(bs_enum, BossType)) and self.answer(self.sta_code.ERR_ARG, hint='该商店类型不存在')

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 1.查询商品
        match boss_type:
            case BossType.MONOPOLY_STORE:
                express = await ConfMonopolyStoreRC.get_monopoly_store_item_by_id(store_id=trade_item)
            case _:
                platform = req.args.get('c_platform') or ''
                os = req.args.get('c_os') or ''
                express = await ConfStoreRC.get_store_item_by_id(store_id=trade_item, platform=platform, os=os)

        # 2.验货 / 检查商品有效性
        (not express) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="该商品暂时缺货")
        conf_items = express.get("conf_items")
        (not conf_items) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint='商品缺货，请联系客服')
        check_sta, check_desc, buy_record = await self.__check_item_validity(uid, trade_item, trade_item_count, express)
        (not check_sta) and self.answer(code=self.sta_code.NOT_IN_VALID_STATE, hint=f"{check_desc}")

        pay_type = express.get("pay_type")
        (pay_type == PayType.BY_RMB) and self.answer(code=self.sta_code.ERR_ARG, hint='该物品只支持充值获取')
        pt_enum = PayType.find_member_by_val(pay_type)
        (not isinstance(pt_enum, PayType)) and self.answer(self.sta_code.ERR_ARG, hint='没有此兑换方式')

        # 4.按兑换方式处理
        map_func = {
            PayType.BY_FREE.val: self.pay_by_free,
            PayType.BY_DIAMOND.val: self.pay_by_diamond,
            PayType.BY_GOLD.val: self.pay_by_gold,
            PayType.BY_FIVE_AGGREGATES.val: self.pay_by_five_aggregates
        }
        pay_func = map_func.get(pay_type)
        if pay_func and callable(pay_func):
            all_items, show_items = await pay_func(u_info, express.get("store_type"), int(express.get("price", 0)),
                                                   trade_item_count, conf_items)
            self.log_info(uid, f'PayByRedemption {pt_enum.phrase}兑换结果', True if all_items and show_items else False)
            if all_items and show_items:
                try:
                    async with in_transaction(connection_name=DbKey.DEFAULT):
                        await GoodsManagerRC.pack_goods_list(all_items, is_all=True)
                        await UpAssets.update_assets(uid, all_items, [], is_notice=is_notice)
                        if buy_record:
                            await BaseUserRC.cache_count_buy_limit(uid, trade_item, buy_record)
                except Exception as e:
                    self.log_err(f'{pt_enum.phrase}事务执行失败，原因：{e}')
                    self.answer(self.sta_code.FAIL, hint=f'{pt_enum.phrase}兑换错误，请稍后再试')

                return self.answer(data=show_items)
            return self.answer(code=self.sta_code.FAIL)

    async def __check_item_validity(self, uid, trade_item, trade_count: int, express: dict):
        """检查商品有效性，包括限购次数以及销售时间范围"""
        # 检查销售时间
        cur_time = tool_dt.cur_time()
        start_sale_time = express.get("start_sale_time", 0)
        end_sale_time = express.get("end_sale_time", 0)

        if start_sale_time > 0 and cur_time < start_sale_time:
            return False, '商品尚未开始销售', {}
        if end_sale_time > 0 and cur_time > end_sale_time:
            return False, '商品已经结束销售', {}

        # 检查限购次数
        buy_record = {}
        buy_limit = json_parse(express.get("buy_limit")) if express.get("buy_limit") else None
        if buy_limit:
            buy_record = await BaseUserRC.get_count_buy_limit(uid, trade_item)
            # 如果没有购买记录，则初始化一个新的记录
            if not buy_record:
                buy_record = {"buy_times": 0, "buy_limit": buy_limit}

            buy_times = buy_record.get("buy_times") or 0
            need_count = buy_times + trade_count

            # 检查限购次数是否超出
            if need_count > buy_limit.get("times") or 0:
                return False, '已达到限购次数，请下次再来', {}

            # 更新限购次数
            buy_record["buy_times"] = need_count

        return True, 'OK', buy_record

    async def pay_by_gold(self, u_info, _, unit_price: int, trade_count: int, conf_items: list):
        """金币兑换"""
        price = unit_price * trade_count  # 总价，单价 * 交易数量（默认1）
        gold = u_info.get("gold", 0)
        (gold < price) and self.answer(self.sta_code.DIAMOND_NOT_ENOUGH, hint='金币不足，请先购买金币')

        # 扣费
        cost_item = {
            "goods_id": GoodsItem.GOLD.val,
            "goods_type": GoodsType.V_ASSET.val,
            "goods_count": -price,
            "reason": ReasonCostGold.GOLD_EXCHANGE
        }
        show_items = []
        for ci in conf_items:
            goods_count = ci.get("goods_count")  # 货物数量（单个商品配置）
            goods_count *= trade_count  # 总数，货物数量 * 交易数量
            ci["goods_count"] = int(goods_count)
            show_items.append(ci)

        all_items = [cost_item] + show_items
        return all_items, show_items

    async def pay_by_diamond(self, u_info, store_type, unit_price: int, trade_count: int, conf_items: list):
        """钻石兑换"""
        price = unit_price * trade_count  # 总价，单价 * 交易数量（默认1）
        diamond = u_info.get("diamond", 0)
        (diamond < price) and self.answer(self.sta_code.DIAMOND_NOT_ENOUGH, hint='钻石不足，请先购买钻石')

        # 扣费
        cost_item = {
            "goods_id": GoodsItem.DIAMOND.val,
            "goods_type": GoodsType.V_ASSET.val,
            "goods_count": -price,
            "reason": ReasonCostDiamond.DIAMOND_EXCHANGE
        }
        show_items = []
        for ci in conf_items:
            goods_count = ci.get("goods_count")  # 货物数量（单个商品配置）
            goods_count *= trade_count  # 总数，货物数量 * 交易数量
            match store_type:
                case StoreType.GOLD:
                    ci["goods_count"] = int(goods_count)
                    ci["reason"] = ReasonCostGold.DIAMOND_EX_GOLD
                    show_items.append(ci)
                case _:
                    ci["goods_count"] = int(goods_count)
                    show_items.append(ci)

        all_items = [cost_item] + show_items
        return all_items, show_items

    async def pay_by_five_aggregates(self, u_info, store_type, unit_price: int, trade_count: int, conf_items: list):
        """五蕴丹兑换"""
        uid = u_info.get("uid")
        price = unit_price * trade_count  # 总价，单价 * 交易数量（默认1）
        # 查询五蕴丹余额
        five_data = await UserBagRC.get_user_bag_by_id(uid, goods_id=GoodsItem.FIVE_AGGREGATES.val) or {}
        (five_data.get("goods_count", 0) < price) and self.answer(self.sta_code.DIAMOND_NOT_ENOUGH,
                                                                  hint='五蕴丹不足，请在西行路玩法获取')

        # 扣费
        cost_item = {
            "goods_id": GoodsItem.FIVE_AGGREGATES.val,
            "goods_type": GoodsType.MAGIC.val,
            "goods_count": -price,
        }
        show_items = []
        for ci in conf_items:
            goods_count = ci.get("goods_count")  # 货物数量（单个商品配置）
            goods_count *= trade_count  # 总数，货物数量 * 交易数量
            match store_type:
                case StoreType.SKIN:
                    skin_conf = await ItemsSkinRC.get_skin_items_by_id(ci.get("goods_id"))  # 当前法相配置
                    (not skin_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint='缺少当前法相配置')

                    held_sta, convert_goods = await UserSkinRC.deal_skin_convert(uid, skin_conf)
                    if held_sta in (HeldSta.CAN_MAX_LEVEL, HeldSta.MAX_LEVEL):
                        self.answer(self.sta_code.NOT_IN_VALID_STATE, hint='该法相已满级或精魄足够升到满级')

                    if convert_goods:
                        show_items.append(convert_goods)

                case StoreType.GOLD:
                    ci["goods_count"] = int(goods_count)
                    ci["reason"] = ReasonCostGold.DIAMOND_EX_GOLD
                    show_items.append(ci)

                case _:
                    ci["goods_count"] = int(goods_count)
                    show_items.append(ci)

        all_items = [cost_item] + show_items
        return all_items, show_items

    @staticmethod
    async def pay_by_free(_, store_type, __, ___, conf_items: list):
        """白嫖"""
        gain_items = []
        for ci in conf_items:
            match store_type:
                case StoreType.GOLD:
                    ci["reason"] = ReasonCostGold.STORE_FREE_GOLD
                    gain_items.append(ci)
                case _:
                    gain_items.append(ci)

        return gain_items, gain_items


class SwitchStaHandler(GameAuthApi):
    """ 开关状态（内购...） """
    decorators = []

    async def get(self, req: Request, **_):
        conf_switch = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_SWITCH)
        c_os = req.args.get("c_os")
        c_platform = req.args.get("c_platform")
        switch_type = req.args.get("switch_type")
        if switch_type:
            switch_type = self.check_int(switch_type, require=True, minval=1)
        else:
            switch_type = 1
        match switch_type:
            case switch_type_enum.IAP:
                data = conf_switch.get("iap")
                platform = PlatForm.get_val_by_phrase(c_platform)
                switch = data.get(f'{c_os}_{platform}') or switch_enum.OPEN
                one_of_model = get_one_of_model()
                one_of_model.switch = switch
                self.answer(data=one_of_model)
            case _:
                self.answer(code=self.sta_code.ERR_AUTH, hint='参数有误（switch_type）')
