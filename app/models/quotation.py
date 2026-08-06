"""
نموذج عرض السعر
"""
import enum
from datetime import timezone, date, datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, Date, Numeric, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class QuotationStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quote_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    status: Mapped[QuotationStatus] = mapped_column(SAEnum(QuotationStatus), default=QuotationStatus.DRAFT, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None), nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # العلاقات
    client = relationship("Client", back_populates="quotations")
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan", order_by="QuotationItem.sort_order")

    def __repr__(self) -> str:
        return f"<Quotation {self.quote_number}>"


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quotation_id: Mapped[int] = mapped_column(Integer, ForeignKey("quotations.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # العلاقات
    quotation = relationship("Quotation", back_populates="items")
