"""
مسارات لوحة التحكم
"""
from datetime import datetime, date
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.dependencies import get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.models.client import Client
from app.models.contract import Contract
from app.models.payment import Payment
from app.models.expense import Expense, ExpenseStatus
from app.services.report_service import ReportService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = _shared_templates


def require_login(request: Request):
    if not request.session.get("user_id"):
        from fastapi.responses import RedirectResponse
        return None
    return request.session.get("user_id")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login", status_code=302)

    today = date.today()
    current_year = today.year
    current_month = today.month

    # إحصائيات الشهر الحالي
    monthly_revenue = db.query(func.sum(Payment.amount)).filter(
        extract("year", Payment.payment_date) == current_year,
        extract("month", Payment.payment_date) == current_month,
    ).scalar() or 0

    total_clients = db.query(func.count(Client.id)).filter(Client.is_active == True).scalar() or 0
    pending_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL])
    ).scalar() or 0
    overdue_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.status == InvoiceStatus.OVERDUE
    ).scalar() or 0

    # الفواتير الأخيرة
    latest_invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(5).all()

    # العقود الأخيرة
    latest_contracts = db.query(Contract).order_by(Contract.created_at.desc()).limit(5).all()

    # بيانات الرسم البياني (12 شهر)
    report_service = ReportService(db)
    monthly_data = report_service.get_monthly_revenue(current_year)
    chart_labels = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
    chart_revenue = [m["revenue"] for m in monthly_data]
    chart_expenses = [m["expenses"] for m in monthly_data]

    # إجمالي المصروفات هذا الشهر
    monthly_expenses = db.query(func.sum(Expense.amount)).filter(
        extract("year", Expense.expense_date) == current_year,
        extract("month", Expense.expense_date) == current_month,
        Expense.status == ExpenseStatus.APPROVED,
    ).scalar() or 0

    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "monthly_revenue": float(monthly_revenue),
        "monthly_expenses": float(monthly_expenses),
        "total_clients": total_clients,
        "pending_invoices": pending_invoices,
        "overdue_invoices": overdue_invoices,
        "latest_invoices": latest_invoices,
        "latest_contracts": latest_contracts,
        "chart_labels": chart_labels,
        "chart_revenue": chart_revenue,
        "chart_expenses": chart_expenses,
    })
