"""
إعداد قاعدة البيانات وجلسة SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings


_db_url = settings.effective_db_url
_is_sqlite = _db_url.startswith("sqlite")
engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False, "timeout": 30} if _is_sqlite else {},
    echo=settings.DEBUG,
)

# Enable WAL mode and busy timeout for SQLite to prevent "database is locked" errors
if _is_sqlite:
    from sqlalchemy import event as _sa_event

    @_sa_event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

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
