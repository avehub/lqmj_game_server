# lucky_game/handler/apple.py
import base64
import json
import time
import hashlib
import hmac

import aiohttp
import jwt
import requests
from typing import Optional, Dict, Any
from nsanic.libs.mult_log import NLogger
from common.public.conf import IOSConfig, ENV
from lucky_game.const import OrderStatus, CurrencyType


class AppleService:
    """iOS 应用内购服务"""

    def __init__(self,):
        """
        初始化iOS支付服务
        """
        sandbox = True
        if ENV == "prod":
            sandbox = False
        self.sandbox = sandbox
        self.bundle_id = IOSConfig.BUNDLE_ID
        self.key_id = IOSConfig.KEY_ID
        self.issuer_id = IOSConfig.ISSUER_ID
        self.private_key = IOSConfig.PRIVATE_KEY
        self.team_id = IOSConfig.TEAM_ID
        # self.apple_root_ca = IOSConfig.APPLE_ROOT_CA
        self.url = (
            "https://sandbox.itunes.apple.com/verifyReceipt"
            if self.sandbox
            else "https://buy.itunes.apple.com/verifyReceipt"
        )

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

    def _generate_client_secret(self) -> str:
        """
        生成 Apple 客户端密钥
        注意：这里需要你的 Apple 开发者账号的私钥
        """
        # 从配置中获取私钥信息
        private_key = self.private_key

        # 创建 JWT 头部
        headers = {
            "alg": "ES256",
            "kid": self.key_id,  # 在 Apple 开发者网站创建的密钥 ID
            "typ": "JWT"
        }

        # 创建 JWT 负载
        now = int(time.time())
        payload = {
            "iss": self.team_id,  # 你的团队 ID
            "iat": now,
            "exp": now + 3600,  # 1 小时过期
            "aud": "https://appleid.apple.com",
            "sub": "YOUR_CLIENT_ID"  # 你的 App ID 或 Services ID
        }

        # 生成 JWT
        client_secret = jwt.encode(
            payload=payload,
            key=private_key,
            algorithm="ES256",
            headers=headers
        )

        return client_secret

    async def verify_receipt(self, receipt_data: str) -> Dict[str, Any]:
        """
        验证App Store收据
        :param receipt_data: 客户端传上来的收据数据(base64编码)
        :return: 验证结果
        """
        payload = {
            "receipt-data": receipt_data,
            "password": IOSConfig.SHARED_SECRET,  # 仅用于自动续期订阅
            "exclude-old-transactions": True
        }

        try:
            response = requests.post(self.url, json=payload, timeout=10)
            result = response.json()

            # 如果是沙箱环境但收据是生产环境的，重试沙箱环境
            if (result.get("status") == 21007 and not self.sandbox):
                self.sandbox = True
                return await self.verify_receipt(receipt_data)

            return result

        except Exception as e:
            NLogger.error(f"iOS receipt verification failed: {str(e)}")
            return {"status": -1, "message": str(e)}

    async def process_payment(self, order_id: str, receipt_data: str, sandbox: int):
        """
        处理iOS支付
        :param order_id: 订单ID
        :param receipt_data: 收据数据
        :param sandbox: 沙箱环境：0否 1是
        :return: 处理结果
        """
        if sandbox:
            self.sandbox = True
            self.url = "https://sandbox.itunes.apple.com/verifyReceipt"
        # 验证收据
        receipt_info = await self.verify_receipt(receipt_data)
        NLogger.info("IOS支付回调通知 解析回调数据", receipt_info)
        if not receipt_info or "status" not in receipt_info:
            NLogger.error("IOS支付回调通知 解析回调数据 失败", receipt_info)
            NLogger.info("IOS支付回调失败原因Msg", self._get_error_message(receipt_info.get("status")))
            return False, "收据验证失败"
        order_status = OrderStatus.FAIL
        transaction_id = ""
        if receipt_info.get("status") == 0:
            order_status = OrderStatus.PAID
            # IOS7版本以上才会存在in_app
            data = receipt_info.get("receipt")
            if "in_app" in data:
                in_app = data.get("in_app")
                transaction_id = in_app[0].get('transaction_id')
            else:
                transaction_id = data.get('transaction_id')
        result = {
            "order_no": order_id,
            "trade_no": transaction_id,
            "trade_status": order_status,
        }
        return True, result

    async def query_order(self, receipt_data: str, is_sandbox: bool = False):
        """
        查询苹果支付订单状态

        Args:
            receipt_data: 苹果支付收据数据(base64编码)
            is_sandbox: 是否沙箱环境

        Returns:
            Tuple[是否成功, 消息, 订单信息]
        """
        try:
            # 1. 准备请求参数
            payload = {
                "receipt-data": receipt_data,
                "password": self.shared_secret,  # 如果有配置共享密钥
                "exclude-old-transactions": True  # 只返回最新的收据信息
            }

            # 2. 发送验证请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        self.url,
                        json=payload,
                        timeout=10
                ) as response:
                    if response.status != 200:
                        return False, f"请求失败，状态码: {response.status}", None

                    result = await response.json()
                    NLogger.info(f"Apple 订单查询响应: {result}")

                    # 3. 处理响应
                    status = result.get('status', -1)

                    # 状态码为0表示成功
                    if status == 0:
                        # 获取收据信息
                        receipt = result.get('receipt', {})
                        latest_receipt_info = result.get('latest_receipt_info')

                        # 如果有最新的收据信息，使用最新的
                        if latest_receipt_info:
                            if isinstance(latest_receipt_info, list) and len(latest_receipt_info) > 0:
                                receipt_info = latest_receipt_info[-1]  # 取最新的交易记录
                            else:
                                receipt_info = latest_receipt_info
                        else:
                            receipt_info = receipt.get('in_app', [{}])[0] if receipt.get('in_app') else {}

                        # 提取订单信息
                        order_info = {
                            "transaction_id": receipt_info.get('transaction_id', ''),
                            "original_transaction_id": receipt_info.get('original_transaction_id', ''),
                            "product_id": receipt_info.get('product_id', ''),
                            "purchase_date_ms": receipt_info.get('purchase_date_ms', ''),
                            "expires_date_ms": receipt_info.get('expires_date_ms', ''),
                            "is_trial_period": receipt_info.get('is_trial_period', ''),
                            "environment": "Sandbox" if is_sandbox else "Production",
                            "status": status
                        }

                        return True, "查询成功", order_info
                    else:
                        # 返回错误信息
                        error_msg = self._get_error_message(status)
                        NLogger.error(f"Apple 订单查询失败: {error_msg}")
                        return False, error_msg, None

        except aiohttp.ClientError as e:
            NLogger.error(f"Apple 订单查询网络错误: {str(e)}")
            return False, f"网络错误: {str(e)}", None
        except Exception as e:
            NLogger.error(f"Apple 订单查询异常: {str(e)}")
            return False, f"查询异常: {str(e)}", None

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

    async def get_apple_user_info(self, code: str) -> dict:
        """
        使用 Apple 授权码获取用户信息
        :param code: Apple 授权码
        :return: 用户信息字典
        """
        try:
            # 1. 使用 code 获取 access token
            token_url = "https://appleid.apple.com/auth/token"
            headers = {'content-type': "application/x-www-form-urlencoded"}

            # 2. 准备请求参数
            data = {
                'client_id': self.bundle_id,  # 你的 App ID
                'client_secret': self._generate_client_secret(),
                'code': code,
                'grant_type': 'authorization_code',
            }

            # 3. 发送请求获取 access token
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data, headers=headers) as response:
                    result = await response.json()

            # 4. 检查错误
            if 'error' in result:
                NLogger.error(f"Apple token 获取失败: {result}")
                return {}

            # 5. 解析 id_token 获取用户信息
            id_token = result.get('id_token')
            if not id_token:
                return {}

            # 6. 解析 JWT token (不验证签名，因为我们已经从 Apple 获取的 token)
            try:
                payload = jwt.decode(id_token, options={"verify_signature": False})
                return payload
            except jwt.PyJWTError as e:
                NLogger.error(f"解析 Apple id_token 失败: {str(e)}")
                return {}

        except Exception as e:
            NLogger.error(f"获取 Apple 用户信息失败: {str(e)}")
            return {}


# 创建全局实例
ios_service = AppleService()

