"""
مسارات سجل العمليات
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates as _shared_templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activity-log", tags=["activity"])
templates = _shared_templates


@router.get("", response_class=HTMLResponse)
async def activity_log(
    request: Request, db: Session = Depends(get_db),
    module: Optional[str] = None, page: int = 1,
):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=302)
    service = ActivityService(db)
    logs, total = service.get_logs(skip=(page - 1) * 50, limit=50, module=module)
    return templates.TemplateResponse("activity_log/list.html", {
        "request": request, "logs": logs, "total": total,
        "page": page, "total_pages": (total + 49) // 50,
        "module_filter": module,
    })
