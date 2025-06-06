"""
主要支付接口
"""
import asyncio
from datetime import datetime
from dg_sdk import DGTools
from sanic import Request, response
from tortoise.transactions import in_transaction
from c_services.const.cs_enum_const import CmdWorkers
from common.public.conf import DouYinConf, WeChatConf, HuiFuConf, LIVE_SERVER
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.douyin import DouYin
from lucky_game.handler.huifu import DouGongPay
from lucky_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_db.main import RecordsTradeOrder
from lucky_game.handler.wechat import WeChat
from lucky_game.handler.WXBizMsgCrypt import WXBizMsgCrypt
from lucky_game.handler.up_assets import UpAssets
from nsanic.libs import tool_dt
from lucky_game.handler.alipay import Alipay
from common.utils.utils import UtilsTool
from lucky_game.model_rc.base_store import ConfStoreRC
from common.proto.py_pb2.common import get_one_of_model
from common.public.enum_const import DbKey, TaskId
from nsanic.libs.tool import json_parse, json_encode
from lucky_game.const import PayMode, OrderStatus, DeliverStatus, PlatForm, GoodsItem, RandType


class BaseSomePay(GameAuthApi):

    @classmethod
    def info_log(cls, *data):
        cls.conf.info_log("支付日志：", *data)

    @classmethod
    def error_log(cls, *data):
        cls.conf.info_log("支付错误：", *data)

    async def process_after_deliver(self, uid, trade_amount):
        """发货后处理（更新物品和发货状态之后）"""
        # 更新VIP经验
        vip_info = {"amount": int(trade_amount)}
        await self.push_task2worker(CmdWorkers.UPDATE_USER_VIP_LEVEL, msg=vip_info, uid=uid)

        # 更新任务
        task_info = {"task_id": TaskId.BUY_PACKAGE_1, "add_val": 1}
        await self.push_task2worker(CmdWorkers.UPDATE_GAME_TASK, msg=task_info, uid=uid)

        # 终生卡激活保险箱
        # if act_type == ActivityType.LIFETIME_CARD:
        #     await self.push_task2worker(CmdWorkers.PROCESS_SAFE_BOX, uid=uid)

    async def process_after_received(self, uid, order_info: dict, buy_record=None):
        """收货后处理（发货后需要查询获得物品时）"""
        trade_item = order_info.get("trade_item")
        # 更新购买次数（仅充值礼包促销）
        if buy_record:
            await BaseUserRC.cache_count_buy_limit(uid, trade_item, buy_record)

        # 更新订单次数（若查询、回调都更新会导致客户端查货的时候没有首单赠品）
        count_info = {
            'trade_item': trade_item,
            'order_id': order_info.get("order_id"),
            'trade_item_count': order_info.get("trade_item_count")
        }
        await self.push_task2worker(CmdWorkers.UPDATE_ITEM_ORDER_COUNT, msg=count_info, uid=uid)

    @classmethod
    async def verify_goods(cls, uid, trade_item):
        """ 验证货物 """
        item_num, _ = UtilsTool.explode_command(trade_item, digit=3)
        if item_num == 3:
            express = await ConfActivityRC.get_activity_item_by_id(act_id=trade_item)
        else:
            express = await ConfStoreRC.get_store_item_by_id(store_id=trade_item)

        randed = False  # 是否返利
        if not express:
            return {}, item_num, {}, randed, '商品缺货，请联系客服'

        # 检查限购次数（仅充值礼包促销）
        buy_record = {}
        buy_limit = json_parse(express.get("buy_limit")) if express.get("buy_limit") else None
        sale_limit = json_parse(express.get("sale_limit")) if express.get("sale_limit") else None
        if buy_limit or sale_limit:
            # 如果没有购买记录，则初始化一个新的记录
            buy_record = await BaseUserRC.get_count_buy_limit(uid, trade_item) or {"buy_times": 0}
            buy_times = buy_record.get("buy_times") or 0
            need_count = buy_times + 1

            # 限购
            if buy_limit:
                buy_record['buy_limit'] = buy_limit
                # 检查限购次数是否超出
                if need_count > buy_limit.get("times") or 0:
                    return {}, item_num, {}, randed, '已达到限购次数，请下次再来'
            # 促销
            elif sale_limit:
                # 两个配置的礼包加入首次翻倍并使用折扣价（不足/复仇）
                if buy_times < sale_limit.get("times") or 0:
                    rand_type = express.get("rand_type") or RandType.NONE
                    buy_record['buy_limit'] = sale_limit

                    if rand_type == RandType.BACK_AND_DISCOUNT:
                        # 使用折扣价，现价>>特价 / 原价>>现价
                        discount_price = express.get("discount_price") or 0
                        price = express.get("price") or 0
                        if discount_price > 0:
                            express["orig_price"] = price
                            express["price"] = discount_price

                        # 返还金币
                        conf_items = express.get("conf_items")
                        for c in conf_items or []:
                            multiple = sale_limit.get("multiple")
                            if c.get("goods_id") == GoodsItem.GOLD.val and multiple > 1:
                                c["goods_count"] = c.get("goods_count") * multiple

                        randed = True
            # 更新限购次数
            buy_record["buy_times"] = need_count
        return express, item_num, buy_record, randed, 'OK'

    async def alipay_game_coin_pay(self, open_id, order_id, trade_amount, trade_name, trade_desc):
        """AliPay 扣减游戏币"""
        (not all([open_id, order_id, trade_amount, trade_name, trade_desc])) and self.answer(code=self.sta_code.ERR_ARG)

        result, req_data = await Alipay.ali_mini_game_coin_pay(open_id, order_id, trade_amount, trade_name, trade_desc)
        self.info_log("AliPay 扣减游戏币结果", req_data)
        if not result:
            data = {"errcode": int(req_data.get('code')), "errmsg": req_data.get('sub_msg')}
            return self.answer(self.sta_code.EXTERNAL_ERR, data)
        return True

    async def douyin_game_coin_pay(self, open_id, order_id, trade_amount, access_token):
        """DouYin 扣减游戏币"""
        (not all([open_id, order_id, trade_amount, access_token])) and self.answer(code=self.sta_code.ERR_ARG)

        errcode, req_data = await DouYin.douyin_mini_game_coin_pay(open_id, access_token, trade_amount, order_id)
        self.info_log("DouYin 扣减游戏币结果：", errcode, req_data)
        if errcode:
            data = {"errcode": int(errcode), "errmsg": req_data}
            return self.answer(self.sta_code.EXTERNAL_ERR, data)
        return True

    async def wechat_game_coin_pay(self, uid, open_id, order_id, trade_amount, access_token, u_ip):
        """WeChat 扣减游戏币"""
        (not all([uid, open_id, order_id, trade_amount, access_token, u_ip])) and self.answer(
            code=self.sta_code.ERR_ARG)

        errcode, req_data = await WeChat.wechat_mini_game_coin_pay(uid, open_id, access_token, trade_amount, order_id,
                                                                   u_ip)
        self.info_log("WeChat 扣减游戏币结果：", errcode, req_data)
        if errcode:
            data = {"errcode": int(errcode), "errmsg": req_data}
            return self.answer(self.sta_code.EXTERNAL_ERR, data)
        return True

    async def douyin_get_access_token(self):
        """DouYin 获取TOKEN"""
        if not LIVE_SERVER:
            # return self.answer(self.sta_code.FAIL, hint="非正式环境不获取抖音token")
            return "08011218474439544a56377756473068485058586d6978554d673d3d"
        errcode, access_token = await DouYin.douyin_get_access_token()
        self.info_log("DouYin 获取TOKEN结果：", errcode)
        if errcode:
            data = {"errcode": int(errcode), "errmsg": access_token}
            return self.answer(self.sta_code.EXTERNAL_ERR, data)
        return access_token

    async def wechat_get_access_token(self, app_id=WeChatConf.WE_CHAT_MG_APP_ID,
                                      app_secret=WeChatConf.WE_CHAT_MG_APP_SECRET):
        """WeChat 获取TOKEN"""
        errcode, access_token = await WeChat.wechat_get_access_token_stable(app_id=app_id, app_secret=app_secret)
        self.info_log("WeChat 获取TOKEN结果：", errcode)
        if errcode:
            data = {"errcode": int(errcode), "errmsg": access_token}
            return self.answer(self.sta_code.EXTERNAL_ERR, data)
        return access_token

    def wechat_check_signature(self, req: Request, push_token=WeChatConf.WE_CHAT_MG_PUSH_TOKEN):
        """微信验签"""
        signature = req.args.get("signature") or ""
        timestamp = req.args.get("timestamp") or ""
        nonce = req.args.get("nonce") or ""

        tmp_arr = [push_token, timestamp, nonce]
        tmp_arr.sort()  # 默认是按照字符串排序，类似于PHP的SORT_STRING
        tmp_str = ''.join(tmp_arr)  # 使用join函数代替implode
        tmp_str = UtilsTool.calc_hash(tmp_str, htype="sha1")
        self.info_log("wechat_check_signature 微信验签", signature, '=?=', tmp_str)
        if tmp_str != signature:
            return response.json({"ErrCode": self.sta_code.ERR_AUTH, "ErrMsg": "验签失败"})

    async def wechat_decode_data(self, req: Request, push_token=WeChatConf.WE_CHAT_MG_PUSH_TOKEN,
                                 aes_key=WeChatConf.WE_CHAT_MG_AES_KEY, app_id=WeChatConf.WE_CHAT_MG_APP_ID):
        """微信密文、数据格式等解析"""
        decrypt_tool = WXBizMsgCrypt(push_token, aes_key, app_id)

        msg_signature = req.args.get("msg_signature")
        timestamp = req.args.get("timestamp")
        nonce = req.args.get("nonce")
        decrypt_res, decrypt_json = decrypt_tool.DecryptMsg(req.json, msg_signature, timestamp, nonce)
        decrypt_data = json_parse(decrypt_json)
        self.info_log("wechat_decode_data 密文解析：", decrypt_res, decrypt_data)
        if decrypt_res != 0:
            return response.json({"ErrCode": self.sta_code.ERR_AUTH, "ErrMsg": "密文消息解密失败"})

        return decrypt_data

    def rep_balance(self, balance):
        one_of_model = get_one_of_model()
        one_of_model.balance = balance
        return self.answer(self.sta_code.PASS, data=one_of_model)

    def rep_express(self, goods, gifts):
        express = goods + (gifts if gifts else [])
        return self.answer(self.sta_code.PASS, data=express)


