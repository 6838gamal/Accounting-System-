"""
معالجة الاستثناءات العامة — لا يرى المستخدم أي Stack Trace أو خطأ داخلي.
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)
sec_logger = logging.getLogger("security")


# ─── صفحة خطأ HTML آمنة ────────────────────────────────────────────────────

def _safe_html_error(status_code: int, title: str, message: str) -> HTMLResponse:
    """صفحة خطأ HTML بدون أي معلومات داخلية."""
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body{{font-family:Arial,sans-serif;text-align:center;padding:80px;background:#f8fafc;color:#1e293b}}
    .box{{background:#fff;border-radius:12px;padding:40px;max-width:480px;margin:auto;box-shadow:0 2px 16px rgba(0,0,0,.08)}}
    h1{{color:#dc2626;font-size:2rem;margin-bottom:.5rem}}
    p{{color:#64748b;margin-bottom:2rem}}
    a{{color:#2563eb;text-decoration:none;font-weight:600}}
  </style>
</head>
<body>
  <div class="box">
    <h1>{status_code}</h1>
    <p>{message}</p>
    <a href="/">العودة للرئيسية</a>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=status_code)


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


# ─── Handlers ──────────────────────────────────────────────────────────────

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code in (301, 302, 307, 308):
        location = (exc.headers or {}).get("Location", "/")
        return RedirectResponse(url=location, status_code=exc.status_code)

    if exc.status_code == 401:
        return RedirectResponse(url="/auth/login", status_code=302)

    if exc.status_code == 403:
        sec_logger.warning(
            "Access denied | path=%s | ip=%s | req_id=%s",
            request.url.path, _get_ip(request), _req_id(request),
        )
        return _safe_html_error(403, "غير مصرح", "ليس لديك صلاحية الوصول لهذه الصفحة.")

    if exc.status_code == 404:
        return _safe_html_error(404, "غير موجود", "الصفحة التي تبحث عنها غير موجودة.")

    if exc.status_code == 413:
        return _safe_html_error(413, "حجم كبير", "حجم الطلب يتجاوز الحد المسموح.")

    if exc.status_code == 429:
        return _safe_html_error(429, "طلبات كثيرة", "لقد تجاوزت الحد المسموح. يرجى الانتظار.")

    logger.warning(
        "HTTP %s | path=%s | ip=%s | req_id=%s",
        exc.status_code, request.url.path, _get_ip(request), _req_id(request),
    )
    return _safe_html_error(exc.status_code, "خطأ", "حدث خطأ في معالجة طلبك.")


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error | path=%s | errors=%s | req_id=%s",
        request.url.path, str(exc.errors())[:300], _req_id(request),
    )
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return _safe_html_error(422, "بيانات غير صالحة", "البيانات المُدخَلة غير صحيحة.")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "البيانات المُدخَلة غير صحيحة.",
            "error_code": "VALIDATION_ERROR",
        },
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(
        "Database error | path=%s | type=%s | req_id=%s",
        request.url.path, type(exc).__name__, _req_id(request),
        exc_info=True,
    )
    return _safe_html_error(500, "خطأ في قاعدة البيانات",
                            "حدث خطأ في قاعدة البيانات. يرجى المحاولة لاحقاً.")


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.critical(
        "Unhandled exception | path=%s | type=%s | ip=%s | req_id=%s",
        request.url.path, type(exc).__name__, _get_ip(request), _req_id(request),
        exc_info=True,
    )
    return _safe_html_error(500, "خطأ داخلي",
                            "حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")
