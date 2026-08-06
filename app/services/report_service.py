"""
خدمة التقارير — محسّنة لتقليل عدد الاستعلامات وتوحيد الأساس المحاسبي
"""
from datetime import date
from decimal import Decimal
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.expense import Expense, ExpenseStatus
from app.models.client import Client

import logging
logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    # ─── مساعدات ────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_dates(start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise ValueError("تاريخ البداية يجب أن يكون قبل تاريخ النهاية")

    # ─── تقرير المبيعات (Accrual Basis) ────────────────────────────────────

    def get_sales_report(self, start_date: date, end_date: date) -> dict:
        """تقرير المبيعات على أساس الاستحقاق (Accrual)."""
        self._validate_dates(start_date, end_date)

        invoices = self.db.query(Invoice).filter(
            Invoice.issue_date >= start_date,
            Invoice.issue_date <= end_date,
            Invoice.status != InvoiceStatus.CANCELLED,
            Invoice.status != InvoiceStatus.DRAFT,
        ).all()

        total_invoiced = sum(Decimal(str(inv.total)) for inv in invoices)
        total_paid = sum(Decimal(str(inv.paid_amount)) for inv in invoices)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_invoices": len(invoices),
            "total_invoiced": float(total_invoiced),
            "total_paid": float(total_paid),
            "total_pending": float(total_invoiced - total_paid),
            "invoices": invoices,
        }

    # ─── الإيرادات الشهرية (استعلامان بدل 24) ───────────────────────────────

    def get_monthly_revenue(self, year: int) -> List[dict]:
        """
        الإيرادات والمصروفات الشهرية — Cash Basis.
        استعلامان فقط بدل 24.
        """
        if not (2000 <= year <= 2100):
            raise ValueError("سنة غير صالحة")

        # استعلام واحد لكل الإيرادات الشهرية
        revenue_rows = self.db.query(
            extract("month", Payment.payment_date).label("month"),
            func.sum(Payment.amount).label("total"),
        ).filter(
            extract("year", Payment.payment_date) == year,
        ).group_by(extract("month", Payment.payment_date)).all()

        # استعلام واحد لكل المصروفات الشهرية
        expense_rows = self.db.query(
            extract("month", Expense.expense_date).label("month"),
            func.sum(Expense.amount).label("total"),
        ).filter(
            extract("year", Expense.expense_date) == year,
            Expense.status == ExpenseStatus.APPROVED,
        ).group_by(extract("month", Expense.expense_date)).all()

        revenue_map = {int(r.month): float(r.total) for r in revenue_rows}
        expense_map = {int(r.month): float(r.total) for r in expense_rows}

        results = []
        for month in range(1, 13):
            rev = revenue_map.get(month, 0.0)
            exp = expense_map.get(month, 0.0)
            results.append({
                "month": month,
                "revenue": rev,
                "expenses": exp,
                "profit": rev - exp,
            })
        return results

    # ─── تقرير العملاء ──────────────────────────────────────────────────────

    def get_client_report(self, start_date: date, end_date: date) -> List[dict]:
        """تقرير العملاء — يشمل العملاء ذوو الصفر فواتير في الفترة."""
        self._validate_dates(start_date, end_date)

        # استخدام outer join مع شرط في JOIN وليس WHERE للحفاظ على العملاء بلا فواتير
        results = self.db.query(
            Client.id,
            Client.name,
            func.count(Invoice.id).label("invoice_count"),
            func.coalesce(func.sum(Invoice.total), 0).label("total_amount"),
            func.coalesce(func.sum(Invoice.paid_amount), 0).label("paid_amount"),
        ).outerjoin(
            Invoice,
            (Invoice.client_id == Client.id) &
            (Invoice.issue_date >= start_date) &
            (Invoice.issue_date <= end_date) &
            (Invoice.status != InvoiceStatus.CANCELLED),
        ).filter(
            Client.is_active == True,
        ).group_by(Client.id, Client.name).order_by(
            func.coalesce(func.sum(Invoice.total), 0).desc()
        ).all()

        return [
            {
                "id": r.id,
                "name": r.name,
                "invoice_count": r.invoice_count or 0,
                "total_amount": float(r.total_amount or 0),
                "paid_amount": float(r.paid_amount or 0),
            }
            for r in results
        ]

    # ─── تقرير المصروفات ────────────────────────────────────────────────────

    def get_expense_report(self, start_date: date, end_date: date) -> dict:
        """تقرير المصروفات المعتمدة فقط (Approved)."""
        self._validate_dates(start_date, end_date)

        expenses = self.db.query(Expense).filter(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
            Expense.status == ExpenseStatus.APPROVED,
        ).all()

        by_category: dict = {}
        for exp in expenses:
            cat = exp.category
            if cat not in by_category:
                by_category[cat] = {"count": 0, "total": 0.0}
            by_category[cat]["count"] += 1
            by_category[cat]["total"] += float(exp.amount)

        total = sum(float(e.amount) for e in expenses)
        return {
            "start_date": start_date,
            "end_date": end_date,
            "expenses": expenses,
            "by_category": by_category,
            "total": total,
        }

    # ─── تقرير الأرباح والخسائر (Cash Basis موحّد) ──────────────────────────

    def get_profit_loss(self, start_date: date, end_date: date) -> dict:
        """
        تقرير الأرباح والخسائر — Cash Basis موحّد.
        الإيرادات: مجموع الدفعات المستلمة في الفترة.
        المصروفات: مجموع المصروفات المعتمدة في الفترة.
        """
        self._validate_dates(start_date, end_date)

        revenue = self.db.query(func.sum(Payment.amount)).filter(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date,
        ).scalar() or Decimal("0")

        expenses = self.db.query(func.sum(Expense.amount)).filter(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
            Expense.status == ExpenseStatus.APPROVED,
        ).scalar() or Decimal("0")

        return {
            "revenue": float(revenue),
            "expenses": float(expenses),
            "profit": float(revenue) - float(expenses),
            "start_date": start_date,
            "end_date": end_date,
        }
