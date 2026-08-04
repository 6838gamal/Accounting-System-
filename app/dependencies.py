"""
Dependencies مشتركة للتطبيق — محصّنة أمنياً
"""
import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from typing import Optional

logger = logging.getLogger(__name__)
sec_logger = logging.getLogger("security")


def get_db():
    """Dependency لإنشاء جلسة قاعدة البيانات مع إغلاق آمن."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = None):
    """
    الحصول على المستخدم الحالي من الجلسة.
    يتحقق من قاعدة البيانات لضمان أن الحساب لا يزال نشطاً.
    """
    from app.models.user import User

    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/auth/login"},
        )

    _db_owned = db is None
    if _db_owned:
        _gen = get_db()
        db = next(_gen)

    try:
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True,
        ).first()
    except Exception:
        user = None
    finally:
        if _db_owned:
            try:
                _gen.close()
            except StopIteration:
                pass

    if not user:
        # مسح الجلسة إذا كان المستخدم غير موجود أو غير نشط
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/auth/login"},
        )
    return user


def require_role(*roles: str):
    """
    Dependency للتحقق من الدور.
    يتحقق من الدور في الجلسة فقط (سريع) — يكفي لمعظم الحالات.
    للعمليات الحساسة يُضاف get_current_user للتحقق من DB.
    """
    def checker(request: Request):
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": "/auth/login"},
            )
        user_role = request.session.get("user_role")
        if user_role not in roles:
            sec_logger.warning(
                "Authorization denied | user_id=%s | role=%s | required=%s | path=%s",
                user_id, user_role, roles, request.url.path,
            )
            raise HTTPException(status_code=403, detail="غير مصرح")
        return user_role
    return checker


def get_optional_user(request: Request) -> Optional[dict]:
    """الحصول على المستخدم الحالي بشكل اختياري (لا يرفع استثناء)."""
    user_id = request.session.get("user_id")
    if user_id:
        return {
            "id": user_id,
            "username": request.session.get("username"),
            "full_name": request.session.get("full_name"),
            "role": request.session.get("user_role"),
        }
    return None
