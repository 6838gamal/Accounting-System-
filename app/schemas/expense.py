"""
مخططات Pydantic للمصروفات
"""
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from decimal import Decimal
from app.models.expense import ExpenseStatus


class ExpenseBase(BaseModel):
    title: str
    category: str
    amount: Decimal
    expense_date: date
    description: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[Decimal] = None
    expense_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[ExpenseStatus] = None


class ExpenseRead(ExpenseBase):
    id: int
    status: ExpenseStatus
    receipt_path: Optional[str] = None
    created_at: datetime
    created_by: Optional[int] = None

    model_config = {"from_attributes": True}
