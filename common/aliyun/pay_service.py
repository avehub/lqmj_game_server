import base64
import time

from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayTradeAppPayModel import AlipayTradeAppPayModel
from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel
from alipay.aop.api.domain.AlipayTradeRefundModel import AlipayTradeRefundModel
from alipay.aop.api.domain.AlipayTradeCloseModel import AlipayTradeCloseModel
from alipay.aop.api.request.AlipayTradeAppPayRequest import AlipayTradeAppPayRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.request.AlipayTradeRefundRequest import AlipayTradeRefundRequest
from alipay.aop.api.request.AlipayTradeCloseRequest import AlipayTradeCloseRequest
from alipay.aop.api.request.AlipayTradeWapPayRequest import AlipayTradeWapPayRequest
from alipay.aop.api.exception.Exception import AopException
from alipay.aop.api.util.SignatureUtils import get_sign_content, verify_with_rsa
from nsanic.libs.tool import json_parse

from common.public.common_class import CommonApi
from common.public.conf import AliPayConf, SERVER_ADDR
from nsanic.libs.mult_log import NLogger
from alipay.aop.api.util import EncryptUtils

from lucky_game.const import OrderStatus

RESPONSE_CODE = {
    "WAIT_BUYER_PAY": "交易创建，等待买家付款。",
    "TRADE_CLOSED": "未付款交易超时关闭，或支付完成后全额退款。",
    "TRADE_SUCCESS": "交易支付成功。",
    "TRADE_FINISHED": "交易结束，不可退款。",
}
# 接口调用成功码
SUCCESS_CODE = "10000"


