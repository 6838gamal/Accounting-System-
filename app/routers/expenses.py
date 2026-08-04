"""
مسارات إدارة المصروفات
"""
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.models.expense import Expense, ExpenseStatus
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/expenses", tags=["expenses"])
templates = Jinja2Templates(directory="app/templates")

EXPENSE_CATEGORIES = [
    "رواتب", "إيجار", "مرافق", "تسويق", "سفر", "معدات", "صيانة",
    "قرطاسية", "اتصالات", "تأمين", "ضرائب ورسوم", "أخرى"
]


@router.get("", response_class=HTMLResponse)
async def list_expenses(request: Request, db: Session = Depends(get_db), page: int = 1, status: Optional[str] = None):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(Expense)
    if status:
        query = query.filter(Expense.status == status)
    total = query.count()
    expenses = query.order_by(Expense.expense_date.desc()).offset((page - 1) * 20).limit(20).all()
    total_amount = sum(float(e.amount) for e in db.query(Expense).filter(Expense.status == ExpenseStatus.APPROVED).all())
    return templates.TemplateResponse("expenses/list.html", {
        "request": request, "expenses": expenses, "total": total,
        "page": page, "total_pages": (total + 19) // 20,
        "total_amount": total_amount, "status_filter": status,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_expense(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("expenses/form.html", {
        "request": request, "expense": None, "categories": EXPENSE_CATEGORIES
    })


@router.post("/new")
async def create_expense(
    request: Request, db: Session = Depends(get_db),
    title: str = Form(...), category: str = Form(...),
    amount: float = Form(...), expense_date: str = Form(...),
    description: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    expense = Expense(
        title=title, category=category,
        amount=Decimal(str(amount)),
        expense_date=date.fromisoformat(expense_date),
        description=description or None,
        created_by=request.session["user_id"],
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    ActivityService(db).log(request.session["user_id"], "create", "expenses", expense.id, f"مصروف: {title}")
    return RedirectResponse(url="/expenses", status_code=302)


@router.post("/{expense_id}/approve")
async def approve_expense(request: Request, expense_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense:
        expense.status = ExpenseStatus.APPROVED
        db.commit()
    return RedirectResponse(url="/expenses", status_code=302)


@router.post("/{expense_id}/reject")
async def reject_expense(request: Request, expense_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense:
        expense.status = ExpenseStatus.REJECTED
        db.commit()
    return RedirectResponse(url="/expenses", status_code=302)
