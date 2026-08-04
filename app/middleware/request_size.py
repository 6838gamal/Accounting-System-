"""
Request Size Limiter — الحماية من DoS عبر طلبات ضخمة.
"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("security")

DEFAULT_MAX_BODY = 5 * 1024 * 1024  # 5 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """يرفض أي طلب حجمه يتجاوز الحد المحدد."""

    def __init__(self, app, max_body_size: int = DEFAULT_MAX_BODY):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_body_size:
                    ip = (
                        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                        or (request.client.host if request.client else "unknown")
                    )
                    logger.warning(
                        "Request too large | size=%d | limit=%d | path=%s | ip=%s",
                        size, self.max_body_size, request.url.path, ip,
                    )
                    from starlette.responses import HTMLResponse
                    return HTMLResponse(
                        content="حجم الطلب كبير جداً",
                        status_code=413,
                    )
            except ValueError:
                pass  # content-length غير صالح — نتركه يمر
        return await call_next(request)
