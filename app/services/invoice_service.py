"""
خدمة إدارة الفواتير
"""
from datetime import date, datetime
from typing import List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.payment import Payment
from app.config import settings


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def generate_number(self) -> str:
        """توليد رقم فاتورة جديد"""
        last = self.db.query(Invoice).order_by(Invoice.id.desc()).first()
        next_id = (last.id + 1) if last else 1
        return f"{settings.INVOICE_PREFIX}-{datetime.now().year}-{next_id:04d}"

    def calculate_totals(self, items: list, tax_rate: Decimal, discount: Decimal) -> dict:
        """حساب المجاميع"""
        subtotal = sum(Decimal(str(i.get("quantity", 1))) * Decimal(str(i.get("unit_price", 0))) for i in items)
        tax_amount = subtotal * (tax_rate / 100)
        total = subtotal + tax_amount - discount
        return {
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "total": max(total, Decimal("0")),
        }

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Invoice], int]:
        query = self.db.query(Invoice)
        if client_id:
            query = query.filter(Invoice.client_id == client_id)
        if status:
            query = query.filter(Invoice.status == status)
        total = query.count()
        invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
        return invoices, total

    def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def create(self, data: dict, items_data: list, created_by: int) -> Invoice:
        tax_rate = Decimal(str(data.get("tax_rate", 0)))
        discount = Decimal(str(data.get("discount", 0)))
        totals = self.calculate_totals(items_data, tax_rate, discount)

        invoice = Invoice(
            invoice_number=self.generate_number(),
            created_by=created_by,
            **{k: v for k, v in data.items() if k not in ("items",)},
            **totals,
        )
        self.db.add(invoice)
        self.db.flush()

        for i, item_data in enumerate(items_data):
            qty = Decimal(str(item_data.get("quantity", 1)))
            price = Decimal(str(item_data.get("unit_price", 0)))
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=item_data.get("description", ""),
                quantity=qty,
                unit_price=price,
                total=qty * price,
                sort_order=i,
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def record_payment(self, invoice_id: int, amount: Decimal, payment_data: dict, created_by: int) -> Payment:
        """تسجيل دفعة على فاتورة"""
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            raise ValueError("الفاتورة غير موجودة")

        payment = Payment(
            invoice_id=invoice_id,
            client_id=invoice.client_id,
            amount=amount,
            created_by=created_by,
            **payment_data,
        )
        self.db.add(payment)

        # تحديث المبلغ المدفوع وحالة الفاتورة
        invoice.paid_amount = (invoice.paid_amount or Decimal("0")) + amount
        if invoice.paid_amount >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIAL

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update_overdue(self):
        """تحديث حالة الفواتير المتأخرة"""
        today = date.today()
        self.db.query(Invoice).filter(
            Invoice.due_date < today,
            Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL]),
        ).update({"status": InvoiceStatus.OVERDUE})
        self.db.commit()

    def get_summary(self) -> dict:
        """ملخص الفواتير"""
        total = self.db.query(func.sum(Invoice.total)).scalar() or 0
        paid = self.db.query(func.sum(Invoice.paid_amount)).scalar() or 0
        pending_count = self.db.query(func.count(Invoice.id)).filter(
            Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL])
        ).scalar() or 0
        overdue_count = self.db.query(func.count(Invoice.id)).filter(
            Invoice.status == InvoiceStatus.OVERDUE
        ).scalar() or 0
        return {
            "total_invoiced": float(total),
            "total_paid": float(paid),
            "total_pending": float(total) - float(paid),
            "pending_count": pending_count,
            "overdue_count": overdue_count,
        }
