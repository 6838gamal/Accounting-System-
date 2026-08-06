"""
مسارات إدارة المدفوعات
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.models.payment import Payment

router = APIRouter(prefix="/payments", tags=["payments"])
templates = _shared_templates


@router.get("", response_class=HTMLResponse)
async def list_payments(request: Request, db: Session = Depends(get_db), page: int = 1):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(Payment)
    total = query.count()
    payments = query.order_by(Payment.payment_date.desc()).offset((page - 1) * 20).limit(20).all()
    total_amount = sum(float(p.amount) for p in db.query(Payment).all())
    return templates.TemplateResponse("payments/list.html", {
        "request": request, "payments": payments, "total": total,
        "page": page, "total_pages": (total + 19) // 20,
        "total_amount": total_amount,
    })
