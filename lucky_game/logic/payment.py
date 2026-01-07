""" 支付相关逻辑处理 """
import decimal
import random

from nsanic.libs.mk_random import RngMaker
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from tortoise.transactions import in_transaction

from c_services.const.cs_enum_const import CmdWorkers
from common.public.enum_const import DbKey
from common.public.common_class import CommonApi
from lucky_game.handler.vivo_pay import vivo_payment
from lucky_game.logic.activity import FirstCharge
from lucky_game.logic.tournament import TournamentLogic
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.base_store import GoodRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import ReasonCostGold, CurrencyType, PayMode, OrderStatus, GainStatus, GoodsSku, PlatForm, \
    OperatingSystem, StoreType
from nsanic.libs.mult_log import NLogger
from common.public.conf import ENV
from common.public.conf import LIVE_SERVER
from lucky_game.handler.huifu import DouGongPay
from lucky_game.handler.wechat import WeChat
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from common.aliyun.pay_service import AlipayPayment
from lucky_game.model_rc.vip_level import UserVipRC
from lucky_proxy.game_adapter.game_data_adapter import GameDataAdapter
from lucky_proxy.logic.game_data_sync import PromotionOrderDataDTO
from lucky_game.model_rc.distribution_settle_conf import DistributionSettleConfRC


