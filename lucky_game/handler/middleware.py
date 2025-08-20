import json
from typing import Callable, Awaitable, Dict, Any
from sanic import Request, HTTPResponse
from sanic.response import json as sanic_json
from nsanic.libs.mult_log import NLogger
from nsanic.libs.component import ConfMeta


class LoggingMiddleware(ConfMeta):
    """请求日志中间件"""

    def __init__(self):
        # Make it callable as a function
        self._is_old_style = False

    async def main(self, request: Request):
        # 记录请求信息
        self._log_request(request)

        # try:
        #     # 处理请求
        #     response = await handler(request)
        #
        #     # 记录响应信息
        #     self._log_response(request, response)
        #     return response
        #
        # except Exception as e:
        #     NLogger.error(f"Request processing failed: {str(e)}")
        #     raise
    async def __call__(self, request: Request, handler: Callable[[Request], Awaitable[HTTPResponse]]) -> HTTPResponse:
        # 记录请求信息
        self._log_request(request)

        try:
            # 处理请求
            response = await handler(request)

            # 记录响应信息
            self._log_response(request, response)
            return response

        except Exception as e:
            NLogger.error(f"Request processing failed: {str(e)}")
            raise

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
                "Response",response_data
            )
        except Exception as e:
            NLogger.error(f"Error logging response: {str(e)}")

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


class CorsMiddleware(ConfMeta):
    """CORS 中间件"""
    def __init__(self):
        # Make it callable as a function
        self._is_old_style = False
    async def main(self, request: Request, handler: Callable[[Request], Awaitable[HTTPResponse]]) -> HTTPResponse:
        # 处理预检请求
        if request.method == "OPTIONS":
            return self._options_response()

        # 添加 CORS 头
        response = await handler(request)
        self._add_cors_headers(response)
        return response

    async def __call__(self, request: Request, handler: Callable[[Request], Awaitable[HTTPResponse]]) -> HTTPResponse:
        # 处理预检请求
        if request.method == "OPTIONS":
            return self._options_response()

        # 添加 CORS 头
        response = await handler(request)
        self._add_cors_headers(response)
        return response

    def _options_response(self) -> HTTPResponse:
        """处理 OPTIONS 请求"""
        response = sanic_json({}, status=204)
        self._add_cors_headers(response)
        return response

    def _add_cors_headers(self, response: HTTPResponse) -> None:
        """添加 CORS 头"""
        response.headers.update({
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": (
                "Content-Type, Authorization, X-Requested-With, "
                "X-CSRF-Token, X-Request-ID, X-Requested-With, "
                "X-Forwarded-For, X-Forwarded-Host, X-Forwarded-Proto"
            ),
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        })


# 创建中间件实例
logging_middleware = LoggingMiddleware()
cors_middleware = CorsMiddleware()