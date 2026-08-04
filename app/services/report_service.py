"""
خدمة التقارير
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.expense import Expense, ExpenseStatus
from app.models.client import Client
from app.models.contract import Contract


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_sales_report(self, start_date: date, end_date: date) -> dict:
        """تقرير المبيعات"""
        invoices = self.db.query(Invoice).filter(
            Invoice.issue_date >= start_date,
            Invoice.issue_date <= end_date,
            Invoice.status != InvoiceStatus.CANCELLED,
        ).all()

        total_invoiced = sum(float(inv.total) for inv in invoices)
        total_paid = sum(float(inv.paid_amount) for inv in invoices)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_invoices": len(invoices),
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "total_pending": total_invoiced - total_paid,
            "invoices": invoices,
        }

    def get_monthly_revenue(self, year: int) -> List[dict]:
        """الإيرادات الشهرية"""
        results = []
        for month in range(1, 13):
            revenue = self.db.query(func.sum(Payment.amount)).filter(
                extract("year", Payment.payment_date) == year,
                extract("month", Payment.payment_date) == month,
            ).scalar() or 0
            expenses = self.db.query(func.sum(Expense.amount)).filter(
                extract("year", Expense.expense_date) == year,
                extract("month", Expense.expense_date) == month,
                Expense.status == ExpenseStatus.APPROVED,
            ).scalar() or 0
            results.append({
                "month": month,
                "revenue": float(revenue),
                "expenses": float(expenses),
                "profit": float(revenue) - float(expenses),
            })
        return results

    def get_client_report(self, start_date: date, end_date: date) -> List[dict]:
        """تقرير العملاء"""
        results = self.db.query(
            Client.id,
            Client.name,
            func.count(Invoice.id).label("invoice_count"),
            func.sum(Invoice.total).label("total_amount"),
            func.sum(Invoice.paid_amount).label("paid_amount"),
        ).join(Invoice, Invoice.client_id == Client.id, isouter=True).filter(
            Invoice.issue_date >= start_date,
            Invoice.issue_date <= end_date,
        ).group_by(Client.id, Client.name).order_by(func.sum(Invoice.total).desc()).all()

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

    def get_expense_report(self, start_date: date, end_date: date) -> dict:
        """تقرير المصروفات"""
        expenses = self.db.query(Expense).filter(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
        ).all()

        by_category = {}
        for exp in expenses:
            cat = exp.category
            if cat not in by_category:
                by_category[cat] = {"count": 0, "total": 0}
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

    def get_profit_loss(self, start_date: date, end_date: date) -> dict:
        """تقرير الأرباح والخسائر"""
        revenue = self.db.query(func.sum(Payment.amount)).filter(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date,
        ).scalar() or 0

        expenses = self.db.query(func.sum(Expense.amount)).filter(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
            Expense.status == ExpenseStatus.APPROVED,
        ).scalar() or 0

        return {
            "revenue": float(revenue),
            "expenses": float(expenses),
            "profit": float(revenue) - float(expenses),
            "start_date": start_date,
            "end_date": end_date,
        }
