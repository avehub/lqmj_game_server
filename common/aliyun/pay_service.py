from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayTradeCreateModel import AlipayTradeCreateModel
from alipay.aop.api.domain.AlipayTradeAppPayModel import AlipayTradeAppPayModel
from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel
from alipay.aop.api.domain.AlipayTradeRefundModel import AlipayTradeRefundModel
from alipay.aop.api.domain.AlipayTradeCloseModel import AlipayTradeCloseModel
from alipay.aop.api.request.AlipayTradeAppPayRequest import AlipayTradeAppPayRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.request.AlipayTradeRefundRequest import AlipayTradeRefundRequest
from alipay.aop.api.request.AlipayTradeCloseRequest import AlipayTradeCloseRequest
from alipay.aop.api.request.AlipayTradeWapPayRequest import AlipayTradeWapPayRequest
from alipay.aop.api.response.AlipayResponse import AlipayResponse
from alipay.aop.api.response.AlipayTradeAppPayResponse import AlipayTradeAppPayResponse
from alipay.aop.api.response.AlipayTradeQueryResponse import AlipayTradeQueryResponse
from alipay.aop.api.response.AlipayTradeRefundResponse import AlipayTradeRefundResponse
from alipay.aop.api.response.AlipayTradeCloseResponse import AlipayTradeCloseResponse
from alipay.aop.api.exception.Exception import AopException
from alipay.aop.api.util.SignatureUtils import get_sign_content, verify_with_rsa
from common.public.conf import AliPayConf
from datetime import datetime
from nsanic.libs.mult_log import NLogger
from alipay.aop.api.util import EncryptUtils


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
        # self.client_config.app_id = self.type_conf.get("APP_ID")
        # self.client_config.app_private_key = self.type_conf.get("PRIVATE_KEY")
        # self.client_config.return_url = AliPayConf.RETURN_URL
        # self.client_config.alipay_public_key = AliPayConf.ALIPAY_PUBLIC_KEY
        # self.notify_url = AliPayConf.NOTIFY_URL
        self.private_key = self.type_conf.get("PRIVATE_AES")
        """ 沙箱环境配置
        APPID: 9021000140665835
        应用名称: sandbox 默认应用:2088721044134099
        绑定的商家账号（PID）: 2088721044134099
        支付宝网关地址: https://openapi-sandbox.dl.alipaydev.com/gateway.do
        """
        self.client_config.app_id = "9021000140665835"
        self.client_config.app_private_key = "MIIEowIBAAKCAQEAtOuLYXapuud0HcAyokJtNCXvYuIW0Nn07oRXzLuALzZeyISMRbiNPmM3O2cyKayhPcmYNmD33hvTPIaU4P6TEj8Te4I8ronYLqrCPjUGX5p+/Pai2YsxRtdHRwlSjZARdpXP3s30U7eDdPTeLyuHQa6JXw4IGMnjrFc/3C87FBjqOGRlpErKhV5fTVPPheTuphl2XuQOCY7okj4oEync8y+Zl9q7msK0ZGUFOLcqcJ9kUPc1KFBD3ilNzVd4POJ50u29SM6BieUET6mTIcYuuz4HsaeqCXjl8+Z7QIw96Whm7ZVtQX7sxQyhMWkn5tJptjFg9n91SDGhlxS8c4W5uwIDAQABAoIBABlqqeckW431bDutv69J87uKxMm4h4oJxL4pe4g4ozZ+xewXqvk0hytHlv/SbJqsNO7QPoENOGVMtW1gXtQJD7JViDAmyM2gce2Ecct5eY6+zq5NG+3B/0c7gTj6l01p+voU6+IaPwPv2Rj6OaiYzeStV4EyIHMTEdgpXcBaJkuZQ/aUjU2JpXyTWvSTqt7OQ+0F/TCSu3UHAFfr5l7e7POvbjvTH4jfJu/Oe/xvVE2sNdo7sssemAxgNkpabx5hE2VvUZXuYFFrCYcwGQrar+bdUJvApcZiIf7gVaaJh8RzJq9jCbcFO/CS/oahmmr4IDiOwa9AZJt4ftcVGIPJytkCgYEA3ioe6TsFIE7O7GWZEuafMFHcakTeynnUh3fWhKpo0usrSZmfWN0rn/aHagSIMkCYKyDRvYHOn7NobfZw0fgcpv6a5M28fdklY5kDJlYbbGBUkSUzfGygmft0E3On8FsSowQUZod07jhJZKyct5fxEmNwxYQXAhJZ/+K4ESbhWLcCgYEA0HlcmFpJY9xIOcSYMM5Ja9LkbVHiAaSDbSwxd1hB64MnfOs0F0AWYEg73uk9i+pHd0q9iCTQPbwG5X72LegClWTjrlJPNMWXpVKlauf63zqm9+UzNhCEF8fHcjP1rC0+ElzYuF7sd3N2RQJ5KVyg6WtOBDAXUbWMKRIYHQZXux0CgYB24ldUO28M0N9OBTgasyqwcr3eaChIdVVTgL9ckswxQgMSCZEJvqDfos7n3rD7IzHKsm9KV7I4J4tUfLH2yiya+Ffu5GFfftnRKEpVM3LNVecrHJsmlAKFI9gDqLpPloysizxXeVkLOTedFflvDXHFg00PhRXC2AstMSeKliG0lQKBgQCR0vJ0F2OSmHlk/yE9sm4lH+VsmoQuhfbwnKMVSgUCSkGK3bMYOFnui1hluly0y/GlfgBJhQasyCNC0KY+wjVcbq/cNfL1hOloWQEgYJhZIVu9tvM1dCQRxkq6laHZB+SNT6jAfpWFkJw/9VTvG73qyIZP45vMKeOaru9zDga7+QKBgBEi05i4WyhmXv6KzXSEMs53GtQ7h5TusynrTzDB257S9MRIgei63gJFIFrf92QKoLfEbjV5r6KYiHQTTBDhBHyXc4Tf1O56IgelLo2ziaEZpLqkK1g4rv8KNsDpfCNSPAwWv+swaoMnD+EuxbpJGllTeU711v276UK/FjKmUNcY"
        self.client_config.server_url = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
        self.client_config.alipay_public_key = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzlMZ5W/L5Nd5vnhPDJLb+02ss8yLzmuCKNOhbAZaADFpbG5taaJeMHsSPHBEd+eSx0PmCYeejvYkYv8t17a2qBx2DA7lf59prH+Oc3bRHRPvw3Y3PZgCN1deOv4gwJKGW2s3xnVtyeqrDrquYXphHZ94zCqU7e/dd7OGpVH0V9NsvevjHSvq7NAoP0YzYsezf2EYozWoUozu8w/BW6wkE6V+UuO0IW5+1tVzTyAPaISSubHykGpjuu/twVE6XAQxMskWz9DJr3cX9bWxIiSuaRMQ0jtOphBNU9AzFwbsT+ZozBxlirOpctgiHMEfFMGLBkEQFW6jSZQiEOr6cGDRhQIDAQAB"
        self.notify_url = "https://jadzzweb.0858sy.com/luckyGame/CallbackAli"

        # 初始化客户端
        self.client = DefaultAlipayClient(self.client_config)
        # 保存支付类型
        self.payment_type = payment_type

    def create_h5_payment(self, subject, out_trade_no, total_amount, return_url=None):
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
            response_content = self.client.sdk_execute(request)
            NLogger.info(f"支付宝APP支付订单响应参数: response {response_content} ")
            response = AlipayTradeAppPayResponse()
            # 解析响应结果
            response.parse_response_content(response_content)
            NLogger.info(f"支付宝APP支付订单响应参数解析: response {response} ")
            if response.is_success():
                return True, "OK", response.body
            else:
                return False, response.msg, response
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
            NLogger.error(f"验证支付通知: sign_content {str(sign_content)}")
            # 使用支付宝公钥验证签名
            if sign_content:
                return verify_with_rsa(self.client_config.alipay_public_key, sign_content, signature)
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
            response = self.client.execute(request)
            return response
        except AopException as e:
            NLogger.error(f"查询订单状态失败: {str(e)}")
            raise

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

    def verify_callback(self, request_data):
        """
        验证支付宝回调通知
        :param request_data: 回调请求数据
        :return: 验证结果和支付信息
        """
        try:
            # 获取请求参数
            params = request_data.copy()
            sign_type = params.get('sign_type', None)
            encrypt_type = params.pop('encrypt_type', None)
            # 移除签名参数
            sign = params.pop('sign', None)
            data = self.verify_payment(params, sign)
            
            # 验证签名
            if not data:
                NLogger.error("支付宝回调签名验证失败")
                return False, None
            if encrypt_type == 'AES':
                data = self.verify_aes(data)
                
            # 获取支付信息
            trade_status = params.get('trade_status')
            out_trade_no = params.get('out_trade_no')
            trade_no = params.get('trade_no')
            total_amount = params.get('total_amount')
            
            # 验证支付状态
            if trade_status == 'TRADE_SUCCESS':
                NLogger.info(f"支付成功: out_trade_no={out_trade_no}, trade_no={trade_no}")
                return True, {
                    'trade_status': trade_status,
                    'out_trade_no': out_trade_no,
                    'trade_no': trade_no,
                    'total_amount': total_amount
                }
            else:
                NLogger.warning(f"支付状态异常: {trade_status}")
                return False, None
                
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