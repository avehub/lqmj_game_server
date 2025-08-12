""" 支付相关逻辑处理 """
import decimal
import random

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
    BossType, HeldSta, PlatForm, CurrencyType, PayMode, OrderStatus, DeliverStatus, RandType, OperatingSystem
from nsanic.libs.mult_log import NLogger
from common.public.conf import WeChatConf, HuiFuConf, PROD_SERVER_ADDR, LIVE_SERVER, TEST_SERVER_ADDR
from lucky_game.handler.douyin import DouYin
from lucky_game.handler.huifu import DouGongPay
from dg_sdk import DGTools
from lucky_game.handler.wechat import WeChat
from lucky_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.handler.ios_pay import ios_payment_service


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
                case CurrencyType.BY_RMB:
                    # 充值

                    pass
            amount = u_info.get(field)
            if amount < price:
                return False, f'{field_name}不足', {}
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

    async def pay(self, uid: int, data_before: dict, express: dict):
        """
        支付处理
        :return:
        """
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
                    return False, e
        else:
            # 充值处理
            pass
        # 扣除商品数量
        if express.get("total") > 0:
            await GoodRC.update_int_field(sku, "total", 1, "sub")

        return True, "ok"

    async def __pay_type(self, pay_mode: int, c_os: str, platform: int,):
        if platform in [PlatForm.WEBPAGE, PlatForm.WECHAT_MP, PlatForm.WECHAT_MINI_GAME]:
            # 汇付天下
            pass
        elif platform == PlatForm.NATIVE_APP and c_os == OperatingSystem.IOS:
            # 苹果
            pass
        elif platform == PlatForm.NATIVE_APP and c_os == OperatingSystem.Android:
            # 微信
            pass
        elif platform == PlatForm.NATIVE_APP and c_os == OperatingSystem.VIVO:
            # VIVO
            pass
        # elif platform == PlatForm.WEBPAGE and pay_mode == OperatingSystem.PC:
        else:
            # 支付宝
            pass
        return True, {}

    async def pay_after(self, u_info: dict, express: dict, order_no: str):
        """
        支付后处理
        :param u_info:
        :param express:
        :param order_no:
        :return:
        """
        uid = u_info.get("uid")
        content = json_parse(express.get("content"))
        bag_type = express.get("bag_type")
        if bag_type:
            pass
        else:
            # 支付成功校验
            order, msg = await OrderRC.get_order_info(order_no)
            # 当为兑换商品时，直接修改订单状态
            if order.get("currency") != CurrencyType.BY_RMB:
                order_sta, e = await OrderRC.up_order(
                    {
                        "status": OrderStatus.PAID
                    },
                    order_no
                )
                NLogger.info(f"兑换商品成功-更新订单 订单创建结果order_sta: {order_sta} e: {e}", order)
                if not order_sta:
                    return False, e
            else:
                pass

            # 更新用户资源
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

    async def create_order(self, uid, express, pay_mode, platform, num: int = 1, explain: str = ""):
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
            PayMode.HUI_FU_PAY.val: self.deal_order_general,
            PayMode.ALIPAY.val: self.deal_order_general,
            PayMode.WECHAT_PAY.val: self.deal_order_general,
            PayMode.VIVO_PAY.val: self.deal_order_general,
            PayMode.APPLE_PAY.val: self.deal_order_general
        }
        deal_func = map_func.get(pay_mode)
        if deal_func and callable(deal_func):
            order_info = await deal_func(uid, new.order_no, new.created, new.amount)
            NLogger.info(f"create_order uid: {uid} 订单创建结果", order_info)
            return order_info, "ok"
        return {}, "无此交易方式"


    async def deal_order_general(self, _, order_no, trade_time, trade_amount):
        """通用订单处理"""
        return_data = {
            "order_no": order_no,
            "trade_time": trade_time,
            "trade_amount": trade_amount
        }
        return return_data


    async def pay_huifu(self, order_id: str, code: str):
        """
                获取汇付支付信息（实际上是后端请求汇付天下之后斗拱的聚合正扫）
                1.用code换取gzh_openid，监测实时订单价变化；
                2.通过DouGongPay获取，并返回pay_info信息返回给前端；
                3.用order_id缓存pay_info，可以匹配上每一个H5链接；
                """
        # 查询本地订单
        order_info = await OrderRC.get_order_info(order_no=order_id) or {}
        if not order_info:
            NLogger.error("WeChatGetPayInfo 无此订单", order_id)
            return False, '无此订单'

        # 检查订单状态是否可拉取支付
        if order_info.get("status") != OrderStatus.WAIT_PAY:
            return False, '已经支付了或重复支付'
        uid = order_info.get('uid')
        req_res = await BaseUserRC.get_user_pay_info(uid, order_id)
        # 生成支付信息
        if not req_res:
            gzh_openid = await WeChat.update_gzh_openid(uid, code)
            if not gzh_openid:
                return False, 'Invalid gzh_openid or code.'

            order_info["gzh_openid"] = gzh_openid
            req_res = await DouGongPay.dou_gong_js_pay(**order_info)
            NLogger.info('HuiFuGetPayInfo DouGong res:', req_res)

            resp_code = req_res.get('resp_code')
            if resp_code != '00000100':  # 下单成功
                return {"resp_cog": req_res}
            await BaseUserRC.cache_user_pay_info(uid, order_id, req_res)

        pay_info = req_res.get('pay_info')
        if not pay_info:
            return False, 'Not Found pay_info.'
        return {"pay_info": pay_info}


    async def HuiFuPayQueryOrder(self, order_id: str):
        """
        汇付天下交易查询
        即时更新支付状态，缓存待发货快递
        """

        # 1.查询本地订单
        order_info = await OrderRC.get_order_info(order_no=order_id)
        if not order_info:
            NLogger.error("HuiFuPayQueryOrder 无此订单", order_id)
            return False, '无此订单'
        uid = order_info.get("uid")
        trade_amount = order_info.get("trade_amount") or 0
        trade_item = order_info.get("trade_item")

        # 2.汇付天下交易查询
        req_res = await DouGongPay.dou_gong_query(order_id)
        # NLogger.error("HuiFuPayQueryOrder 解析查询数据：", req_res)
        resp_code = req_res.get('resp_code')
        if resp_code != '00000000':
            return {"resp_cog": req_res}

        if req_res.get("trans_stat") != "S":  # P：处理中；S：成功；F：失败；I: 初始（初始状态很罕见，请联系汇付技术人员处理）；交易状态以此字段为准。
            NLogger.error("HuiFuPayQueryOrder 支付失败或支付成功未发币到账", order_id)
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
                    await OrderRC.up_order(order_id, update_paid, order_info)
                    await BaseUserRC.cache_user_paid_order(uid, order_id, goods, gifts)  # 预发货
            except Exception as e:
                NLogger.error(f"HuiFuPayQueryOrder 事务执行失败，原因：{e}")
                return False, '快递打包失败'
        else:
            NLogger.error("HuiFuPayQueryOrder 快递已经发出", order_id)

        NLogger.error("HuiFuPayQueryOrder 快递入站成功", order_id)
        return {"order_id": order_id, "order_status": order_status}

    def __check_signature(self, req: Request):
        """ 检查签名 """
        form = req.get_form()

        resp_code = form.get('resp_code')
        resp_desc = form.get('resp_desc')
        resp_data_str = form.get('resp_data')
        sign = form.get('sign')
        NLogger.info("汇付天下支付回调通知", resp_code, resp_desc)

        if resp_code != '00000000':
            return False, 'Invalid resp_code.'

        # 使用斗拱平台公钥进行验签
        resp_data = json_parse(resp_data_str)
        result = DGTools.verify_sign(resp_data, sign, pub_key=HuiFuConf.DOUGONG_APP_PUBLIC_KEY)
        if not result:
            NLogger.error(f"HuiFu 汇付天下支付回调通知{result}验签失败")
            return False, "验签失败"
        return True, resp_data

    async def notify_huifu(self, req: Request):
        """
               汇付天下支付回调通知
               参考文档：https://paas.huifu.com/open/doc/api/#/smzf/api_jhzs?id=%e5%bc%82%e6%ad%a5%e8%bf%94%e5%9b%9e%e5%8f%82%e6%95%b0
               即时更新支付状态，缓存待发货快递
               """
        """默认格式为 application/x-www-form-urlencode，form表单格式"""
        res, res_dict = self.__check_signature(req)
        if not res:
            return res_dict

        # 1.验签成功后，处理业务逻辑
        NLogger.info("汇付天下支付回调通知 解析回调数据", res_dict)
        order_id = res_dict.get('req_seq_id')  # 交易时传入，原样返回
        if res_dict.get("trans_stat") != "S":  # P：处理中；S：成功；F：失败；I: 初始（初始状态很罕见，请联系汇付技术人员处理）；交易状态以此字段为准。
            NLogger.info("HuiFuPayNotify 支付失败或支付成功未发币到账", order_id)
            return False, "支付失败或支付成功未发币到账"

        # 1.查询本地订单状态（查无订单直接返成功，为了防止来自测试服订单的回调，仅回调使用此逻辑）
        order_info = await OrderRC.get_order_info(order_no=order_id)
        if not order_info:
            NLogger.error("HuiFuPayNotify 无此订单", order_id)
            return False, "无此订单"
        uid = order_info.get("uid")
        trade_amount = order_info.get("trade_amount") or 0
        trade_item = order_info.get("trade_item")

        # 2.验证买家
        u_info = await BaseUserRC.cache_by_uid(uid)
        if not u_info:
            NLogger.error("HuiFuPayNotify 找不到对应下单用户", order_id)
            return False, "找不到对应下单用户"

        # 3.查询货物 goods立得货物 / gifts赠物
        express, _, buy_record, __, desc = await self.verify_goods(uid, trade_item)
        if not express:
            return False, desc
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 4.更新支付状态，缓存待领取订单
        if order_info.get("order_status") != OrderStatus.PAID:
            update_paid = {"order_status": OrderStatus.PAID}
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await OrderRC.up_order(update_paid, order_id)
                    await BaseUserRC.cache_user_paid_order(uid, order_id, goods, gifts)  # 预发货
            except Exception as e:
                NLogger.error(f"HuiFuPayNotify 事务执行失败，原因：{e}")
                return False, "HuiFuPayNotify 快递打包失败"
        else:
            NLogger.error("HuiFuPayNotify 快递已经发出", order_id)

        NLogger.error("HuiFuPayNotify 快递入站成功", order_id)
        return False, "Success"


    async def CompletePaidOrder(self, _, **kwargs):
        """
                完成已支付订单
                即时更新发货状态、购买数据（可批量）
                """
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 1.注意物品和赠品以预发货的为主
        paid_orders = await BaseUserRC.get_user_paid_order(uid)
        if not paid_orders:
            return False,  '没有待领取订单'
        all_goods = []
        all_gifts = []

        for order in paid_orders:
            order_id = order.get("order_id")
            goods = order.get("goods")
            gifts = order.get("gifts")

            # 2.查询多个本地订单
            order_info = await OrderRC.get_order_info(order_no=order_id)
            if not order_info:
                NLogger.error("CompletePaidOrder 无此待领取订单", order_id)
                return False, '无此待领取订单'

            # 3.发货并准备派送
            if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
                update_deliver = {
                    "deliver_status": DeliverStatus.SHIPPED,
                    "finish_time": tool_dt.cur_time(),
                }
                try:
                    async with in_transaction(connection_name=DbKey.DEFAULT):
                        await OrderRC.up_order(update_deliver, order_id)
                        await UpAssets.update_assets(uid, goods, gifts)

                        # 4.查询货物，注意此处主要是查询活动的，物品在缓存取
                        express, item_num, _, __, ___ = await self.verify_goods(uid, order_info.get("trade_item"))
                        if express and item_num == 3:
                            await UserActivityRC.update_user_charge_records(uid, express)
                except Exception as e:
                    NLogger.error(f"CompletePaidOrder 事务执行失败，原因：{e}")
                    return False, '查询发货失败'

                # 4.将当前订单的货物和奖励加入总结果
                all_goods.extend(goods)
                all_gifts.extend(gifts)
            else:
                NLogger.error("CompletePaidOrder 已经取件了", order_id)

        NLogger.error("CompletePaidOrder 订单交易成功")
        return all_goods, all_gifts

    async def IOSPaymentHandler(self, request: Request, **kwargs):
        """
        处理iOS应用内购买
        """
        try:
            # 获取请求参数
            order_id = request.json.get("order_id")
            receipt_data = request.json.get("receipt_data")

            if not all([order_id, receipt_data]):
                return self.answer(
                    code=400,
                    message="Missing required parameters"
                )

            # 查询订单
            order = await OrderRC.get_order_info(order_no=order_id)
            if not order:
                return self.answer(
                    code=404,
                    message="Order not found"
                )

            # 验证订单状态
            if order.get("status") != OrderStatus.WAIT_PAY:
                return self.answer(
                    code=400,
                    message="Invalid order status"
                )

            # 处理支付
            result = await ios_payment_service.process_payment(order_id, receipt_data)

            if not result.get("success"):
                return self.answer(
                    code=result.get("code", 400),
                    message=result.get("message", "Payment verification failed")
                )

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

            return self.answer(
                data={
                    "order_id": order_id,
                    "status": OrderStatus.PAID
                }
            )

        except Exception as e:
            NLogger.error(f"iOS payment processing failed: {str(e)}")
            return self.answer(
                code=500,
                message="Internal server error"
            )

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

    async def __2_pay(self, open_id, order_id, trade_amount, trade_name, trade_desc):
        """支付宝支付(H5)"""
        pass

        # (not all([open_id, order_id, trade_amount, trade_name, trade_desc])) and self.answer(code=self.sta_code.ERR_ARG)
        #
        result, req_data = await Alipay.ali_mini_game_coin_pay(open_id, order_id, trade_amount, trade_name, trade_desc)
        # self.log_info("AliPay 扣减游戏币结果", req_data)
        # if not result:
        #     data = {"errcode": int(req_data.get('code')), "errmsg": req_data.get('sub_msg')}
        #     return self.answer(self.sta_code.EXTERNAL_ERR, data)
        # return True
