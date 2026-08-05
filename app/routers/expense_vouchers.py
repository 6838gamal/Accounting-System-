"""
مسارات سندات المصاريف
"""
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies import get_db
from app.models.expense_voucher import ExpenseVoucher, VoucherPaymentMethod
from app.services.activity_service import ActivityService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/expense-vouchers", tags=["expense_vouchers"])
templates = Jinja2Templates(directory="app/templates")

EXPENSE_CATEGORIES = [
    "رواتب", "إيجار", "مرافق", "تسويق", "سفر", "معدات", "صيانة",
    "قرطاسية", "اتصالات", "تأمين", "ضرائب ورسوم", "أخرى"
]

METHOD_LABELS = {
    "cash": "نقداً",
    "bank_transfer": "تحويل بنكي",
    "check": "شيك",
    "card": "بطاقة",
}


def _next_voucher_number(db: Session) -> str:
    last = db.query(ExpenseVoucher).order_by(ExpenseVoucher.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"EV-{datetime.utcnow().year}-{next_id:04d}"


def _require_login(request: Request):
    return request.session.get("user_id")


@router.get("", response_class=HTMLResponse)
async def list_expense_vouchers(request: Request, db: Session = Depends(get_db), page: int = 1):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(ExpenseVoucher)
    total = query.count()
    vouchers = query.order_by(ExpenseVoucher.voucher_date.desc()).offset((page - 1) * 20).limit(20).all()
    total_amount = sum(float(v.amount) for v in db.query(ExpenseVoucher).all())
    return templates.TemplateResponse("expense_vouchers/list.html", {
        "request": request,
        "vouchers": vouchers,
        "total": total,
        "page": page,
        "total_pages": (total + 19) // 20,
        "total_amount": total_amount,
        "method_labels": METHOD_LABELS,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_expense_voucher(request: Request, db: Session = Depends(get_db)):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    suggested_number = _next_voucher_number(db)
    return templates.TemplateResponse("expense_vouchers/form.html", {
        "request": request,
        "voucher": None,
        "categories": EXPENSE_CATEGORIES,
        "methods": list(VoucherPaymentMethod),
        "method_labels": METHOD_LABELS,
        "suggested_number": suggested_number,
        "today": date.today().isoformat(),
    })


@router.post("/new")
async def create_expense_voucher(
    request: Request, db: Session = Depends(get_db),
    voucher_number: str = Form(...),
    voucher_date: str = Form(...),
    payee: str = Form(...),
    amount: float = Form(...),
    method: str = Form("cash"),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    reference: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    try:
        voucher = ExpenseVoucher(
            voucher_number=voucher_number,
            voucher_date=date.fromisoformat(voucher_date),
            payee=payee,
            amount=Decimal(str(amount)),
            method=VoucherPaymentMethod(method),
            category=category or None,
            description=description or None,
            reference=reference or None,
            notes=notes or None,
            created_by=request.session["user_id"],
        )
        db.add(voucher)
        db.commit()
        db.refresh(voucher)
        ActivityService(db).log(
            request.session["user_id"], "create", "expense_vouchers", voucher.id,
            f"سند مصروف: {voucher_number} - {payee}"
        )
        return RedirectResponse(url=f"/expense-vouchers/{voucher.id}", status_code=302)
    except Exception:
        db.rollback()
        return RedirectResponse(url="/expense-vouchers?error=حدث+خطأ+أثناء+حفظ+السند،+يرجى+التحقق+من+البيانات", status_code=302)


@router.get("/{voucher_id}", response_class=HTMLResponse)
async def detail_expense_voucher(request: Request, voucher_id: int, db: Session = Depends(get_db)):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    voucher = db.query(ExpenseVoucher).filter(ExpenseVoucher.id == voucher_id).first()
    if not voucher:
        return RedirectResponse(url="/expense-vouchers", status_code=302)
    settings = SettingsService(db).get_all()
    return templates.TemplateResponse("expense_vouchers/detail.html", {
        "request": request,
        "voucher": voucher,
        "settings": settings,
        "method_labels": METHOD_LABELS,
    })


@router.get("/{voucher_id}/print", response_class=HTMLResponse)
async def print_expense_voucher(request: Request, voucher_id: int, db: Session = Depends(get_db)):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    voucher = db.query(ExpenseVoucher).filter(ExpenseVoucher.id == voucher_id).first()
    if not voucher:
        return RedirectResponse(url="/expense-vouchers", status_code=302)
    settings = SettingsService(db).get_all()
    return templates.TemplateResponse("expense_vouchers/print.html", {
        "request": request,
        "voucher": voucher,
        "settings": settings,
        "method_labels": METHOD_LABELS,
    })


@router.post("/{voucher_id}/delete")
async def delete_expense_voucher(request: Request, voucher_id: int, db: Session = Depends(get_db)):
    if not _require_login(request):
        return RedirectResponse(url="/auth/login", status_code=302)
    voucher = db.query(ExpenseVoucher).filter(ExpenseVoucher.id == voucher_id).first()
    if voucher:
        ActivityService(db).log(
            request.session["user_id"], "delete", "expense_vouchers", voucher_id,
            f"حذف سند مصروف: {voucher.voucher_number}"
        )
        db.delete(voucher)
        db.commit()
    return RedirectResponse(url="/expense-vouchers?success=تم+حذف+السند+بنجاح", status_code=302)
