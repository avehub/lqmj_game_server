import asyncio
import adapay
import dg_sdk
from functools import partial

from nsanic.libs.mk_random import RngMaker

from common.utils.kit_dt import KitDt
from common.public.conf import WeChatConf, HuiFuConf, PROD_SERVER_ADDR, LIVE_SERVER, TEST_SERVER_ADDR


class DouGongPay:
    """汇付天下支付相关（斗拱 SDK）"""
    DG_SDK = None

    @classmethod
    def dou_gong_init(cls):
        """初始化SDK"""
        if not cls.DG_SDK:
            sys_id = HuiFuConf.DOUGONG_SYS_ID
            product_id = HuiFuConf.DOUGONG_PRODUCT_ID
            private_key = HuiFuConf.DOUGONG_PRIVATE_KEY
            public_key = HuiFuConf.DOUGONG_APP_PUBLIC_KEY

            dg_sdk.DGClient.mer_config = dg_sdk.MerConfig(private_key, public_key, sys_id, product_id)
            cls.DG_SDK = dg_sdk
        return cls.DG_SDK

    @classmethod
    async def dou_gong_js_pay(cls, **order_info):
        """
        聚合正扫（斗拱）
        参考文档：https://paas.huifu.com/open/doc/api/#/smzf/api_jhzs
        """
        DG_SDK = cls.dou_gong_init()
        # 创建并设置请求对象的基本属性
        request = DG_SDK.V2TradePaymentJspayRequest()
        request.huifu_id = HuiFuConf.DOUGONG_SYS_ID
        request.req_date = KitDt.get_date_str()
        request.req_seq_id = order_info.get('order_id')
        request.goods_desc = str(order_info.get('item_name')) or '未知商品'
        request.trade_type = 'T_JSAPI'  # T_JSAPI: 微信公众号
        request.trans_amt = f"{float(order_info.get('trade_amount')):.2f}"  # 交易金额，必须大于0，保留两位小数点，如0.10、100.05等

        # 准备extend_infos，包括所有需要额外传递的参数
        server_addr = PROD_SERVER_ADDR if LIVE_SERVER else TEST_SERVER_ADDR
        extend_infos = {
            "notify_url": f'{server_addr}/promisingGame/HuiFuPayNotify',  # 交易异步通知地址
            "wx_data": {
                "sub_appid": WeChatConf.WE_CHAT_GZH_APP_ID,  # 微信子应用ID
                "sub_openid": str(order_info.get('gzh_openid')) or '',  # 用户在子商户下唯一标识
            }
        }
        # 异步请求
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: request.post(extend_infos))
        return response

    @classmethod
    async def dou_gong_query(cls, order_id):
        """
        扫码交易查询
        参考文档：https://paas.huifu.com/open/doc/api/#/smzf/api_qrpay_cx
        """
        DG_SDK = cls.dou_gong_init()
        # 组装接口请求参数
        request = DG_SDK.V2TradePaymentScanpayQueryRequest()
        request.huifu_id = HuiFuConf.DOUGONG_SYS_ID
        request.org_req_date = KitDt.get_date_str()
        request.org_req_seq_id = order_id  # 确保至少有一个必填项被设置

        extend_infos = {}
        # 异步请求
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: request.post(extend_infos))
        return response

    @classmethod
    async def dou_gong_busi_config(cls):
        """
        微信商户配置
        参考文档：https://paas.huifu.com/open/doc/api/#/shgl/shjj/api_shjj_wxshpz
        """
        DG_SDK = cls.dou_gong_init()
        # 组装接口请求参数
        request = DG_SDK.V2MerchantBusiConfigRequest()
        request.huifu_id = HuiFuConf.DOUGONG_SYS_ID
        request.req_date = KitDt.get_date_str()
        request.req_seq_id = await RngMaker.gen_num(str_len=32)
        request.fee_type = '01'
        request.wx_woa_app_id = WeChatConf.WE_CHAT_GZH_APP_ID
        request.wx_woa_secret = WeChatConf.WE_CHAT_GZH_APP_SECRET

        extend_infos = {}
        # 异步请求
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: request.post(extend_infos))
        return response