class MakeOrder(BaseSomePay):
    """ 通用创建订单 """

    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        trade_item = self.check_int(req.json.get("trade_item"), require=True, minval=2000, maxval=4000,
                                    p_name="trade_item")
        pay_mode = req.json.get("pay_mode")
        platform = req.args.get('c_platform') or ''
        count = req.json.get("count") or 1

        order_info, hint = await self.create_order(uid, trade_item, pay_mode, platform, req, count=count)
        if order_info:
            return self.answer(data=order_info)
        return self.answer(self.sta_code.FAIL, hint=hint)

    @classmethod
    async def create_order(cls, uid, trade_item, pay_mode, platform, req: Request, count=1):
        if not (trade_item and 2000 <= trade_item <= 4000):
            return {}, "缺少商品ID或商品ID超出范围！"

        pm_enum = PayMode.find_member_by_val(pay_mode)
        if not pm_enum:
            return {}, "不支持的支付方式"

        platform_val = PlatForm.get_val_by_phrase(platform)
        if platform_val is None:
            return {}, "不支持的移动平台"

        # 1.验货
        express, item_num, _, randed, desc = await cls.verify_goods(uid, trade_item)
        if not express:
            return {}, desc

        extra_info = {}
        if randed:
            extra_info["rand_type"] = express.get("rand_type") or 0

        # 2.创建订单，插入订单表
        data = {
            "uid": uid,
            "orig_price": express.get("orig_price") or 0,
            "trade_item": trade_item,
            "trade_item_count": count,
            "trade_amount": express.get("price") or 0,
            "order_desc": pm_enum.phrase,
            "pay_type": express.get("pay_type") or 0,
            "pay_mode": pm_enum.val,
            "client_ip": cls.ori_ip(req),
            "order_source": platform_val,
            "extra_info": json_encode(extra_info) if extra_info else extra_info,
        }
        insert_data = await RecordsTradeOrder.gen_insert_data(**data)
        record_trade = await RecordsTradeOrder.add_one(insert_data)
        if not record_trade:
            cls.error_log(uid, "MakeOrder 订单表插入失败", insert_data)
            return {}, "订单创建失败"

        # 3.订单创建完成，按下单平台返回数据
        map_func = {
            PayMode.WECHAT_MINI_GAME.val: cls.deal_order_general,
            PayMode.ALIPAY_MINI_GAME.val: cls.deal_order_general,
            PayMode.DOUYIN_MINI_GAME.val: cls.deal_order_general,
            PayMode.IOS_TO_H5.val: cls.deal_order_general
        }
        deal_func = map_func.get(pay_mode)
        if deal_func and callable(deal_func):
            order_info = await deal_func(uid, insert_data)
            cls.info_log(uid, f"MakeOrder {pm_enum.phrase} 订单创建结果", order_info)
            return order_info, "ok"
        return {}, "无此交易方式"

    @classmethod
    async def deal_order_wechat_goods(cls, uid, insert_data):
        """微信道具直购"""
        extra_info = insert_data.get("extra_info")
        extra_info = json_parse(extra_info) if extra_info else {}
        params = await WeChat.wechat_mini_game_return_order(uid, insert_data.get("trade_amount"),
                                                            insert_data.get("order_id"),
                                                            extra_info.get("product_id")
                                                            )
        if not params:
            return
        return_data = {
            "order_id": insert_data.get("order_id"),
            "trade_time": insert_data.get("trade_time"),
            "trade_amount": insert_data.get("trade_amount"),
            "param": json_encode(params)
        }
        return return_data

    @classmethod
    async def deal_order_general(cls, _, insert_data):
        """通用订单处理"""
        return_data = {
            "order_id": insert_data.get("order_id"),
            "trade_time": insert_data.get("trade_time"),
            "trade_amount": insert_data.get("trade_amount")
        }
        return return_data


class ReduceBalanceByWechatMiniProgram(BaseSomePay):
    """
    微信扣减游戏币 pay_v2.pay（客户端自用）
    参考连接：https://developers.weixin.qq.com/minigame/dev/api-backend/midas-payment-v2/pay_v2.pay.html
    """

    async def post(self, req: Request, **kwargs):
        trade_item = self.check_int(
            req.json.get("trade_item"), require=True, minval=2000, maxval=4000, p_name="trade_item")
        order_id = self.check_str(req.json.get("order_id"), require=True, p_name="order_id")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        open_id = u_info.get("openid")
        u_ip = u_info.get("ip")

        # 1.查询订单
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
        if not order_info:
            self.error_log(uid, "ReduceBalanceByWechatMiniProgram 无此订单", order_id)
            self.answer(self.sta_code.ORDER_NOT_FOUND, hint="无此订单")
        trade_amount = order_info.get("trade_amount") or 0

        # 2.扣减游戏币/更新支付状态
        if order_info.get("order_status") != OrderStatus.PAID:
            access_token = await self.wechat_get_access_token()
            await self.wechat_game_coin_pay(uid, open_id, order_id, trade_amount, access_token, u_ip)

            update_paid = {"order_status": OrderStatus.PAID}
            await RecordsTradeOrder.update_by_pk(order_id, update_paid, order_info)

        # 3.查询货物 goods立得货物 / gifts赠物
        express, item_num, buy_record, _, desc = await self.verify_goods(uid, trade_item)
        if not express:
            self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint=desc)
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 4.发货
        if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
            update_deliver = {
                "deliver_status": DeliverStatus.SHIPPED,
                "finish_time": tool_dt.cur_time()
            }
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(order_id, update_deliver, order_info)
                    await UpAssets.update_assets(uid, goods, gifts)
                    if item_num == 3:
                        await UserActivityRC.update_user_charge_records(uid, express)
            except Exception as e:
                self.error_log(f"事务执行失败，原因：{e}")
                self.answer(self.sta_code.FAIL, hint="支付宝代币支付订单发货失败")

            # 7.发货后处理
            await self.process_after_deliver(uid, trade_amount)
        else:
            self.info_log(uid, "ReduceBalanceByWechatMiniProgram 已经发货了", order_id)

        await self.process_after_received(uid, order_info, buy_record=buy_record)
        self.info_log(uid, "ReduceBalanceByWechatMiniProgram 订单交易成功", order_id)
        return self.rep_express(goods, gifts)


