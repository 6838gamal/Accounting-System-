"""
إعداد الاختبارات العامة — conftest.py الجذري
"""
import os
# يجب تعيين DEBUG=true قبل استيراد أي كود للتطبيق لأن settings تُهيَّأ عند الاستيراد.
# https_only=True (وهو الحال عند DEBUG=False) يُفعّل Secure على cookie، مما يمنع
# httpx من إرسالها عبر HTTP في TestClient. نفرض True لضمان عمل الجلسات في الاختبارات.
os.environ['DEBUG'] = 'true'

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base
# جميع الـ routers تستورد get_db من app.dependencies — يجب إبطال نفس الكائن
from app.dependencies import get_db
from app.services.auth_service import AuthService

TEST_DB_URL = "sqlite:///./test_accounting.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── إعادة تهيئة Rate Limiter تلقائياً قبل كل اختبار ───────────────────────

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    إعادة تهيئة Rate Limiter بين الاختبارات لمنع التأثير المتقاطع.
    هذا الـ fixture يُطبَّق تلقائياً على جميع الاختبارات في المشروع.
    """
    from app.core.rate_limiter import login_limiter, general_limiter
    login_limiter._store.clear()
    general_limiter._store.clear()
    yield
    login_limiter._store.clear()
    general_limiter._store.clear()


# ─── Fixtures المشتركة ──────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db):
    """إنشاء مستخدم مشرف للاختبار"""
    service = AuthService(db)
    return service.create_default_admin()
