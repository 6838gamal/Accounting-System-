"""
التطبيق الرئيسي لـ FastAPI — محصّن أمنياً
"""
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import init_db

# ─── Logging (أول شيء قبل أي import آخر) ──────────────────────────────────
from app.core.logging_config import setup_logging
setup_logging(debug=settings.DEBUG)

logger = logging.getLogger(__name__)

# ─── Routers ────────────────────────────────────────────────────────────────
from app.routers import (
    auth, dashboard, users, clients, contracts,
    quotations, invoices, payments, expenses,
    reports, settings as settings_router, activity_log,
)
from app.routers import expense_vouchers, receipt_vouchers

# ─── Exception Handlers ─────────────────────────────────────────────────────
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    unhandled_exception_handler,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

# ─── Middleware ─────────────────────────────────────────────────────────────
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_size import RequestSizeLimitMiddleware
from app.middleware.csrf_middleware import CSRFMiddleware


# ─── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Graceful startup وshutdown."""
    logger.info("Starting %s v%s | debug=%s", settings.APP_NAME, settings.APP_VERSION, settings.DEBUG)
    try:
        init_db()
        # إنشاء المشرف الافتراضي وتهيئة الإعدادات
        from app.database import SessionLocal
        from app.services.auth_service import AuthService
        from app.services.settings_service import SettingsService
        db = SessionLocal()
        try:
            AuthService(db).create_default_admin()
            SettingsService(db).init_defaults()
        finally:
            db.close()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.critical("Startup failed: %s", exc, exc_info=True)
        raise

    yield  # التطبيق يعمل هنا

    logger.info("Application shutting down gracefully")


# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    # إخفاء docs/redoc في الإنتاج
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ─── Exception Handlers ──────────────────────────────────────────────────────
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ─── Middleware (LIFO — آخر مضاف أول مُنفَّذ) ───────────────────────────────

# 1. حد حجم الطلب — أول شيء يُفحص
app.add_middleware(RequestSizeLimitMiddleware, max_body_size=settings.MAX_UPLOAD_SIZE)

# 2. GZip للاستجابات الكبيرة
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 3. رؤوس الأمان + Request ID + تسجيل الطلبات
app.add_middleware(
    SecurityHeadersMiddleware,
    is_production=not settings.DEBUG,
)

# 4. حماية CSRF — بعد الجلسات مباشرة
app.add_middleware(CSRFMiddleware)

# 5. جلسات المستخدم
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.effective_session_key,
    max_age=settings.SESSION_MAX_AGE,
    https_only=not settings.DEBUG,   # True في الإنتاج
    same_site="lax",
    session_cookie="__Host-session" if not settings.DEBUG else "session",
)

# ─── Static Files ────────────────────────────────────────────────────────────
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# مجلد الرفع
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# ─── Templates ───────────────────────────────────────────────────────────────
templates = Jinja2Templates(directory="app/templates")

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(clients.router)
app.include_router(contracts.router)
app.include_router(quotations.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(expenses.router)
app.include_router(expense_vouchers.router)
app.include_router(receipt_vouchers.router)
app.include_router(reports.router)
app.include_router(settings_router.router)
app.include_router(activity_log.router)


# ─── Root Route ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/auth/login", status_code=302)
