"""阿里云短信服务封装"""
import json
import logging
from typing import Dict, Any, List, Optional, Union
from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
from alibabacloud_tea_util import models as util_models

from common.public.conf import AliYunSms

logger = logging.getLogger('sms')


class AliyunSmsService:
    def __init__(self):
        self.client = self._create_client()

    def _create_client(self) -> Dysmsapi20170525Client:
        """
        创建阿里云短信客户端
        """
        config = open_api_models.Config(
            access_key_id=AliYunSms.ACCESS_KEY_ID,
            access_key_secret=AliYunSms.ACCESS_KEY_SECRET,
            endpoint=AliYunSms.ENDPOINT
        )
        return Dysmsapi20170525Client(config)

    async def send_sms(self,
                       phone_number: str,
                       template_code: str,
                       template_param: Dict[str, Any] = None,
                       sign_name: str = None) -> Dict[str, Any]:
        """
        发送短信

        Args:
            phone_number: 接收短信的手机号码
            template_code: 短信模板CODE
            template_param: 短信模板参数，JSON格式
            sign_name: 短信签名，默认使用配置中的签名

        Returns:
            Dict: 发送结果
        """
        try:
            if sign_name is None:
                sign_name = AliYunSms.SIGN_NAME

            # 构造请求
            request = dysmsapi_models.SendSmsRequest(
                phone_numbers=phone_number,
                sign_name=sign_name,
                template_code=template_code,
                template_param=json.dumps(template_param) if template_param else None
            )

            # 发送请求
            runtime = util_models.RuntimeOptions()
            response = await self.client.send_sms_with_options_async(request, runtime)

            # 处理响应
            result = {
                'success': response.body.code == 'OK',
                'request_id': response.body.request_id,
                'code': response.body.code,
                'message': response.body.message,
                'biz_id': response.body.biz_id
            }

            # 记录日志
            if result['success']:
                logger.info(
                    f"SMS sent successfully to {phone_number}, template: {template_code}, bizId: {result['biz_id']}")
            else:
                logger.error(
                    f"Failed to send SMS to {phone_number}, template: {template_code}, error: {result['message']}")

            return result

        except Exception as e:
            logger.exception(f"SMS sending error: {str(e)}")
            return {
                'success': False,
                'code': 'ClientError',
                'message': str(e)
            }

    async def send_verification_code(self, phone_number: str, code: str, expire_minutes: int = 5) -> Dict[str, Any]:
        """
        发送验证码短信

        Args:
            phone_number: 接收短信的手机号码
            code: 验证码
            expire_minutes: 验证码有效期(分钟)

        Returns:
            Dict: 发送结果
        """
        template_param = {
            'code': code,
            'minutes': str(expire_minutes)
        }
        return await self.send_sms(
            phone_number=phone_number,
            template_code=AliYunSms.TEMPLATES['verification'],
            template_param=template_param
        )

    async def send_batch_sms(self,
                             phone_numbers: List[str],
                             template_code: str,
                             template_param: Union[Dict[str, Any], List[Dict[str, Any]]] = None,
                             sign_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        批量发送短信

        Args:
            phone_numbers: 接收短信的手机号码列表
            template_code: 短信模板CODE
            template_param: 短信模板参数，单一参数或列表参数
            sign_names: 短信签名列表，默认使用配置中的签名

        Returns:
            Dict: 发送结果
        """
        try:
            # 默认签名处理
            if sign_names is None:
                sign_names = [AliYunSms.SIGN_NAME] * len(phone_numbers)
            elif len(sign_names) != len(phone_numbers):
                raise ValueError("签名列表长度必须与手机号列表长度一致")

            # 模板参数处理
            if isinstance(template_param, dict):
                # 如果是单一参数，复制为列表
                template_params_list = [template_param] * len(phone_numbers)
            elif isinstance(template_param, list):
                # 如果是参数列表，确保长度一致
                if len(template_param) != len(phone_numbers):
                    raise ValueError("模板参数列表长度必须与手机号列表长度一致")
                template_params_list = template_param
            else:
                template_params_list = [None] * len(phone_numbers)

            # 构造请求
            request = dysmsapi_models.SendBatchSmsRequest(
                phone_number_json=json.dumps(phone_numbers),
                sign_name_json=json.dumps(sign_names),
                template_code=template_code,
                template_param_json=json.dumps([json.dumps(p) if p else "{}" for p in template_params_list])
            )

            # 发送请求
            runtime = util_models.RuntimeOptions()
            response = await self.client.send_batch_sms_with_options_async(request, runtime)

            # 处理响应
            result = {
                'success': response.body.code == 'OK',
                'request_id': response.body.request_id,
                'code': response.body.code,
                'message': response.body.message,
                'biz_id': response.body.biz_id
            }

            # 记录日志
            if result['success']:
                logger.info(
                    f"Batch SMS sent successfully to {len(phone_numbers)} recipients, template: {template_code}")
            else:
                logger.error(f"Failed to send batch SMS, template: {template_code}, error: {result['message']}")

            return result

        except Exception as e:
            logger.exception(f"Batch SMS sending error: {str(e)}")
            return {
                'success': False,
                'code': 'ClientError',
                'message': str(e)
            }


# 创建单例实例
sms_service = AliyunSmsService()
