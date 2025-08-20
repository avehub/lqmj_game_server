"""
商店相关接口
"""
import traceback
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
        platform = self.check_str(req.args.get("platform"), require=False, p_name="平台ID")
        type_id = self.check_int(req.args.get("type_id"), require=False, p_name="类型ID")
        status = self.check_int(req.args.get("status") or 1, require=False,  p_name="状态")
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        if not platform:
            platform = PlatForm.all_values()
        store, e = await StoreRC.get_store_filter(platform=platform, type_id=type_id, status=status)
        self.loginfo("store", store)
        if not store:
            return self.answer(data=store, hint=e)
        sid = [item.get("sid") for item in store]
        self.loginfo("sid", sid)
        goods, e = await GoodRC.get_good_filter(sid=sid, status=status)
        self.loginfo("goods", goods)
        if not goods:
            return self.answer(data=goods, hint=e)
            # data = await self.list_by_group(goods, "sid", unordered=False)
        return self.answer(data=goods)


class PayByGood(GameAuthApi):
    """ 商店购物 """
    async def post(self, req: Request, **kwargs):
        platform = self.check_int(req.args.get("platform"), require=True, p_name='平台ID')
        sku = self.check_str(req.json.get("sku"), require=True, p_name='商品SKU')
        if not sku:
            return self.answer(self.sta_code.ERR_ARG, hint="请选择商品")
        pay_mode = self.check_int(req.json.get("pay_mode"), require=True, p_name='支付方式')
        num = self.check_int(req.json.get("num"), require=False, minval=1, default=1, p_name='购买数量')
        plat_enum = PlatForm.find_member_by_val(platform)
        pay_enum = PayMode.find_member_by_val(pay_mode)
        (not isinstance(plat_enum, PlatForm) or not isinstance(pay_enum, PayMode)) and self.answer(self.sta_code.ERR_ARG, hint='无效参数')
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 查询商品、校验
        express = await GoodRC.get_good_info(sku)
        payment = PaymentLogic()

        (not express) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="商品异常，请联系客服")
        check_sta, check_desc, buy_record = await payment.check_good_validity(u_info, express)
        (not check_sta) and self.answer(code=self.sta_code.NOT_IN_VALID_STATE, hint=f"{check_desc}")

        pay_type = express.get("currency")
        pt_enum = PayType.find_member_by_val(pay_type)
        (not isinstance(pt_enum, PayType)) and self.answer(self.sta_code.ERR_ARG, hint='没有此兑换方式')

        self.loginfo(f"商店购物：user={u_info}，good={express}")
        # 支付前校验
        sta_before, msg, data_before = await payment.pay_before(u_info, express, pay_mode, platform, num)
        self.loginfo(f"支付前校验：sta_before={sta_before}, msg={msg}, data_before={data_before}")
        # 支付前校验失败
        if not sta_before:
            return self.answer(self.sta_code.RESOURCE_NOT_ENOUGH, hint=msg)
        # 购买商品事务处理
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                # 支付中
                sta_pay, msg, _ = await payment.pay(u_info, data_before, express)
                self.loginfo(f"支付处理：sta_pay={sta_pay}，msg={msg}")
                # 支付后（如果为兑换商品则直接处理）
                if pay_type != PayType.BY_RMB:
                    sta_after, msg = await payment.pay_after(u_info, express, data_before.get("order")["order_no"])
                    self.loginfo(f"支付成功后资源变更：sta_after={sta_after}，msg={msg}")

                await BaseUserRC.cache_count_buy_limit(uid, sku, buy_record)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for frame in tb:
                self.logerr(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            self.logerr(f'{pt_enum.phrase}事务执行失败，原因：{e}')
            self.answer(self.sta_code.FAIL, hint=f'{pt_enum.phrase}兑换错误，请稍后再试')
        data = data_before.get("order")
        data["buy_good"] = express["content"]
        data["buy_good"]["img"] = express.get("img")
        return self.answer(data=data)






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
