"""
خدمة إدارة العملاء
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.contract import Contract


class ClientService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Client], int]:
        query = self.db.query(Client)
        if search:
            query = query.filter(
                or_(
                    Client.name.ilike(f"%{search}%"),
                    Client.email.ilike(f"%{search}%"),
                    Client.phone.ilike(f"%{search}%"),
                )
            )
        if is_active is not None:
            query = query.filter(Client.is_active == is_active)
        total = query.count()
        clients = query.order_by(Client.name).offset(skip).limit(limit).all()
        return clients, total

    def get_by_id(self, client_id: int) -> Optional[Client]:
        return self.db.query(Client).filter(Client.id == client_id).first()

    def create(self, data: dict, created_by: int) -> Client:
        client = Client(**data, created_by=created_by)
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def update(self, client_id: int, data: dict) -> Optional[Client]:
        client = self.get_by_id(client_id)
        if not client:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(client, key, value)
        self.db.commit()
        self.db.refresh(client)
        return client

    def delete(self, client_id: int) -> bool:
        client = self.get_by_id(client_id)
        if not client:
            return False
        client.is_active = False
        self.db.commit()
        return True

    def get_stats(self, client_id: int) -> dict:
        """إحصائيات العميل"""
        total_invoices = self.db.query(func.count(Invoice.id)).filter(
            Invoice.client_id == client_id
        ).scalar() or 0
        total_revenue = self.db.query(func.sum(Invoice.paid_amount)).filter(
            Invoice.client_id == client_id
        ).scalar() or 0
        total_contracts = self.db.query(func.count(Contract.id)).filter(
            Contract.client_id == client_id
        ).scalar() or 0
        return {
            "total_invoices": total_invoices,
            "total_revenue": float(total_revenue),
            "total_contracts": total_contracts,
        }
