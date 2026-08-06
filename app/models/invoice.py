"""
نموذج الفاتورة
"""
import enum
from datetime import timezone, date, datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, Date, Numeric, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"), nullable=False)
    contract_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("contracts.id"), nullable=True)
    quotation_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("quotations.id"), nullable=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None), nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # العلاقات
    client = relationship("Client", back_populates="invoices")
    contract = relationship("Contract", back_populates="invoices")
    quotation = relationship("Quotation", foreign_keys=[quotation_id], lazy="joined")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.sort_order")
    payments = relationship("Payment", back_populates="invoice", lazy="dynamic")

    @property
    def remaining_amount(self) -> Decimal:
        return self.total - self.paid_amount

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number}>"


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(Integer, ForeignKey("invoices.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # العلاقات
    invoice = relationship("Invoice", back_populates="items")
