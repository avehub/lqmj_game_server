# lucky_game/service/ios_payment.py
import base64
import json
import time
import hashlib
import hmac
import requests
from typing import Optional, Dict, Any
from nsanic.libs.mult_log import NLogger
from common.public.conf import IOSConfig, ENV
from lucky_game.const import OrderStatus, CurrencyType


class IOSpayPayment:
    """iOS 应用内购服务"""

    def __init__(self):
        """
        初始化iOS支付服务
        """
        sandbox = False
        if ENV == "prod":
            sandbox = True
        self.sandbox = sandbox
        self.bundle_id = IOSConfig.BUNDLE_ID
        self.key_id = IOSConfig.KEY_ID
        self.issuer_id = IOSConfig.ISSUER_ID
        self.private_key = IOSConfig.PRIVATE_KEY
        # self.apple_root_ca = IOSConfig.APPLE_ROOT_CA

    def generate_jwt_token(self) -> str:
        """生成JWT token用于App Store Server API认证"""
        header = {
            "alg": "ES256",
            "kid": self.key_id,
            "typ": "JWT"
        }

        now = int(time.time())
        payload = {
            "iss": self.issuer_id,
            "iat": now,
            "exp": now + 1200,  # 20分钟有效期
            "aud": "appstoreconnect-v1",
            "bid": self.bundle_id
        }

        # 生成JWT
        encoded_header = base64.urlsafe_b64encode(
            json.dumps(header).encode('utf-8')
        ).decode('utf-8').rstrip('=')

        encoded_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode('utf-8')
        ).decode('utf-8').rstrip('=')

        message = f"{encoded_header}.{encoded_payload}"

        # 使用私钥签名
        signature = hmac.new(
            self.private_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()

        encoded_signature = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

        return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

    async def verify_receipt(self, receipt_data: str) -> Dict[str, Any]:
        """
        验证App Store收据
        :param receipt_data: 客户端传上来的收据数据(base64编码)
        :return: 验证结果
        """
        url = (
            "https://sandbox.itunes.apple.com/verifyReceipt"
            if self.sandbox
            else "https://buy.itunes.apple.com/verifyReceipt"
        )

        payload = {
            "receipt-data": receipt_data,
            "password": IOSConfig.SHARED_SECRET,  # 仅用于自动续期订阅
            "exclude-old-transactions": True
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()

            # 如果是沙箱环境但收据是生产环境的，重试沙箱环境
            if (result.get("status") == 21007 and not self.sandbox):
                self.sandbox = True
                return await self.verify_receipt(receipt_data)

            return result

        except Exception as e:
            NLogger.error(f"iOS receipt verification failed: {str(e)}")
            return {"status": -1, "message": str(e)}

    async def process_payment(self, order_id: str, receipt_data: str):
        """
        处理iOS支付
        :param order_id: 订单ID
        :param receipt_data: 收据数据
        :return: 处理结果
        """
        # 验证收据
        receipt_info = await self.verify_receipt(receipt_data)
        NLogger.info("IOS支付回调通知 解析回调数据", receipt_info)
        if not receipt_info or "status" not in receipt_info:
            NLogger.error("IOS支付回调通知 解析回调数据 失败", receipt_info)
            return False, "收据验证失败"
        NLogger.info("IOS支付回调Msg", self._get_error_message(receipt_info.get("status")))
        order_status = OrderStatus.FAIL
        if receipt_info.get("status") == 0:
            order_status = OrderStatus.PAID
        # IOS7版本以上才会存在in_app
        if "in_app" in receipt_info:
            data = receipt_info.get("in_app")
            order_id = data.get('hf_seq_id')
        else:
            data = receipt_info.get("receipt")
            order_id = data.get('hf_seq_id')
        result = {
            "order_no": order_id,
            "order_status": order_status,
        }
        return True, result

    def _validate_order(self, receipt_info: Dict[str, Any], order_id: str) -> bool:
        """验证订单信息是否匹配"""
        result = False
        # 订单验证逻辑
        # 检查product_id是否与订单匹配，金额是否一致等
        return result

    @staticmethod
    def _get_error_message(status: int) -> str:
        """获取错误信息"""
        error_messages = {
            21000: "App Store无法读取你提供的JSON对象",
            21002: "收据数据不符合格式",
            21003: "收据无法被验证",
            21004: "你提供的共享密钥和账户的共享密钥不一致",
            21005: "收据服务器当前不可用",
            21006: "收据是有效的，但订阅服务已经过期",
            21007: "收据信息是测试用（sandbox），但却被发送到产品环境中验证",
            21008: "收据信息是产品环境中使用，但却被发送到测试环境中验证",
            21010: "此收据无法被授权",
            21100: "内部数据访问错误",
        }
        return error_messages.get(status, f"未知错误 (状态码: {status})")


# 创建全局实例
ios_payment_service = IOSpayPayment()
