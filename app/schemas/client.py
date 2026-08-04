"""
مخططات Pydantic للعملاء
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.client import ClientType


class ClientBase(BaseModel):
    name: str
    type: ClientType = ClientType.COMPANY
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_number: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[ClientType] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_number: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ClientRead(ClientBase):
    id: int
    created_at: datetime
    created_by: Optional[int] = None

    model_config = {"from_attributes": True}
