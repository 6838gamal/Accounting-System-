"""
مسارات سندات الاستلام
"""
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies import get_db
from app.models.receipt_voucher import ReceiptVoucher
from app.models.expense_voucher import VoucherPaymentMethod
from app.models.client import Client
from app.services.activity_service import ActivityService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/receipt-vouchers", tags=["receipt_vouchers"])
templates = _shared_templates
logger = logging.getLogger(__name__)

_VALID_METHODS = {m.value for m in VoucherPaymentMethod}

METHOD_LABELS = {
    "cash": "نقداً", "bank_transfer": "تحويل بنكي", "check": "شيك", "card": "بطاقة",
}


def _next_voucher_number(db: Session) -> str:
    last = db.query(ReceiptVoucher).order_by(ReceiptVoucher.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"RV-{datetime.now().year}-{next_id:04d}"


def _require_login(request: Request):
    return request.session.get("user_id")


def _err_redirect(base: str, msg: str) -> RedirectResponse:
    return RedirectResponse(url=f"{base}?error={quote_plus(msg)}", status_code=302)


def _ok_redirect(base: str, msg: str) -> RedirectResponse:
    return RedirectResponse(url=f"{base}?success={quote_plus(msg)}", status_code=302)


@router.get("", response_class=HTMLResponse)
async def list_receipt_vouchers(
    request: Request, db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(ReceiptVoucher)
    total = query.count()
    vouchers = query.order_by(ReceiptVoucher.voucher_date.desc()).offset((page - 1) * 20).limit(20).all()
    total_amount = sum(float(v.amount) for v in db.query(ReceiptVoucher).all())
    return templates.TemplateResponse("receipt_vouchers/list.html", {
        "request": request, "vouchers": vouchers, "total": total,
        "page": page, "total_pages": max(1, (total + 19) // 20),
        "total_amount": total_amount, "method_labels": METHOD_LABELS,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_receipt_voucher(request: Request, db: Session = Depends(get_db)):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    return templates.TemplateResponse("receipt_vouchers/form.html", {
        "request": request, "voucher": None, "clients": clients,
        "methods": list(VoucherPaymentMethod), "method_labels": METHOD_LABELS,
        "suggested_number": _next_voucher_number(db),
        "today": date.today().isoformat(), "error": None,
    })


@router.post("/new")
async def create_receipt_voucher(
    request: Request, db: Session = Depends(get_db),
    voucher_number: str = Form(...), voucher_date: str = Form(...),
    received_from: str = Form(...), amount: str = Form(...),
    method: str = Form("cash"), client_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None), reference: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)

    def _form_error(msg: str):
        clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
        return templates.TemplateResponse("receipt_vouchers/form.html", {
            "request": request, "voucher": None, "clients": clients,
            "methods": list(VoucherPaymentMethod), "method_labels": METHOD_LABELS,
            "suggested_number": _next_voucher_number(db),
            "today": date.today().isoformat(), "error": msg,
        })

    voucher_number = voucher_number.strip()
    if not voucher_number:
        return _form_error("رقم السند مطلوب.")

    received_from = received_from.strip()
    if not received_from:
        return _form_error("اسم المستلم منه مطلوب.")

    try:
        d_amount = Decimal(amount)
    except (InvalidOperation, ValueError):
        return _form_error("المبلغ غير صالح.")
    if d_amount <= 0:
        return _form_error("المبلغ يجب أن يكون أكبر من الصفر.")

    if method not in _VALID_METHODS:
        return _form_error("طريقة الدفع غير صالحة.")

    # التحقق من العميل إذا حُدِّد
    if client_id:
        client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
        if not client:
            return _form_error("العميل المحدد غير موجود أو غير نشط.")

    try:
        parsed_date = date.fromisoformat(voucher_date)
    except (ValueError, TypeError):
        return _form_error("تاريخ غير صالح. يرجى التحقق من تاريخ السند.")

    try:
        voucher = ReceiptVoucher(
            voucher_number=voucher_number, voucher_date=parsed_date,
            received_from=received_from, amount=d_amount,
            method=VoucherPaymentMethod(method),
            client_id=client_id if client_id else None,
            description=description or None, reference=reference or None,
            notes=notes or None, created_by=request.session["user_id"],
        )
        db.add(voucher)
        db.commit()
        db.refresh(voucher)
    except Exception:
        logger.exception("خطأ أثناء حفظ سند القبض")
        db.rollback()
        return _form_error("حدث خطأ أثناء حفظ السند، يرجى التحقق من البيانات.")

    try:
        ActivityService(db).log(
            request.session["user_id"], "create", "receipt_vouchers", voucher.id,
            f"سند قبض: {voucher_number} - {received_from}",
        )
    except Exception:
        logger.warning("فشل تسجيل النشاط لسند القبض %s", voucher.id)

    return RedirectResponse(url=f"/receipt-vouchers/{voucher.id}", status_code=302)


@router.get("/{voucher_id}", response_class=HTMLResponse)
async def detail_receipt_voucher(request: Request, voucher_id: int, db: Session = Depends(get_db)):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    voucher = db.query(ReceiptVoucher).filter(ReceiptVoucher.id == voucher_id).first()
    if not voucher:
        return RedirectResponse(url="/receipt-vouchers", status_code=302)
    return templates.TemplateResponse("receipt_vouchers/detail.html", {
        "request": request, "voucher": voucher,
        "settings": SettingsService(db).get_all(), "method_labels": METHOD_LABELS,
    })


@router.get("/{voucher_id}/print", response_class=HTMLResponse)
async def print_receipt_voucher(request: Request, voucher_id: int, db: Session = Depends(get_db)):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    voucher = db.query(ReceiptVoucher).filter(ReceiptVoucher.id == voucher_id).first()
    if not voucher:
        return RedirectResponse(url="/receipt-vouchers", status_code=302)
    return templates.TemplateResponse("receipt_vouchers/print.html", {
        "request": request, "voucher": voucher,
        "settings": SettingsService(db).get_all(), "method_labels": METHOD_LABELS,
    })


@router.post("/{voucher_id}/delete")
async def delete_receipt_voucher(request: Request, voucher_id: int, db: Session = Depends(get_db)):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    voucher = db.query(ReceiptVoucher).filter(ReceiptVoucher.id == voucher_id).first()
    if not voucher:
        return RedirectResponse(url="/receipt-vouchers", status_code=302)

    saved_number = voucher.voucher_number

    try:
        db.delete(voucher)
        db.commit()
    except Exception:
        logger.exception("خطأ أثناء حذف سند القبض %s", voucher_id)
        db.rollback()
        return _err_redirect("/receipt-vouchers", "حدث خطأ أثناء حذف السند.")

    try:
        ActivityService(db).log(
            request.session["user_id"], "delete", "receipt_vouchers", voucher_id,
            f"حذف سند قبض: {saved_number}",
        )
    except Exception:
        logger.warning("فشل تسجيل النشاط لحذف سند القبض %s", voucher_id)

    return _ok_redirect("/receipt-vouchers", "تم حذف السند بنجاح")
