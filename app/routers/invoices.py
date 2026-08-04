"""
مسارات إدارة الفواتير
"""
import json
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.services.invoice_service import InvoiceService
from app.services.activity_service import ActivityService
from app.services.settings_service import SettingsService
from app.models.client import Client

router = APIRouter(prefix="/invoices", tags=["invoices"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def list_invoices(
    request: Request, db: Session = Depends(get_db),
    status: Optional[str] = None, client_id: Optional[int] = None, page: int = 1,
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    service = InvoiceService(db)
    service.update_overdue()
    invoices, total = service.get_all(skip=(page - 1) * 20, limit=20, client_id=client_id, status=status)
    summary = service.get_summary()
    return templates.TemplateResponse("invoices/list.html", {
        "request": request, "invoices": invoices, "total": total,
        "page": page, "total_pages": (total + 19) // 20,
        "status_filter": status, "summary": summary,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_invoice(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    settings_svc = SettingsService(db)
    tax_rate = settings_svc.get("default_tax_rate", "15")
    return templates.TemplateResponse("invoices/form.html", {
        "request": request, "invoice": None, "clients": clients,
        "default_tax_rate": tax_rate, "error": None,
    })


@router.post("/new")
async def create_invoice(
    request: Request, db: Session = Depends(get_db),
    client_id: int = Form(...), issue_date: str = Form(...),
    due_date: Optional[str] = Form(None), tax_rate: float = Form(0),
    discount: float = Form(0), notes: Optional[str] = Form(None),
    items_json: str = Form("[]"),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    items = json.loads(items_json)
    service = InvoiceService(db)
    invoice = service.create(
        {
            "client_id": client_id,
            "issue_date": date.fromisoformat(issue_date),
            "due_date": date.fromisoformat(due_date) if due_date else None,
            "tax_rate": Decimal(str(tax_rate)),
            "discount": Decimal(str(discount)),
            "notes": notes or None,
        },
        items_data=items,
        created_by=request.session["user_id"],
    )
    ActivityService(db).log(request.session["user_id"], "create", "invoices", invoice.id, f"إنشاء فاتورة: {invoice.invoice_number}")
    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=302)


@router.get("/{invoice_id}", response_class=HTMLResponse)
async def view_invoice(request: Request, invoice_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    invoice = InvoiceService(db).get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    settings = SettingsService(db).get_all()
    return templates.TemplateResponse("invoices/detail.html", {
        "request": request, "invoice": invoice, "settings": settings
    })


@router.get("/{invoice_id}/pdf")
async def invoice_pdf(request: Request, invoice_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    invoice = InvoiceService(db).get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404)
    company_settings = SettingsService(db).get_all()
    from app.services.pdf_service import generate_invoice_pdf
    pdf_bytes = generate_invoice_pdf(invoice, company_settings)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=invoice-{invoice.invoice_number}.pdf"},
    )


@router.post("/{invoice_id}/payment")
async def add_payment(
    request: Request, invoice_id: int, db: Session = Depends(get_db),
    amount: float = Form(...), payment_date: str = Form(...),
    method: str = Form("cash"), reference: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    service = InvoiceService(db)
    service.record_payment(
        invoice_id=invoice_id,
        amount=Decimal(str(amount)),
        payment_data={"payment_date": date.fromisoformat(payment_date), "method": method, "reference": reference, "notes": notes},
        created_by=request.session["user_id"],
    )
    ActivityService(db).log(request.session["user_id"], "payment", "invoices", invoice_id, f"دفعة: {amount}")
    return RedirectResponse(url=f"/invoices/{invoice_id}", status_code=302)
