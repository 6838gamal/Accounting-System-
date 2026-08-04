"""
مسارات إدارة العقود
"""
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from app.dependencies import get_db
from app.models.contract import Contract, ContractStatus
from app.models.client import Client
from app.services.activity_service import ActivityService
from app.services.settings_service import SettingsService
from app.config import settings

router = APIRouter(prefix="/contracts", tags=["contracts"])
templates = Jinja2Templates(directory="app/templates")


def _generate_number(db: Session) -> str:
    last = db.query(Contract).order_by(Contract.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"{settings.CONTRACT_PREFIX}-{datetime.now().year}-{next_id:04d}"


@router.get("", response_class=HTMLResponse)
async def list_contracts(request: Request, db: Session = Depends(get_db), search: Optional[str] = None, page: int = 1):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(Contract)
    if search:
        query = query.filter(Contract.title.ilike(f"%{search}%"))
    total = query.count()
    contracts = query.order_by(Contract.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    return templates.TemplateResponse("contracts/list.html", {
        "request": request, "contracts": contracts, "total": total,
        "page": page, "search": search or "", "total_pages": (total + 19) // 20,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_contract(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    return templates.TemplateResponse("contracts/form.html", {
        "request": request, "contract": None, "clients": clients, "error": None
    })


@router.post("/new")
async def create_contract(
    request: Request, db: Session = Depends(get_db),
    client_id: int = Form(...), title: str = Form(...),
    description: Optional[str] = Form(None), amount: float = Form(0),
    start_date: Optional[str] = Form(None), end_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    from datetime import date
    contract = Contract(
        contract_number=_generate_number(db),
        client_id=client_id, title=title,
        description=description or None,
        amount=Decimal(str(amount)),
        start_date=date.fromisoformat(start_date) if start_date else None,
        end_date=date.fromisoformat(end_date) if end_date else None,
        notes=notes or None,
        created_by=request.session["user_id"],
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    ActivityService(db).log(request.session["user_id"], "create", "contracts", contract.id, f"إنشاء عقد: {title}")
    return RedirectResponse(url=f"/contracts/{contract.id}", status_code=302)


@router.get("/{contract_id}", response_class=HTMLResponse)
async def view_contract(request: Request, contract_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    return templates.TemplateResponse("contracts/detail.html", {"request": request, "contract": contract})


@router.get("/{contract_id}/edit", response_class=HTMLResponse)
async def edit_contract(request: Request, contract_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
    return templates.TemplateResponse("contracts/form.html", {
        "request": request, "contract": contract, "clients": clients, "error": None
    })


@router.post("/{contract_id}/edit")
async def update_contract(
    request: Request, contract_id: int, db: Session = Depends(get_db),
    client_id: int = Form(...), title: str = Form(...),
    description: Optional[str] = Form(None), amount: float = Form(0),
    start_date: Optional[str] = Form(None), end_date: Optional[str] = Form(None),
    status: str = Form("draft"), notes: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    from datetime import date
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404)
    contract.client_id = client_id
    contract.title = title
    contract.description = description or None
    contract.amount = Decimal(str(amount))
    contract.start_date = date.fromisoformat(start_date) if start_date else None
    contract.end_date = date.fromisoformat(end_date) if end_date else None
    contract.status = status
    contract.notes = notes or None
    db.commit()
    ActivityService(db).log(request.session["user_id"], "update", "contracts", contract_id, f"تعديل عقد: {title}")
    return RedirectResponse(url=f"/contracts/{contract_id}", status_code=302)


@router.get("/{contract_id}/print", response_class=HTMLResponse)
async def print_contract(request: Request, contract_id: int, db: Session = Depends(get_db)):
    """صفحة طباعة العقد"""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    company_settings = SettingsService(db).get_all()
    return templates.TemplateResponse("contracts/print.html", {
        "request": request, "contract": contract, "settings": company_settings
    })


@router.get("/{contract_id}/pdf")
async def download_contract_pdf(request: Request, contract_id: int, db: Session = Depends(get_db)):
    """تنزيل العقد كملف PDF"""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    company_settings = SettingsService(db).get_all()
    from app.services.pdf_service import generate_contract_pdf
    pdf_bytes = generate_contract_pdf(contract, company_settings)
    filename = f"contract-{contract.contract_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{contract_id}/to-invoice")
async def contract_to_invoice(request: Request, contract_id: int, db: Session = Depends(get_db)):
    """تحويل العقد إلى فاتورة"""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404)
    from app.services.invoice_service import InvoiceService
    from datetime import date
    service = InvoiceService(db)
    invoice = service.create(
        {
            "client_id": contract.client_id,
            "contract_id": contract.id,
            "issue_date": date.today(),
            "tax_rate": Decimal("0"),
            "discount": Decimal("0"),
            "notes": f"تم إنشاؤها من العقد رقم {contract.contract_number}",
        },
        items_data=[{"description": contract.title, "quantity": 1, "unit_price": float(contract.amount)}],
        created_by=request.session["user_id"],
    )
    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=302)