class GetBalanceByWechatMiniProgram(BaseSomePay):
    """
    微信查询游戏币 pay_v2.getBalance
    参考连接：https://developers.weixin.qq.com/minigame/dev/api-backend/midas-payment-v2/pay_v2.getBalance.html
    """

    async def get(self, _: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        openid = u_info.get("openid")
        u_ip = u_info.get("ip")

        access_token = await self.wechat_get_access_token()
        errcode, req_data = await WeChat.wechat_mini_game_coin_query(uid, openid, access_token, u_ip)
        if errcode != 0:
            self.info_log(uid, "失败查询Wechat游戏币余额：", errcode, req_data)
            data = {"errcode": int(errcode), "errmsg": req_data}
            self.answer(self.sta_code.EXTERNAL_ERR, data, hint=req_data)
        else:
            balance = req_data.get("balance") or 0
            self.info_log(uid, "成功查询Wechat游戏币余额：", errcode, req_data)
            return self.rep_balance(balance)


class MiniGameQueryOrder(BaseSomePay):
    """
    微信MG订单查询 pay_v2.queryOrder
    参考文档：https://docs.qq.com/doc/DVFBybVlRWHVhRmZj?code=TxnmQLUsjkiErEunFwGJ5CoekYpT1ZPe7Tn5Seqgi5I&state=weworklogin&u=4187683d01314903b57f8cf4bb93aa63
    """

    async def post(self, req: Request, **kwargs):
        trade_item = self.check_int(
            req.json.get("trade_item"), require=True, minval=2000, maxval=4000, p_name="trade_item")
        order_id = self.check_str(req.json.get("order_id"), require=True, p_name="order_id")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        open_id = u_info.get("openid")
        u_ip = u_info.get("ip")

        # 1.查询本地订单
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
        if not order_info:
            self.error_log(uid, "MiniGameQueryOrder 无此订单", order_id)
            self.answer(self.sta_code.ORDER_NOT_FOUND, hint="无此订单")
        trade_amount = order_info.get("trade_amount") or 0
        self.info_log(datetime.now().strftime("%Y年%m月%d日%H时%M分%S秒"), f"主动查询，本地结果 {order_info}")

        # 2.查询微信小游戏订单
        access_token = await self.wechat_get_access_token()
        errcode, req_data = await WeChat.wechat_mini_game_query_order(uid, open_id, access_token, order_id)
        self.info_log(uid, "MiniGameQueryOrder 解析查询数据：", req_data, errcode)
        if errcode:
            data = {"errcode": errcode, "errmsg": req_data}
            self.answer(self.sta_code.EXTERNAL_ERR, data, hint=req_data)

        if req_data.get("pay_state") != OrderStatus.PAID:  # 支付状态（用户是否已支付）1 未支付 2 已支付
            self.info_log(uid, "MiniGameQueryOrder 订单未支付", order_id)
            self.answer(self.sta_code.FAIL, hint="订单未支付")

        # 3.更新订单
        if order_info.get("order_status") != OrderStatus.PAID:
            await self.wechat_game_coin_pay(uid, open_id, order_id, trade_amount, access_token, u_ip)

            update_paid = {"order_status": OrderStatus.PAID}
            await RecordsTradeOrder.update_by_pk(order_id, update_paid, order_info)

        # 4.查询货物 goods立得货物 / gifts赠物
        express, item_num, buy_record, _, desc = await self.verify_goods(uid, trade_item)
        if not express:
            self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint=desc)
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 5.发货
        if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
            update_deliver = {
                "deliver_status": DeliverStatus.SHIPPED,
                "finish_time": tool_dt.cur_time(),
            }
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(order_id, update_deliver, order_info)
                    await UpAssets.update_assets(uid, goods, gifts)
                    if item_num == 3:
                        await UserActivityRC.update_user_charge_records(uid, express)
            except Exception as e:
                self.error_log(f"事务执行失败，原因：{e}")
                self.answer(self.sta_code.FAIL, hint="微信订单查询发货失败")

            # 6.发货后处理
            await self.process_after_deliver(uid, trade_amount)
        else:
            self.info_log(uid, "MiniGameQueryOrder 已经发货了", order_id)

        await self.process_after_received(uid, order_info, buy_record=buy_record)
        self.info_log(uid, "MiniGameQueryOrder 订单交易成功", order_id)
        return self.rep_express(goods, gifts)


class MiniGameRecvPush(BaseSomePay):
    """
    微信MG支付回调通知
    参考文档：https://docs.qq.com/doc/DR1hhWlpnQXJXWHRh
    """
    decorators = []

    async def get(self, req: Request):
        """测试用"""
        self.wechat_check_signature(req)
        _ = await self.wechat_decode_data(req)
        self.info_log("MiniGameRecvPush 消息推送解密测试：", req.args)
        return response.text(body=req.args.get("echostr"))

    async def post(self, req: Request):
        """
        “道具直购”和“商店道具”、“代币支付”等的发货推送是用post推送
        """
        self.wechat_check_signature(req)
        decrypt_data = await self.wechat_decode_data(req)
        payload_data = json_parse(decrypt_data.get("MiniGame", {}).get("Payload"))

        out_trade_no = payload_data.get("OutTradeNo")  # 拿到订单号
        to_openid = payload_data.get("OpenId")  # 收货的玩家openid(发给谁)
        if len(out_trade_no) + len(to_openid) <= 40:  # 测试通过性
            return response.json({"ErrCode": 0, "ErrMsg": "Success"})

        # 3.查询用户信息
        u_info = await BaseUserRC.cache_by_unique({"openid": to_openid, "platform": PlatForm.WECHAT_MINI_GAME},
                                                  BaseUserRC.KEY_OPENID)
        if not u_info:
            self.error_log("MiniGameRecvPush 找不到对应下单用户", out_trade_no)
            return response.json({"ErrCode": self.sta_code.ERR_ARG, "ErrMsg": "找不到对应下单用户"})
        uid = u_info.get("uid")
        u_ip = u_info.get("ip")

        # 4.查询本地订单信息
        order_info = await RecordsTradeOrder.query_trade_order(order_id=out_trade_no)
        self.info_log(datetime.now().strftime("%Y年%m月%d日%H时%M分%S秒"), f"回调通知，本地结果 {order_info}")
        if not order_info:
            self.error_log(uid, "MiniGameRecvPush 无此订单", out_trade_no)
            return response.json({"ErrCode": self.sta_code.ORDER_NOT_FOUND, "ErrMsg": "无此订单"})

        # 重复查询，避免订单更新不及时
        if order_info.get("order_status") != OrderStatus.PAID:
            await asyncio.sleep(1)
            order_info = await RecordsTradeOrder.query_trade_order(order_id=out_trade_no)
            self.info_log(tool_dt.cur_time(), f"MiniGameRecvPush 延迟1秒开始重复查询，本地结果 {order_info}")
        trade_item = order_info.get("trade_item")
        trade_amount = order_info.get("trade_amount") or 0

        # 5.更新订单
        if order_info.get("order_status") != OrderStatus.PAID:
            access_token = await self.wechat_get_access_token()
            await self.wechat_game_coin_pay(uid, to_openid, out_trade_no, trade_amount, access_token, u_ip)

            update_paid = {"order_status": OrderStatus.PAID}
            await RecordsTradeOrder.update_by_pk(out_trade_no, update_paid, order_info)

        if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
            # 6.发货、查询货物 goods立得货物 / gifts赠物
            express, item_num, _, __, desc = await self.verify_goods(uid, trade_item)
            if not express:
                return response.json({"ErrCode": self.sta_code.GOODS_NOT_FOUND, "ErrMsg": desc})
            goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

            update_deliver = {
                "deliver_status": DeliverStatus.SHIPPED,
                "finish_time": tool_dt.cur_time()
            }
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(out_trade_no, update_deliver, order_info)
                    await UpAssets.update_assets(uid, goods, gifts)
                    if item_num == 3:
                        await UserActivityRC.update_user_charge_records(uid, express)
            except Exception as e:
                self.error_log(f"事务执行失败，原因：{e}")
                return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": "发货事务失败"})

            # 7.发货后处理
            await self.process_after_deliver(uid, trade_amount)
        else:
            self.info_log(uid, "MiniGameRecvPush 已经发货了", out_trade_no)
            return response.json({"ErrCode": 0, "ErrMsg": "Success"})

        self.info_log(uid, "MiniGameRecvPush 订单交易成功", out_trade_no)
        return response.json({"ErrCode": 0, "ErrMsg": "Success"})


