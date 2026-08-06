"""
اختبارات تكاملية — لوحة التحكم والصفحات العامة
"""
import pytest


def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


class TestDashboard:
    def test_dashboard_requires_login(self, client):
        r = client.get("/dashboard", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_root_redirects_to_login_when_unauthenticated(self, client):
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (302, 303)
        assert "/auth/login" in r.headers.get("location", "")

    def test_root_redirects_to_dashboard_when_authenticated(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (302, 303)
        assert "/dashboard" in r.headers.get("location", "")

    def test_dashboard_loads_for_authenticated_user(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/dashboard")
        assert r.status_code == 200

    def test_dashboard_slash_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/dashboard/")
        assert r.status_code == 200

    def test_dashboard_shows_stats(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/dashboard")
        assert r.status_code == 200
        # Should contain some dashboard content
        assert len(r.text) > 100


class TestActivityLog:
    def test_requires_login(self, client):
        r = client.get("/activity-log", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_loads_for_authenticated(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/activity-log")
        assert r.status_code == 200

    def test_filter_by_module(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/activity-log?module=clients")
        assert r.status_code == 200

    def test_pagination_valid(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/activity-log?page=1")
        assert r.status_code == 200

    def test_pagination_invalid_rejected(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/activity-log?page=0", follow_redirects=False)
        assert r.status_code in (400, 422, 302)


class TestPayments:
    def test_requires_login(self, client):
        r = client.get("/payments", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_loads_for_authenticated(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/payments")
        assert r.status_code == 200

    def test_pagination_invalid_rejected(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/payments?page=0", follow_redirects=False)
        assert r.status_code in (400, 422, 302)

    def test_pagination_valid(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/payments?page=2")
        assert r.status_code == 200


class TestSettings:
    def test_requires_login(self, client):
        r = client.get("/settings", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_loads_for_authenticated(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/settings")
        assert r.status_code == 200

    def test_save_settings(self, client, admin_user):
        _login(client, admin_user)
        import re
        page = client.get("/settings")
        m = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
        csrf = m.group(1) if m else ""
        r = client.post("/settings", data={
            "company_name": "شركة الاختبار",
            "currency": "SAR",
            "default_tax_rate": "15",
            "invoice_notes": "شكراً لتعاملكم",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_saved_flag_shown(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/settings?saved=1")
        assert r.status_code == 200


class TestSecurityHeadersOnAllPages:
    """التحقق من وجود رؤوس الأمان على الصفحات الرئيسية."""

    def test_login_page_has_security_headers(self, client):
        r = client.get("/auth/login")
        assert "X-Frame-Options" in r.headers
        assert r.headers["X-Frame-Options"] == "DENY"

    def test_dashboard_has_no_store_cache(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/dashboard")
        cc = r.headers.get("Cache-Control", "")
        assert "no-store" in cc

    def test_server_header_obfuscated(self, client):
        r = client.get("/auth/login")
        server = r.headers.get("Server", "")
        assert "uvicorn" not in server.lower()
        assert "python" not in server.lower()
        assert "fastapi" not in server.lower()
