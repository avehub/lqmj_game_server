import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import logging
import traceback
import functools
from typing import List, Callable, Type, Any, Optional, Union, Dict
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from common.public.conf import DINGTALK_SECRET, DINGTALK_WEBHOOK


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass
class DingTalkConfig:
    """钉钉机器人配置"""
    webhook_url: DINGTALK_WEBHOOK
    secret: DINGTALK_SECRET
    timeout: int = 30


class DingTalkRobotService:
    """
    钉钉机器人消息服务
    支持文本、链接、Markdown消息类型
    """

    def __init__(self, config: DingTalkConfig):
        """
        初始化钉钉机器人服务

        Args:
            config: 钉钉机器人配置
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DingTalk-Robot-Python/1.0'
        })

    def send_text_message(self, content: str, at_mobiles: Optional[List[str]] = None,
                          is_at_all: bool = False) -> bool:
        """
        发送文本消息

        Args:
            content: 消息内容
            at_mobiles: 被@的手机号列表
            is_at_all: 是否@所有人

        Returns:
            发送结果
        """
        try:
            message = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }

            if at_mobiles or is_at_all:
                message["at"] = {
                    "atMobiles": at_mobiles or [],
                    "isAtAll": is_at_all
                }

            return self._send_message(message)
        except Exception as e:
            logger.error(f"发送文本消息失败: {e}")
            return False

    def send_link_message(self, title: str, text: str, message_url: str,
                          pic_url: Optional[str] = None) -> bool:
        """
        发送链接消息

        Args:
            title: 消息标题
            text: 消息内容
            message_url: 点击消息跳转的URL
            pic_url: 图片URL

        Returns:
            发送结果
        """
        try:
            message = {
                "msgtype": "link",
                "link": {
                    "title": title,
                    "text": text,
                    "messageUrl": message_url
                }
            }

            if pic_url:
                message["link"]["picUrl"] = pic_url

            return self._send_message(message)
        except Exception as e:
            logger.error(f"发送链接消息失败: {e}")
            return False

    def send_markdown_message(self, title: str, text: str,
                              at_mobiles: Optional[List[str]] = None,
                              is_at_all: bool = False) -> bool:
        """
        发送Markdown消息

        Args:
            title: 首屏会话透出的展示内容
            text: markdown格式的消息
            at_mobiles: 被@的手机号列表
            is_at_all: 是否@所有人

        Returns:
            发送结果
        """
        try:
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": text
                }
            }

            if at_mobiles or is_at_all:
                message["at"] = {
                    "atMobiles": at_mobiles or [],
                    "isAtAll": is_at_all
                }

            return self._send_message(message)
        except Exception as e:
            logger.error(f"发送Markdown消息失败: {e}")
            return False

    def send_business_alert(self, alert_type: str, message: str,
                            level: AlertLevel = AlertLevel.INFO) -> bool:
        """
        发送业务告警消息（封装的便捷方法）

        Args:
            alert_type: 告警类型
            message: 告警消息
            level: 告警级别

        Returns:
            发送结果
        """
        emoji = self._get_emoji_by_level(level)
        title = f"{emoji} {alert_type}告警"

        content = f"""## {title}
**告警级别：** {level.value}
**告警时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**告警内容：** {message}
请及时处理！"""
        return self.send_markdown_message(title, content)

    def send_exception_alert(self, service_name: str, exception_message: str,
                             stack_trace: Optional[str] = None) -> bool:
        """
        发送异常告警消息

        Args:
            service_name: 服务名称
            exception_message: 异常信息
            stack_trace: 堆栈信息（可选）

        Returns:
            发送结果
        """
        content = f"""## 系统异常告警
**服务名称：** {service_name}
**异常时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**异常信息：** {exception_message}
"""

        if stack_trace:
            content += f"**堆栈信息：** \n```\n{stack_trace}\n```\n\n"

        content += "请立即处理！"

        return self.send_markdown_message("系统异常告警", content)

    def send_balance_alert(self, account_type: str, current_balance: float,
                           threshold: float) -> bool:
        """
        发送余额不足告警

        Args:
            account_type: 账户类型
            current_balance: 当前余额
            threshold: 告警阈值

        Returns:
            发送结果
        """
        title = "余额不足告警"
        content = f"""## {title}
