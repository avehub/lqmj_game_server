# common/utils/exceptions.py
import logging
from typing import Optional
from sanic.exceptions import SanicException
from sanic.response import json
from nsanic.base_conf import BaseConf
from nsanic.libs.component import LogMeta


class CommonException(SanicException):
    """基础异常类"""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, status_code=status_code)


class ValidationException(CommonException):
    """参数验证异常"""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class NotFoundException(CommonException):
    """资源未找到异常"""

    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class DatabaseException(CommonException):
    """数据库操作异常"""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class GlobalExceptionHandler:
    """全局异常处理器"""

    def __init__(self):
        self.conf = None

    def set_conf(self, conf: BaseConf):
        """设置配置"""
        self.conf = conf

    async def catch_req(self, request, exception):
        """处理所有未捕获的异常"""
        LogMeta.logerr(f"Unhandled exception: {str(exception)}")

        # 根据异常类型返回不同的响应
        if isinstance(exception, SanicException):
            return json({
                "code": exception.status_code,
                "msg": str(exception)
            }, status=exception.status_code)

        return json({
            "code": 500,
            "msg": "系统错误，请稍后重试"
        }, status=500)


# 实例化全局异常处理器
global_exception_handler = GlobalExceptionHandler()