"""
مسارات عروض الأسعار
"""
import json
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.models.quotation import Quotation, QuotationItem, QuotationStatus
from app.models.client import Client
from app.services.activity_service import ActivityService
from app.services.settings_service import SettingsService
from app.config import settings as app_settings

router = APIRouter(prefix="/quotations", tags=["quotations"])
templates = Jinja2Templates(directory="app/templates")


def _gen_number(db: Session) -> str:
    last = db.query(Quotation).order_by(Quotation.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"{app_settings.QUOTE_PREFIX}-{datetime.now().year}-{n:04d}"


def _calc(items, tax_rate, discount):
    subtotal = sum(Decimal(str(i.get("quantity", 1))) * Decimal(str(i.get("unit_price", 0))) for i in items)
    tax = subtotal * (Decimal(str(tax_rate)) / 100)
    total = subtotal + tax - Decimal(str(discount))
    return subtotal, tax, max(total, Decimal("0"))


@router.get("", response_class=HTMLResponse)
async def list_quotations(request: Request, db: Session = Depends(get_db), page: int = 1):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(Quotation)
    total = query.count()
    quotations = query.order_by(Quotation.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    return templates.TemplateResponse("quotations/list.html", {
        "request": request, "quotations": quotations, "total": total,
        "page": page, "total_pages": (total + 19) // 20,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_quotation(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    tax_rate = SettingsService(db).get("default_tax_rate", "15")
    return templates.TemplateResponse("quotations/form.html", {
        "request": request, "quotation": None, "clients": clients,
        "default_tax_rate": tax_rate,
    })


@router.post("/new")
async def create_quotation(
    request: Request, db: Session = Depends(get_db),
    client_id: int = Form(...), title: str = Form(...),
    tax_rate: float = Form(0), discount: float = Form(0),
    valid_until: Optional[str] = Form(None), notes: Optional[str] = Form(None),
    items_json: str = Form("[]"),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    items = json.loads(items_json)
    subtotal, tax, total = _calc(items, tax_rate, discount)
    q = Quotation(
        quote_number=_gen_number(db), client_id=client_id, title=title,
        tax_rate=Decimal(str(tax_rate)), discount=Decimal(str(discount)),
        subtotal=subtotal, tax_amount=tax, total=total,
        valid_until=date.fromisoformat(valid_until) if valid_until else None,
        notes=notes or None, created_by=request.session["user_id"],
    )
    db.add(q)
    db.flush()
    for i, item in enumerate(items):
        qty = Decimal(str(item.get("quantity", 1)))
        price = Decimal(str(item.get("unit_price", 0)))
        db.add(QuotationItem(quotation_id=q.id, description=item.get("description", ""),
                              quantity=qty, unit_price=price, total=qty * price, sort_order=i))
    db.commit()
    db.refresh(q)
    ActivityService(db).log(request.session["user_id"], "create", "quotations", q.id, f"إنشاء عرض: {q.quote_number}")
    return RedirectResponse(url=f"/quotations/{q.id}", status_code=302)


@router.get("/{qid}", response_class=HTMLResponse)
async def view_quotation(request: Request, qid: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    q = db.query(Quotation).filter(Quotation.id == qid).first()
    if not q:
        raise HTTPException(status_code=404)
    company_settings = SettingsService(db).get_all()
    return templates.TemplateResponse("quotations/detail.html", {
        "request": request, "quotation": q, "settings": company_settings
    })


@router.get("/{qid}/print", response_class=HTMLResponse)
async def print_quotation(request: Request, qid: int, db: Session = Depends(get_db)):
    """صفحة طباعة عرض السعر"""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    q = db.query(Quotation).filter(Quotation.id == qid).first()
    if not q:
        raise HTTPException(status_code=404)
    company_settings = SettingsService(db).get_all()
    return templates.TemplateResponse("quotations/print.html", {
        "request": request, "quotation": q, "settings": company_settings
    })


@router.get("/{qid}/pdf")
async def download_quotation_pdf(request: Request, qid: int, db: Session = Depends(get_db)):
    """تنزيل عرض السعر كملف PDF"""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    q = db.query(Quotation).filter(Quotation.id == qid).first()
    if not q:
        raise HTTPException(status_code=404)
    company_settings = SettingsService(db).get_all()
    from app.services.html_pdf_service import generate_quotation_pdf
    pdf_bytes = generate_quotation_pdf(q, company_settings)
    filename = f"quotation-{q.quote_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{qid}/to-invoice")
async def quotation_to_invoice(request: Request, qid: int, db: Session = Depends(get_db)):
    """تحويل عرض السعر إلى فاتورة"""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    q = db.query(Quotation).filter(Quotation.id == qid).first()
    if not q:
        raise HTTPException(status_code=404)
    from app.services.invoice_service import InvoiceService
    service = InvoiceService(db)
    items = [{"description": i.description, "quantity": float(i.quantity), "unit_price": float(i.unit_price)} for i in q.items]
    invoice = service.create(
        {"client_id": q.client_id, "quotation_id": q.id, "issue_date": date.today(),
         "tax_rate": q.tax_rate, "discount": q.discount, "notes": q.notes},
        items_data=items, created_by=request.session["user_id"],
    )
    q.status = QuotationStatus.ACCEPTED
    db.commit()
    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=302)