**账户类型：** {account_type}
**当前余额：** {current_balance}
**告警阈值：** {threshold}
**告警时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
请及时充值！"""

        return self.send_markdown_message(title, content)

    def send_custom_card_message(self, title: str, content: str,
                                 buttons: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        发送自定义卡片消息

        Args:
            title: 卡片标题
            content: 卡片内容
            buttons: 按钮列表，格式: [{"title": "按钮名", "actionURL": "跳转链接"}]

        Returns:
            发送结果
        """
        try:
            message = {
                "msgtype": "actionCard",
                "actionCard": {
                    "title": title,
                    "text": content,
                    "hideAvatar": "0",
                    "btnOrientation": "0"
                }
            }

            if buttons:
                if len(buttons) == 1:
                    # 单个按钮
                    message["actionCard"]["singleTitle"] = buttons[0]["title"]
                    message["actionCard"]["singleURL"] = buttons[0]["actionURL"]
                else:
                    # 多个按钮
                    message["actionCard"]["btns"] = buttons

            return self._send_message(message)
        except Exception as e:
            logger.error(f"发送卡片消息失败: {e}")
            return False

    def _get_emoji_by_level(self, level: AlertLevel) -> str:
        """根据告警级别获取对应emoji"""
        emoji_map = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARN: "⚠️",
            AlertLevel.ERROR: "🚨"
        }
        return emoji_map.get(level, "📢")

    def _send_message(self, message: Dict[str, Any]) -> bool:
        """
        发送消息到钉钉

        Args:
            message: 消息内容

        Returns:
            发送结果
        """
        try:
            url = self._build_signed_url()

            response = self.session.post(
                url,
                json=message,
                timeout=self.config.timeout
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    logger.info(f"钉钉消息发送成功: {result}")
                    return True
                else:
                    logger.error(f"钉钉消息发送失败: {result}")
                    return False
            else:
                logger.error(f"钉钉消息发送失败，状态码: {response.status_code}, 响应: {response.text}")
                return False

        except Exception as e:
            logger.error(f"发送钉钉消息异常: {e}")
            return False

    def _build_signed_url(self) -> str:
        """
        构建带签名的URL

        Returns:
            签名后的URL
        """
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.config.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.config.secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')

        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

        return f"{self.config.webhook_url}&timestamp={timestamp}&sign={sign}"


# 单例模式的便捷类
class DingTalkNotifier:
    """钉钉通知器单例"""

    _instance = None
    _service = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        if DINGTALK_WEBHOOK and DINGTALK_SECRET:
            cls._instance.initialize()
        return cls._instance

    def initialize(self, webhook_url: str = DINGTALK_WEBHOOK, secret: str = DINGTALK_SECRET, timeout: int = 30):
        """
        初始化钉钉通知器

        Args:
            webhook_url: 钉钉机器人webhook地址
            secret: 钉钉机器人密钥
            timeout: 请求超时时间
        """
        config = DingTalkConfig(webhook_url, secret, timeout)
        self._service = DingTalkRobotService(config)

    def get_service(self) -> DingTalkRobotService:
        """获取钉钉机器人服务实例"""
        if self._service is None:
            raise ValueError("DingTalkNotifier has not been initialized")
        return self._service


# 装饰器：异常自动通知
def dingtalk_exception_handler(
        service_name: str = "警告",
        notify_on_error: bool = True,
        exclude_exceptions: tuple[Type[Exception], ...] = (),
        include_request_context: bool = False,
        rate_limit_seconds: int = 300  # 5 minutes rate limiting
):
    """
    异常自动通知装饰器
    Args:
        service_name: 服务名称
        notify_on_error: 是否在异常时通知
        exclude_exceptions: 不发送通知的异常类型
        include_request_context: 是否包含请求上下文
        rate_limit_seconds: 相同错误通知的最小间隔(秒)
    """

    def decorator(func: Callable) -> Callable:
        last_error_time: Dict[str, float] = {}  # 用于限速的缓存

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 获取请求上下文（如果是web请求）
            request_context = {}
            if include_request_context and hasattr(args[0], 'request'):
                request = args[0].request
                request_context = {
                    'method': getattr(request, 'method', ''),
                    'path': getattr(request, 'path', ''),
                    'query_params': dict(getattr(request, 'query_params', {})),
                    'user': str(getattr(request, 'user', 'anonymous')),
                    'remote_ip': getattr(request, 'META', {}).get('REMOTE_ADDR', '')
                }

            try:
                return func(*args, **kwargs)

            except exclude_exceptions:
                raise

            except Exception as e:
                if not notify_on_error:
                    raise

                # 获取完整的堆栈信息
                stack_trace = ''.join(traceback.format_exception(type(e), e, e.__traceback__))

                # 生成错误指纹，用于限速
                error_fingerprint = f"{func.__module__}.{func.__name__}:{type(e).__name__}:{str(e)[:100]}"
                current_time = datetime.now().timestamp()

                # 检查是否需要限速
                if (error_fingerprint in last_error_time and
                        (current_time - last_error_time[error_fingerprint]) < rate_limit_seconds):
                    raise

                last_error_time[error_fingerprint] = current_time

                # 准备通知内容
                try:
                    notifier = DingTalkNotifier()
                    service = notifier.get_service()

                    # 构建详细错误信息
                    error_details = {
                        "服务名称": service_name,
                        "异常类型": type(e).__name__,
                        "异常信息": str(e),
                        "发生时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "函数模块": func.__module__,
                        "函数名称": func.__name__,
                        "请求上下文": request_context if request_context else "无",
                        "堆栈跟踪": stack_trace[-2000:]  # 限制长度
                    }

                    # 发送通知
                    service.send_exception_alert(
                        service_name=f"{service_name} - {type(e).__name__}",
                        exception_message=str(e),
                        stack_trace=json.dumps(error_details, ensure_ascii=False, indent=2)
                    )
                except Exception as notify_err:
                    logger.error(f"发送钉钉通知失败: {notify_err}")

                raise

        return wrapper

    return decorator


