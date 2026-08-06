"""
نموذج العميل
"""
import enum
from datetime import timezone, datetime
from sqlalchemy import String, Boolean, DateTime, Text, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ClientType(str, enum.Enum):
    COMPANY = "company"
    INDIVIDUAL = "individual"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    type: Mapped[ClientType] = mapped_column(SAEnum(ClientType), default=ClientType.COMPANY, nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None), nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # العلاقات
    contracts = relationship("Contract", back_populates="client", lazy="dynamic")
    quotations = relationship("Quotation", back_populates="client", lazy="dynamic")
    invoices = relationship("Invoice", back_populates="client", lazy="dynamic")
    payments = relationship("Payment", back_populates="client", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Client {self.name}>"
