"""
Dependencies مشتركة للتطبيق
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from typing import Optional


def get_db():
    """Dependency لإنشاء جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = None):
    """الحصول على المستخدم الحالي من الجلسة"""
    from app.models.user import User
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/auth/login"},
        )
    if db is None:
        db = next(get_db())
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/auth/login"},
        )
    return user


def require_role(*roles):
    """Dependency للتحقق من الدور"""
    def checker(request: Request):
        user_role = request.session.get("user_role")
        if user_role not in roles:
            raise HTTPException(status_code=403, detail="غير مصرح")
        return user_role
    return checker


def get_optional_user(request: Request) -> Optional[dict]:
    """الحصول على المستخدم الحالي بشكل اختياري"""
    user_id = request.session.get("user_id")
    if user_id:
        return {
            "id": user_id,
            "username": request.session.get("username"),
            "full_name": request.session.get("full_name"),
            "role": request.session.get("user_role"),
        }
    return None
