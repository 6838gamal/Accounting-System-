"""
نموذج سند الاستلام
"""
import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, Date, Numeric, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.expense_voucher import VoucherPaymentMethod


class ReceiptVoucher(Base):
    __tablename__ = "receipt_vouchers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    voucher_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    voucher_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_from: Mapped[str] = mapped_column(String(255), nullable=False)   # المستلم منه
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    method: Mapped[VoucherPaymentMethod] = mapped_column(
        SAEnum(VoucherPaymentMethod), default=VoucherPaymentMethod.CASH, nullable=False
    )
    client_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("clients.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)      # البيان
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)  # رقم المرجع
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    client = relationship("Client", foreign_keys=[client_id])
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<ReceiptVoucher {self.voucher_number} - {self.amount}>"
