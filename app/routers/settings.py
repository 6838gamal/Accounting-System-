"""
مسارات الإعدادات
"""
import base64
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.services.settings_service import SettingsService, DEFAULT_SETTINGS

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory="app/templates")

# الحجم الأقصى للصور 2MB
_MAX_LOGO_SIZE = 2 * 1024 * 1024
_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/webp"}


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    settings = SettingsService(db).get_all()
    return templates.TemplateResponse("settings/index.html", {
        "request": request, "settings": settings, "saved": False, "error": None
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
    error = None

    # حفظ الحقول النصية العادية
    text_keys = {k for k in DEFAULT_SETTINGS if k not in ("company_logo", "company_stamp")}
    data = {k: str(v) for k, v in form_data.items() if k in text_keys}
    # معالجة الـ checkbox — إذا لم يُرسَل يعني غير محدد
    if "pdf_show_signatures" in text_keys:
        data["pdf_show_signatures"] = "1" if "pdf_show_signatures" in form_data else "0"
    service.save_all(data)

    # معالجة الشعار
    if remove_logo == "1":
        service.set("company_logo", "")
    elif company_logo_file and company_logo_file.filename:
        if company_logo_file.content_type not in _ALLOWED_TYPES:
            error = "نوع الملف غير مدعوم. يُرجى رفع صورة PNG أو JPG أو SVG."
        else:
            content = await company_logo_file.read()
            if len(content) > _MAX_LOGO_SIZE:
                error = "حجم الشعار يتجاوز الحد المسموح (2MB)."
            else:
                mime = company_logo_file.content_type
                b64 = base64.b64encode(content).decode("utf-8")
                service.set("company_logo", f"data:{mime};base64,{b64}")

    # معالجة الختم
    if remove_stamp == "1":
        service.set("company_stamp", "")
    elif company_stamp_file and company_stamp_file.filename:
        if company_stamp_file.content_type not in _ALLOWED_TYPES:
            error = "نوع ملف الختم غير مدعوم. يُرجى رفع صورة PNG أو JPG."
        else:
            content = await company_stamp_file.read()
            if len(content) > _MAX_LOGO_SIZE:
                error = "حجم الختم يتجاوز الحد المسموح (2MB)."
            else:
                mime = company_stamp_file.content_type
                b64 = base64.b64encode(content).decode("utf-8")
                service.set("company_stamp", f"data:{mime};base64,{b64}")

    settings = service.get_all()
    return templates.TemplateResponse("settings/index.html", {
        "request": request, "settings": settings,
        "saved": error is None, "error": error
    })
