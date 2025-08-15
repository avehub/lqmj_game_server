""" 支付相关逻辑处理 """
import decimal
import random
import time

from nsanic.libs.mk_random import RngMaker
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
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.base_store import StoreRC, GoodRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import PayType, GoodsItem, ReasonCostDiamond, ReasonCostGold, GoodsType, StoreType, \
    BossType, HeldSta, PlatForm, CurrencyType, PayMode, OrderStatus, GainStatus, RandType, OperatingSystem
from nsanic.libs.mult_log import NLogger
from common.public.conf import WeChatConf, HuiFuConf, PROD_SERVER_ADDR, LIVE_SERVER
from lucky_game.handler.douyin import DouYin
from lucky_game.handler.huifu import DouGongPay
from dg_sdk import DGTools
from lucky_game.handler.wechat import WeChat
from lucky_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.handler.ios_pay import ios_payment_service
from common.aliyun.pay_service import AlipayPayment


class PaymentLogic:
    def __init__(self):
        pass

    async def check_good_validity(self, u_info, express: dict):
        """检查商品有效性，包括限购次数以及销售时间范围"""
        (not express.get("status") or express.get("total") == 0) and self.answer(code=self.sta_code.GOODS_NOT_FOUND,
                                                                                 hint="该商品暂时缺货")
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

    async def pay_before(self, u_info: dict, express: dict, pay_mode: int, platform: int, num: int = 1):
        """
        支付前校验及生成订单
        :param u_info:
        :param express:
        :param pay_mode:
        :param platform:
        :return:
        """
        currency = express.get("currency")
        price = express.get("price")
        uid = u_info.get("uid")
        # 确保 price 是 Decimal 类型
        if isinstance(price, (int, float)):
            price = decimal.Decimal(price)
        elif not isinstance(price, decimal.Decimal):
            return False, '商品价格格式不正确', {}
        price *= num
        field = field_name = ""
        if price > 0:
            if currency == CurrencyType.BY_RMB:
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
                if pay_mode not in [PayMode.WECHAT_PAY, PayMode.ALI_PAY, PayMode.HUIFU_PAY, PayMode.IOS_PAY]:
                    pass

        else:
            # 校验今日领取次数
            start_time, end_time = await CommonApi.get_time_range("day")
            NLogger.info(f"校验今日领取次数 uid: {uid} start_time: {start_time} end_time: {end_time}")
            count, e = await OrderRC.get_order_filter(uid=uid, sku=express["sku"], status=OrderStatus.PAID, start_time=start_time, end_time=end_time, count=True)
            NLogger.info(f"今日领取次数 count: {count} e: {e}", express)
            if count > 0:
                return False, "已领取", {}
            field_name = "免费领取"
            field = "gold"
            # 随机今日领取金币
            if "content" in express and isinstance(express["content"], list) and express["content"]:
                express["content"] = express["content"][random.randint(0, len(express["content"]) - 1)]
            else:
                express["content"] = 0  # 如果没有配置content或格式不正确，设置为默认值0
        express["price"] = price
        order, msg = await self.create_order(u_info.get("uid"), express, pay_mode, platform, num)
        return True, msg, {"field": field, "field_name": field_name, "order": order}

    async def pay(self, u_info: dict, data_before: dict, express: dict):
        """
        支付处理
        :return:
        """
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
                    explain=f"消费{data_before.get('field_name')}"
                )
                if not sub_sta:
                    return False, e, {}
            sta, msg, result = True, "OK", {}
        else:
            # 充值处理
            sta, msg, result = await self.pay_method(data_before, u_info, express)
        # 扣除商品数量
        if express.get("total") > 0:
            await GoodRC.update_int_field(sku, "total", 1, "sub")

        return sta, msg, result

    async def pay_method(self, order_info: dict, u_info: dict, express: dict):
        """支付方法"""
        # 检查订单状态是否可拉取支付
        pay_mode = order_info.get("pay_mode")
        if order_info.get("status") != OrderStatus.WAIT_PAY:
            return False, '已支付或订单已关闭', {}
        map_func = {
            PayMode.HUI_FU_PAY.val: self.pay_1,
            PayMode.ALIPAY.val: self.pay_2,
            PayMode.WECHAT_PAY.val: self.pay_3,
            PayMode.VIVO_PAY.val: self.pay_4,
            PayMode.APPLE_PAY.val: self.pay_5
        }
        deal_func = map_func.get(pay_mode)
        NLogger.info(f"pay_method 去支付订单：{deal_func}")
        if deal_func and callable(deal_func):
            order_info = await deal_func(order_info)
            NLogger.info(f"pay_method 去支付订单", order_info)
        return True, "无此交易方式", {}

    async def order_method(self, pay_mode: int, order_no: str, code: str, u_info: dict, express: dict):
        """查询订单"""
        # 1.查询本地订单
        order_info = await OrderRC.get_order_info(order_no=order_no)
        if not order_info:
            NLogger.error("HuiFuPayQueryOrder 无此订单", order_no)
            return False, '无此订单'

        func = self.pay_platform(pay_mode)
        # 动态方法
        method = getattr(self, func)
        if method is not None:
            return await method(order_id, code)
        return None

    async def callback_method(self, order_no: str, out_trade_no: str, out_trade_status: int, express: str):
        """支付方法"""
        # 将不同的支付平台处理
        if pay_mode == PayMode.ALIPAY:
            express = "支付宝"
        elif pay_mode == PayMode.WECHAT_PAY:
            express = "微信"
        else:
            pexpress = "汇付天下"

        sta, msg = self.completed_order(order_no=order_no, trade_no=out_trade_no, out_trade_status=out_trade_status, explain=express)

        return sta, msg

    async def pay_platform(self, pay_mode: int):
        """获取支付平台方法"""
        if pay_mode == PayMode.DEFAULT_MODE:
            # 免费
            func = ""
        else:
            func = f"pay_{pay_mode}"
        return func

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
        async with in_transaction(connection_name=DbKey.DEFAULT):
            if bag_type:
                pass
            else:
                # 支付成功校验
                order, msg = await OrderRC.get_order_info(order_no)
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
                            explain=f"获得{item.get('type')}"
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
                        explain=f"获得{content.get('type')}"
                    )
                    if not add_sta:
                        return False, e

            return True, "ok"

    async def create_order(self, uid, express, pay_mode, platform, num: int = 1, explain: str = "", return_url: str = None):
        # 创建订单
        order_no = await RngMaker.gen_num(str_len=32)
        new, msg = await OrderRC.add_order(
            uid=uid,
            good_id=express.get("good_id"),
            sku=express.get("sku"),
            platform=platform,
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

        # 订单创建完成，按下单平台返回数据
        map_func = {
            PayMode.DEFAULT_MODE.val: self.deal_order_general,
            PayMode.HUI_FU_PAY.val: self.pay_1,
            PayMode.ALIPAY.val: self.pay_2,
            PayMode.WECHAT_PAY.val: self.pay_3,
            PayMode.VIVO_PAY.val: self.pay_4,
            PayMode.APPLE_PAY.val: self.deal_order_general
        }
        deal_func = map_func.get(pay_mode)
        NLogger.info(f"create_order 订单支付方式：{pay_mode} 执行方法：{deal_func}")
        if deal_func and callable(deal_func):
            sta, order_info = await deal_func(new, return_url=return_url)
            NLogger.info(f"create_order uid: {uid} 订单创建状态 : {sta} 订单创建结果：", order_info)
            if not sta:
                return {}, order_info
            if pay_mode != PayMode.DEFAULT_MODE.val:
                order_info += self.deal_order_general(new)
            if pay_mode == PayMode.APPLE_PAY.val:
                order_info += {"ios_product_id": express.get("desc")}
            return order_info, "ok"
        return {}, "无此交易方式"


    async def deal_order_general(self, order: dict, return_url: str = None):
        """通用订单处理"""
        return_data = {
            "order_no": order.order_no,
            "trade_time": order.created,
            "trade_amount": order.amount,
            "pay_mode": order.pay_mode,
        }
        return True, return_data


    async def pay_1(self, order_info: dict, return_url: str = None):
        """
        获取汇付支付信息（实际上是后端请求汇付天下之后斗拱的聚合正扫）
        1.用code换取gzh_openid，监测实时订单价变化；
        2.通过DouGongPay获取，并返回pay_info信息返回给前端；
        3.用order_no缓存pay_info，可以匹配上每一个H5链接；
        """
        order_no = order_info.order_no
        uid = order_info.uid
        req_res = await BaseUserRC.get_user_pay_info(uid, order_no)
        # 生成支付信息
        if not req_res:
            u_info = await BaseUserRC.cache_by_pk(uid)
            gzh_openid = u_info.get("openid") or ""
            if not gzh_openid:
                # gzh_openid = await WeChat.update_gzh_openid(uid, code)
                return False, 'Invalid gzh_openid or code.'

            info = {
                "order_no": order_no,
                "sku": order_info.sku,
                "gzh_openid": gzh_openid,
                "amount": order_info.amount,
            }
            req_res = await DouGongPay.dou_gong_js_pay(**info)
            NLogger.info('HuiFuGetPayInfo DouGong res:', req_res)

            resp_code = req_res.get('resp_code')
            if resp_code != '00000100':  # 下单成功
                return False, req_res.get("bank_message")
            await BaseUserRC.cache_user_pay_info(uid, order_no, req_res)

        pay_info = req_res.get('pay_info')
        if not pay_info:
            return False, 'Not Found pay_info.'
        return True, json_parse(pay_info)


    async def order_1(self, order_info: dict):
        """
        汇付天下交易查询
        即时更新支付状态，缓存待发货快递
        """
        order_no = order_info.get("order_no")
        uid = order_info.get("uid")
        trade_amount = order_info.get("trade_amount") or 0
        trade_item = order_info.get("trade_item")

        # 2.汇付天下交易查询
        req_res = await DouGongPay.dou_gong_query(order_no)
        # NLogger.error("HuiFuPayQueryOrder 解析查询数据：", req_res)
        resp_code = req_res.get('resp_code')
        if resp_code != '00000000':
            return {"resp_cog": req_res}

        if req_res.get("trans_stat") != "S":  # P：处理中；S：成功；F：失败；I: 初始（初始状态很罕见，请联系汇付技术人员处理）；交易状态以此字段为准。
            NLogger.error("HuiFuPayQueryOrder 支付失败或支付成功未发币到账", order_no)
            return False, '支付失败或支付成功未发币到账'

        # 3.查询货物 goods立得货物 / gifts赠物
        express, _, buy_record, __, desc = await self.verify_goods(uid, trade_item)
        if not express:
            return False, desc
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 4.更新支付状态，缓存待领取订单
        order_status = order_info.get("order_status")
        if order_status != OrderStatus.PAID:
            order_status = OrderStatus.PAID
            update_paid = {"order_status": order_status}
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await OrderRC.up_order(order_no, update_paid, order_info)
                    await BaseUserRC.cache_user_paid_order(uid, order_no, goods, gifts)  # 预发货
            except Exception as e:
                NLogger.error(f"HuiFuPayQueryOrder 事务执行失败，原因：{e}")
                return False, '快递打包失败'
        else:
            NLogger.error("HuiFuPayQueryOrder 快递已经发出", order_no)

        NLogger.error("HuiFuPayQueryOrder 快递入站成功", order_no)
        return {"order_no": order_no, "order_status": order_status}


    async def pay_2(self, order, return_url: str = None):
        """支付宝支付(H5)"""
        good = await GoodRC.get_good_info(order.sku)
        url = await AlipayPayment().create_h5_payment(good["name"], order.order_no, order.amount, return_url)
        return_data = {
            "order_no": order.order_no,
            "trade_time": order.created,
            "trade_amount": order.amount,
            "pay_url": url
        }
        return True, return_data

    async def order_2(self, order_no: str):
        pass


    async def pay_3(self, order, return_url: str = None):
        """微信支付"""
        good = await GoodRC.get_good_info(order.sku)
        url = await AlipayPayment().create_h5_payment(good["name"], order.order_no, order.amount, return_url)
        return_data = {
            "order_no": order.order_no,
            "trade_time": order.created,
            "trade_amount": order.amount,
            "pay_url": url
        }
        return True, return_data

    async def order_3(self, order_no: str):
        pass


    async def pay_4(self, order, return_url: str = None):
        """VIVO支付"""
        good = await GoodRC.get_good_info(order.sku)
        url = await AlipayPayment().create_h5_payment(good["name"], order.order_no, order.amount)
        return_data = {
            "order_no": order.order_no,
            "trade_time": order.created,
            "trade_amount": order.amount,
            "pay_url": url
        }
        return True, return_data

    async def order_4(self, order_no: str):
        pass


    async def pay_5(self, order, return_url: str = None):
        """苹果支付"""
        good = await GoodRC.get_good_info(order.sku)
        url = await ios_payment_service.create_h5_payment(good["name"], order.order_no, order.amount)
        return_data = {
            "order_no": order.order_no,
            "trade_time": order.created,
            "trade_amount": order.amount,
            "pay_url": url
        }
        return True, return_data

    async def order_5(self, order_no: str):
        pass



    async def completed_order(self, **kwargs):
        """
        完成已支付订单
        即时更新发货状态、购买数据（可批量）
        """
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        order_no = kwargs.get("order_no")
        trade_no = kwargs.get("trade_no")
        order_status = kwargs.get("order_status")
        gain_status = GainStatus.DEFAULT
        if order_status == OrderStatus.PAID:
            gain_status = GainStatus.GAINED
        explain = kwargs.get("explain")
        order_info = await OrderRC.get_order_info(order_no=order_no)
        if not order_info:
            NLogger.error("completed_order 无此待领取订单", order_no)
            return False, '无此待领取订单'
        good_info = await GoodRC.get_good_info(order_info.get("sku"))
        goods = good_info["content"]
        up_data = {
            "status": order_status,
            "gain_status": gain_status,
            "out_order_no": trade_no,
            "explain": explain,
        }

        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await OrderRC.up_order(up_data, order_no)
                # 更新用户资产
                if isinstance(goods, list):
                    for good in goods:
                        await ExtraUserResourceChangesRC.change_user_resource(uid, good["type"], good["amount"],
                                                                              explain="充值获得")
                else:
                    await ExtraUserResourceChangesRC.change_user_resource(uid, goods["type"], goods["amount"],
                                                                              explain="充值获得")
        except Exception as e:
            NLogger.error(f"completed_order 事务执行失败，原因：{e}")
            return False, '查询发货失败'
        return True, "OK", goods

    async def pay_ios(self, request: Request, **kwargs):
        """
        处理iOS应用内购买
        """
        try:
            # 获取请求参数
            order_id = request.json.get("order_id")
            receipt_data = request.json.get("receipt_data")

            if not all([order_id, receipt_data]):
                return False, "Missing required parameters"

            # 查询订单
            order = await OrderRC.get_order_info(order_no=order_id)
            if not order:
                return False, "Order not found"

            # 验证订单状态
            if order.get("status") != OrderStatus.WAIT_PAY:
                return False, "Invalid order status"

            # 处理支付
            result = await ios_payment_service.process_payment(order_id, receipt_data)

            if not result.get("success"):
                return False, "Payment verification failed"

            # 更新订单状态
            async with in_transaction(connection_name=DbKey.DEFAULT):
                # 更新订单状态为已支付
                await OrderRC.up_order(
                    {
                        "status": OrderStatus.PAID,
                        "out_order_no": result["data"]["transaction_id"],
                        "updated": int(time.time())
                    },
                    order_id
                )

                # 发放游戏内物品
                # 这里根据你的业务逻辑实现
                # 例如：await self._deliver_items(order, result["data"])
            data = {
                "order_id": order_id,
                "status": OrderStatus.PAID
            }
            return True, "OK", data

        except Exception as e:
            NLogger.error(f"iOS payment processing failed: {str(e)}")
            return False, "Internal server error"

    async def _deliver_items(self, order: dict, receipt_data: dict):
        """发放游戏内物品"""
        # 根据订单信息发放对应的游戏内物品
        # 例如：
        # await ExtraUserResourceChangesRC.change_user_resource(
        #     uid=order["uid"],
        #     resource_type="diamond",
        #     amount=100,
        #     operation="add",
        #     reason="ios_payment",
        #     extra_data={
        #         "order_id": order["order_no"],
        #         "product_id": receipt_data.get("product_id")
        #     }
        # )
        pass

