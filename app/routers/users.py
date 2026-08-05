"""
مسارات إدارة المستخدمين
"""
import logging
from urllib.parse import quote_plus
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
security_logger = logging.getLogger("security")

PASSWORD_MIN_LENGTH = 8

ROLE_LABELS = {
    "admin": "مشرف",
    "manager": "مدير",
    "accountant": "محاسب",
    "viewer": "مشاهد",
}


def _require_admin(request: Request):
    """Returns current admin user_id or None if not admin."""
    if request.session.get("user_role") != "admin":
        return None
    return request.session.get("user_id")


def _redirect_forbidden(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/auth/login", status_code=302)


def _count_active_admins(db: Session) -> int:
    return (
        db.query(User)
        .filter(User.role == UserRole.admin, User.is_active == True)
        .count()
    )


@router.get("", response_class=HTMLResponse)
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    success: Optional[str] = None,
):
    if not _require_admin(request):
        return _redirect_forbidden(request)

    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        "users/list.html",
        {
            "request": request,
            "users": users,
            "role_labels": ROLE_LABELS,
            "success": success,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_user(request: Request):
    if not _require_admin(request):
        return _redirect_forbidden(request)
    return templates.TemplateResponse(
        "users/form.html",
        {"request": request, "user": None, "roles": UserRole, "role_labels": ROLE_LABELS, "error": None},
    )


@router.post("/new")
async def create_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(default=""),
    email: str = Form(default=""),
    full_name: str = Form(default=""),
    role: str = Form(default="accountant"),
    password: str = Form(default=""),
):
    admin_id = _require_admin(request)
    if not admin_id:
        return _redirect_forbidden(request)

    def form_error(msg: str):
        return templates.TemplateResponse(
            "users/form.html",
            {
                "request": request,
                "user": None,
                "roles": UserRole,
                "role_labels": ROLE_LABELS,
                "error": msg,
                "form_data": {
                    "username": username,
                    "email": email,
                    "full_name": full_name,
                    "role": role,
                },
            },
        )

    # Manual validation (keeps form context on error)
    import re as _re
    if not username or len(username) < 3:
        return form_error("اسم المستخدم يجب أن يكون 3 أحرف على الأقل")
    if len(username) > 50 or not _re.fullmatch(r'[a-zA-Z0-9_]+', username):
        return form_error("اسم المستخدم: حروف إنجليزية وأرقام وشرطة سفلية فقط (3-50 حرفاً)")
    if not email or len(email) > 100:
        return form_error("البريد الإلكتروني مطلوب (100 حرف كحد أقصى)")
    if not full_name or len(full_name) > 100:
        return form_error("الاسم الكامل مطلوب (100 حرف كحد أقصى)")
    if not password:
        return form_error("كلمة المرور مطلوبة")

    # Validate role
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        return form_error("الدور المحدد غير صالح")

    # Password strength
    if len(password) < PASSWORD_MIN_LENGTH:
        return form_error(f"كلمة المرور يجب أن تكون {PASSWORD_MIN_LENGTH} أحرف على الأقل")

    # Duplicate username
    if db.query(User).filter(User.username == username).first():
        return form_error("اسم المستخدم موجود بالفعل")

    # Duplicate email
    if db.query(User).filter(User.email == email).first():
        return form_error("البريد الإلكتروني مستخدم بالفعل")

    service = AuthService(db)
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        role=role,
        password_hash=service.get_password_hash(password),
    )
    db.add(user)
    db.commit()

    security_logger.info(
        "user_created",
        extra={"admin_id": admin_id, "new_username": username, "role": role},
    )
    return RedirectResponse(url="/users?success=تم+إنشاء+المستخدم+بنجاح", status_code=302)


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return _redirect_forbidden(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    return templates.TemplateResponse(
        "users/form.html",
        {"request": request, "user": user, "roles": UserRole, "role_labels": ROLE_LABELS, "error": None},
    )


@router.post("/{user_id}/edit")
async def update_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    email: str = Form(..., max_length=100),
    full_name: str = Form(..., max_length=100),
    role: str = Form("accountant"),
    is_active: Optional[str] = Form(None),  # checkbox: present="true", absent=None
    password: Optional[str] = Form(None),
):
    admin_id = _require_admin(request)
    if not admin_id:
        return _redirect_forbidden(request)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    def form_error(msg: str):
        return templates.TemplateResponse(
            "users/form.html",
            {
                "request": request,
                "user": user,
                "roles": UserRole,
                "role_labels": ROLE_LABELS,
                "error": msg,
            },
        )

    # Validate role
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        return form_error("الدور المحدد غير صالح")

    # Compute new is_active (checkbox sends "true" when checked, nothing when unchecked)
    new_is_active = is_active == "true"

    # Prevent self-deactivation or self-demotion from admin
    if user_id == admin_id:
        if not new_is_active:
            return form_error("لا يمكنك تعطيل حسابك الخاص")
        if role != "admin":
            return form_error("لا يمكنك تغيير دور حسابك الخاص")

    # Prevent removing last active admin
    if user.role == UserRole.admin and (role != "admin" or not new_is_active):
        remaining = _count_active_admins(db)
        # If this user IS the last active admin, block
        if remaining <= 1:
            return form_error("لا يمكن تغيير دور أو تعطيل المشرف الوحيد في النظام")

    # Duplicate email check (exclude self)
    conflict = db.query(User).filter(User.email == email, User.id != user_id).first()
    if conflict:
        return form_error("البريد الإلكتروني مستخدم من قبل مستخدم آخر")

    # Password validation
    if password:
        if len(password) < PASSWORD_MIN_LENGTH:
            return form_error(f"كلمة المرور يجب أن تكون {PASSWORD_MIN_LENGTH} أحرف على الأقل")
        user.password_hash = AuthService(db).get_password_hash(password)
        security_logger.info(
            "password_changed_by_admin",
            extra={"admin_id": admin_id, "target_user_id": user_id},
        )

    old_role = user.role.value if user.role else None
    user.email = email
    user.full_name = full_name
    user.role = role
    user.is_active = new_is_active
    db.commit()

    if old_role != role:
        security_logger.info(
            "role_changed",
            extra={"admin_id": admin_id, "target_user_id": user_id, "old_role": old_role, "new_role": role},
        )

    return RedirectResponse(url="/users?success=تم+تحديث+المستخدم+بنجاح", status_code=302)


@router.post("/{user_id}/delete")
async def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
):
    admin_id = _require_admin(request)
    if not admin_id:
        return _redirect_forbidden(request)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    # Prevent self-deletion
    if user_id == admin_id:
        return RedirectResponse(url="/users?error=لا+يمكنك+حذف+حسابك+الخاص", status_code=302)

    # Prevent deleting last active admin
    if user.role == UserRole.admin and user.is_active:
        if _count_active_admins(db) <= 1:
            return RedirectResponse(
                url="/users?error=لا+يمكن+حذف+المشرف+الوحيد+في+النظام", status_code=302
            )

    username = user.username
    db.delete(user)
    db.commit()

    security_logger.warning(
        "user_deleted",
        extra={"admin_id": admin_id, "deleted_username": username, "deleted_user_id": user_id},
    )
    return RedirectResponse(url="/users?success=تم+حذف+المستخدم+بنجاح", status_code=302)
