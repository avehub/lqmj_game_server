import json
from cgitb import handler
from typing import Callable, Awaitable, Any
from sanic import Request, HTTPResponse
from nsanic.libs.mult_log import NLogger
from nsanic.libs.component import ConfMeta


class LoggingMiddleware(ConfMeta):
    """请求日志中间件"""

    def main(self, request: Request):
        # 记录请求信息
        self._log_request(request)


    def _log_request(self, request: Request) -> None:
        """记录请求日志"""
        try:
            # 获取请求数据
            request_data = {
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "query_params": dict(request.args),
                "body": self._get_request_body(request),
                "ip": request.remote_addr or request.ip
            }

            NLogger.info(
                "Request", request_data
            )
        except Exception as e:
            NLogger.error(f"Error logging request: {str(e)}")

    def _log_response(self, request: Request, response: HTTPResponse) -> None:
        """记录响应日志"""
        try:
            response_data = {
                "status": response.status,
                "headers": dict(response.headers),
                "body": self._get_response_body(response),
                "request_url": request.url
            }

            NLogger.info(
                "Response", response_data
            )
        except Exception as e:
            NLogger.error(f"Error logging response: {str(e)}")

    async def after_response(self, request, response):
        """在所有响应返回后执行的钩子"""
        # 获取响应数据
        response_data = getattr(response, 'data', None)
        return request, response_data

    def _get_request_body(self, request: Request) -> Any:
        """获取请求体"""
        try:
            if request.body:
                if request.content_type == "application/json":
                    return request.json
                return request.body.decode('utf-8')
            return None
        except:
            return None

    def _get_response_body(self, response: HTTPResponse) -> Any:
        """获取响应体"""
        try:
            if hasattr(response, 'body'):
                if response.content_type == "application/json":
                    return json.loads(response.body.decode('utf-8'))
                return response.body.decode('utf-8')
            return None
        except:
            return None



# 创建中间件实例
logging_middleware = LoggingMiddleware()
