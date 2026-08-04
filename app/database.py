"""
إعداد قاعدة البيانات وجلسة SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings


engine = create_engine(
    settings.SQLITE_URL,
    connect_args={"check_same_thread": False},
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
