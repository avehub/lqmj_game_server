import asyncio
import adapay
import dg_sdk
from functools import partial

from dg_sdk import DGTools
from nsanic.libs.mk_random import RngMaker
from nsanic.libs.mult_log import NLogger
from nsanic.libs.tool import json_parse

from common.utils.kit_dt import KitDt
from common.public.conf import WeChatConf, HuiFuConf, SERVER_ADDR, LIVE_SERVER, AliPayConf
from lucky_game.const import OrderStatus, GainStatus, PlatForm

RESPONSE_CODE = {
    "00000000": "交易受理成功；注：交易状态以trans_stat为准",
    "00000100": "下单成功",
    "10000000": "产品号不能为空",
    "10000000": "交易类型不能为空",
    "10000000": "%s不能为空",
    "10000000": "%s长度固定%d位",
    "10000000": "%s最大长度为%d位",
    "10000000": "%s的传入枚举[%s]不存在",
    "10000000": "%s不符合%s格式。如：交易金额不符合金额格式",
    "10000000": "订单已超时",
    "20000000": "重复交易",
    "21000000": "手续费金额、手续费收取方式、手续费扣款标识、手续费子客户号、手续费账户号，必须同时为空或同时必填",
    "22000000": "产品号不存在",
    "22000000": "产品号状态异常",
    "22000002": "商户信息不存在",
    "22000002": "商户状态异常",
    "22000003": "延迟账户不存在",
    "22000003": "商户账户信息不存在",
    "22000004": "暂未开通分账权限",
    "22000004": "暂未开通%s权限",
    "22000004": "暂未开通延迟入账权限",
    "22000005": "手续费承担方必须参与分账",
    "22000005": "分账列表必须包含主交易账户",
    "22000005": "其他商户分账比例过高",
    "22000005": "商户入驻信息配置有误(多通道)",
    "22000005": "商户分期贴息未激活",
    "22000005": "分期交易不能重复激活",
    "22000005": "手续费配置有误",
    "22000005": "商户贴息信息未配置",
    "22000005": "花呗分期费率配置有误",
    "22000005": "分账配置有误",
    "22000005": "分账配置未包含手续费承担方",
    "22000005": "商户入驻配置信息有误",
    "22000005": "商户支付宝/微信入驻信息配置有误",
    "22000005": "商户银联入驻信息配置有误",
    "22000005": "商户贴息分期费率未配置渠道号",
    "22000005": "商户贴息分期费率未配置费率类型",
    "22000005": "商户贴息分期费率配置有误",
    "22000005": "手续费费率未配置",
    "22000005": "手续费计算错误",
    "22000005": "商户贴息信息配置有误",
    "22000005": "商户未报名活动或活动已过期",
    "22000005": "数字货币手续费费率未配置",
    "22000005": "数字货币手续费配置有误",
    "22000005": "商户未配置默认入驻信息（多通道）",
    "23000003": "交易金额不足以支付内扣手续费",
    "23000003": "优惠金额大于交易金额",
    "23000004": "交易类型不支持",
    "23000004": "当前交易类型不支持商户贴息",
    "90000000": "业务执行失败；如：账户可用余额不足",
    "90000000": "该功能已关闭，请联系客服",
    "90000000": "交易失败，单日金额超限，请联系额服提额",
    "90000000": "交易存在风险",
    "91111119": "通道异常，请稍后重试",
    "98888888": "系统错误",
}

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
        request.req_seq_id = order_info.get('order_no')
        request.goods_desc = str(order_info.get('sku')) or '未知商品'
        # T_JSAPI: 微信公众号, JS-A_JSAPI: 支付宝, T_APP: 微信APP支付, 微信小程序: T_MINIAPP
        trade_type = ""
        wx_data = {}
        if order_info.get('platform') == PlatForm.WECHAT_MP:
            trade_type = "T_JSAPI"
            wx_data = {
                "sub_appid": WeChatConf.WE_CHAT_GZH_APP_ID,  # 微信公众号应用ID
                "sub_openid": str(order_info.get('user_openid')) or '',  # 用户在子商户下唯一标识
            }
        elif order_info.get('platform') == PlatForm.WECHAT_MINI_GAME:
            trade_type = "T_MINIAPP"
            wx_data = {
                "sub_appid": WeChatConf.WE_CHAT_MG_APP_ID,  # 微信小程序应用ID
                "sub_openid": str(order_info.get('user_openid')) or '',  # 用户在子商户下唯一标识
            }
        request.trade_type = trade_type
        request.trans_amt = f"{float(order_info.get('amount')):.2f}"  # 交易金额，必须大于0，保留两位小数点，如0.10、100.05等

        # 准备extend_infos，包括所有需要额外传递的参数
        extend_infos = {
            "notify_url": SERVER_ADDR + AliPayConf.NOTIFY_URL,  # 交易异步通知地址
            "wx_data": wx_data
        }
        # 异步请求
        loop = asyncio.get_running_loop()

        NLogger.info("汇付天下js_pay支付请求参数：", extend_infos)
        response = await loop.run_in_executor(None, lambda: request.post(extend_infos))
        NLogger.info("汇付天下js_pay支付响应结果：", response)
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
        NLogger.info("汇付天下查询订单请求参数：", extend_infos)
        response = await loop.run_in_executor(None, lambda: request.post(extend_infos))
        NLogger.info("汇付天下查询订单响应结果：", response)
        if not response:
            return False, "查询失败", {}
        # res, res_dict = cls.check_signature(response)
        # NLogger.info("汇付天下支付回调通知 解析回调数据", res, res_dict)
        data = {
            "order_no": response.get('req_seq_id'),
            "order_status": OrderStatus.FAIL,
        }

        resp_code = response.get('resp_code')
        # P：处理中；S：成功；F：失败；I: 初始（初始状态很罕见，请联系汇付技术人员处理）；交易状态以此字段为准。
        if resp_code == '00000000':
            if response.get("trans_stat") == "S":
                data["order_status"] = OrderStatus.PAID
            elif response.get("trans_stat") == "F":
                data["order_status"] = OrderStatus.FAIL
        return True, response.get("resp_desc"), data

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

    @classmethod
    async def dou_gong_busi_config_query(cls):
        """
        微信配置查询
        参考文档：https://paas.huifu.com/open/doc/api/#/shgl/shjj/api_shjj_wxshpzcx
        """
        DG_SDK = cls.dou_gong_init()
        # 组装接口请求参数
        request = DG_SDK.V2MerchantBusiConfigQueryRequest()
        request.huifu_id = HuiFuConf.DOUGONG_SYS_ID
        request.req_date = KitDt.get_date_str()
        request.req_seq_id = await RngMaker.gen_num(str_len=32)

        extend_infos = {}
        # 异步请求
        loop = asyncio.get_running_loop()
        NLogger.info("汇付天下查询微信配置请求参数：", request)
        response = await loop.run_in_executor(None, lambda: request.post(extend_infos))
        NLogger.info("汇付天下查询微信配置响应结果：", response)
        return response

    @classmethod
    async def check_signature(cls, form):
        """ 检查签名 """
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

    @classmethod
    async def dou_gong_notify(cls, form):
        """
        汇付天下支付回调通知
        参考文档：https://paas.huifu.com/open/doc/api/#/smzf/api_jhzs?id=%e5%bc%82%e6%ad%a5%e8%bf%94%e5%9b%9e%e5%8f%82%e6%95%b0
        即时更新支付状态，缓存待发货快递
        """
        res, res_dict = await cls.check_signature(form)
        NLogger.info("汇付天下支付回调通知 解析回调数据", res, res_dict)
        if not res:
            return False, res_dict

        # 验签成功后，处理业务逻辑
        data = {
            "order_no": res_dict.get('req_seq_id'),
            "out_trans_id": res_dict.get('out_trans_id'),
            "trade_no": res_dict.get('hf_seq_id'),
        }
        order_status = OrderStatus.FAIL
        if res_dict.get("trans_stat") == "S":  # P：处理中；S：成功；F：失败；I: 初始（初始状态很罕见，请联系汇付技术人员处理）；交易状态以此字段为准。
            order_status = OrderStatus.PAID

        data["trade_status"] = order_status
        return True, data


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
            "pay_amt": f"{float(order_info.get('amount')):.2f}",  # 交易金额，必须大于0，保留两位小数点，如0.10、100.05等
            "goods_title": str(order_info.get('sku')) or '',
            "goods_desc": str(order_info.get('desc')) or '',
            "mer_key": 'merchant_key',
            "device_info": {'device_ip': ''},
            "expend": {
                'open_id': str(order_info.get('explain')) or ''
            }
        }
        # 使用partial来处理关键字参数
        loop = asyncio.get_running_loop()
        create_with_kwargs = partial(adapay.Payment.create, **payment_params)
        response = await loop.run_in_executor(None, create_with_kwargs)

        # 更简洁的方式
        # response = await loop.run_in_executor(None, lambda: adapay.Payment.create(**payment_params))
        return response


