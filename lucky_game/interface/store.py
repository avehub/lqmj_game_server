"""
商店相关接口
"""
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from tortoise.transactions import in_transaction
from common.proto.py_pb2.common import switch_enum, get_one_of_model, switch_type_enum
from common.public.enum_const import DbKey, ServiceEnum
from common.public.common_class import CommonApi
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.up_assets import UpAssets
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.base_store import StoreRC, GoodRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import PayType, GoodsItem, ReasonCostDiamond, ReasonCostGold, GoodsType, StoreType, \
    BossType, HeldSta, PlatForm, CurrencyType, PayMode
from lucky_game.logic.payment import PaymentLogic
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC


class StoreHandler(GameAuthApi):
    """ 获取商店商品 """

    async def get(self, req: Request, **kwargs):
        platform = self.check_int(req.args.get("platform"), require=False, p_name="平台ID")
        type_id = self.check_int(req.args.get("type_id"), require=False, p_name="类型ID")
        status = self.check_int(req.args.get("status") or 1, require=False,  p_name="状态")
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        if not platform:
            platform = PlatForm.all_values()
        data = []
        store, e = await StoreRC.get_store_filter(platform=platform, type_id=type_id, status=status)
        self.loginfo("store", store)
        (not store) and self.answer(self.sta_code.NO_CONFIGURATION, hint=e)
        if store:
            sid = [item.get("sid") for item in store]
            self.loginfo("sid", sid)
            goods, e = await GoodRC.get_good_filter(sid=sid, status=status)
            self.loginfo("goods", goods)
            if goods:
                data = await CommonApi.list_by_group(goods, "sid")
        return self.answer(data=data)


class PayByRedemption(GameAuthApi):
    """ 购买商品 """
    async def post(self, req: Request, **kwargs):
        platform = self.check_int(req.args.get("platform"), require=True, p_name='平台ID')
        sku = self.check_str(req.json.get("sku"), require=True, p_name='商品SKU')
        pay_mode = self.check_str(req.json.get("pay_mode"), require=True, p_name='支付方式')
        plat_enum = PlatForm.find_member_by_val(platform)
        pay_enum = PayMode.find_member_by_val(pay_mode)
        (not isinstance(plat_enum, PlatForm) or not isinstance(pay_enum, PayMode)) and self.answer(self.sta_code.ERR_ARG, hint='无效参数')
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 查询商品、校验
        express = await GoodRC.get_good_info(sku)
        (not express) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="商品异常，请联系客服")
        check_sta, check_desc, buy_record = await self.__check_good_validity(u_info, express)
        (not check_sta) and self.answer(code=self.sta_code.NOT_IN_VALID_STATE, hint=f"{check_desc}")

        pay_type = express.get("pay_type")
        (pay_type == PayType.BY_RMB) and self.answer(code=self.sta_code.ERR_ARG, hint='该物品只支持充值获取')
        pt_enum = PayType.find_member_by_val(pay_type)
        (not isinstance(pt_enum, PayType)) and self.answer(self.sta_code.ERR_ARG, hint='没有此兑换方式')

        # 资源处理
        price = express.get("price")
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                sta_before, msg, data_before = await PaymentLogic().pay_before(u_info, express, pay_mode, platform)
                if not sta_before:
                    return self.answer(self.sta_code.RESOURCE_NOT_ENOUGH, hint=msg)
                # 用户资源更新
                change_field = data_before.get("field", "")
                if change_field:
                    sub_sta, e = await ExtraUserResourceChangesRC.change_user_resource(
                        uid,
                        change_field,
                        price,
                        "sub",
                        explain=f"消费{data_before.get('field_name')}"
                    )
                    if not sub_sta:
                        return self.answer(self.sta_code.FAIL, hint=e)

                self.loginfo(f"购买商品：user={u_info}，good={express}")
                # 扣除商品数量
                if express.get("total") > 0:
                    await GoodRC.update_int_field(sku, "total", 1, "sub")
                await BaseUserRC.cache_count_buy_limit(uid, sku, buy_record)
        except Exception as e:
            self.log_err(f'{pt_enum.phrase}事务执行失败，原因：{e}')
            self.answer(self.sta_code.FAIL, hint=f'{pt_enum.phrase}兑换错误，请稍后再试')

        return self.answer(data=data_before.get("order"))



    async def __check_good_validity(self, u_info, express: dict):
        """检查商品有效性，包括限购次数以及销售时间范围"""
        (not express.get("status") or express.get("total") == 0) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="该商品暂时缺货")
        # 检查销售时间
        cur_time = tool_dt.cur_time()
        start_sale_time = express.get("up_time", 0)
        end_sale_time = express.get("down_time", 0)
        if start_sale_time > 0 and cur_time < start_sale_time:
            return False, '商品尚未开始销售', {}
        if 0 < end_sale_time < cur_time:
            return False, '商品已经结束销售', {}

        uid = u_info.get("uid")
        purchase_limit = express.get("purchase_limit")
        sku = express.get("sku")
        # 限购条件校验
        buy_record = {}
        if purchase_limit:
            buy_limit = json_parse(purchase_limit).get("buy_limit")
            if buy_limit:
                buy_record = await BaseUserRC.get_count_buy_limit(uid, sku)
                # 如果没有购买记录，则初始化一个新的记录
                if not buy_record:
                    buy_record = {"buy_times": 0, "buy_limit": buy_limit}
                buy_times = buy_record.get("buy_times") or 0
                need_count = buy_times + 1
                # 检查限购次数是否超出
                if need_count > buy_limit:
                    return False, '已达到限购次数，请下次再来', {}

                # 更新限购次数
                buy_record["buy_times"] = need_count
        return True, 'OK', buy_record


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
