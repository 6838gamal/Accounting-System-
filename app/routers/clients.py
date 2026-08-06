"""
مسارات إدارة العملاء
"""
import logging
import re as _re
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.services.client_service import ClientService
from app.services.activity_service import ActivityService
from app.models.client import ClientType

_EMAIL_RE = _re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

router = APIRouter(prefix="/clients", tags=["clients"])
templates = _shared_templates
logger = logging.getLogger(__name__)

_VALID_TYPES = {t.value for t in ClientType}


@router.get("", response_class=HTMLResponse)
async def list_clients(
    request: Request,
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    service = ClientService(db)
    skip = (page - 1) * 20
    clients, total = service.get_all(skip=skip, limit=20, search=search)
    return templates.TemplateResponse("clients/list.html", {
        "request": request, "clients": clients, "total": total,
        "page": page, "search": search or "",
        "total_pages": max(1, (total + 19) // 20),
    })


@router.get("/new", response_class=HTMLResponse)
async def new_client(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("clients/form.html", {
        "request": request, "client": None, "error": None
    })


@router.post("/new")
async def create_client(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    type: str = Form("company"),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    tax_number: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)

    def _form_error(msg: str):
        return templates.TemplateResponse("clients/form.html", {
            "request": request, "client": None, "error": msg
        })

    name = name.strip()
    if not name:
        return _form_error("اسم العميل مطلوب.")
    if len(name) > 200:
        return _form_error("اسم العميل يجب ألا يتجاوز 200 حرف.")

    if type not in _VALID_TYPES:
        return _form_error("نوع العميل غير صالح.")

    # تنظيف الحقول الاختيارية والتحقق من البريد الإلكتروني
    email = email.strip() if email else None
    phone = phone.strip() if phone else None
    tax_number = tax_number.strip() if tax_number else None

    if email and not _EMAIL_RE.match(email):
        return _form_error("صيغة البريد الإلكتروني غير صحيحة.")

    try:
        service = ClientService(db)
        client = service.create({
            "name": name, "type": type, "email": email or None,
            "phone": phone or None, "address": address or None,
            "tax_number": tax_number or None, "notes": notes or None,
        }, created_by=request.session["user_id"])
    except Exception:
        logger.exception("خطأ أثناء إنشاء العميل")
        db.rollback()
        return _form_error("حدث خطأ أثناء حفظ بيانات العميل. يرجى التحقق من البيانات.")

    try:
        ActivityService(db).log(request.session["user_id"], "create", "clients", client.id, f"إنشاء عميل: {name}")
    except Exception:
        logger.warning("فشل تسجيل النشاط لإنشاء العميل %s", client.id)

    return RedirectResponse(url=f"/clients/{client.id}", status_code=302)


@router.get("/{client_id}", response_class=HTMLResponse)
async def view_client(request: Request, client_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    client = ClientService(db).get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="العميل غير موجود")
    stats = ClientService(db).get_stats(client_id)
    return templates.TemplateResponse("clients/detail.html", {
        "request": request, "client": client, "stats": stats
    })


@router.get("/{client_id}/edit", response_class=HTMLResponse)
async def edit_client(request: Request, client_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    client = ClientService(db).get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="العميل غير موجود")
    return templates.TemplateResponse("clients/form.html", {
        "request": request, "client": client, "error": None
    })


@router.post("/{client_id}/edit")
async def update_client(
    request: Request, client_id: int, db: Session = Depends(get_db),
    name: str = Form(...), type: str = Form("company"),
    email: Optional[str] = Form(None), phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None), tax_number: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)

    service = ClientService(db)
    client = service.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    def _form_error(msg: str):
        return templates.TemplateResponse("clients/form.html", {
            "request": request, "client": client, "error": msg
        })

    name = name.strip()
    if not name:
        return _form_error("اسم العميل مطلوب.")
    if len(name) > 200:
        return _form_error("اسم العميل يجب ألا يتجاوز 200 حرف.")

    if type not in _VALID_TYPES:
        return _form_error("نوع العميل غير صالح.")

    email = email.strip() if email else None
    phone = phone.strip() if phone else None
    tax_number = tax_number.strip() if tax_number else None

    if email and not _EMAIL_RE.match(email):
        return _form_error("صيغة البريد الإلكتروني غير صحيحة.")

    try:
        service.update(client_id, {
            "name": name, "type": type, "email": email or None,
            "phone": phone or None, "address": address or None,
            "tax_number": tax_number or None, "notes": notes or None,
        })
    except Exception:
        logger.exception("خطأ أثناء تعديل العميل %s", client_id)
        db.rollback()
        return _form_error("حدث خطأ أثناء حفظ التعديلات. يرجى التحقق من البيانات.")

    try:
        ActivityService(db).log(request.session["user_id"], "update", "clients", client_id, f"تعديل عميل: {name}")
    except Exception:
        logger.warning("فشل تسجيل النشاط لتعديل العميل %s", client_id)

    return RedirectResponse(url=f"/clients/{client_id}", status_code=302)


@router.post("/{client_id}/delete")
async def delete_client(request: Request, client_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)

    client = ClientService(db).get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    try:
        ClientService(db).delete(client_id)
    except Exception:
        logger.exception("خطأ أثناء حذف العميل %s", client_id)
        db.rollback()
        return RedirectResponse(url="/clients", status_code=302)

    try:
        ActivityService(db).log(request.session["user_id"], "delete", "clients", client_id, "حذف عميل")
    except Exception:
        logger.warning("فشل تسجيل النشاط لحذف العميل %s", client_id)

    return RedirectResponse(url="/clients", status_code=302)
