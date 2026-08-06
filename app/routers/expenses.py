"""
مسارات إدارة المصروفات
"""
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.models.expense import Expense, ExpenseStatus
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/expenses", tags=["expenses"])
templates = _shared_templates
logger = logging.getLogger(__name__)

EXPENSE_CATEGORIES = [
    "رواتب", "إيجار", "مرافق", "تسويق", "سفر", "معدات", "صيانة",
    "قرطاسية", "اتصالات", "تأمين", "ضرائب ورسوم", "أخرى"
]
_VALID_CATEGORIES = set(EXPENSE_CATEGORIES)


@router.get("", response_class=HTMLResponse)
async def list_expenses(
    request: Request, db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1), status: Optional[str] = None,
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(Expense)
    if status and status in {s.value for s in ExpenseStatus}:
        query = query.filter(Expense.status == status)
    else:
        status = None
    total = query.count()
    expenses = query.order_by(Expense.expense_date.desc()).offset((page - 1) * 20).limit(20).all()
    total_amount = sum(float(e.amount) for e in db.query(Expense).filter(Expense.status == ExpenseStatus.APPROVED).all())
    return templates.TemplateResponse("expenses/list.html", {
        "request": request, "expenses": expenses, "total": total,
        "page": page, "total_pages": max(1, (total + 19) // 20),
        "total_amount": total_amount, "status_filter": status,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_expense(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("expenses/form.html", {
        "request": request, "expense": None, "categories": EXPENSE_CATEGORIES, "error": None
    })


@router.post("/new")
async def create_expense(
    request: Request, db: Session = Depends(get_db),
    title: str = Form(...), category: str = Form(...),
    amount: str = Form(...), expense_date: str = Form(...),
    description: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)

    def _form_error(msg: str):
        return templates.TemplateResponse("expenses/form.html", {
            "request": request, "expense": None, "categories": EXPENSE_CATEGORIES, "error": msg
        })

    title = title.strip()
    if not title:
        return _form_error("عنوان المصروف مطلوب.")
    if len(title) > 200:
        return _form_error("عنوان المصروف يجب ألا يتجاوز 200 حرف.")

    if category not in _VALID_CATEGORIES:
        return _form_error("الفئة المحددة غير صالحة.")

    try:
        d_amount = Decimal(amount)
    except (InvalidOperation, ValueError):
        return _form_error("المبلغ غير صالح.")
    if d_amount <= 0:
        return _form_error("المبلغ يجب أن يكون أكبر من الصفر.")

    try:
        parsed_date = date.fromisoformat(expense_date)
    except (ValueError, TypeError):
        return _form_error("تاريخ غير صالح. يرجى التحقق من تاريخ المصروف.")

    try:
        expense = Expense(
            title=title, category=category,
            amount=d_amount, expense_date=parsed_date,
            description=description.strip() or None if description else None,
            created_by=request.session["user_id"],
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)
    except Exception:
        logger.exception("خطأ أثناء إنشاء المصروف")
        db.rollback()
        return _form_error("حدث خطأ أثناء حفظ المصروف. يرجى التحقق من البيانات.")

    try:
        ActivityService(db).log(request.session["user_id"], "create", "expenses", expense.id, f"مصروف: {title}")
    except Exception:
        logger.warning("فشل تسجيل النشاط للمصروف %s", expense.id)

    return RedirectResponse(url="/expenses", status_code=302)


@router.post("/{expense_id}/approve")
async def approve_expense(request: Request, expense_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="المصروف غير موجود")
    if expense.status != ExpenseStatus.PENDING:
        return RedirectResponse(url="/expenses", status_code=302)
    try:
        expense.status = ExpenseStatus.APPROVED
        db.commit()
    except Exception:
        logger.exception("خطأ أثناء اعتماد المصروف %s", expense_id)
        db.rollback()
    return RedirectResponse(url="/expenses", status_code=302)


@router.post("/{expense_id}/reject")
async def reject_expense(request: Request, expense_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="المصروف غير موجود")
    if expense.status != ExpenseStatus.PENDING:
        return RedirectResponse(url="/expenses", status_code=302)
    try:
        expense.status = ExpenseStatus.REJECTED
        db.commit()
    except Exception:
        logger.exception("خطأ أثناء رفض المصروف %s", expense_id)
        db.rollback()
    return RedirectResponse(url="/expenses", status_code=302)
