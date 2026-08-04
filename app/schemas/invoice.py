"""
مخططات Pydantic للفواتير
"""
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from app.models.invoice import InvoiceStatus


class InvoiceItemBase(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    sort_order: int = 0


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemRead(InvoiceItemBase):
    id: int
    total: Decimal
    model_config = {"from_attributes": True}


class InvoiceBase(BaseModel):
    client_id: int
    contract_id: Optional[int] = None
    quotation_id: Optional[int] = None
    issue_date: date
    due_date: Optional[date] = None
    tax_rate: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate] = []


class InvoiceUpdate(BaseModel):
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    tax_rate: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    status: Optional[InvoiceStatus] = None
    notes: Optional[str] = None


class InvoiceRead(InvoiceBase):
    id: int
    invoice_number: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    paid_amount: Decimal
    status: InvoiceStatus
    created_at: datetime
    items: List[InvoiceItemRead] = []

    model_config = {"from_attributes": True}
