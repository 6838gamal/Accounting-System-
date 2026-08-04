"""
اختبارات وحدة الخدمات
"""
import pytest
from decimal import Decimal
from datetime import date
from tests.conftest import TestingSessionLocal
from sqlalchemy import create_engine
from app.database import Base
from app.models.user import User
from app.models.client import Client
from app.services.auth_service import AuthService
from app.services.client_service import ClientService
from app.services.invoice_service import InvoiceService
from app.services.settings_service import SettingsService

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
Session = TestingSessionLocal.__class__(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy.orm import sessionmaker
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    s = TestSession()
    try:
        yield s
    finally:
        s.close()


class TestAuthService:
    def test_password_hashing(self, db):
        service = AuthService(db)
        hashed = service.get_password_hash("testpassword")
        assert hashed != "testpassword"
        assert service.verify_password("testpassword", hashed)

    def test_create_default_admin(self, db):
        service = AuthService(db)
        admin = service.create_default_admin()
        assert admin.username == "admin"
        assert admin.role.value == "admin"
        assert admin.is_active == True

    def test_authenticate_user(self, db):
        service = AuthService(db)
        service.create_default_admin()
        user = service.authenticate_user("admin", "admin123")
        assert user is not None
        assert user.username == "admin"

    def test_authenticate_wrong_password(self, db):
        service = AuthService(db)
        service.create_default_admin()
        user = service.authenticate_user("admin", "wrongpassword")
        assert user is None


class TestClientService:
    def test_create_client(self, db):
        service = ClientService(db)
        client = service.create({"name": "عميل اختبار", "type": "company"}, created_by=1)
        assert client.id is not None
        assert client.name == "عميل اختبار"

    def test_get_all_clients(self, db):
        service = ClientService(db)
        service.create({"name": "العميل الأول", "type": "company"}, created_by=1)
        service.create({"name": "العميل الثاني", "type": "individual"}, created_by=1)
        clients, total = service.get_all()
        assert total == 2

    def test_search_clients(self, db):
        service = ClientService(db)
        service.create({"name": "شركة التقنية", "type": "company"}, created_by=1)
        service.create({"name": "محمد أحمد", "type": "individual"}, created_by=1)
        clients, total = service.get_all(search="تقنية")
        assert total == 1


class TestSettingsService:
    def test_init_defaults(self, db):
        service = SettingsService(db)
        service.init_defaults()
        company_name = service.get("company_name")
        assert company_name is not None

    def test_set_and_get(self, db):
        service = SettingsService(db)
        service.set("company_name", "شركة الاختبار")
        assert service.get("company_name") == "شركة الاختبار"
