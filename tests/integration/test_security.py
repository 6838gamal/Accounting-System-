"""
اختبارات الأمان — CSRF، المصادقة، التفويض، إدخالات خبيثة
"""
import pytest
import re
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.auth_service import AuthService
from app.models.client import Client

engine = create_engine("sqlite:///./test_security.db", connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """إعادة تهيئة rate limiter بين الاختبارات لمنع التأثير المتقاطع."""
    from app.core.rate_limiter import login_limiter, general_limiter
    login_limiter._store.clear()
    general_limiter._store.clear()
    yield
    login_limiter._store.clear()
    general_limiter._store.clear()


@pytest.fixture
def db():
    s = TestSession()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client(db):
    def override():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    return AuthService(db).create_default_admin()


@pytest.fixture
def logged_in_client(client, admin_user):
    """عميل HTTP مع جلسة مسجّلة الدخول."""
    from app.core.rate_limiter import login_limiter
    login_limiter._store.clear()
    resp = client.post("/auth/login",
                       data={"username": "admin", "password": "admin123"},
                       follow_redirects=False)
    # قد يُعيد 302 redirect إلى dashboard
    assert resp.status_code in (200, 302)
    return client


# ─── اختبارات CSRF ────────────────────────────────────────────────────────

class TestCSRFProtection:
    def test_post_without_csrf_token_blocked_when_logged_in(self, logged_in_client):
        """POST بدون CSRF token يجب أن يُرفض (403) للمستخدم المسجّل."""
        resp = logged_in_client.post(
            "/clients/new",
            data={"name": "اختبار CSRF", "type": "company"},
            follow_redirects=False,
        )
        assert resp.status_code == 403

    def test_post_with_valid_csrf_token_allowed(self, logged_in_client):
        """POST مع CSRF token صحيح يجب أن يمر للمعالجة."""
        get_resp = logged_in_client.get("/clients/new")
        assert get_resp.status_code == 200
        match = re.search(r'name="csrf_token" value="([^"]+)"', get_resp.text)
        assert match, "CSRF token not found in form"
        token = match.group(1)

        resp = logged_in_client.post(
            "/clients/new",
            data={"name": "عميل اختبار CSRF", "type": "company", "csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code != 403

    def test_csrf_token_in_forms(self, logged_in_client):
        """تحقق أن صفحات GET تحتوي على CSRF token في النماذج."""
        for page in ["/clients/new", "/invoices/new", "/expenses/new", "/settings"]:
            resp = logged_in_client.get(page)
            assert resp.status_code == 200, f"{page} returned {resp.status_code}"
            assert "csrf_token" in resp.text, f"No CSRF token in {page}"


# ─── اختبارات المصادقة ────────────────────────────────────────────────────

class TestAuthentication:
    def test_unauthenticated_redirects_to_login(self, client):
        for path in ["/dashboard", "/clients", "/invoices", "/settings"]:
            resp = client.get(path, follow_redirects=False)
            assert resp.status_code in (302, 307), f"{path} did not redirect"
            location = resp.headers.get("location", "")
            assert "login" in location, f"{path} did not redirect to login"

    def test_rate_limiting_on_login(self, client, admin_user):
        """بعد استنفاد الحد، يجب حظر الطلبات برسالة rate_limit."""
        for i in range(5):
            client.post("/auth/login",
                        data={"username": "admin", "password": "wrong"},
                        follow_redirects=False)
        # الطلب بعد الاستنفاد يُعاد توجيهه بسبب rate limit
        resp = client.post("/auth/login",
                           data={"username": "admin", "password": "wrong"},
                           follow_redirects=False)
        assert resp.status_code == 302
        assert "rate_limit" in resp.headers.get("location", "")

    def test_login_error_message_uniform(self, client, admin_user):
        """رسالة الخطأ موحدة — لا تكشف إن كان المستخدم موجوداً."""
        resp_existing = client.post(
            "/auth/login",
            data={"username": "admin", "password": "wrongpassword"},
        )
        from app.core.rate_limiter import login_limiter
        login_limiter._store.clear()
        resp_nonexistent = client.post(
            "/auth/login",
            data={"username": "nonexistent_user_xyz_abc", "password": "wrongpassword"},
        )
        assert "غير صحيحة" in resp_existing.text
        assert "غير صحيحة" in resp_nonexistent.text

    def test_logout_clears_session(self, logged_in_client):
        # الوصول للوحة التحكم بعد تسجيل الدخول
        resp = logged_in_client.get("/dashboard", follow_redirects=True)
        assert resp.status_code == 200

        # الحصول على CSRF token للخروج
        get_resp = logged_in_client.get("/clients/new")
        match = re.search(r'name="csrf_token" value="([^"]+)"', get_resp.text)
        token = match.group(1) if match else ""
        logged_in_client.post("/auth/logout", data={"csrf_token": token}, follow_redirects=False)

        # بعد الخروج يجب إعادة التوجيه للصفحة الرئيسية
        resp = logged_in_client.get("/dashboard", follow_redirects=False)
        assert resp.status_code in (302, 307)


# ─── اختبارات رؤوس الأمان ────────────────────────────────────────────────

class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        resp = client.get("/auth/login")
        assert "x-frame-options" in resp.headers
        assert resp.headers["x-frame-options"] == "DENY"
        assert "x-content-type-options" in resp.headers
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert "content-security-policy" in resp.headers

    def test_server_header_does_not_reveal_stack(self, client):
        resp = client.get("/auth/login")
        server = resp.headers.get("server", "").lower()
        assert "python" not in server
        assert "uvicorn" not in server

    def test_no_stack_trace_in_404(self, client):
        resp = client.get("/this-page-does-not-exist-xyz-abc")
        assert "Traceback" not in resp.text
        assert "sqlalchemy" not in resp.text.lower()
        assert resp.status_code == 404

    def test_x_request_id_present(self, client):
        resp = client.get("/auth/login")
        assert "x-request-id" in resp.headers


# ─── اختبارات XSS ────────────────────────────────────────────────────────

class TestXSSPrevention:
    def test_xss_payload_escaped_in_output(self, logged_in_client):
        """الـ XSS payload يجب أن يكون مُهرَّباً في الإخراج."""
        get_resp = logged_in_client.get("/clients/new")
        match = re.search(r'name="csrf_token" value="([^"]+)"', get_resp.text)
        token = match.group(1) if match else ""

        xss_name = '<script>alert("xss")</script>'
        resp = logged_in_client.post(
            "/clients/new",
            data={"name": xss_name, "type": "company", "csrf_token": token},
            follow_redirects=True,
        )
        if resp.status_code == 200 and xss_name in resp.text:
            # يجب أن يكون مُهرَّباً
            assert "&lt;script&gt;" in resp.text or "alert" not in resp.text

    def test_sql_injection_in_search(self, logged_in_client):
        """SQL injection في البحث يجب أن يُعالج بأمان."""
        resp = logged_in_client.get("/clients?search=' OR '1'='1")
        assert resp.status_code == 200
        assert "Traceback" not in resp.text
