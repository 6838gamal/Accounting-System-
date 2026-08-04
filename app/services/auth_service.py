"""
خدمة المصادقة وإدارة المستخدمين
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """التحقق من بيانات تسجيل الدخول"""
        user = self.db.query(User).filter(
            User.username == username,
            User.is_active == True
        ).first()
        if not user:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        # تحديث وقت آخر دخول
        user.last_login = datetime.utcnow()
        self.db.commit()
        return user

    def create_default_admin(self) -> User:
        """إنشاء المشرف الافتراضي إذا لم يكن موجوداً"""
        admin = self.db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=self.get_password_hash("admin123"),
                full_name="مشرف النظام",
                role=UserRole.ADMIN,
                is_active=True,
            )
            self.db.add(admin)
            self.db.commit()
            self.db.refresh(admin)
        return admin