class AlipayPayment:
    def __init__(self, payment_type='H5'):
        """
        初始化支付宝支付服务
        :param payment_type: 支付类型，'H5' 或 'APP'
        """
        # 初始化配置

        self.debug = AliPayConf.DEBUG_MODE
        self.client_config = AlipayClientConfig(self.debug)
        self.client_config.sign_type = "RSA2"
        self.client_config.timeout = 30
        # 根据支付类型设置不同的配置
        self.type_conf = AliPayConf.PLATFORM.get(payment_type)
        self.client_config.app_id = self.type_conf.get("APP_ID")
        self.client_config.app_private_key = self.type_conf.get("PRIVATE_KEY")
        # self.client_config.return_url = AliPayConf.RETURN_URL
        self.client_config.alipay_public_key = AliPayConf.ALIPAY_PUBLIC_KEY
        self.client_config.server_url = AliPayConf.SERVER_URL
        self.notify_url = SERVER_ADDR + AliPayConf.NOTIFY_URL
        if self.client_config.app_id != AliPayConf.SANDBOX.APP_ID:
            self.private_key = self.type_conf.get("PRIVATE_AES")
        # 初始化客户端
        self.client = DefaultAlipayClient(self.client_config)
        # 保存支付类型
        self.payment_type = payment_type

    async def create_h5_payment(self, subject, out_trade_no, total_amount, return_url=None):
        """
        创建H5支付订单
        :param subject: 商品标题
        :param out_trade_no: 商户订单号
        :param total_amount: 订单金额（单位：元）
        :param return_url: 支付成功后的返回页面URL
        :return: 支付页面URL
        """
        try:
            if self.payment_type != 'H5':
                raise ValueError("当前实例不是H5支付类型")

            NLogger.info(f"支付宝H5支付订单: subject {subject} out_trade_no {out_trade_no} total_amount {total_amount}")
            # 创建支付模型
            model = AlipayTradeAppPayModel()
            model.subject = subject
            model.out_trade_no = out_trade_no
            model.total_amount = str(total_amount)

            # 创建支付请求
            request = AlipayTradeWapPayRequest(biz_model=model)
            request.notify_url = self.notify_url
            if return_url:
                request.return_url = await CommonApi.append_query_params(return_url, {"order_no": out_trade_no, "t": time.time()})
            # 获取支付页面URL

            NLogger.info(f"支付宝H5支付订单请求参数: request {request} ")
            response = self.client.page_execute(request, http_method="GET")
            NLogger.info(f"支付宝H5支付订单响应参数: response {response} ")
            return response
        except Exception as e:
            NLogger.error(f"创建H5支付订单失败: {str(e)}")
            raise

    def create_app_payment(self, subject, out_trade_no, total_amount, product_code='QUICK_MSECURITY_PAY'):
        """
        创建APP支付订单
        :param subject: 商品标题
        :param out_trade_no: 商户订单号
        :param total_amount: 订单金额（单位：元）
        :param product_code: 产品码，默认为QUICK_MSECURITY_PAY
        :return: 支付参数字典
        """
        try:
            if self.payment_type != 'APP':
                raise ValueError("当前实例不是APP支付类型")
                
            # 创建支付模型
            model = AlipayTradeAppPayModel()
            model.subject = subject
            model.out_trade_no = out_trade_no
            model.total_amount = str(total_amount)
            model.product_code = product_code
            # 创建支付请求
            request = AlipayTradeAppPayRequest(biz_model=model)
            request.notify_url = self.notify_url
            # 获取支付参数
            NLogger.info(f"支付宝APP支付订单请求参数: request {request} ")
            response = self.client.sdk_execute(request)
            NLogger.info(f"支付宝APP支付订单响应参数: response {response} ")
            return response
        except Exception as e:
            NLogger.error(f"创建APP支付订单失败: {str(e)}")
            return False, str(e), {}

    def verify_payment(self, data, signature):
        """
        验证支付通知
        :param data: 支付通知数据
        :param signature: 签名
        :return: 验证结果
        """
        try:
            # 获取签名内容
            sign_content = get_sign_content(data)
            # 使用支付宝公钥验证签名
            if sign_content:
                return verify_with_rsa(self.client_config.alipay_public_key, sign_content.encode("utf-8"), signature)
            else:
                return False
        except AopException as e:
            NLogger.error(f"支付通知验证失败: {str(e)}")
            return None


    def verify_aes(self, data):
        """
        解密AES加密数据
        :param data: 支付通知数据
        :return: 验证结果
        """
        try:
            content = EncryptUtils.aes_decrypt_content(data, self.private_key, "utf-8")
            if content:
                return content
            else:
                return False
        except AopException as e:
            NLogger.error(f"支付通知AES解密失败: {str(e)}")
            return None

    def query_trade_status(self, out_trade_no=None, trade_no=None):
        """
        查询订单状态
        :param out_trade_no: 商户订单号
        :param trade_no: 支付宝交易号
        :return: 订单状态信息
        """
        try:
            # 创建查询模型
            model = AlipayTradeQueryModel()
            if out_trade_no:
                model.out_trade_no = out_trade_no
            elif trade_no:
                model.trade_no = trade_no
            else:
                raise ValueError("必须提供out_trade_no或trade_no之一")

            # 创建查询请求
            request = AlipayTradeQueryRequest(biz_model=model)

            # 执行查询
            NLogger.info(f"查询订单状态请求参数: request {request} ")
            response = json_parse(self.client.execute(request))
            NLogger.info(f"查询订单状态响应参数: response {response} ")
            if response.get("code") == SUCCESS_CODE:
                order_status = OrderStatus.WAIT_PAY
                if response.get("trade_status") in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
                    order_status = OrderStatus.PAID
                elif response.get("trade_status") == "TRADE_CLOSED":
                    order_status = OrderStatus.CLOSED
                return True, "OK", {"trade_status": order_status, "trade_no": response.get("trade_no"), "order_no": response.get("out_trade_no")}
            else:
                return False, response.get("msg"), response
        except AopException as e:
            NLogger.error(f"查询订单状态失败: {str(e)}")

    def refund(self, out_trade_no, refund_amount, refund_reason=None):
        """
        发起退款
        :param out_trade_no: 商户订单号
        :param refund_amount: 退款金额（单位：元）
        :param refund_reason: 退款原因
        :return: 退款结果
        """
        try:
            # 创建退款模型
            model = AlipayTradeRefundModel()
            model.out_trade_no = out_trade_no
            model.refund_amount = str(refund_amount)
            if refund_reason:
                model.refund_reason = refund_reason

            # 创建退款请求
            request = AlipayTradeRefundRequest(biz_model=model)

            # 执行退款
            response = self.client.execute(request)
            return response
        except AopException as e:
            NLogger.error(f"发起退款失败: {str(e)}")
            raise

    def close_trade(self, out_trade_no):
        """
        关闭订单
        :param out_trade_no: 商户订单号
        :return: 关闭结果
        """
        try:
            # 创建关闭模型
            model = AlipayTradeCloseModel()
            model.out_trade_no = out_trade_no

            # 创建关闭请求
            request = AlipayTradeCloseRequest(biz_model=model)

            # 执行关闭
            response = self.client.execute(request)
            return response
        except AopException as e:
            NLogger.error(f"关闭订单失败: {str(e)}")
            raise

    def verify_callback(self, request_data, sign):
        """
        验证支付宝回调通知
        :param request_data: 回调请求数据
        :param sign: 回调请求签名
        :return: 验证结果和支付信息
        """
        try:
            # 获取请求参数
            params = request_data.copy()
            # 移除签名参数
            params.pop('sign_type', None)
            params.pop('sign', None)
            clean_params = {}
            for k, v in params.items():
                if k == "fund_bill_list":
                    clean_params[k] = v[0]
                else:
                    if isinstance(v, list):
                        clean_params[k] = v[0]
                    else:
                        clean_params[k] = v
            data = self.verify_payment(clean_params, sign)
            # 验证签名
            if not data:
                NLogger.error("支付宝回调签名验证失败")
                return False, None

            # 获取支付信息
            trade_status = clean_params.get('trade_status')
            out_trade_no = clean_params.get('out_trade_no')
            trade_no = clean_params.get('trade_no')
            data = {
                "order_no": clean_params.get('out_trade_no'),
                "trade_no": clean_params.get('trade_no'),
            }
            # 验证支付状态
            order_status = OrderStatus.FAIL
            if trade_status in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
                NLogger.info(f"支付成功: out_trade_no={out_trade_no}, trade_no={trade_no}")
                order_status = OrderStatus.PAID
            else:
                NLogger.warning(f"支付状态异常: {trade_status}")
            data["trade_status"] = order_status
            return True, data
        except Exception as e:
            NLogger.error(f"处理支付宝回调失败: {str(e)}")
            raise

    def handle_sync_callback(self, request_data):
        """
        处理同步回调（return_url）
        :param request_data: 同步回调请求数据
        :return: 处理结果
        """
        try:
            # 验证回调
            is_valid, pay_info = self.verify_callback(request_data)
            if not is_valid:
                return "fail"
                
            # 处理业务逻辑
            if self.payment_type == 'H5':
                # H5支付的同步回调处理逻辑
                NLogger.info(f"处理H5支付同步回调: {pay_info}")
                # TODO: 实现具体的业务处理逻辑
                
            return "success"
            
        except Exception as e:
            NLogger.error(f"处理同步回调失败: {str(e)}")
            raise

    def handle_async_callback(self, request_data):
        """
        处理异步回调（notify_url）
        :param request_data: 异步回调请求数据
        :return: 处理结果
        """
        try:
            # 验证回调
            is_valid, pay_info = self.verify_callback(request_data)
            if not is_valid:
                return "fail"
                
            # 处理业务逻辑
            if self.payment_type == 'H5':
                # H5支付的异步回调处理逻辑
                NLogger.info(f"处理H5支付异步回调: {pay_info}")
                # TODO: 实现具体的业务处理逻辑
                
            elif self.payment_type == 'APP':
                # APP支付的异步回调处理逻辑
                NLogger.info(f"处理APP支付异步回调: {pay_info}")
                # TODO: 实现具体的业务处理逻辑
                
            return "success"
            
        except Exception as e:
            NLogger.error(f"处理异步回调失败: {str(e)}")
            raise