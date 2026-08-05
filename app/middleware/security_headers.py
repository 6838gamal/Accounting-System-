"""
Security Headers Middleware
يضيف رؤوس HTTP الأمنية لكل Response ويضبط Request ID.
"""
import uuid
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import set_request_id

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    يضيف:
    - X-Frame-Options             → ضد Clickjacking
    - X-Content-Type-Options      → ضد MIME Sniffing
    - Referrer-Policy             → تقليل تسريب المعلومات
    - Permissions-Policy          → تقييد APIs الحساسة
    - Content-Security-Policy     → ضد XSS وInjection
    - X-Request-ID                → تتبع الطلبات
    - Strict-Transport-Security   → إجبار HTTPS (في الإنتاج)
    """

    CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' "
        "  https://cdn.jsdelivr.net "
        "  https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' "
        "  https://cdn.jsdelivr.net "
        "  https://fonts.googleapis.com "
        "  https://fonts.gstatic.com; "
        "font-src 'self' "
        "  https://fonts.gstatic.com "
        "  https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    def __init__(self, app, *, is_production: bool = False):
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next) -> Response:
        # إنشاء Request ID فريد وتخزينه في ContextVar
        request_id = str(uuid.uuid4())[:16]
        set_request_id(request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # تسجيل الطلب
        logger.info(
            "%s %s | status=%s | %.1fms | ip=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            _get_ip(request),
        )

        # ─── Security Headers ──────────────────────────────────────────────
        h = response.headers
        h["X-Request-ID"] = request_id
        h["X-Frame-Options"] = "DENY"
        h["X-Content-Type-Options"] = "nosniff"
        h["Referrer-Policy"] = "strict-origin-when-cross-origin"
        h["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), fullscreen=(self)"
        )
        h["Content-Security-Policy"] = self.CSP
        h["X-XSS-Protection"] = "1; mode=block"
        h["Server"] = "AccountingSystem"

        # منع المتصفح من تخزين صفحات HTML — يضمن إعادة التحقق من الجلسة
        # عند الضغط على "رجوع" بعد تسجيل الخروج
        content_type = response.headers.get("content-type", "")
        is_static = request.url.path.startswith("/static/")
        if not is_static and "text/html" in content_type:
            h["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            h["Pragma"] = "no-cache"
            h["Expires"] = "0"

        if self.is_production:
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        if "x-powered-by" in h:
            del h["x-powered-by"]

        return response


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
