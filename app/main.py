"""
التطبيق الرئيسي لـ FastAPI
"""
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import init_db
from app.routers import (
    auth, dashboard, users, clients, contracts,
    quotations, invoices, payments, expenses,
    reports, settings as settings_router, activity_log,
)

# إنشاء مجلد الرفع إن لم يكن موجوداً
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
)

# Middleware للجلسات
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=settings.SESSION_MAX_AGE,
    https_only=False,
)

# الملفات الثابتة
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# القوالب
templates = Jinja2Templates(directory="app/templates")

# تسجيل المسارات
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(clients.router)
app.include_router(contracts.router)
app.include_router(quotations.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(expenses.router)
app.include_router(reports.router)
app.include_router(settings_router.router)
app.include_router(activity_log.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/auth/login", status_code=302)


@app.on_event("startup")
async def startup():
    """تهيئة قاعدة البيانات عند بدء التطبيق"""
    init_db()
    # إنشاء المشرف الافتراضي
    from app.database import SessionLocal
    from app.services.auth_service import AuthService
    from app.services.settings_service import SettingsService
    db = SessionLocal()
    try:
        AuthService(db).create_default_admin()
        SettingsService(db).init_defaults()
    finally:
        db.close()