class GetBalanceByAliMiniProgram(BaseSomePay):
    """ 支付宝查询游戏币 """

    async def get(self, _, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")
        open_id = user.get("openid")

        results, req_data = await Alipay.ali_mini_game_coin_query(open_id)
        if not results:
            balance = 0
            self.info_log(uid, "失败查询Ali游戏币余额：", req_data)
        else:
            data = json_parse(req_data)
            balance = data.get("balance")
            self.info_log(uid, "成功查询Ali游戏币余额：", data)

        return self.rep_balance(balance)


class ReduceBalanceByAliMiniProgram(BaseSomePay):
    """ 支付宝扣减游戏币（客户端自用） """

    async def post(self, req: Request, **kwargs):
        trade_item = self.check_int(
            req.json.get("trade_item"), require=True, minval=2000, maxval=4000, p_name="trade_item")
        order_id = self.check_str(req.json.get("order_id"), require=True, p_name="order_id")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        open_id = u_info.get("openid")

        # 1.查询本地订单
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
        if not order_info:
            self.error_log(uid, "ReduceBalanceByAliMiniProgram 无此订单", order_id)
            self.answer(self.sta_code.ORDER_NOT_FOUND, hint="无此订单")
        trade_amount = order_info.get("trade_amount") or 0

        # 2.查询货物 goods立得货物 / gifts赠物
        express, item_num, buy_record, _, desc = await self.verify_goods(uid, trade_item)
        if not express:
            self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint=desc)
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 3.扣减游戏币/更新支付状态
        if order_info.get("order_status") != OrderStatus.PAID:
            trade_name = express.get("store_name") or express.get("act_name") or f"商品{trade_item}"
            await self.alipay_game_coin_pay(open_id, order_id, trade_amount, trade_name,
                                            express.get("desc", trade_name))
            update_paid = {"order_status": OrderStatus.PAID}
            await RecordsTradeOrder.update_by_pk(order_id, update_paid, order_info)

        # 4.发货
        if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
            update_deliver = {
                "deliver_status": DeliverStatus.SHIPPED,
                "finish_time": tool_dt.cur_time()
            }
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(order_id, update_deliver, order_info)
                    await UpAssets.update_assets(uid, goods, gifts)
                    if item_num == 3:
                        await UserActivityRC.update_user_charge_records(uid, express)
            except Exception as e:
                self.error_log(f"事务执行失败，原因：{e}")
                self.answer(self.sta_code.FAIL, hint="支付宝代币支付订单发货失败")

            # 5.发货后处理
            await self.process_after_deliver(uid, trade_amount)
        else:
            self.info_log(uid, "ReduceBalanceByAliMiniProgram 已经发货了", order_id)

        await self.process_after_received(uid, order_info, buy_record=buy_record)
        self.info_log(uid, "ReduceBalanceByAliMiniProgram 订单交易成功", order_id)
        return self.rep_express(goods, gifts)


class AliPayQueryStatus(BaseSomePay):
    """
    支付宝MG订单查询
    参考文档：https://opendocs.alipay.com/apis/085anm
    """

    async def post(self, req: Request, **kwargs):
        trade_item = self.check_int(
            req.json.get("trade_item"), require=True, minval=2000, maxval=4000, p_name="trade_item")
        order_id = self.check_str(req.json.get("order_id"), require=True, p_name="order_id")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        open_id = u_info.get("openid")

        # 1.查询本地订单
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
        if not order_info:
            self.error_log(uid, "AliPayQueryStatus 无此订单", order_id)
            self.answer(self.sta_code.ORDER_NOT_FOUND, hint="无此订单")
        trade_amount = order_info.get("trade_amount") or 0

        # 2.查询阿里订单
        results, req_data = await Alipay.ali_order_query_status(open_id, order_id)
        self.info_log(uid, "AliPayQueryStatus 解析查询数据：", results, req_data)
        if not results:
            data = {"errcode": int(req_data.get('code')), "errmsg": req_data.get('sub_msg')}
            self.answer(self.sta_code.EXTERNAL_ERR, data)

        if req_data.get("status") != 'success':  # 支付状态 成功: success / 关闭: closed / 已退款: refunded / 中间状态: processing
            self.info_log(uid, "AliPayQueryStatus 订单未支付", order_id)
            self.answer(self.sta_code.FAIL, hint="订单未支付")

        # 3.查询货物 goods立得货物 / gifts赠物
        express, item_num, buy_record, _, desc = await self.verify_goods(uid, trade_item)
        if not express:
            self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint=desc)
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 4.扣减游戏币/更新支付状态
        if order_info.get("order_status") != OrderStatus.PAID:
            trade_name = express.get("store_name") or express.get("act_name") or f"商品{trade_item}"
            await self.alipay_game_coin_pay(open_id, order_id, trade_amount, trade_name,
                                            express.get("desc", trade_name))
            update_paid = {"order_status": OrderStatus.PAID}
            await RecordsTradeOrder.update_by_pk(order_id, update_paid, order_info)

        # 5.发货
        if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
            update_deliver = {
                "deliver_status": DeliverStatus.SHIPPED,
                "finish_time": tool_dt.cur_time(),
            }
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(order_id, update_deliver, order_info)
                    await UpAssets.update_assets(uid, goods, gifts)
                    if item_num == 3:
                        await UserActivityRC.update_user_charge_records(uid, express)
            except Exception as e:
                self.error_log(f"事务执行失败，原因：{e}")
                self.answer(self.sta_code.FAIL, hint="支付宝订单查询发货失败")

            # 6.发货后处理
            await self.process_after_deliver(uid, trade_amount)
        else:
            self.info_log(uid, "AliPayQueryStatus 已经发货了", order_id)

        await self.process_after_received(uid, order_info, buy_record=buy_record)
        self.info_log(uid, "AliPayQueryStatus 订单交易成功", order_id)
        return self.rep_express(goods, gifts)


