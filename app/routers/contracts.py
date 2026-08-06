"""
مسارات إدارة العقود
"""
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.models.contract import Contract, ContractStatus
from app.models.client import Client
from app.services.activity_service import ActivityService
from app.services.settings_service import SettingsService
from app.config import settings

router = APIRouter(prefix="/contracts", tags=["contracts"])
templates = _shared_templates
logger = logging.getLogger(__name__)

# الحالات التي يُسمح فيها بتحويل العقد إلى فاتورة
_CONVERTIBLE_STATUSES = {ContractStatus.DRAFT, ContractStatus.ACTIVE}


def _generate_number(db: Session) -> str:
    last = db.query(Contract).order_by(Contract.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"{settings.CONTRACT_PREFIX}-{datetime.now().year}-{next_id:04d}"


@router.get("", response_class=HTMLResponse)
async def list_contracts(
    request: Request, db: Session = Depends(get_db),
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    query = db.query(Contract)
    if search:
        query = query.filter(Contract.title.ilike(f"%{search}%"))
    total = query.count()
    contracts = query.order_by(Contract.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    return templates.TemplateResponse("contracts/list.html", {
        "request": request, "contracts": contracts, "total": total,
        "page": page, "search": search or "", "total_pages": max(1, (total + 19) // 20),
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
    description: Optional[str] = Form(None), amount: str = Form("0"),
    start_date: Optional[str] = Form(None), end_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    from datetime import date
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()

    def _form_error(msg: str):
        return templates.TemplateResponse("contracts/form.html", {
            "request": request, "contract": None, "clients": clients, "error": msg
        })

    # التحقق من العميل
    client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
    if not client:
        return _form_error("العميل المحدد غير موجود أو غير نشط.")

    title = title.strip()
    if not title:
        return _form_error("عنوان العقد مطلوب.")

    # التحقق من المبلغ
    try:
        d_amount = Decimal(amount)
    except (InvalidOperation, ValueError):
        return _form_error("قيمة العقد غير صالحة.")
    if d_amount < 0:
        return _form_error("قيمة العقد لا يمكن أن تكون سالبة.")

    # التحقق من التواريخ
    try:
        parsed_start = date.fromisoformat(start_date) if start_date else None
        parsed_end = date.fromisoformat(end_date) if end_date else None
    except (ValueError, TypeError):
        return _form_error("تاريخ غير صالح. يرجى التحقق من تواريخ العقد.")

    if parsed_start and parsed_end and parsed_end < parsed_start:
        return _form_error("تاريخ الانتهاء يجب أن يكون بعد تاريخ البداية أو مساوياً له.")

    try:
        contract = Contract(
            contract_number=_generate_number(db),
            client_id=client_id, title=title,
            description=description or None,
            amount=d_amount,
            start_date=parsed_start, end_date=parsed_end,
            notes=notes or None,
            created_by=request.session["user_id"],
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
    except Exception:
        logger.exception("خطأ أثناء إنشاء العقد")
        db.rollback()
        return _form_error("حدث خطأ أثناء إنشاء العقد. يرجى التحقق من البيانات.")

    try:
        ActivityService(db).log(request.session["user_id"], "create", "contracts", contract.id, f"إنشاء عقد: {title}")
    except Exception:
        logger.warning("فشل تسجيل النشاط لإنشاء العقد %s", contract.id)

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
    description: Optional[str] = Form(None), amount: str = Form("0"),
    start_date: Optional[str] = Form(None), end_date: Optional[str] = Form(None),
    status: str = Form("draft"), notes: Optional[str] = Form(None),
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    from datetime import date
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404)
    clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()

    def _form_error(msg: str):
        return templates.TemplateResponse("contracts/form.html", {
            "request": request, "contract": contract, "clients": clients, "error": msg
        })

    title = title.strip()
    if not title:
        return _form_error("عنوان العقد مطلوب.")

    try:
        d_amount = Decimal(amount)
    except (InvalidOperation, ValueError):
        return _form_error("قيمة العقد غير صالحة.")
    if d_amount < 0:
        return _form_error("قيمة العقد لا يمكن أن تكون سالبة.")

    # التحقق من الحالة
    valid_statuses = {s.value for s in ContractStatus}
    if status not in valid_statuses:
        return _form_error("حالة العقد غير صالحة.")

    try:
        parsed_start = date.fromisoformat(start_date) if start_date else None
        parsed_end = date.fromisoformat(end_date) if end_date else None
    except (ValueError, TypeError):
        return _form_error("تاريخ غير صالح. يرجى التحقق من تواريخ العقد.")

    if parsed_start and parsed_end and parsed_end < parsed_start:
        return _form_error("تاريخ الانتهاء يجب أن يكون بعد تاريخ البداية أو مساوياً له.")

    try:
        contract.client_id = client_id
        contract.title = title
        contract.description = description or None
        contract.amount = d_amount
        contract.start_date = parsed_start
        contract.end_date = parsed_end
        contract.status = ContractStatus(status)
        contract.notes = notes or None
        db.commit()
    except Exception:
        logger.exception("خطأ أثناء تعديل العقد %s", contract_id)
        db.rollback()
        return _form_error("حدث خطأ أثناء حفظ التعديلات. يرجى التحقق من البيانات.")

    try:
        ActivityService(db).log(request.session["user_id"], "update", "contracts", contract_id, f"تعديل عقد: {title}")
    except Exception:
        logger.warning("فشل تسجيل النشاط لتعديل العقد %s", contract_id)

    return RedirectResponse(url=f"/contracts/{contract_id}", status_code=302)


@router.get("/{contract_id}/print", response_class=HTMLResponse)
async def print_contract(request: Request, contract_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    company_settings = SettingsService(db).get_all()
    return templates.TemplateResponse("contracts/print.html", {
        "request": request, "contract": contract, "settings": company_settings
    })


@router.get("/{contract_id}/layout-editor", response_class=HTMLResponse)
async def layout_editor(request: Request, contract_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    company_settings = SettingsService(db).get_all()
    return templates.TemplateResponse("contracts/layout_editor.html", {
        "request": request, "contract": contract, "settings": company_settings
    })


@router.get("/{contract_id}/pdf")
async def download_contract_pdf(request: Request, contract_id: int, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    company_settings = SettingsService(db).get_all()
    try:
        from app.services.pdf_service import generate_contract_pdf
        pdf_bytes = generate_contract_pdf(contract, company_settings)
    except Exception:
        logger.exception("فشل توليد PDF للعقد %s", contract_id)
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء توليد ملف PDF")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="contract-{contract.contract_number}.pdf"'},
    )


@router.post("/{contract_id}/to-invoice")
async def contract_to_invoice(request: Request, contract_id: int, db: Session = Depends(get_db)):
    """تحويل العقد إلى فاتورة — مسموح فقط للعقود النشطة أو المسودة"""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404)

    if contract.status not in _CONVERTIBLE_STATUSES:
        return RedirectResponse(url=f"/contracts/{contract_id}?error=1", status_code=302)

    try:
        from app.services.invoice_service import InvoiceService
        from datetime import date
        service = InvoiceService(db)
        invoice = service.create(
            {"client_id": contract.client_id, "contract_id": contract.id,
             "issue_date": date.today(), "tax_rate": Decimal("0"), "discount": Decimal("0"),
             "notes": f"تم إنشاؤها من العقد رقم {contract.contract_number}"},
            items_data=[{"description": contract.title, "quantity": 1, "unit_price": float(contract.amount)}],
            created_by=request.session["user_id"],
        )
    except Exception:
        logger.exception("خطأ أثناء تحويل العقد %s إلى فاتورة", contract_id)
        db.rollback()
        return RedirectResponse(url=f"/contracts/{contract_id}?error=1", status_code=302)

    try:
        ActivityService(db).log(request.session["user_id"], "create", "invoices", invoice.id, f"تحويل من عقد: {contract.contract_number}")
    except Exception:
        logger.warning("فشل تسجيل النشاط لتحويل العقد %s", contract_id)

    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=302)
