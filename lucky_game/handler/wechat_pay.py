# lucky_game/handler/wechat_pay.py
from typing import Dict, Optional, Union
from wechatpayv3 import WeChatPay, WeChatPayType
from common.public.conf import WeChatConf
from nsanic.libs.mult_log import NLogger

class WeChatPayService:
    def __init__(self):
        """Initialize WeChat Pay service with configuration"""
        self.wxpay = WeChatPay(
            wechatpay_type=WeChatPayType.MINIPROG,
            mchid=WeChatConf.MCHID,
            private_key=WeChatConf.PRIVATE_KEY,
            cert_serial_no=WeChatConf.CERT_SERIAL_NO,
            apiv3_key=WeChatConf.APIV3_KEY,
            appid=WeChatConf.APPID,
            notify_url=WeChatConf.NOTIFY_URL,
            cert_dir=WeChatConf.CERT_DIR,
            partner_mode=WeChatConf.PARTNER_MODE,
            proxy=WeChatConf.PROXY,
            timeout=WeChatConf.TIMEOUT,
        )

    # ========== 支付方法 ==========

    async def create_native_payment(
            self,
            out_trade_no: str,
            amount: int,
            description: str,
            **kwargs
    ) -> Dict:
        """
        创建Native支付订单（扫码支付）
        :param out_trade_no: 商户订单号
        :param amount: 金额（分）
        :param description: 商品描述
        :return: 支付参数
        """
        try:
            code, message = await self.wxpay.pay(
                description=description,
                out_trade_no=out_trade_no,
                amount={'total': amount},
                pay_type=WeChatPayType.NATIVE,
                **kwargs
            )
            if code in [200, 201]:
                return {'code': 0, 'data': message}
            return {'code': -1, 'message': message}
        except Exception as e:
            NLogger.error(f"Native支付创建失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    async def create_jsapi_payment(
            self,
            openid: str,
            out_trade_no: str,
            amount: int,
            description: str,
            **kwargs
    ) -> Dict:
        """
        创建JSAPI支付订单（小程序/公众号支付）
        :param openid: 用户openid
        :param out_trade_no: 商户订单号
        :param amount: 金额（分）
        :param description: 商品描述
        :return: 支付参数
        """
        try:
            code, message = await self.wxpay.pay(
                description=description,
                out_trade_no=out_trade_no,
                amount={'total': amount},
                pay_type=WeChatPayType.JSAPI,
                payer={'openid': openid},
                **kwargs
            )
            if code in [200, 201]:
                return {'code': 0, 'data': message}
            return {'code': -1, 'message': message}
        except Exception as e:
            NLogger.error(f"JSAPI支付创建失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    async def create_app_payment(
            self,
            out_trade_no: str,
            amount: int,
            description: str,
            **kwargs
    ) -> Dict:
        """
        创建APP支付订单
        """
        try:
            code, message = await self.wxpay.pay(
                description=description,
                out_trade_no=out_trade_no,
                amount={'total': amount},
                pay_type=WeChatPayType.APP,
                **kwargs
            )
            if code in [200, 201]:
                return {'code': 0, 'data': message}
            return {'code': -1, 'message': message}
        except Exception as e:
            NLogger.error(f"APP支付创建失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    async def create_h5_payment(
            self,
            out_trade_no: str,
            amount: int,
            description: str,
            **kwargs
    ) -> Dict:
        """
        创建H5支付订单
        """
        try:
            code, message = await self.wxpay.pay(
                description=description,
                out_trade_no=out_trade_no,
                amount={'total': amount},
                pay_type=WeChatPayType.H5,
                scene_info={
                    'h5_info': {
                        'type': 'Wap',
                        'app_name': 'Your App Name',
                        'app_url': 'https://your-domain.com'
                    }
                },
                **kwargs
            )
            if code in [200, 201]:
                return {'code': 0, 'data': message}
            return {'code': -1, 'message': message}
        except Exception as e:
            NLogger.error(f"H5支付创建失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    # ========== 查询与操作 ==========

    async def query_order(
            self,
            out_trade_no: str = None,
            transaction_id: str = None
    ) -> Dict:
        """
        查询订单
        :param out_trade_no: 商户订单号
        :param transaction_id: 微信支付订单号
        :return: 订单信息
        """
        try:
            code, message = await self.wxpay.query(out_trade_no=out_trade_no, transaction_id=transaction_id)
            if code == 200:
                return {'code': 0, 'data': message}
            return {'code': -1, 'message': message}
        except Exception as e:
            NLogger.error(f"订单查询失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    async def close_order(self, out_trade_no: str) -> Dict:
        """
        关闭订单
        :param out_trade_no: 商户订单号
        :return: 操作结果
        """
        try:
            code, message = await self.wxpay.close(out_trade_no=out_trade_no)
            if code == 200:
                return {'code': 0, 'message': '订单已关闭'}
            return {'code': -1, 'message': message}
        except Exception as e:
            NLogger.error(f"订单关闭失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    async def refund(
            self,
            out_refund_no: str,
            amount: int,
            out_trade_no: str = None,
            transaction_id: str = None,
            reason: str = None,
            **kwargs
    ) -> Dict:
        """
        申请退款
        :param out_refund_no: 商户退款单号
        :param amount: 退款金额（分）
        :param out_trade_no: 商户订单号
        :param transaction_id: 微信支付订单号
        :param reason: 退款原因
        :return: 退款结果
        """
        try:
            code, message = await self.wxpay.refund(
                out_refund_no=out_refund_no,
                amount={'refund': amount, 'total': amount, 'currency': 'CNY'},
                out_trade_no=out_trade_no,
                transaction_id=transaction_id,
                reason=reason,
                **kwargs
            )
            if code == 200:
                return {'code': 0, 'data': message}
            return {'code': -1, 'message': message}
        except Exception as e:
            NLogger.error(f"退款申请失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    # ========== 回调处理 ==========

    async def verify_notification(self, request) -> Optional[Dict]:
        """
        验证支付结果通知
        :param request: FastAPI请求对象
        :return: 解析后的通知数据或None
        """
        try:
            # 获取请求头
            headers = {
                'Wechatpay-Signature': request.headers.get('Wechatpay-Signature', ''),
                'Wechatpay-Timestamp': request.headers.get('Wechatpay-Timestamp', ''),
                'Wechatpay-Nonce': request.headers.get('Wechatpay-Nonce', ''),
                'Wechatpay-Serial': request.headers.get('Wechatpay-Serial', ''),
            }

            # 获取请求体
            body = await request.body()

            # 验证签名并解密数据
            result = await self.wxpay.decrypt(headers, body)
            if result and 'resource' in result:
                return result['resource']
            return None
        except Exception as e:
            NLogger.error(f"支付通知验证失败: {str(e)}")
            return None


# 创建全局实例
wechat_pay_service = WeChatPayService()