class AliPayNotify(BaseSomePay):
    """
    支付宝MG支付回调通知
    https://linksprod.alipay.com/custom/snippet/667d196509e1a00457c0b3c8/latest/?type=new
    spi.alipay.user.gamecenter.payment.notify(支付宝游戏币充值成功状态通知)
    参考文档：https://opendocs.alipay.com/common/02km9j
    """
    decorators = []

    def __check_signature_old(self, req: Request) -> bool:
        """ 验证签名 """
        signature = req.args.pop("sign", ""),
        req.args.pop("sign_type", "")
        verify_tuple = []
        # query
        for key in req.args.keys():
            verify_tuple.append((key, req.args.get(key)))

        # body
        for key in req.form.keys():
            verify_tuple.append((key, req.form.get(key)))

        # header
        for key in req.headers.keys():
            verify_tuple.append((key, req.headers.get(key)))

        verify_tuple.sort(key=lambda x: x[0])
        verify_list = [f"{data[0]}={data[1]}" for data in verify_tuple]
        wait_verify_str = "&".join(verify_list).encode("utf-8")
        try:
            flag = Alipay.verify_with_rsa(wait_verify_str, signature)
            return flag
        except Exception as e:
            self.error_log("支付回调验签失败: ", e)
            return False

    def __check_signature(self, req: Request, signature):
        # 参考地址：https://blog.csdn.net/qq_27169365/article/details/140161688
        content = ''
        req_params = req.args

        req_params.pop('sign')
        req_params.pop('sign_type')  # 去除sign、sigh_type
        new_list = sorted(req_params, reverse=False)  # 待验签参数进行排序
        for i in new_list:
            p = i + '=' + req_params.get(i) + '&'
            content += p
        sorted_params = content.strip('&')

        # 转换成字节串
        message = bytes(sorted_params, encoding='utf-8')
        try:
            flag = Alipay.verify_with_rsa(message, signature)
            self.info_log("支付回调验签结果: ", flag)
            return flag
        except Exception as e:
            self.error_log("支付回调验签失败: ", e)

            # todo:返回TRUE观测修改之后的验签结果
            return True

    async def post(self, req: Request):
        # 1.验证通知的真伪，没问题后修改订单状态
        signature = req.json.get("sign", "")
        flag = self.__check_signature(req, signature)
        if not flag:
            return response.json({"response": {"code": '40004', "msg": 'Business Failed'}, "sign": signature})

        data = req.form
        to_openid = data.get("open_id")
        custom_id = data.get("custom_id")  # 下单时传入的订单号
        self.info_log("AliPayNotify req form: ", data, "u_info: ", to_openid)

        # 2.验证买家和查询本地订单
        u_info = await BaseUserRC.cache_by_unique({"openid": to_openid, "platform": PlatForm.ALI_MINI_GAME},
                                                  BaseUserRC.KEY_OPENID)
        if not u_info:
            self.error_log("AliPayNotify 找不到对应下单用户", to_openid)
            return response.json({"response": {"code": '40004', "msg": 'Business Failed'}, "sign": signature})
        uid = u_info.get("uid")

        order_info = await RecordsTradeOrder.query_trade_order(order_id=custom_id)
        if not order_info:
            self.error_log(uid, "AliPayNotify 无此订单", custom_id)
            return response.json({"response": {"code": '40004', "msg": 'Business Failed'}, "sign": signature})
        order_id = order_info.get("order_id")
        trade_item = order_info.get("trade_item")
        trade_amount = order_info.get("trade_amount") or 0

        # 4.查询阿里订单
        results, req_data = await Alipay.ali_order_query_status(custom_id, order_id)
        self.info_log(uid, "AliPayNotify 解析查询数据：", results, req_data)
        if not results:
            return response.json({"response": {"code": '40004', "msg": 'Business Failed'}, "sign": signature})

        query_data = json_parse(req_data)
        if query_data.get("status") != 'success':  # 支付状态 成功: success / 关闭: closed / 已退款: refunded / 中间状态: processing
            return response.json({"response": {"code": '40004', "msg": 'Business Failed'}, "sign": signature})

        # 4.查询货物 goods立得货物 / gifts赠物
        express, item_num, _, __, desc = await self.verify_goods(uid, trade_item)
        if not express:
            return response.json({"response": {"code": '40004', "msg": 'Business Failed'}, "sign": signature})
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 5.扣减游戏币/更新支付状态
        if order_info.get("order_status") != OrderStatus.PAID:
            trade_name = express.get("store_name") or express.get("act_name") or f"商品{trade_item}"
            await self.alipay_game_coin_pay(to_openid, custom_id, trade_amount, trade_name,
                                            express.get("desc", trade_name))
            update_paid = {"order_status": OrderStatus.PAID}
            await RecordsTradeOrder.update_by_pk(custom_id, update_paid, order_info)

        # 6.发货
        if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
            update_deliver = {
                "deliver_status": DeliverStatus.SHIPPED,
                "finish_time": tool_dt.cur_time(),
            }
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(custom_id, update_deliver, order_info)
                    await UpAssets.update_assets(uid, goods, gifts)
                    if item_num == 3:
                        await UserActivityRC.update_user_charge_records(uid, express)
            except Exception as e:
                self.error_log(f"事务执行失败，原因：{e}")
                return response.json(
                    {"response": {"code": self.sta_code.FAIL, "msg": '发货事务失败'}, "sign": signature})

            # 7.发货后处理
            await self.process_after_deliver(uid, trade_amount)
        else:
            self.info_log(uid, "AliPayNotify 已经发货了", custom_id)
            return response.json({"response": {"code": '10000', "msg": 'Success'}, "sign": signature})

        self.info_log(uid, "AliPayNotify 订单交易成功", custom_id)
        return response.json({"response": {"code": '10000', "msg": 'Success'}, "sign": signature})


class AliPayRefund(BaseSomePay):
    """
    支付宝MG充值退款（开发者自用）
    参考文档：https://opendocs.alipay.com/mini-game/6fc63327_alipay.user.gamecenter.payment.refund?pathHash=91f535af
    """

    async def post(self, req: Request, **kwargs):
        trade_no = self.check_str(req.json.get("trade_no"), require=True, p_name="trade_no")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        open_id = u_info.get("openid")

        results, req_data = await Alipay.ali_payment_refund(open_id, trade_no)
        self.info_log(uid, "AliPayRefund 解析请求数据：", results, req_data)
        if not results:
            data = {"errcode": int(req_data.get('code')), "errmsg": req_data.get('sub_msg')}
            self.answer(self.sta_code.EXTERNAL_ERR, data, hint=req_data)

        self.answer(hint="申请退款成功，平台正在处理")


class GetBalanceByDouYinGame(BaseSomePay):
    """ 抖音查询游戏币 """

    async def get(self, _, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        open_id = u_info.get("openid")

        access_token = await self.douyin_get_access_token()
        errcode, req_data = await DouYin.douyin_mini_game_coin_query(open_id, access_token)
        if errcode:
            balance = 0
            self.info_log(uid, "失败查询DouYin游戏币余额：", errcode, req_data)
        else:
            balance = req_data.get("balance") or 0  # 用户游戏币余额，单位个，整数
            self.info_log(uid, "成功查询DouYin游戏币余额：", errcode, req_data)

        return self.rep_balance(balance)


class ReduceBalanceByDouYinGame(BaseSomePay):
    """ 抖音扣减游戏币（客户端自用） """

    async def post(self, req: Request, **kwargs):
        trade_item = self.check_int(
            req.json.get("trade_item"), require=True, minval=2000, maxval=4000, p_name="trade_item")
        order_id = self.check_str(req.json.get("order_id"), require=True, p_name="order_id")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        open_id = u_info.get("openid")

        # 1.查询本地订单
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
        if not order_info:
            self.error_log(uid, "ReduceBalanceByDouYinGame 无此订单", order_id)
            self.answer(self.sta_code.ORDER_NOT_FOUND, hint="无此订单")
        trade_amount = order_info.get("trade_amount") or 0

        # 2.扣减游戏币/更新支付状态
        if order_info.get("order_status") != OrderStatus.PAID:
            access_token = await self.douyin_get_access_token()
            await self.douyin_game_coin_pay(open_id, order_id, trade_amount, access_token)

            update_paid = {"order_status": OrderStatus.PAID}
            await RecordsTradeOrder.update_by_pk(order_id, update_paid, order_info)

        # 3.查询货物 goods立得货物 / gifts赠物
        express, item_num, buy_record, _, desc = await self.verify_goods(uid, trade_item)
        if not express:
            self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint=desc)
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 4.发货
        if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
            update_deliver = {
                "deliver_status": DeliverStatus.SHIPPED,
                "finish_time": tool_dt.cur_time()
            }
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(order_id, update_deliver, order_info)
                    await UpAssets.update_assets(uid, goods, gifts)
                    if item_num == 3:
                        await UserActivityRC.update_user_charge_records(uid, express)
            except Exception as e:
                self.error_log(f"事务执行失败，原因：{e}")
                self.answer(self.sta_code.FAIL, hint="支付宝代币支付订单发货失败")

            # 5.发货后处理
            await self.process_after_deliver(uid, trade_amount)
        else:
            self.info_log(uid, "ReduceBalanceByDouYinGame 已经发货了", order_id)

        await self.process_after_received(uid, order_info, buy_record=buy_record)
        self.info_log(uid, "ReduceBalanceByDouYinGame 订单交易成功", order_id)
        return self.rep_express(goods, gifts)


