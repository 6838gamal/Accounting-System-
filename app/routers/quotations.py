"""
مسارات عروض الأسعار
"""
import json
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
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
logger = logging.getLogger(__name__)

# الحالات التي يُسمح فيها بتحويل العرض إلى فاتورة
_CONVERTIBLE_STATUSES = {QuotationStatus.DRAFT, QuotationStatus.SENT}


def _gen_number(db: Session) -> str:
    last = db.query(Quotation).order_by(Quotation.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"{app_settings.QUOTE_PREFIX}-{datetime.now().year}-{n:04d}"


def _calc(items, tax_rate: Decimal, discount: Decimal):
    subtotal = sum(Decimal(str(i.get("quantity", 1))) * Decimal(str(i.get("unit_price", 0))) for i in items)
    tax = subtotal * (tax_rate / 100)
    total = subtotal + tax - discount
    return subtotal, tax, max(total, Decimal("0"))


def _validate_items(items: list) -> Optional[str]:
    if not items:
        return "يجب إضافة بند واحد على الأقل."
    for i, item in enumerate(items, 1):
        try:
            qty = Decimal(str(item.get("quantity", 0)))
            price = Decimal(str(item.get("unit_price", 0)))
        except (InvalidOperation, ValueError):
            return f"البند {i}: قيمة الكمية أو السعر غير صالحة."
        if qty <= 0:
            return f"البند {i}: الكمية يجب أن تكون أكبر من الصفر."
        if price < 0:
            return f"البند {i}: السعر لا يمكن أن يكون سالباً."
        if not str(item.get("description", "")).strip():
            return f"البند {i}: الوصف مطلوب."
    return None


@router.get("", response_class=HTMLResponse)
async def list_quotations(
    request: Request, db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(Quotation)
    total = query.count()
    quotations = query.order_by(Quotation.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    return templates.TemplateResponse("quotations/list.html", {
        "request": request, "quotations": quotations, "total": total,
        "page": page, "total_pages": max(1, (total + 19) // 20),
    })


@router.get("/new", response_class=HTMLResponse)
async def new_quotation(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    s = SettingsService(db).get_all()
    return templates.TemplateResponse("quotations/form.html", {
        "request": request, "quotation": None, "clients": clients,
        "default_tax_rate": s.get("default_tax_rate", "15"),
        "currency": s.get("currency", "SAR"),
        "error": None,
    })


@router.post("/new")
async def create_quotation(
    request: Request, db: Session = Depends(get_db),
    client_id: int = Form(...), title: str = Form(...),
    tax_rate: str = Form("0"), discount: str = Form("0"),
    valid_until: Optional[str] = Form(None), notes: Optional[str] = Form(None),
    items_json: str = Form("[]"),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    s = SettingsService(db).get_all()

    def _form_error(msg: str):
        return templates.TemplateResponse("quotations/form.html", {
            "request": request, "quotation": None, "clients": clients,
            "default_tax_rate": s.get("default_tax_rate", "15"),
            "currency": s.get("currency", "SAR"),
            "error": msg,
        })

    # التحقق من العميل
    client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
    if not client:
        return _form_error("العميل المحدد غير موجود أو غير نشط.")

    title = title.strip()
    if not title:
        return _form_error("عنوان العرض مطلوب.")

    # تحليل البنود
    try:
        items = json.loads(items_json)
        if not isinstance(items, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        return _form_error("بيانات البنود غير صالحة. يرجى إعادة إدخال البنود.")

    item_error = _validate_items(items)
    if item_error:
        return _form_error(item_error)

    # التحقق من الأرقام
    try:
        d_tax = Decimal(tax_rate)
        d_discount = Decimal(discount)
    except (InvalidOperation, ValueError):
        return _form_error("نسبة الضريبة أو الخصم غير صالحة.")
    if d_tax < 0:
        return _form_error("نسبة الضريبة لا يمكن أن تكون سالبة.")
    if d_discount < 0:
        return _form_error("قيمة الخصم لا يمكن أن تكون سالبة.")

    # التحقق من التاريخ
    try:
        parsed_valid_until = date.fromisoformat(valid_until) if valid_until else None
    except (ValueError, TypeError):
        return _form_error("تاريخ الصلاحية غير صالح.")

    try:
        subtotal, tax, total = _calc(items, d_tax, d_discount)
        q = Quotation(
            quote_number=_gen_number(db), client_id=client_id, title=title,
            tax_rate=d_tax, discount=d_discount,
            subtotal=subtotal, tax_amount=tax, total=total,
            valid_until=parsed_valid_until,
            notes=notes or None, created_by=request.session["user_id"],
        )
        db.add(q)
        db.flush()
        for i, item in enumerate(items):
            qty = Decimal(str(item.get("quantity", 1)))
            price = Decimal(str(item.get("unit_price", 0)))
            db.add(QuotationItem(
                quotation_id=q.id, description=item.get("description", "").strip(),
                quantity=qty, unit_price=price, total=qty * price, sort_order=i,
            ))
        db.commit()
        db.refresh(q)
    except Exception:
        logger.exception("خطأ أثناء إنشاء عرض السعر")
        db.rollback()
        return _form_error("حدث خطأ أثناء إنشاء العرض. يرجى التحقق من البيانات.")

    try:
        ActivityService(db).log(request.session["user_id"], "create", "quotations", q.id, f"إنشاء عرض: {q.quote_number}")
    except Exception:
        logger.warning("فشل تسجيل النشاط لعرض السعر %s", q.id)

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
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    q = db.query(Quotation).filter(Quotation.id == qid).first()
    if not q:
        raise HTTPException(status_code=404)
    company_settings = SettingsService(db).get_all()
    try:
        from app.services.pdf_service import generate_quotation_pdf
        pdf_bytes = generate_quotation_pdf(q, company_settings)
    except Exception:
        logger.exception("فشل توليد PDF لعرض السعر %s", qid)
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء توليد ملف PDF")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="quotation-{q.quote_number}.pdf"'},
    )


@router.post("/{qid}/to-invoice")
async def quotation_to_invoice(request: Request, qid: int, db: Session = Depends(get_db)):
    """تحويل عرض السعر إلى فاتورة — مسموح فقط للمسودات والمرسلة"""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    q = db.query(Quotation).filter(Quotation.id == qid).first()
    if not q:
        raise HTTPException(status_code=404)

    if q.status not in _CONVERTIBLE_STATUSES:
        # العرض المقبول/المرفوض/المنتهي لا يُحوَّل مجدداً
        return RedirectResponse(url=f"/quotations/{qid}?error=1", status_code=302)

    try:
        from app.services.invoice_service import InvoiceService
        service = InvoiceService(db)
        items = [
            {"description": i.description, "quantity": float(i.quantity), "unit_price": float(i.unit_price)}
            for i in q.items
        ]
        invoice = service.create(
            {"client_id": q.client_id, "quotation_id": q.id, "issue_date": date.today(),
             "tax_rate": q.tax_rate, "discount": q.discount, "notes": q.notes},
            items_data=items, created_by=request.session["user_id"],
        )
        q.status = QuotationStatus.ACCEPTED
        db.commit()
    except Exception:
        logger.exception("خطأ أثناء تحويل عرض السعر %s إلى فاتورة", qid)
        db.rollback()
        return RedirectResponse(url=f"/quotations/{qid}?error=1", status_code=302)

    try:
        ActivityService(db).log(request.session["user_id"], "create", "invoices", invoice.id, f"تحويل من عرض: {q.quote_number}")
    except Exception:
        logger.warning("فشل تسجيل النشاط لتحويل العرض %s", qid)

    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=302)
