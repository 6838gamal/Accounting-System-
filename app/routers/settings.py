"""
مسارات الإعدادات
"""
import base64
import logging
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.services.settings_service import SettingsService, DEFAULT_SETTINGS

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

# الحجم الأقصى للصور 2MB
_MAX_LOGO_SIZE = 2 * 1024 * 1024
_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/webp"}


@router.get("", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    saved: bool = False,
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    settings = SettingsService(db).get_all()
    return templates.TemplateResponse("settings/index.html", {
        "request": request, "settings": settings, "saved": saved, "error": None
    })


@router.post("")
async def save_settings(
    request: Request,
    db: Session = Depends(get_db),
    company_logo_file: Optional[UploadFile] = File(None),
    remove_logo: Optional[str] = Form(None),
    company_stamp_file: Optional[UploadFile] = File(None),
    remove_stamp: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)

    form_data = await request.form()
    service = SettingsService(db)

    # ─── 1. جمع الحقول النصية ───────────────────────────────────────────────
    text_keys = {k for k in DEFAULT_SETTINGS if k not in ("company_logo", "company_stamp")}
    data: dict = {k: str(v) for k, v in form_data.items() if k in text_keys}
    if "pdf_show_signatures" in text_keys:
        data["pdf_show_signatures"] = "1" if "pdf_show_signatures" in form_data else "0"

    # ─── 2. التحقق من الشعار والختم قبل أي كتابة ───────────────────────────
    logo_value: Optional[str] = None   # None = لا تغيير، "" = حذف، "data:..." = جديد
    stamp_value: Optional[str] = None

    if remove_logo == "1":
        logo_value = ""
    elif company_logo_file and company_logo_file.filename:
        if company_logo_file.content_type not in _ALLOWED_TYPES:
            settings = service.get_all()
            return templates.TemplateResponse("settings/index.html", {
                "request": request, "settings": settings, "saved": False,
                "error": "نوع الملف غير مدعوم. يُرجى رفع صورة PNG أو JPG أو SVG."
            })
        content = await company_logo_file.read()
        if len(content) > _MAX_LOGO_SIZE:
            settings = service.get_all()
            return templates.TemplateResponse("settings/index.html", {
                "request": request, "settings": settings, "saved": False,
                "error": "حجم الشعار يتجاوز الحد المسموح (2MB)."
            })
        mime = company_logo_file.content_type
        logo_value = f"data:{mime};base64,{base64.b64encode(content).decode()}"

    if remove_stamp == "1":
        stamp_value = ""
    elif company_stamp_file and company_stamp_file.filename:
        if company_stamp_file.content_type not in _ALLOWED_TYPES:
            settings = service.get_all()
            return templates.TemplateResponse("settings/index.html", {
                "request": request, "settings": settings, "saved": False,
                "error": "نوع ملف الختم غير مدعوم. يُرجى رفع صورة PNG أو JPG."
            })
        content = await company_stamp_file.read()
        if len(content) > _MAX_LOGO_SIZE:
            settings = service.get_all()
            return templates.TemplateResponse("settings/index.html", {
                "request": request, "settings": settings, "saved": False,
                "error": "حجم الختم يتجاوز الحد المسموح (2MB)."
            })
        mime = company_stamp_file.content_type
        stamp_value = f"data:{mime};base64,{base64.b64encode(content).decode()}"

    # ─── 3. دمج جميع القيم وحفظها في معاملة واحدة ───────────────────────────
    if logo_value is not None:
        data["company_logo"] = logo_value
    if stamp_value is not None:
        data["company_stamp"] = stamp_value

    try:
        service.save_all(data)
    except Exception:
        logger.exception("خطأ أثناء حفظ الإعدادات")
        db.rollback()
        settings = service.get_all()
        return templates.TemplateResponse("settings/index.html", {
            "request": request, "settings": settings, "saved": False,
            "error": "حدث خطأ أثناء حفظ الإعدادات. يرجى المحاولة مرة أخرى."
        })

    # PRG — إعادة التوجيه بعد الحفظ الناجح لمنع إعادة الإرسال عند التحديث
    return RedirectResponse(url="/settings?saved=1", status_code=302)