class DouYinGamePayNotify(BaseSomePay):
    """
    抖音MG支付回调通知
    参考文档：https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/api/payment/payment-server-callback
    """
    decorators = []

    def __check_signature(self, req: Request):
        """ 检查签名 """
        # 1.timestamp、nonce、msg、echostr 是验证请求的 body 里面的参数
        signature = req.json.get("signature") or ""
        timestamp = req.json.get("timestamp") or ""
        nonce = req.json.get("nonce") or ""
        msg = req.json.get("msg") or ""
        token = DouYinConf.DOUYIN_NOTIFY_TOKEN

        # 2.将 token，timestamp，nonce，msg 四个参数进行拼接，然后按照字符串自然大小进行排序，使用 SHA1 算法得到 sign_str
        sorted_str = [token, timestamp, nonce, msg]
        sorted_str.sort()
        join_str = ''.join(sorted_str)
        sign_str = UtilsTool.calc_hash(join_str, htype="sha1")

        self.info_log(f"DouYinGamePayNotify: {req.json}")
        if sign_str != signature:
            self.error_log("DouYin 小游戏支付回调通知验签失败", sign_str, signature)
            return False
        return True

    async def get(self, req: Request):
        """ 测试用 """
        return response.text(body=req.args.get("echostr"))

    async def post(self, req: Request):
        """ 订单成功支付之后(支付失败不会收到回调)，服务端会通过POST方式回调 """
        res = self.__check_signature(req)
        if not res:
            return response.json({"ErrCode": self.sta_code.ERR_AUTH, "ErrMsg": "验签失败"})

        msg = req.json.get("msg") or ""  # 订单详细信息
        msg = json_parse(msg)
        cp_orderno = msg.get("cp_orderno")

        # 1.查询订单状态（查无订单直接返成功，为了防止来自测试服订单的回调，仅回调使用此逻辑）
        order_info = await RecordsTradeOrder.query_trade_order(order_id=cp_orderno)
        if not order_info:
            self.error_log("DouYinGamePayNotify 无此订单", cp_orderno)
            return response.json({"ErrCode": self.sta_code.PASS, "ErrMsg": "Success"})
            # return response.json({"ErrCode": self.sta_code.ORDER_NOT_FOUND, "ErrMsg": "无此订单"})

        uid = order_info.get("uid")
        trade_item = order_info.get("trade_item")
        trade_amount = order_info.get("trade_amount") or 0

        # 2.验证买家
        u_info = await BaseUserRC.cache_by_uid(uid)
        if not u_info:
            self.error_log("DouYinGamePayNotify 找不到对应下单用户", cp_orderno)
            return response.json({"ErrCode": self.sta_code.ERR_ARG, "ErrMsg": "找不到对应下单用户"})

        # 3.扣减游戏币/更新支付状态
        if order_info.get("order_status") != OrderStatus.PAID:
            access_token = await self.douyin_get_access_token()
            await self.douyin_game_coin_pay(u_info.get("openid"), cp_orderno, trade_amount, access_token)

            update_paid = {"order_status": OrderStatus.PAID}
            await RecordsTradeOrder.update_by_pk(cp_orderno, update_paid, order_info)

        if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
            # 4.查询货物 goods立得货物 / gifts赠物
            express, item_num, _, __, desc = await self.verify_goods(uid, trade_item)
            if not express:
                return response.json({"ErrCode": self.sta_code.GOODS_NOT_FOUND, "ErrMsg": desc})
            goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

            # 5.发货
            update_deliver = {
                "deliver_status": DeliverStatus.SHIPPED,
                "finish_time": tool_dt.cur_time(),
            }
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(cp_orderno, update_deliver, order_info)
                    await UpAssets.update_assets(uid, goods, gifts)
                    if item_num == 3:
                        await UserActivityRC.update_user_charge_records(uid, express)
            except Exception as e:
                self.error_log(f"事务执行失败，原因：{e}")
                return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": "发货事务失败"})

            # 6.发货后处理
            await self.process_after_deliver(uid, trade_amount)
        else:
            self.info_log(uid, "DouYinGamePayNotify 已经发货了", cp_orderno)
            return response.json({"ErrCode": self.sta_code.PASS, "ErrMsg": "Success"})

        self.info_log(uid, "DouYinGamePayNotify 订单交易成功", cp_orderno)
        return response.json({"ErrCode": self.sta_code.PASS, "ErrMsg": "Success"})


class DouYinGameQueryOrder(BaseSomePay):
    """
    抖音MG订单查询
    参考文档：https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/api/payment/payment-server-callback?#querypaystate
    """

    async def post(self, req: Request, **kwargs):
        order_id = self.check_str(req.json.get("order_id"), require=True, p_name="order_id")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 1.查询本地订单
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
        if not order_info:
            self.error_log(uid, "DouYinGameQueryOrder 无此订单", order_id)
            self.answer(self.sta_code.ORDER_NOT_FOUND, hint="无此订单")

        open_id = u_info.get("openid")
        trade_item = order_info.get("trade_item")
        trade_amount = order_info.get("trade_amount") or 0

        # 2.抖音小游戏订单查询
        access_token = await self.douyin_get_access_token()
        errcode, req_data = await DouYin.douyin_query_pay_status(access_token, order_id)
        self.info_log(uid, "DouYinGameQueryOrder 解析查询数据：", errcode, req_data)
        if errcode:
            data = {"errcode": int(errcode), "errmsg": req_data}
            self.answer(self.sta_code.EXTERNAL_ERR, data, hint=req_data)

        if req_data.get("status") != "success":  # success 表示支付成功且发币到账，unsuccess 表示支付失败或支付成功未发币到账
            self.info_log(uid, "DouYinGameQueryOrder 支付失败或支付成功未发币到账", order_id)
            self.answer(self.sta_code.FAIL, hint="支付失败或支付成功未发币到账")

        # 3.扣减游戏币/更新支付状态
        if order_info.get("order_status") != OrderStatus.PAID:
            await self.douyin_game_coin_pay(open_id, order_id, trade_amount, access_token)
            update_paid = {"order_status": OrderStatus.PAID}
            await RecordsTradeOrder.update_by_pk(order_id, update_paid, order_info)

        # 4.查询货物 goods立得货物 / gifts赠物
        express, item_num, buy_record, _, desc = await self.verify_goods(uid, trade_item)
        if not express:
            self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint=desc)
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 5.发货
        if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
            update_deliver = {
                "deliver_status": DeliverStatus.SHIPPED,
                "finish_time": tool_dt.cur_time(),
            }
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(order_id, update_deliver, order_info)
                    await UpAssets.update_assets(uid, goods, gifts)
                    if item_num == 3:
                        await UserActivityRC.update_user_charge_records(uid, express)
            except Exception as e:
                self.error_log(f"事务执行失败，原因：{e}")
                self.answer(self.sta_code.FAIL, hint="抖音订单查询发货失败")

            # 6.发货后处理
            await self.process_after_deliver(uid, trade_amount)
        else:
            self.info_log(uid, "DouYinGameQueryOrder 已经发货了", order_id)

        await self.process_after_received(uid, order_info, buy_record=buy_record)

        call_admin = kwargs.get("call_admin") or False
        self.info_log(uid, "DouYinGameQueryOrder 订单交易成功1", order_id, call_admin)
        if call_admin:
            self.info_log(uid, "DouYinGameQueryOrder 后台补单", order_id, call_admin)
            return self.answer()
        return self.rep_express(goods, gifts)


