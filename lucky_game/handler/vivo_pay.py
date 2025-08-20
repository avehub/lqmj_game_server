"""
VIVO支付处理
"""
import time
import json
import hashlib
import requests
from urllib.parse import quote
from nsanic.libs.mult_log import NLogger
from common.public.conf import ENV, VIVO_APP_ID, VIVO_APP_KEY, VIVO_CP_ID

class VivoPayment:
    """VIVO支付处理类"""
    
    # VIVO支付环境配置
    if ENV == "prod":
        GATEWAY = "https://pay.vivo.com.cn/vivopay"
    else:
        GATEWAY = "https://sandbox.vivopos.com/vivopay"
    
    def __init__(self):
        self.app_id = VIVO_APP_ID
        self.app_key = VIVO_APP_KEY
        self.cp_id = VIVO_CP_ID
    
    def _generate_sign(self, params: dict) -> str:
        """生成签名"""
        # 1. 参数按key排序
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        # 2. 拼接参数
        sign_str = ""
        for k, v in sorted_params:
            if v and k != 'signature':
                sign_str += f"{k}={v}&"
        # 3. 拼接appKey
        sign_str += f"key={self.app_key}"
        # 4. 计算MD5
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
    
    async def create_order(self, order_no: str, amount: float, product_name: str, 
                         product_desc: str = "", notify_url: str = None) -> dict:
        """
        创建VIVO支付订单
        :param order_no: 商户订单号
        :param amount: 金额(元)
        :param product_name: 商品名称
        :param product_desc: 商品描述
        :param notify_url: 支付结果通知地址
        :return: 支付参数
        """
        try:
            # 转换为分
            total_fee = int(float(amount) * 100)
            
            params = {
                'version': '1.0.0',
                'cpId': self.cp_id,
                'appId': self.app_id,
                'cpOrderNumber': order_no,
                'notifyUrl': notify_url or f"{self.GATEWAY}/v1/notify/vivo",
                'orderTime': time.strftime('%Y%m%d%H%M%S'),
                'orderAmount': str(total_fee),
                'orderTitle': product_name,
                'orderDesc': product_desc or product_name,
                'signMethod': 'MD5',
                'extInfo': json.dumps({"uid": ""})  # 可以传递额外参数
            }
            
            # 生成签名
            sign = self._generate_sign(params)
            params['signature'] = sign
            
            # 发起支付请求
            response = requests.post(
                f"{self.GATEWAY}/v1/order/create",
                json=params,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            NLogger.info(f"VIVO create_order response: {result}")
            
            if result.get('respCode') == '0000':
                return True, {
                    'order_no': order_no,
                    'pay_info': result.get('payInfo', ''),
                    'trade_no': result.get('tradeNo', '')
                }
            else:
                return False, f"VIVO支付创建失败: {result.get('respMsg')}"
                
        except Exception as e:
            NLogger.error(f"VIVO支付创建订单异常: {str(e)}")
            return False, f"VIVO支付创建订单异常: {str(e)}"
    
    async def verify_notify(self, params: dict) -> tuple:
        """
        验证VIVO支付结果通知
        :param params: 通知参数
        :return: (是否成功, 订单号, 交易号, 金额(分))
        """
        try:
            sign = params.pop('signature', '')
            local_sign = self._generate_sign(params)
            
            if sign != local_sign:
                return False, None, None, None
                
            # 验证订单状态
            if params.get('tradeStatus') == '0000':  # 支付成功
                return (
                    True,
                    params.get('cpOrderNumber'),
                    params.get('tradeNo'),
                    int(params.get('orderAmount', 0))
                )
            return False, None, None, None
            
        except Exception as e:
            NLogger.error(f"VIVO支付通知验证异常: {str(e)}")
            return False, None, None, None

# 创建全局实例
vivo_payment = VivoPayment()
