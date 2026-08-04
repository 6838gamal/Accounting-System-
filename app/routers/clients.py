"""
مسارات إدارة العملاء
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.services.client_service import ClientService
from app.services.activity_service import ActivityService
from app.models.client import ClientType

router = APIRouter(prefix="/clients", tags=["clients"])
templates = Jinja2Templates(directory="app/templates")


def get_user(request: Request):
    if not request.session.get("user_id"):
        return None
    return request.session.get("user_id")


@router.get("", response_class=HTMLResponse)
async def list_clients(
    request: Request,
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    page: int = 1,
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    service = ClientService(db)
    skip = (page - 1) * 20
    clients, total = service.get_all(skip=skip, limit=20, search=search)
    return templates.TemplateResponse("clients/list.html", {
        "request": request,
        "clients": clients,
        "total": total,
        "page": page,
        "search": search or "",
        "total_pages": (total + 19) // 20,
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
    service = ClientService(db)
    client = service.create({
        "name": name, "type": type, "email": email or None,
        "phone": phone or None, "address": address or None,
        "tax_number": tax_number or None, "notes": notes or None,
    }, created_by=request.session["user_id"])
    ActivityService(db).log(request.session["user_id"], "create", "clients", client.id, f"إنشاء عميل: {name}")
    return RedirectResponse(url=f"/clients/{client.id}", status_code=302)


@router.get("/{client_id}", response_class=HTMLResponse)
async def view_client(request: Request, client_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    service = ClientService(db)
    client = service.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="العميل غير موجود")
    stats = service.get_stats(client_id)
    return templates.TemplateResponse("clients/detail.html", {
        "request": request, "client": client, "stats": stats
    })


@router.get("/{client_id}/edit", response_class=HTMLResponse)
async def edit_client(request: Request, client_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    service = ClientService(db)
    client = service.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="العميل غير موجود")
    return templates.TemplateResponse("clients/form.html", {
        "request": request, "client": client, "error": None
    })


@router.post("/{client_id}/edit")
async def update_client(
    request: Request,
    client_id: int,
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
    service = ClientService(db)
    service.update(client_id, {
        "name": name, "type": type, "email": email or None,
        "phone": phone or None, "address": address or None,
        "tax_number": tax_number or None, "notes": notes or None,
    })
    ActivityService(db).log(request.session["user_id"], "update", "clients", client_id, f"تعديل عميل: {name}")
    return RedirectResponse(url=f"/clients/{client_id}", status_code=302)


@router.post("/{client_id}/delete")
async def delete_client(request: Request, client_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    ClientService(db).delete(client_id)
    ActivityService(db).log(request.session["user_id"], "delete", "clients", client_id, "حذف عميل")
    return RedirectResponse(url="/clients", status_code=302)
