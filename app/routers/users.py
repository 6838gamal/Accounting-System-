"""
مسارات إدارة المستخدمين
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def list_users(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_role") == "admin":
        if request.session.get("user_id"):
            return RedirectResponse(url="/dashboard", status_code=302)
        return RedirectResponse(url="/auth/login", status_code=302)
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse("users/list.html", {"request": request, "users": users})


@router.get("/new", response_class=HTMLResponse)
async def new_user(request: Request):
    if request.session.get("user_role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("users/form.html", {
        "request": request, "user": None, "roles": UserRole, "error": None
    })


@router.post("/new")
async def create_user(
    request: Request, db: Session = Depends(get_db),
    username: str = Form(...), email: str = Form(...),
    full_name: str = Form(...), role: str = Form("accountant"),
    password: str = Form(...),
):
    if request.session.get("user_role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return templates.TemplateResponse("users/form.html", {
            "request": request, "user": None, "roles": UserRole,
            "error": "اسم المستخدم موجود بالفعل"
        })
    service = AuthService(db)
    user = User(
        username=username, email=email, full_name=full_name,
        role=role, password_hash=service.get_password_hash(password),
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/users", status_code=302)


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    if request.session.get("user_role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("users/form.html", {
        "request": request, "user": user, "roles": UserRole, "error": None
    })


@router.post("/{user_id}/edit")
async def update_user(
    request: Request, user_id: int, db: Session = Depends(get_db),
    email: str = Form(...), full_name: str = Form(...),
    role: str = Form("accountant"), is_active: bool = Form(True),
    password: Optional[str] = Form(None),
):
    if request.session.get("user_role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404)
    user.email = email
    user.full_name = full_name
    user.role = role
    user.is_active = is_active
    if password:
        user.password_hash = AuthService(db).get_password_hash(password)
    db.commit()
    return RedirectResponse(url="/users", status_code=302)
