"""
مسارات إدارة المدفوعات
"""
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.dependencies import get_db
from app.models.payment import Payment

router = APIRouter(prefix="/payments", tags=["payments"])
templates = _shared_templates


@router.get("", response_class=HTMLResponse)
async def list_payments(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(Payment)
    total = query.count()
    payments = query.order_by(Payment.payment_date.desc()).offset((page - 1) * 20).limit(20).all()
    # استخدام func.sum بدلاً من تحميل جميع السجلات في الذاكرة
    total_amount = float(db.query(func.sum(Payment.amount)).scalar() or 0)
    return templates.TemplateResponse("payments/list.html", {
        "request": request, "payments": payments, "total": total,
        "page": page, "total_pages": max(1, (total + 19) // 20),
        "total_amount": total_amount,
    })
