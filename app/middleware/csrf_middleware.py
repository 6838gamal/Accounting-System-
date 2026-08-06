"""
CSRF Middleware — يتحقق من توكن CSRF في جميع طلبات POST/PUT/DELETE/PATCH
يقرأ الـ body بشكل آمن دون استهلاكه (يُخزّنه في request._body أولاً).
"""
import logging
import urllib.parse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse
from app.core.csrf import validate_csrf_token, CSRF_FORM_FIELD

logger = logging.getLogger("security")

_CSRF_EXEMPT = {
    "/auth/logout",   # POST للخروج — يكفيه same_site=lax + تنظيف الجلسة
}

_MUTATING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    يتحقق من توكن CSRF في كل طلب يُعدّل حالة.
    يقبل التوكن من:
    1. حقل نموذج csrf_token  (URL-encoded أو multipart)
    2. رأس HTTP X-CSRF-Token  (للطلبات AJAX / fetch)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in _MUTATING_METHODS and request.url.path not in _CSRF_EXEMPT:
            if request.session.get("user_id"):
                submitted = await _extract_csrf_token(request)
                if not validate_csrf_token(request, submitted):
                    ip = _get_ip(request)
                    logger.warning(
                        "CSRF validation failed | path=%s | method=%s | ip=%s",
                        request.url.path, request.method, ip,
                    )
                    return HTMLResponse(content=_csrf_error_html(), status_code=403)
        return await call_next(request)


async def _extract_csrf_token(request: Request) -> str | None:
    """
    استخراج توكن CSRF بأمان.
    - يقرأ الـ body الخام مرة واحدة ويُخزّنه في request._body
    - يحلّل URL-encoded forms يدوياً (بدون استهلاك القناة)
    - للـ multipart وللـ header: يستخدم الطرق المناسبة
    """
    # 1. رأس HTTP (AJAX/fetch)
    header_token = request.headers.get("X-CSRF-Token")
    if header_token:
        return header_token

    content_type = request.headers.get("content-type", "")

    # 2. URL-encoded form — نقرأ الـ body الخام ونحلّله يدوياً
    if "application/x-www-form-urlencoded" in content_type:
        try:
            # await request.body() يُخزّن الـ body في request._body ليُقرأ مجدداً
            raw_body = await request.body()
            params = urllib.parse.parse_qs(
                raw_body.decode("utf-8", errors="replace"),
                keep_blank_values=True,
            )
            tokens = params.get(CSRF_FORM_FIELD, [])
            return tokens[0] if tokens else None
        except Exception:
            return None

    # 3. multipart/form-data — نقرأ عبر request.form()
    if "multipart/form-data" in content_type:
        try:
            # نقرأ الـ body أولاً لتخزينه، ثم نحلّل النموذج
            await request.body()
            form = await request.form()
            return form.get(CSRF_FORM_FIELD)
        except Exception:
            return None

    return None


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _csrf_error_html() -> str:
    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>خطأ أمني</title>
<style>body{font-family:Arial,sans-serif;text-align:center;padding:80px;background:#f8fafc}
.box{background:#fff;border-radius:12px;padding:40px;max-width:480px;margin:auto;box-shadow:0 2px 16px rgba(0,0,0,.08)}
h1{color:#dc2626}p{color:#64748b;margin-bottom:2rem}a{color:#2563eb;font-weight:600}</style>
</head>
<body><div class="box">
<h1>خطأ أمني (403)</h1>
<p>انتهت صلاحية الجلسة أو الطلب غير صالح. يرجى تحديث الصفحة والمحاولة مجدداً.</p>
<a href="/">العودة للرئيسية</a>
</div></body></html>"""