class MiniProgramRecvPush(BaseSomePay):
    """
    微信小程序回调通知
    参考文档：https://developers.weixin.qq.com/miniprogram/dev/framework/server-ability/message-push.html#
    """
    decorators = []

    @classmethod
    def parse_session_from(cls, session_from):
        """
        解析session_from字符串为字典
        :param session_from: 形如 "key1=value1,key2=value2" 的字符串
        """
        params_dict = {}
        for item in session_from.split(','):
            if not item:  # 跳过空字符串项
                continue
            try:
                key, value = item.split('=', 1)
                params_dict[key] = int(value)  # 尝试将值转换为整数
            except ValueError as e:
                cls.info_log(f"无法解析项 '{item}' 到键值对: {e}")
                continue  # 跳过这个项，继续下一个
        return params_dict

    async def get(self, req: Request):
        """测试用"""
        self.wechat_check_signature(req, WeChatConf.WE_CHAT_MP_PUSH_TOKEN)
        _ = await self.wechat_decode_data(req, WeChatConf.WE_CHAT_MP_PUSH_TOKEN, WeChatConf.WE_CHAT_MP_AES_KEY,
                                          WeChatConf.WE_CHAT_MG_APP_ID)
        self.info_log("MiniProgramRecvPush 消息推送解密测试：", req.args)
        return response.text(body=req.args.get("echostr"))

    async def post(self, req: Request):
        """
        用户发给小程序的消息以及开发者需要的事件推送，都将被微信转发至该服务器地址中
        参考文档：https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Receiving_event_pushes.html
        """
        self.wechat_check_signature(req, WeChatConf.WE_CHAT_MP_PUSH_TOKEN)
        payload_data = await self.wechat_decode_data(req, WeChatConf.WE_CHAT_MP_PUSH_TOKEN,
                                                     WeChatConf.WE_CHAT_MP_AES_KEY, WeChatConf.WE_CHAT_MG_APP_ID)
        self.info_log("MiniProgramRecvPush 接收到微信消息推送回调", payload_data)
        session_from = payload_data.get("SessionFrom") or ""
        if not session_from:
            # session_from字段是个自用拓展字段，若是来自前端一定非空，则不处理即可，若为空则大可能来自客户聊天；
            # 目前重点处理支付，其他的客服人员处理
            return response.json({"ErrCode": 0, "ErrMsg": "Success"})
        from_user_name = payload_data.get("FromUserName")  # 发送方账号（一个OpenID）

        # 1.解析数据:客户端获取-传给微信-回调发送后端
        params_dict = self.parse_session_from(session_from)
        self.info_log("MiniProgramRecvPush SessionFrom:", params_dict)
        if params_dict is None:
            return response.json({"ErrCode": self.sta_code.ERR_ARG, "ErrMsg": '参数格式错误，不予回复！'})

        params_key = {"trade_item", "uid", "c_platform", "count"}
        if not params_key.issubset(params_dict.keys()):
            return response.json({"ErrCode": self.sta_code.ERR_ARG, "ErrMsg": '参数缺失，不予回复！'})

        # 2.创建订单
        uid = params_dict.get("uid")
        trade_item = params_dict.get("trade_item")
        platform = params_dict.get('c_platform') or ''
        count = req.json.get("count") or 1

        order_info, hint = await MakeOrder.create_order(uid, trade_item, PayMode.IOS_TO_H5, platform, req, count=count)
        if order_info:
            # 3.发送客服消息（支付界面相关信息）
            access_token = await self.wechat_get_access_token()
            errcode, req_data = await WeChat.wechat_send_custom_msg(uid, from_user_name, access_token, order_info)
            self.info_log(uid, "sendCustomMessage 发送客服消息：", req_data, errcode)
            if not errcode:
                return response.json({"ErrCode": 0, "ErrMsg": "Success"})
            return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": '发送客服消息失败'})
        return response.json({"ErrCode": self.sta_code.FAIL, "ErrMsg": hint})


class HuiFuGetPayInfo(BaseSomePay):
    """
    获取汇付支付信息（实际上是后端请求汇付天下之后斗拱的聚合正扫）
    1.用code换取gzh_openid，监测实时订单价变化；
    2.通过DouGongPay获取，并返回pay_info信息返回给前端；
    3.用order_id缓存pay_info，可以匹配上每一个H5链接；
    """
    decorators = []

    async def post(self, req: Request):
        order_id = self.check_str(req.json.get("order_id"), require=True, p_name="order_id")
        code = self.check_str(req.json.get("code"), require=True, p_name="code")

        # 1.查询本地订单
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id) or {}
        if not order_info:
            self.error_log("WeChatGetPayInfo 无此订单", order_id)
            self.answer_json(data={"ErrCode": self.sta_code.ORDER_NOT_FOUND, "ErrMsg": '无此订单'})

        # 2.检查订单状态是否可拉取支付
        if order_info.get("order_status") != OrderStatus.WAIT_PAY:
            self.answer_json(data={"ErrCode": self.sta_code.PASS, "ErrMsg": '已经支付了或重复支付'})
        uid = order_info.get('uid')

        # 3.查询实时订单价
        express, item_num, _, __, desc = await self.verify_goods(uid, order_info.get('trade_item'))
        if not express:
            self.answer_json(data={"ErrCode": self.sta_code.GOODS_NOT_FOUND, "ErrMsg": desc})
        trade_amount_old = order_info.get("trade_amount") or 0  # 客服下单时的订单价格
        trade_amount_new = express.get("price") or 0  # 实时订单价，以防折扣次数用尽

        item_name = express.get("act_name" if item_num == 3 else "store_name", "未知商品")
        order_info["item_name"] = item_name

        # 4.如果实时订单价与原订单价不一致，则更新订单表
        if trade_amount_old != trade_amount_new:
            update_price = {"trade_amount": trade_amount_new}
            await RecordsTradeOrder.update_by_pk(order_id, update_price, order_info)
            order_info["trade_amount"] = express.get("price")

        req_res = await BaseUserRC.get_user_pay_info(uid, order_id)
        # 6.如果没有缓存的支付信息，或者订单价格发生了变化，则重新生成支付信息
        if not req_res or (trade_amount_old != trade_amount_new):
            gzh_openid = await WeChat.update_gzh_openid(uid, code)
            if not gzh_openid:
                self.answer_json(data={"ErrCode": self.sta_code.FAIL, "ErrMsg": 'Invalid gzh_openid or code.'})

            order_info["gzh_openid"] = gzh_openid
            req_res = await DouGongPay.dou_gong_js_pay(**order_info)
            self.info_log('HuiFuGetPayInfo DouGong res:', req_res, 'old & new:', trade_amount_old, trade_amount_new)

            resp_code = req_res.get('resp_code')
            if resp_code != '00000100':  # 下单成功
                self.answer_json(data={"ErrCode": resp_code, "ErrMsg": req_res})

            await BaseUserRC.cache_user_pay_info(uid, order_id, req_res)

        pay_info = req_res.get('pay_info')
        (not pay_info) and self.answer(self.sta_code.FAIL, hint='Not Found pay_info.')
        return self.answer_json(data={"pay_info": pay_info})


class HuiFuPayQueryOrder(BaseSomePay):
    """
    汇付天下交易查询
    即时更新支付状态，缓存待发货快递
    """
    decorators = []

    async def post(self, req: Request):
        order_id = self.check_str(req.json.get("order_id"), require=True, p_name="order_id")

        # 1.查询本地订单
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
        if not order_info:
            self.error_log("HuiFuPayQueryOrder 无此订单", order_id)
            self.answer_json(data={"ErrCode": self.sta_code.GOODS_NOT_FOUND, "ErrMsg": '无此订单'})
        uid = order_info.get("uid")
        trade_amount = order_info.get("trade_amount") or 0
        trade_item = order_info.get("trade_item")

        # 2.汇付天下交易查询
        req_res = await DouGongPay.dou_gong_query(order_id)
        # self.info_log(uid, "HuiFuPayQueryOrder 解析查询数据：", req_res)
        resp_code = req_res.get('resp_code')
        if resp_code != '00000000':
            self.answer_json(data={"ErrCode": resp_code, "ErrMsg": req_res})

        if req_res.get("trans_stat") != "S":  # P：处理中；S：成功；F：失败；I: 初始（初始状态很罕见，请联系汇付技术人员处理）；交易状态以此字段为准。
            self.info_log(uid, "HuiFuPayQueryOrder 支付失败或支付成功未发币到账", order_id)
            self.answer_json(data={"ErrCode": self.sta_code.FAIL, "ErrMsg": '支付失败或支付成功未发币到账'})

        # 3.查询货物 goods立得货物 / gifts赠物
        express, _, buy_record, __, desc = await self.verify_goods(uid, trade_item)
        if not express:
            self.answer_json(data={"ErrCode": self.sta_code.GOODS_NOT_FOUND, "ErrMsg": desc})
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 4.更新支付状态，缓存待领取订单
        order_status = order_info.get("order_status")
        if order_status != OrderStatus.PAID:
            order_status = OrderStatus.PAID
            update_paid = {"order_status": order_status}
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(order_id, update_paid, order_info)
                    await BaseUserRC.cache_user_paid_order(uid, order_id, goods, gifts)  # 预发货
            except Exception as e:
                self.error_log(f"HuiFuPayQueryOrder 事务执行失败，原因：{e}")
                self.answer_json(data={"ErrCode": self.sta_code.FAIL, "ErrMsg": '快递打包失败'})

            # 5.发快递后处理/预处理货物的购买数据
            await self.process_after_deliver(uid, trade_amount)
            await self.process_after_received(uid, order_info, buy_record=buy_record)
        else:
            self.info_log(uid, "HuiFuPayQueryOrder 快递已经发出", order_id)

        self.info_log(uid, "HuiFuPayQueryOrder 快递入站成功", order_id)
        return self.answer_json(data={"order_id": order_id, "order_status": order_status})