class Adapay:
    """汇付天下支付相关（Adapay SDK）"""
    CONFIG_INFO = None  # 初始化为空

    @classmethod
    def adapay_init(cls, api_key=None, mock_api_key=None, private_key=None):
        """
        初始化配置信息。
        :param api_key: 正式环境API密钥
        :param mock_api_key: 测试环境API密钥
        :param private_key: 私钥
        """
        cls.CONFIG_INFO = {
            'api_key': '未知的配置',
            'private_key': '未知的配置'
        }
        # todo:官方测试请求参数
        # cls.CONFIG_INFO = {
        #     'api_key': 'api_live_9c14f264-e390-41df-984d-df15a6952031',
        #     'mock_api_key': 'api_test_e640fa26-bbe6-458f-ac44-a71723ee2176',
        #     'private_key': 'MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMQhsygJ2pp4nCiDAXiqnZm6AzKSVAh+C0BgGR6QaeXzt0TdSi9VR0OQ7Qqgm92NREB3ofobXvxxT+wImrDNk6R6lnHPMTuJ/bYpm+sx397rPboRAXpV3kalQmbZ3P7oxtEWOQch0zV5B1bgQnTvxcG3REAsdaUjGs9Xvg0iDS2tAgMBAAECgYAqGFmNdF/4234Yq9V7ApOE1Qmupv1mPTdI/9ckWjaAZkilfSFY+2KqO8bEiygo6xMFCyg2t/0xDVjr/gTFgbn4KRPmYucGG+FzTRLH0nVIqnliG5Ekla6a4gwh9syHfstbOpIvJR4DfldicZ5n7MmcrdEwSmMwXrdinFbIS/P1+QJBAOr6NpFtlxVSGzr6haH5FvBWkAsF7BM0CTAUx6UNHb+RCYYQJbk8g3DLp7/vyio5uiusgCc04gehNHX4laqIdl8CQQDVrckvnYy+NLz+K/RfXEJlqayb0WblrZ1upOdoFyUhu4xqK0BswOh61xjZeS+38R8bOpnYRbLf7eoqb7vGpZ9zAkEAobhdsA99yRW+WgQrzsNxry3Ua1HDHaBVpnrWwNjbHYpDxLn+TJPCXvI7XNU7DX63i/FoLhOucNPZGExjLYBH/wJATHNZQAgGiycjV20yicvgla8XasiJIDP119h4Uu21A1Su8G15J2/9vbWn1mddg1pp3rwgvxhw312oInbHoFMxsQJBAJlyDDu6x05MeZ2nMor8gIokxq2c3+cnm4GYWZgboNgq/BknbIbOMBMoe8dJFj+ji3YNTvi1MSTDdSDqJuN/qS0='
        # }
        adapay.mer_config = {'merchant_key': cls.CONFIG_INFO}

    @classmethod
    async def adapay_create_payment(cls, **order_info):
        cls.adapay_init()
        # 创建支付参数字典
        payment_params = {
            "order_no": order_info.get('order_id'),
            "app_id": WeChatConf.WE_CHAT_GZH_APP_ID,
            "pay_channel": "wx_pub",  # 微信公众号支付
            "pay_amt": f"{float(order_info.get('trade_amount')):.2f}",  # 交易金额，必须大于0，保留两位小数点，如0.10、100.05等
            "goods_title": str(order_info.get('trade_item')) or '',
            "goods_desc": str(order_info.get('order_desc')) or '',
            "mer_key": 'merchant_key',
            "device_info": {'device_ip': str(order_info.get('client_ip')) or ''},
            "expend": {
                'open_id': str(order_info.get('gzh_openid')) or ''
            }
        }
        # 使用partial来处理关键字参数
        loop = asyncio.get_running_loop()
        create_with_kwargs = partial(adapay.Payment.create, **payment_params)
        response = await loop.run_in_executor(None, create_with_kwargs)

        # 更简洁的方式
        # response = await loop.run_in_executor(None, lambda: adapay.Payment.create(**payment_params))
        return response
