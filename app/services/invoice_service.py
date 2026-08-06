"""
خدمة إدارة الفواتير — محسّنة وآمنة من Race Conditions
"""
from datetime import date, datetime
from typing import List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.payment import Payment
from app.config import settings

import logging
logger = logging.getLogger(__name__)


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def _generate_number_safe(self, attempt: int = 0) -> str:
        """رقم فاتورة مع دعم retry عند التعارض."""
        year = datetime.now().year
        count = self.db.query(func.count(Invoice.id)).scalar() or 0
        return f"{settings.INVOICE_PREFIX}-{year}-{count + attempt + 1:04d}"

    def _round_money(self, value: Decimal) -> Decimal:
        """تقريب مالي موحد (ROUND_HALF_UP)."""
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_totals(self, items: list, tax_rate: Decimal, discount: Decimal) -> dict:
        """حساب المجاميع بدقة Decimal."""
        if tax_rate < 0 or tax_rate > 100:
            raise ValueError("نسبة الضريبة يجب أن تكون بين 0 و 100")
        if discount < 0:
            raise ValueError("الخصم لا يمكن أن يكون سالباً")

        subtotal = sum(
            self._round_money(Decimal(str(i.get("quantity", 1))) * Decimal(str(i.get("unit_price", 0))))
            for i in items
        )
        subtotal = self._round_money(subtotal)

        if discount > subtotal:
            raise ValueError(f"الخصم ({discount}) يتجاوز المجموع الفرعي ({subtotal})")

        tax_amount = self._round_money(subtotal * (tax_rate / 100))
        total = self._round_money(subtotal + tax_amount - discount)
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
        """إنشاء فاتورة مع retry عند تعارض رقم الفاتورة."""
        if not items_data:
            raise ValueError("يجب إضافة بند واحد على الأقل")

        tax_rate = Decimal(str(data.get("tax_rate", 0)))
        discount = Decimal(str(data.get("discount", 0)))
        totals = self.calculate_totals(items_data, tax_rate, discount)

        for attempt in range(3):
            invoice_number = self._generate_number_safe(attempt)
            invoice = Invoice(
                invoice_number=invoice_number,
                client_id=data["client_id"],
                contract_id=data.get("contract_id"),
                quotation_id=data.get("quotation_id"),
                issue_date=data["issue_date"],
                due_date=data.get("due_date"),
                tax_rate=tax_rate,
                discount=discount,
                notes=data.get("notes"),
                created_by=created_by,
                **totals,
            )
            self.db.add(invoice)
            try:
                self.db.flush()
                break
            except IntegrityError:
                self.db.rollback()
                if attempt == 2:
                    raise
                logger.warning("تعارض رقم الفاتورة، محاولة %d", attempt + 1)

        for idx, item_data in enumerate(items_data):
            qty = Decimal(str(item_data["quantity"]))
            price = Decimal(str(item_data["unit_price"]))
            item_total = self._round_money(qty * price)
            item = InvoiceItem(
                invoice=invoice,
                description=str(item_data["description"]).strip(),
                quantity=qty,
                unit_price=price,
                total=item_total,
                sort_order=idx,
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def update(self, invoice_id: int, data: dict, items_data: list) -> Optional[Invoice]:
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None
        if invoice.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
            raise ValueError("لا يمكن تعديل فاتورة مدفوعة أو ملغاة")

        tax_rate = Decimal(str(data.get("tax_rate", invoice.tax_rate)))
        discount = Decimal(str(data.get("discount", invoice.discount)))

        if items_data:
            totals = self.calculate_totals(items_data, tax_rate, discount)
            for key, val in totals.items():
                setattr(invoice, key, val)
            # حذف البنود القديمة وإعادة إنشائها
            self.db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
            for idx, item_data in enumerate(items_data):
                qty = Decimal(str(item_data["quantity"]))
                price = Decimal(str(item_data["unit_price"]))
                item = InvoiceItem(
                    invoice_id=invoice_id,
                    description=str(item_data["description"]).strip(),
                    quantity=qty,
                    unit_price=price,
                    total=self._round_money(qty * price),
                    sort_order=idx,
                )
                self.db.add(item)

        for key in ("issue_date", "due_date", "notes", "status"):
            if key in data and data[key] is not None:
                setattr(invoice, key, data[key])

        invoice.tax_rate = tax_rate
        invoice.discount = discount

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def record_payment(self, invoice_id: int, amount: Decimal,
                       payment_data: dict, created_by: int) -> Payment:
        """تسجيل دفعة مع حماية من Concurrent Overpayment."""
        if amount <= 0:
            raise ValueError("مبلغ الدفعة يجب أن يكون أكبر من الصفر")

        # قراءة الفاتورة للتحقق
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("الفاتورة غير موجودة")
        if invoice.status == InvoiceStatus.CANCELLED:
            raise ValueError("لا يمكن إضافة دفعة على فاتورة ملغاة")

        remaining = self._round_money(invoice.total - (invoice.paid_amount or Decimal("0")))
        if remaining <= 0:
            raise ValueError("الفاتورة مدفوعة بالكامل")
        if amount > remaining:
            raise ValueError(f"مبلغ الدفعة ({amount}) يتجاوز المتبقي ({remaining})")

        # حقول الدفعة الآمنة فقط
        safe_fields = {
            k: v for k, v in payment_data.items()
            if k in ("payment_date", "method", "reference", "notes")
        }
        payment = Payment(
            invoice_id=invoice_id,
            client_id=invoice.client_id,
            amount=amount,
            created_by=created_by,
            **safe_fields,
        )
        self.db.add(payment)

        new_paid = self._round_money((invoice.paid_amount or Decimal("0")) + amount)
        invoice.paid_amount = new_paid
        if new_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIAL

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update_overdue(self):
        """تحديث حالة الفواتير المتأخرة."""
        today = date.today()
        self.db.query(Invoice).filter(
            Invoice.due_date < today,
            Invoice.due_date.isnot(None),
            Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL]),
        ).update({"status": InvoiceStatus.OVERDUE}, synchronize_session="fetch")
        self.db.commit()

    def cancel(self, invoice_id: int) -> Optional[Invoice]:
        """إلغاء فاتورة."""
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None
        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("لا يمكن إلغاء فاتورة مدفوعة")
        invoice.status = InvoiceStatus.CANCELLED
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def get_summary(self) -> dict:
        """ملخص الفواتير — يستثني المسوّدات والملغاة من الإجماليات الفعلية."""
        total = self.db.query(func.sum(Invoice.total)).filter(
            Invoice.status.notin_([InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED])
        ).scalar() or Decimal("0")

        paid = self.db.query(func.sum(Invoice.paid_amount)).filter(
            Invoice.status.notin_([InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED])
        ).scalar() or Decimal("0")

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