class PaymentLogic:
    def __init__(self):
        pass
    async def buy_count(self, uid: int, sku: str, period: str = "day"):
        start_time, end_time = await CommonApi.get_time_range(period)
        NLogger.info(f"校验今日领取次数 uid: {uid} start_time: {start_time} end_time: {end_time}")
        count, e = await OrderRC.get_order_filter(uid=uid, sku=sku, status=OrderStatus.PAID,
                                                  start_time=start_time, end_time=end_time, count=True)
        NLogger.info(f"今日领取次数 count: {count} e: {e} sku: {sku}")
        return count

    async def check_good_validity(self, u_info, express: dict):
        """检查商品有效性，包括限购次数以及销售时间范围"""
        if not express.get("status") or express.get("total") == 0:
            return False, "该商品暂时缺货", {}
        # 检查销售时间
        cur_time = tool_dt.cur_time()
        start_sale_time = express.get("up_time") or 0
        end_sale_time = express.get("down_time") or 0
        if start_sale_time > 0 and cur_time < start_sale_time:
            return False, '商品尚未开始销售', {}
        if 0 < end_sale_time < cur_time:
            return False, '商品已经结束销售', {}

        uid = u_info.get("uid")
        purchase_limit = express.get("purchase_limit")
        sku = express.get("sku")
        # 限购条件校验
        if sku == GoodsSku.SKU_FREE and 0 < await self.buy_count(uid, sku):
            return False, "已领取", {}
        buy_record = {}
        if purchase_limit:
            buy_limit = json_parse(purchase_limit).get("buy_limit")
            if buy_limit:
                buy_count = await self.buy_count(uid, sku, "perpetual")
                need_count = buy_count + 1
                # 检查限购次数是否超出
                if need_count > buy_limit:
                    return False, '已达到限购次数，请下次再来', {}
        return True, 'OK', buy_record

    async def pay_before(self, u_info: dict, express: dict, pay_mode: int, platform: int, num: int = 1, purchase_uid: int = None, os: str = None):
        """
        支付前校验及生成订单
        :param u_info: 用户信息
        :param express: 商品信息
        :param pay_mode: 支付方式
        :param platform: 平台
        :return:
        """
        currency = express.get("currency")
        price = express.get("price")
        # 确保 price 是 Decimal 类型
        if isinstance(price, (int, float, str)):
            price = decimal.Decimal(price)
        elif not isinstance(price, decimal.Decimal):
            return False, '商品价格格式不正确', {}
        price *= num
        field = field_name = ""
        if price > 0:
            if currency != CurrencyType.BY_RMB:
                match currency:
                    case CurrencyType.BY_GOLD:
                        field = "gold"
                        field_name = "金币"
                    case CurrencyType.BY_DIAMOND:
                        field = "diamond"
                        field_name = "钻石"
                    case CurrencyType.BY_YELLOW_DIAMOND:
                        field = "yellow_diamond"
                        field_name = "黄钻"
                    case CurrencyType.BY_ROOM_CARD:
                        field = "room_card"
                        field_name = "房卡"
                amount = u_info.get(field)
                if amount < price:
                    return False, f'{field_name}不足', {}
            else:
                # 校验支付方式
                if pay_mode not in [PayMode.WECHAT_PAY, PayMode.ALIPAY, PayMode.HUI_FU_PAY, PayMode.APPLE_PAY, PayMode.ALIPAY_APP]:
                    return False, "支付方式错误", {}
                # 购买房卡时获取用户折扣价格
                discount = u_info.get("discount")
                if purchase_uid:
                    purchase_info = await BaseUserRC.cache_by_pk(purchase_uid)
                    discount = purchase_info.get("discount")
                if express.get("type") == StoreType.SKIN and discount < 1:
                    if platform in [PlatForm.WEBPAGE, PlatForm.WECHAT_MP] or (platform == PlatForm.NATIVE_APP and os == OperatingSystem.Android):
                        # 安卓、H5购买房卡才享受折扣
                        price *= decimal.Decimal(discount)
        else:
            field_name = "免费领取"
            field = "gold"
            # 随机今日领取金币
            if "content" in express and isinstance(express["content"], list) and express["content"]:
                express["content"] = express["content"][random.randint(0, len(express["content"]) - 1)]
            else:
                express["content"] = 0  # 如果没有配置content或格式不正确，设置为默认值0
        express["price"] = decimal.Decimal(price)
        order, msg = await self.create_order(u_info.get("uid"), express, pay_mode, platform, num, purchase_uid=purchase_uid)
        return True, msg, {"field": field, "field_name": field_name, "order": order}

    async def pay(self, u_info: dict, data_before: dict, express: dict):
        """
        支付处理(资源扣减)
        :return:
        """
        sta, msg, result = True, "OK", {}
        uid = u_info.get("uid")
        currency = express.get("currency")
        sku = express.get("sku")
        price = express.get("price") or 0
        if currency in [CurrencyType.BY_GOLD, CurrencyType.BY_DIAMOND, CurrencyType.BY_YELLOW_DIAMOND, CurrencyType.BY_ROOM_CARD]:
            # 扣除资源
            change_field = data_before.get("field", "")
            if change_field:
                sub_sta, e = await ExtraUserResourceChangesRC.change_user_resource(
                    uid,
                    change_field,
                    price,
                    "sub",
                    reason=ReasonCostGold.DIAMOND_EX_GOLD
                )
                if not sub_sta:
                    return False, e, {}

        else:
            # 充值处理
            pass
        # 扣除商品数量
        if express.get("kind") and express.get("total") > 0:
            order = data_before.get("order")
            await GoodRC.update_int_field(express["good_id"], "total", order["order"].get("num"), "sub")

        return sta, msg, result

    async def pay_method(self, new_order, express: dict, return_url: str = None):
        """支付方法"""
        pay_mode = new_order.pay_mode
        map_func = {
            PayMode.DEFAULT_MODE.val: self.deal_order_general,
            PayMode.HUI_FU_PAY.val: self.pay_1,
            PayMode.ALIPAY.val: self.pay_2,
            PayMode.WECHAT_PAY.val: self.pay_3,
            PayMode.VIVO_PAY.val: self.pay_4,
            PayMode.APPLE_PAY.val: self.pay_5,
            PayMode.ALIPAY_APP.val: self.pay_6,
        }
        deal_func = map_func.get(pay_mode)
        NLogger.info(f"create_order 订单支付方式：{pay_mode} 执行方法：{deal_func}")
        if deal_func and callable(deal_func):
            # 避免decimal出现科学计数形态直接给到客户端
            new_order.amount = format(new_order.amount, '.2f')
            sta, order_info = await deal_func(new_order, return_url=return_url)
            NLogger.info(f"create_order uid: {new_order.uid} 订单创建状态 : {sta} 订单创建结果：", order_info)
            if not sta:
                return {}, order_info
            if pay_mode == PayMode.APPLE_PAY.val:
                pay_dict = {"apple_product_id": express.get("desc")}
                order_info.update({"pay_5": pay_dict})
            return order_info, "ok"
        return {}, "无此交易方式"

    async def order_method(self, pay_mode: int, order_no: str, out_order_no: str = None):
        """去平台查询订单状态并更新订单"""
        map_func = {
            PayMode.HUI_FU_PAY.val: self.order_1,
            PayMode.ALIPAY.val: self.order_2,
            PayMode.WECHAT_PAY.val: self.order_3,
            PayMode.VIVO_PAY.val: self.order_4,
            PayMode.APPLE_PAY.val: self.order_5,
            PayMode.ALIPAY_APP.val: self.order_6,
        }
        func = map_func.get(pay_mode)
        NLogger.info(f"order_method 查询平台订单状态", func)
        if func and callable(func):
            return await func(order_no)
        else:
            return False, "不支持的支付方式", None


    async def pay_after(self, u_info: dict, express: dict, order_no: str):
        """
        支付后处理(领取资源)
        :param u_info:
        :param express:
        :param order_no:
        :return:
        """
        uid = u_info.get("uid")
        content = json_parse(express.get("content"))
        bag_type = express.get("bag_type")
        order, msg = await OrderRC.get_order_info(order_no)
        async with in_transaction(connection_name=DbKey.DEFAULT):
            if bag_type:
                pass
            else:
                # 当为兑换商品时，直接修改订单状态
                up_data = {
                    "gain_status": GainStatus.RECEIVED
                }
                if order.get("currency") != CurrencyType.BY_RMB:
                    up_data["status"] = OrderStatus.PAID
                order_sta, e = await OrderRC.up_order(
                    up_data,
                    order_no
                )
                NLogger.info(f"兑换商品成功-更新订单 订单创建结果order_sta: {order_sta} e: {e}", order)
                if not order_sta:
                    return False, e
                # 更新用户资源
                NLogger.info("领取资源：content:", content)
                if isinstance(content, list):
                    for item in content:
                        add_sta, e = await ExtraUserResourceChangesRC.change_user_resource(
                            uid,
                            item.get("type"),
                            item.get("amount"),
                            "add",
                            reason=ReasonCostGold.CONVERT_AWARDS
                        )
                        NLogger.info(f"支付成功-更新用户资源 添加结果add_sta: {add_sta} e: {e}", item)
                        if not add_sta:
                            return False, e

                else:
                    add_sta, e = await ExtraUserResourceChangesRC.change_user_resource(
                        uid,
                        content.get("type"),
                        content.get("amount"),
                        "add",
                        reason=ReasonCostGold.CONVERT_AWARDS
                    )
                    if not add_sta:
                        return False, e
                # 如果为返还礼包订单
                if order.get("explain"):
                    await self.return_gold_order(order)
                # 更新用户VIP经验
                if order["amount"] > 1:
                    await UserVipRC.update_user_vip_level(uid, order["amount"])
            return True, "ok"

    async def create_order(self, uid, express, pay_mode, platform, num: int = 1, explain: str = "", return_url: str = None, purchase_uid: int = 0):
        # 创建订单
        NLogger.info("create_order 商品信息: good", express)

        order_no = await RngMaker.gen_num(str_len=32)
        new, msg = await OrderRC.add_order(
            uid=uid,
            purchase_uid=purchase_uid if purchase_uid else uid,
            good_id=express.get("good_id"),
            sku=express.get("sku"),
            platform=int(platform),
            amount=express.get("price"),
            currency=express.get("currency"),
            pay_mode=pay_mode,
            num=num,
            order_no=order_no,
            status=OrderStatus.WAIT_PAY,
            explain=explain,
        )
        NLogger.info("create_order 订单插入状态: new_order", new, msg)
        if not new:
            return {}, "订单创建失败"

        # 按下单平台返回数据
        return await self.pay_method(new, express, return_url)



    async def deal_order_general(self, order, return_url: str = None):
        """通用订单处理"""
        return_data = {
            "order_no": order.order_no,
            "trade_time": order.created,
            "trade_amount": order.amount,
            "pay_mode": order.pay_mode,
            "num": order.num,
        }
        return True, return_data


    async def pay_1(self, order_info, return_url: str = None):
        """
        获取汇付支付信息（实际上是后端请求汇付天下之后斗拱的聚合正扫）
        1.用code换取user_openid，监测实时订单价变化；
        2.通过DouGongPay获取，并返回pay_info信息返回给前端；
        3.用order_no缓存pay_info，可以匹配上每一个H5链接；
        """
        order_no = order_info.order_no
        uid = order_info.uid
        req_res = await BaseUserRC.get_user_pay_info(uid, order_no)
        # 生成支付信息
        if not req_res:
            u_info = await BaseUserRC.cache_by_pk(order_info.purchase_uid)
            user_openid = u_info.get("openid") if u_info else None
            if not user_openid:
                return False, 'Invalid user_openid or code.'

            info = {
                "order_no": order_no,
                "sku": order_info.sku,
                "user_openid": user_openid,
                "amount": order_info.amount,
                "platform": order_info.platform,
            }
            req_res = await DouGongPay.dou_gong_js_pay(**info)
            NLogger.info('HuiFuGetPayInfo DouGong res:', req_res)
            if not req_res or not isinstance(req_res, dict):
                return False, 'HuiFuGetPayInfo DouGong error.'
            resp_code = req_res.get('resp_code', None)
            if resp_code != '00000100':  # 下单成功
                return False, req_res.get("bank_message")
            await BaseUserRC.cache_user_pay_info(uid, order_no, req_res)

        pay_info = req_res.get('pay_info')
        if not pay_info:
            return False, 'Not Found pay_info.'
        suc, general_data = await self.deal_order_general(order_info)
        data = {
            "order": general_data,
            "pay_1": json_parse(pay_info)
        }
        return True, data


    async def order_1(self, order_no):
        """
        汇付天下交易查询
        即时更新支付状态，缓存待发货快递
        """
        # 汇付天下交易查询
        sta, msg, req_res = await DouGongPay.dou_gong_query(order_no)
        res = False
        if sta and req_res:
            order_status = req_res.get("order_status")
            if order_status == OrderStatus.PAID:
                res = True
        return res, msg, req_res


    async def pay_2(self, order, return_url: str = None):
        """支付宝支付(H5)"""
        good = await GoodRC.get_good_info(order.sku)
        url = await AlipayPayment().create_h5_payment(good["name"], order.order_no, order.amount, return_url)
        suc, general_data = await self.deal_order_general(order)
        data = {
            "order": general_data,
            "pay_2": {"pay_url": url}
        }
        return True, data
    async def pay_6(self, order, return_url: str = None):
        """支付宝支付(APP)"""
        good = await GoodRC.get_good_info(order.sku)
        url = AlipayPayment("APP").create_app_payment(good["name"], order.order_no, order.amount)
        suc, general_data = await self.deal_order_general(order)
        data = {
            "order": general_data,
            "pay_6": {"pay_url": url}
        }
        return True, data

    async def order_2(self, order_no: str):
        """支付宝订单查询(H5)"""
        sta, msg, req_res = AlipayPayment().query_trade_status(out_trade_no=order_no)
        NLogger.info(f"支付宝平台订单查询: order_no {order_no} 状态: {sta} 结果: {msg} {req_res}")
        return sta, msg, req_res

    async def order_6(self, order_no: str):
        """支付宝订单查询(APP)"""
        sta, msg, req_res = AlipayPayment("APP").query_trade_status(out_trade_no=order_no)
        NLogger.info(f"支付宝平台订单查询: order_no {order_no} 状态: {sta} 结果: {msg} {req_res}")
        return sta, msg, req_res


    async def pay_3(self, order, return_url: str = None):
        """微信小程序道具直购"""
        params = await WeChat.wechat_mini_game_return_order(order.uid, order.amount, order.order_no, order.sku)
        if not params:
            return False, "微信支付失败"
        suc, general_data = await self.deal_order_general(order)
        data = {
            "order": general_data,
            "pay_3": params
        }
        return True, data

    async def order_3(self, order_no: str):
        """微信小程序道具直购订单查询"""
        order, msg = await OrderRC.get_order_info(order_no=order_no)
        u_info = await BaseUserRC.cache_by_pk(order["uid"])
        sta, msg, req_res = await WeChat.wechat_mini_game_query_order(u_info["uid"], u_info["openid"], order_no)
        NLogger.info(f"微信小程序平台订单查询: order_no {order_no} 状态: {sta} 结果: {msg} {req_res}")
        return sta, msg, req_res


    async def pay_4(self, order, return_url: str = None):
        """VIVO支付"""
        try:
            good = await GoodRC.get_good_info(order.sku)
            product_name = good.get("name", "游戏充值")
            product_desc = good.get("desc", "游戏充值")

            # 获取回调地址
            notify_url = f"{LIVE_SERVER}/api/payment/callback/vivo"

            # 创建VIVO支付订单
            success, result = await vivo_payment.create_order(
                order_no=order.order_no,
                amount=float(order.amount),
                product_name=product_name,
                product_desc=product_desc,
                notify_url=notify_url
            )

            if not success:
                NLogger.error(f"VIVO支付创建订单失败: {result}")
                return False, "创建支付订单失败"

            # 获取通用订单信息
            success, general_data = await self.deal_order_general(order)
            if not success:
                return False, "获取订单信息失败"

            data = {
                "order": general_data,
                "pay_4": {
                    "pay_info": result.get("pay_info", ""),
                    "trade_no": result.get("trade_no", "")
                }
            }
            return True, data

        except Exception as e:
            NLogger.error(f"VIVO支付异常: {str(e)}")
            return False, f"VIVO支付异常: {str(e)}"

    async def order_4(self, order_no: str):
        return False, "OK", {"trade_status": None}


    async def pay_5(self, order, return_url: str = None):
        """苹果支付"""
        suc, general_data = await self.deal_order_general(order)
        data = {
            "order": general_data,
            "pay_5": {}
        }
        return True, data

    async def order_5(self, order_no: str):
        # 苹果的订单查询走苹果的订单校验接口：CallbackIos
        return False, "OK", {"trade_status": None}



    async def completed_order(self, **kwargs):
        """
        完成已支付订单
        即时更新发货状态、购买数据（可批量）
        """
        order_no = kwargs.get("order_no")
        trade_no = kwargs.get("trade_no")
        order_status = kwargs.get("order_status")
        gain_status = GainStatus.DEFAULT
        if order_status == OrderStatus.PAID:
            gain_status = GainStatus.GAINED
        explain = kwargs.get("explain")
        order_info, e = await OrderRC.get_order_info(order_no=order_no)
        if not order_info:
            NLogger.info("completed_order 无此待领取订单", order_no)
            return False, e, {}
        if order_info.get("status") == OrderStatus.PAID:
            NLogger.info("completed_order 订单已处理", order_no)
            return True, "订单已处理", {}
        up_data = {
            "status": order_status,
            "gain_status": gain_status,
            "out_order_no": trade_no,
        }
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await OrderRC.up_order(up_data, order_no)
                # 如果订单为活动订单需要更新活动进度
                if order_status == OrderStatus.PAID:

                    # 临时处理 dev分支已经封装方法等合并后优化
                    room_card_ids = [17, 18, 19, 20, 21, 22, 23, 24, 62, 63, 64, 65, 66, 67, 68, 69, 71, 72]
                    fink_ids = [59]
                    order_type = 0
                    # 房卡分成
                    if order_info["good_id"] in room_card_ids:
                        order_type = 1
                    elif order_info["good_id"] in fink_ids:
                        order_type = 2
                    if order_type:
                        order_info["order_type"] = order_type
                        await CommonApi.push_task2worker(CmdWorkers.PROXY_ORDER_SYNC, uid=order_info["uid"], msg=order_info)
                    await self.pay_success(order_info)
                else:
                    await self.pay_fail(order_info)
        except Exception as e:
            NLogger.error(f"completed_order 事务执行失败，原因：{e}")
            return False, '查询发货失败', {}
        return True, "OK", {}


    async def return_gold_order(self, order: dict):
        """返还金币订单"""
        explain = json_parse(order["explain"])
        return_gold = explain.get("return_gold", 0)
        if return_gold:
            add_sta, e = await ExtraUserResourceChangesRC.change_user_resource(
                order["uid"],
                "gold",
                return_gold,
                "add",
                reason=ReasonCostGold.ACTIVITY_RETURN_GOLD
            )
            if not add_sta:
                return False, e
        return True, "OK"

    async def pay_fail(self, order: dict) -> bool:
        """订单支付失败"""
        express = await GoodRC.get_good_info(order["sku"])
        # 商品库存-退回
        if express:
            if express.get("total") > 0:
                await GoodRC.update_int_field(express["good_id"], "total", order["num"], "add")
        return True

    async def pay_success(self, order: dict) -> bool:
        """订单支付成功"""
        express = await GoodRC.get_good_info(order["sku"])
        # 商品类型判断-方便后续操作
        # 商品为活动订单：10金币补足 11复仇礼包 12返还礼包
        good_type = express.get("type")
        if good_type in [10, 11, 12]:
            await FirstCharge().charge_order(order)
        # 商品为赛事订单：15 农产品
        elif good_type == 15:
            # 发送农产品邮件
            await TournamentLogic().distribute_order_good(order)
            # 发放赛事积分
            await TournamentLogic().distribute_order_point(order)

        return True





