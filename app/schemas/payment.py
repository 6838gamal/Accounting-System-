"""
مخططات Pydantic للمدفوعات
"""
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from decimal import Decimal
from app.models.payment import PaymentMethod


class PaymentBase(BaseModel):
    invoice_id: int
    client_id: int
    amount: Decimal
    payment_date: date
    method: PaymentMethod = PaymentMethod.CASH
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentRead(PaymentBase):
    id: int
    created_at: datetime
    created_by: Optional[int] = None

    model_config = {"from_attributes": True}
