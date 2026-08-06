"""
نموذج المستخدم
"""
import enum
from datetime import timezone, datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.ACCOUNTANT, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None), nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # العلاقات
    activity_logs = relationship("ActivityLog", back_populates="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User {self.username}>"

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_manager(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.MANAGER]

    @property
    def can_edit(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]
