"""
مسارات المصادقة — محصّنة ضد Brute Force وSession Fixation وCSRF
"""
import logging
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.auth_service import AuthService
from app.core.rate_limiter import check_login_rate_limit, get_client_ip

router = APIRouter(prefix="/auth", tags=["auth"])
templates = _shared_templates

logger = logging.getLogger(__name__)
sec_logger = logging.getLogger("security")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    # قراءة رسالة الخطأ من query param (يستخدمها rate limiter)
    error = None
    if request.query_params.get("error") == "rate_limit":
        error = "تجاوزت الحد المسموح لمحاولات الدخول. يرجى الانتظار 5 دقائق."
    elif request.query_params.get("error") == "inactive":
        error = "الحساب غير مفعّل. تواصل مع المشرف."
    return templates.TemplateResponse("auth/login.html", {"request": request, "error": error})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(..., max_length=150),
    password: str = Form(..., max_length=256),
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)

    # ─── Rate Limiting ──────────────────────────────────────────────────
    if not check_login_rate_limit(request):
        sec_logger.warning(
            "Login rate limit hit | ip=%s | username=***",
            ip,
        )
        return RedirectResponse(url="/auth/login?error=rate_limit", status_code=302)

    # ─── Authentication ─────────────────────────────────────────────────
    service = AuthService(db)
    user = service.authenticate_user(username, password)

    if not user:
        # تسجيل محاولة الدخول الفاشلة (بدون كشف اسم المستخدم في السجل)
        sec_logger.warning(
            "Failed login attempt | ip=%s | username_len=%d",
            ip, len(username),
        )
        # رسالة موحدة — لا تُفصح إن كان المستخدم موجوداً أم لا (ضد Enumeration)
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "اسم المستخدم أو كلمة المرور غير صحيحة"},
            status_code=401,
        )

    if not user.is_active:
        sec_logger.warning("Inactive user login attempt | ip=%s | user_id=%s", ip, user.id)
        return RedirectResponse(url="/auth/login?error=inactive", status_code=302)

    # ─── Session Fixation Fix ────────────────────────────────────────────
    # تجديد الجلسة بالكامل بعد المصادقة الناجحة
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["full_name"] = user.full_name or ""
    request.session["user_role"] = user.role.value

    sec_logger.info(
        "Successful login | ip=%s | user_id=%s | role=%s",
        ip, user.id, user.role.value,
    )
    return RedirectResponse(url="/dashboard", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    """
    Logout عبر POST — يمنع CSRF-logout عبر روابط GET.
    الجلسة تُمسح بالكامل.
    """
    user_id = request.session.get("user_id")
    if user_id:
        sec_logger.info("User logout | user_id=%s", user_id)
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=302)


# مسار GET للتوافق فقط — يُعيد Redirect لصفحة الدخول
@router.get("/logout")
async def logout_get(request: Request):
    """Redirect لمنع logout عبر GET مباشرة (حماية من CSRF)."""
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=302)