class HuiFuPayNotify(BaseSomePay):
    """
    汇付天下支付回调通知
    参考文档：https://paas.huifu.com/open/doc/api/#/smzf/api_jhzs?id=%e5%bc%82%e6%ad%a5%e8%bf%94%e5%9b%9e%e5%8f%82%e6%95%b0
    即时更新支付状态，缓存待发货快递
    """
    decorators = []

    def __check_signature(self, req: Request):
        """ 检查签名 """
        form = req.get_form()

        resp_code = form.get('resp_code')
        resp_desc = form.get('resp_desc')
        resp_data_str = form.get('resp_data')
        sign = form.get('sign')
        self.info_log("HuiFuPayNotify 汇付天下支付回调通知", resp_code, resp_desc)

        if resp_code != '00000000':
            return False, {"ErrCode": self.sta_code.FAIL, "ErrMsg": 'Invalid resp_code.'}

        # 使用斗拱平台公钥进行验签
        resp_data = json_parse(resp_data_str)
        result = DGTools.verify_sign(resp_data, sign, pub_key=HuiFuConf.DOUGONG_APP_PUBLIC_KEY)
        if not result:
            self.error_log(f"HuiFu 汇付天下支付回调通知{result}验签失败")
            return False, {"ErrCode": self.sta_code.ERR_AUTH, "ErrMsg": "验签失败"}
        return True, resp_data

    async def post(self, req: Request):
        """默认格式为 application/x-www-form-urlencode，form表单格式"""
        res, res_dict = self.__check_signature(req)
        if not res:
            self.answer_json(data=res_dict)

        # 1.验签成功后，处理业务逻辑
        # self.info_log("HuiFuPayNotify 解析回调数据", res_dict)
        order_id = res_dict.get('req_seq_id')  # 交易时传入，原样返回
        if res_dict.get("trans_stat") != "S":  # P：处理中；S：成功；F：失败；I: 初始（初始状态很罕见，请联系汇付技术人员处理）；交易状态以此字段为准。
            self.info_log("HuiFuPayNotify 支付失败或支付成功未发币到账", order_id)
            self.answer_json(data={"ErrCode": self.sta_code.FAIL, "ErrMsg": "支付失败或支付成功未发币到账"})

        # 1.查询本地订单状态（查无订单直接返成功，为了防止来自测试服订单的回调，仅回调使用此逻辑）
        order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
        if not order_info:
            self.error_log("HuiFuPayNotify 无此订单", order_id)
            self.answer_json(data={"ErrCode": self.sta_code.ORDER_NOT_FOUND, "ErrMsg": "无此订单"})
        uid = order_info.get("uid")
        trade_amount = order_info.get("trade_amount") or 0
        trade_item = order_info.get("trade_item")

        # 2.验证买家
        u_info = await BaseUserRC.cache_by_uid(uid)
        if not u_info:
            self.error_log("HuiFuPayNotify 找不到对应下单用户", order_id)
            self.answer_json(data={"ErrCode": self.sta_code.ERR_ARG, "ErrMsg": "找不到对应下单用户"})

        # 3.查询货物 goods立得货物 / gifts赠物
        express, _, buy_record, __, desc = await self.verify_goods(uid, trade_item)
        if not express:
            self.answer_json(data={"ErrCode": self.sta_code.GOODS_NOT_FOUND, "ErrMsg": desc})
        goods, gifts = await UpAssets.stat_express(uid, express, trade_item)

        # 4.更新支付状态，缓存待领取订单
        if order_info.get("order_status") != OrderStatus.PAID:
            update_paid = {"order_status": OrderStatus.PAID}
            try:
                async with in_transaction(connection_name=DbKey.DEFAULT):
                    await RecordsTradeOrder.update_by_pk(order_id, update_paid, order_info)
                    await BaseUserRC.cache_user_paid_order(uid, order_id, goods, gifts)  # 预发货
            except Exception as e:
                self.error_log(f"HuiFuPayNotify 事务执行失败，原因：{e}")
                self.answer(self.sta_code.FAIL, hint="HuiFuPayNotify 快递打包失败")

            # 5.发快递后处理/预处理货物的购买数据
            await self.process_after_deliver(uid, trade_amount)
            await self.process_after_received(uid, order_info, buy_record=buy_record)
        else:
            self.info_log(uid, "HuiFuPayNotify 快递已经发出", order_id)

        self.info_log(uid, "HuiFuPayNotify 快递入站成功", order_id)
        return self.answer_json(data={"ErrCode": self.sta_code.PASS, "ErrMsg": "Success"})


class CompletePaidOrder(BaseSomePay):
    """
    完成已支付订单
    即时更新发货状态、购买数据（可批量）
    """

    async def post(self, _, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 1.注意物品和赠品以预发货的为主
        paid_orders = await BaseUserRC.get_user_paid_order(uid)
        if not paid_orders:
            data = {"errcode": self.sta_code.ORDER_NOT_FOUND, "errmsg": '没有待领取订单'}
            self.answer(data=data)

        all_goods = []
        all_gifts = []

        for order in paid_orders:
            order_id = order.get("order_id")
            goods = order.get("goods")
            gifts = order.get("gifts")

            # 2.查询多个本地订单
            order_info = await RecordsTradeOrder.query_trade_order(order_id=order_id)
            if not order_info:
                self.error_log("CompletePaidOrder 无此待领取订单", order_id)
                data = {"errcode": self.sta_code.ORDER_NOT_FOUND, "errmsg": '无此待领取订单'}
                self.answer(data=data)

            # 3.发货并准备派送
            if order_info.get("deliver_status") == DeliverStatus.UNSHIPPED:
                update_deliver = {
                    "deliver_status": DeliverStatus.SHIPPED,
                    "finish_time": tool_dt.cur_time(),
                }
                try:
                    async with in_transaction(connection_name=DbKey.DEFAULT):
                        await RecordsTradeOrder.update_by_pk(order_id, update_deliver, order_info)
                        await UpAssets.update_assets(uid, goods, gifts)

                        # 4.查询货物，注意此处主要是查询活动的，物品在缓存取
                        express, item_num, _, __, ___ = await self.verify_goods(uid, order_info.get("trade_item"))
                        if express and item_num == 3:
                            await UserActivityRC.update_user_charge_records(uid, express)
                except Exception as e:
                    self.error_log(f"CompletePaidOrder 事务执行失败，原因：{e}")
                    data = {"errcode": self.sta_code.FAIL, "errmsg": '查询发货失败'}
                    self.answer(data=data)

                # 4.将当前订单的货物和奖励加入总结果
                all_goods.extend(goods)
                all_gifts.extend(gifts)
            else:
                self.info_log(uid, "CompletePaidOrder 已经取件了", order_id)

        self.info_log(uid, "CompletePaidOrder 订单交易成功")
        return self.rep_express(all_goods, all_gifts)
