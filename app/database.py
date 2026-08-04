"""
إعداد قاعدة البيانات وجلسة SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings


_db_url = settings.effective_db_url
engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if _db_url.startswith("sqlite") else {},
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency لإنشاء جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """تهيئة جداول قاعدة البيانات"""
    from app.models import (  # noqa: F401
        user, client, contract, quotation,
        invoice, payment, expense, settings as settings_model,
        activity_log
    )
    Base.metadata.create_all(bind=engine)
