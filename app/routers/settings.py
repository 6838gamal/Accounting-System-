"""
مسارات الإعدادات
"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.services.settings_service import SettingsService, DEFAULT_SETTINGS

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    settings = SettingsService(db).get_all()
    return templates.TemplateResponse("settings/index.html", {
        "request": request, "settings": settings, "saved": False
    })


@router.post("")
async def save_settings(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    form_data = await request.form()
    service = SettingsService(db)
    data = {k: str(v) for k, v in form_data.items() if k in DEFAULT_SETTINGS}
    service.save_all(data)
    settings = service.get_all()
    return templates.TemplateResponse("settings/index.html", {
        "request": request, "settings": settings, "saved": True
    })
