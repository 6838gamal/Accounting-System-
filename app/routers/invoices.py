"""
مسارات إدارة الفواتير
"""
import json
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.services.invoice_service import InvoiceService
from app.services.activity_service import ActivityService
from app.services.settings_service import SettingsService
from app.models.client import Client
from app.models.invoice import InvoiceStatus

router = APIRouter(prefix="/invoices", tags=["invoices"])
templates = _shared_templates
logger = logging.getLogger(__name__)

_VALID_STATUSES = {s.value for s in InvoiceStatus}


def _validate_items(items: list) -> Optional[str]:
    """التحقق من صحة بنود الفاتورة. يُعيد رسالة خطأ أو None."""
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
async def list_invoices(
    request: Request, db: Session = Depends(get_db),
    status: Optional[str] = None, client_id: Optional[int] = None,
    page: int = Query(default=1, ge=1),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    # تجاهل حالة غير معروفة
    if status and status not in _VALID_STATUSES:
        status = None
    service = InvoiceService(db)
    service.update_overdue()
    invoices, total = service.get_all(skip=(page - 1) * 20, limit=20, client_id=client_id, status=status)
    summary = service.get_summary()
    return templates.TemplateResponse("invoices/list.html", {
        "request": request, "invoices": invoices, "total": total,
        "page": page, "total_pages": max(1, (total + 19) // 20),
        "status_filter": status, "summary": summary,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_invoice(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    s = SettingsService(db).get_all()
    return templates.TemplateResponse("invoices/form.html", {
        "request": request, "invoice": None, "clients": clients,
        "default_tax_rate": s.get("default_tax_rate", "15"),
        "currency": s.get("currency", "SAR"),
        "default_notes": s.get("invoice_notes", ""),
        "error": None,
        "today": date.today(),
    })


@router.post("/new")
async def create_invoice(
    request: Request, db: Session = Depends(get_db),
    client_id: int = Form(...), issue_date: str = Form(...),
    due_date: Optional[str] = Form(None), tax_rate: str = Form("0"),
    discount: str = Form("0"), notes: Optional[str] = Form(None),
    items_json: str = Form("[]"),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)

    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    s = SettingsService(db).get_all()

    def _form_error(msg: str):
        return templates.TemplateResponse("invoices/form.html", {
            "request": request, "invoice": None, "clients": clients,
            "default_tax_rate": s.get("default_tax_rate", "15"),
            "currency": s.get("currency", "SAR"),
            "default_notes": s.get("invoice_notes", ""),
            "error": msg, "today": date.today(),
        })

    # التحقق من الطرف الآخر
    client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
    if not client:
        return _form_error("العميل المحدد غير موجود أو غير نشط.")

    # تحليل البنود
    try:
        items = json.loads(items_json) if items_json else []
        if not isinstance(items, list):
            raise ValueError
        if len(items) > 100:
            items = items[:100]
    except (json.JSONDecodeError, ValueError):
        return _form_error("بيانات البنود غير صالحة. يرجى إعادة إدخال البنود.")

    item_error = _validate_items(items)
    if item_error:
        return _form_error(item_error)

    # التحقق من التواريخ
    try:
        parsed_issue = date.fromisoformat(issue_date)
        parsed_due = date.fromisoformat(due_date) if due_date else None
    except (ValueError, TypeError):
        return _form_error("تاريخ غير صالح. يرجى التحقق من تواريخ الفاتورة.")

    if parsed_due and parsed_due < parsed_issue:
        return _form_error("تاريخ الاستحقاق يجب أن يكون بعد تاريخ الإصدار أو مساوياً له.")

    # التحقق من النسب والخصم
    try:
        d_tax = Decimal(tax_rate)
        d_discount = Decimal(discount)
    except (InvalidOperation, ValueError):
        return _form_error("نسبة الضريبة أو الخصم غير صالحة.")

    if d_tax < 0:
        return _form_error("نسبة الضريبة لا يمكن أن تكون سالبة.")
    if d_discount < 0:
        return _form_error("قيمة الخصم لا يمكن أن تكون سالبة.")

    try:
        service = InvoiceService(db)
        invoice = service.create(
            {"client_id": client_id, "issue_date": parsed_issue, "due_date": parsed_due,
             "tax_rate": d_tax, "discount": d_discount, "notes": notes or None},
            items_data=items, created_by=request.session["user_id"],
        )
    except Exception:
        logger.exception("خطأ أثناء إنشاء الفاتورة")
        db.rollback()
        return _form_error("حدث خطأ أثناء حفظ الفاتورة. يرجى التحقق من البيانات.")

    try:
        ActivityService(db).log(request.session["user_id"], "create", "invoices", invoice.id, f"إنشاء فاتورة: {invoice.invoice_number}")
    except Exception:
        logger.warning("فشل تسجيل النشاط للفاتورة %s", invoice.id)

    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=302)


@router.get("/{invoice_id}/edit", response_class=HTMLResponse)
async def edit_invoice_form(request: Request, invoice_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    invoice = InvoiceService(db).get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    if invoice.status.value in ("paid", "cancelled"):
        return RedirectResponse(url=f"/invoices/{invoice_id}", status_code=302)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    s = SettingsService(db).get_all()
    return templates.TemplateResponse("invoices/form.html", {
        "request": request, "invoice": invoice, "clients": clients,
        "default_tax_rate": s.get("default_tax_rate", "15"),
        "currency": s.get("currency", "SAR"),
        "default_notes": s.get("invoice_notes", ""),
        "error": None, "today": invoice.issue_date,
    })


@router.post("/{invoice_id}/edit")
async def update_invoice(
    request: Request, invoice_id: int, db: Session = Depends(get_db),
    client_id: int = Form(...), issue_date: str = Form(...),
    due_date: Optional[str] = Form(None), tax_rate: str = Form("0"),
    discount: str = Form("0"), notes: Optional[str] = Form(None),
    items_json: str = Form("[]"),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)

    existing = InvoiceService(db).get_by_id(invoice_id)
    if not existing:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    if existing.status.value in ("paid", "cancelled"):
        raise HTTPException(status_code=403, detail="لا يمكن تعديل فاتورة مدفوعة أو ملغاة")

    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    s = SettingsService(db).get_all()

    def _form_error(msg: str):
        return templates.TemplateResponse("invoices/form.html", {
            "request": request, "invoice": existing, "clients": clients,
            "default_tax_rate": s.get("default_tax_rate", "15"),
            "currency": s.get("currency", "SAR"),
            "default_notes": s.get("invoice_notes", ""),
            "error": msg, "today": existing.issue_date,
        })

    client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
    if not client:
        return _form_error("العميل المحدد غير موجود أو غير نشط.")

    try:
        items = json.loads(items_json) if items_json else []
        if not isinstance(items, list):
            raise ValueError
        if len(items) > 100:
            items = items[:100]
    except (json.JSONDecodeError, ValueError):
        return _form_error("بيانات البنود غير صالحة. يرجى إعادة إدخال البنود.")

    item_error = _validate_items(items)
    if item_error:
        return _form_error(item_error)

    try:
        parsed_issue = date.fromisoformat(issue_date)
        parsed_due = date.fromisoformat(due_date) if due_date else None
    except (ValueError, TypeError):
        return _form_error("تاريخ غير صالح. يرجى التحقق من تواريخ الفاتورة.")

    if parsed_due and parsed_due < parsed_issue:
        return _form_error("تاريخ الاستحقاق يجب أن يكون بعد تاريخ الإصدار أو مساوياً له.")

    try:
        d_tax = Decimal(tax_rate)
        d_discount = Decimal(discount)
    except (InvalidOperation, ValueError):
        return _form_error("نسبة الضريبة أو الخصم غير صالحة.")

    if d_tax < 0:
        return _form_error("نسبة الضريبة لا يمكن أن تكون سالبة.")
    if d_discount < 0:
        return _form_error("قيمة الخصم لا يمكن أن تكون سالبة.")

    try:
        service = InvoiceService(db)
        invoice = service.update(
            invoice_id,
            {"client_id": client_id, "issue_date": parsed_issue, "due_date": parsed_due,
             "tax_rate": d_tax, "discount": d_discount, "notes": notes or None},
            items_data=items,
        )
    except Exception:
        logger.exception("خطأ أثناء تعديل الفاتورة %s", invoice_id)
        db.rollback()
        return _form_error("حدث خطأ أثناء حفظ التعديلات. يرجى التحقق من البيانات.")

    try:
        ActivityService(db).log(request.session["user_id"], "update", "invoices", invoice.id, f"تعديل فاتورة: {invoice.invoice_number}")
    except Exception:
        logger.warning("فشل تسجيل النشاط للفاتورة %s", invoice_id)

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


@router.get("/{invoice_id}/print", response_class=HTMLResponse)
async def invoice_print(request: Request, invoice_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    invoice = InvoiceService(db).get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404)
    settings = SettingsService(db).get_all()
    return templates.TemplateResponse("invoices/print.html", {
        "request": request, "invoice": invoice, "settings": settings,
    })


@router.get("/{invoice_id}/pdf")
async def invoice_pdf(request: Request, invoice_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    invoice = InvoiceService(db).get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404)
    company_settings = SettingsService(db).get_all()
    try:
        from app.services.pdf_service import generate_invoice_pdf
        pdf_bytes = generate_invoice_pdf(invoice, company_settings)
    except Exception:
        logger.exception("فشل توليد PDF للفاتورة %s", invoice_id)
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء توليد ملف PDF")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=invoice-{invoice.invoice_number}.pdf"},
    )


@router.post("/{invoice_id}/payment")
async def add_payment(
    request: Request, invoice_id: int, db: Session = Depends(get_db),
    amount: str = Form(...), payment_date: str = Form(...),
    method: str = Form("cash"), reference: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)

    try:
        d_amount = Decimal(amount)
    except (InvalidOperation, ValueError):
        return RedirectResponse(url=f"/invoices/{invoice_id}?payment_error=1", status_code=302)

    try:
        parsed_date = date.fromisoformat(payment_date)
    except (ValueError, TypeError):
        return RedirectResponse(url=f"/invoices/{invoice_id}?payment_error=1", status_code=302)

    # التحقق من طريقة الدفع
    valid_methods = {"cash", "bank_transfer", "check", "card"}
    if method not in valid_methods:
        return RedirectResponse(url=f"/invoices/{invoice_id}?payment_error=1", status_code=302)

    try:
        service = InvoiceService(db)
        service.record_payment(
            invoice_id=invoice_id,
            amount=d_amount,
            payment_data={"payment_date": parsed_date, "method": method, "reference": reference, "notes": notes},
            created_by=request.session["user_id"],
        )
    except ValueError as e:
        logger.warning("خطأ في بيانات الدفعة للفاتورة %s: %s", invoice_id, e)
        return RedirectResponse(url=f"/invoices/{invoice_id}?payment_error=1", status_code=302)
    except Exception:
        logger.exception("خطأ أثناء تسجيل الدفعة للفاتورة %s", invoice_id)
        db.rollback()
        return RedirectResponse(url=f"/invoices/{invoice_id}?payment_error=1", status_code=302)

    try:
        ActivityService(db).log(request.session["user_id"], "payment", "invoices", invoice_id, f"دفعة: {d_amount}")
    except Exception:
        logger.warning("فشل تسجيل النشاط للدفعة على الفاتورة %s", invoice_id)

    return RedirectResponse(url=f"/invoices/{invoice_id}", status_code=302)
