"""
اختبارات تكامل إدارة العملاء — تستخدم fixtures من conftest.py المركزي
"""
import re
import pytest
from app.models.client import Client
from app.services.auth_service import AuthService


def _get_csrf(client_http, path: str) -> str:
    resp = client_http.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.text)
    return match.group(1) if match else ""


@pytest.fixture
def auth_client(client, admin_user):
    """HTTP client مع جلسة مسجّلة الدخول."""
    from app.core.rate_limiter import login_limiter
    login_limiter._store.clear()
    resp = client.post("/auth/login",
                       data={"username": "admin", "password": "admin123"},
                       follow_redirects=False)
    assert resp.status_code in (200, 302), f"Login failed with status {resp.status_code}"
    return client


class TestClientList:
    def test_list_requires_login(self, client):
        resp = client.get("/clients", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "login" in resp.headers.get("location", "")

    def test_list_shows_clients(self, auth_client, db, admin_user):
        db.add(Client(name="شركة أ", type="company", created_by=admin_user.id))
        db.add(Client(name="شركة ب", type="company", created_by=admin_user.id))
        db.commit()
        resp = auth_client.get("/clients")
        assert resp.status_code == 200
        assert "شركة أ" in resp.text
        assert "شركة ب" in resp.text

    def test_search_filters_results(self, auth_client, db, admin_user):
        db.add(Client(name="شركة التقنية", type="company", created_by=admin_user.id))
        db.add(Client(name="مؤسسة النور", type="company", created_by=admin_user.id))
        db.commit()
        resp = auth_client.get("/clients?search=تقنية")
        assert resp.status_code == 200
        assert "شركة التقنية" in resp.text
        assert "مؤسسة النور" not in resp.text


class TestClientCreate:
    def test_create_valid_client(self, auth_client):
        token = _get_csrf(auth_client, "/clients/new")
        resp = auth_client.post(
            "/clients/new",
            data={"name": "عميل جديد", "type": "company", "csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/clients/" in resp.headers.get("location", "")

    def test_create_empty_name_rejected(self, auth_client):
        token = _get_csrf(auth_client, "/clients/new")
        resp = auth_client.post(
            "/clients/new",
            data={"name": "", "type": "company", "csrf_token": token},
        )
        assert resp.status_code == 200
        assert "مطلوب" in resp.text or "خطأ" in resp.text

    def test_create_long_name_rejected(self, auth_client):
        token = _get_csrf(auth_client, "/clients/new")
        resp = auth_client.post(
            "/clients/new",
            data={"name": "أ" * 300, "type": "company", "csrf_token": token},
        )
        assert resp.status_code == 200

    def test_create_invalid_type_rejected(self, auth_client):
        token = _get_csrf(auth_client, "/clients/new")
        resp = auth_client.post(
            "/clients/new",
            data={"name": "عميل", "type": "invalid_type", "csrf_token": token},
        )
        assert resp.status_code == 200

    def test_create_individual_client(self, auth_client):
        token = _get_csrf(auth_client, "/clients/new")
        resp = auth_client.post(
            "/clients/new",
            data={"name": "محمد أحمد", "type": "individual", "csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_create_with_special_chars_in_name(self, auth_client):
        token = _get_csrf(auth_client, "/clients/new")
        resp = auth_client.post(
            "/clients/new",
            data={"name": "شركة & مؤسسة 'النور'", "type": "company", "csrf_token": token},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Traceback" not in resp.text


class TestClientView:
    def test_view_existing_client(self, auth_client, db, admin_user):
        c = Client(name="عميل للعرض", type="company", created_by=admin_user.id)
        db.add(c)
        db.commit()
        resp = auth_client.get(f"/clients/{c.id}")
        assert resp.status_code == 200
        assert "عميل للعرض" in resp.text

    def test_view_nonexistent_client(self, auth_client):
        resp = auth_client.get("/clients/99999")
        assert resp.status_code in (302, 404)


class TestClientDelete:
    def test_soft_delete_client(self, auth_client, db, admin_user):
        c = Client(name="عميل للحذف", type="company", created_by=admin_user.id)
        db.add(c)
        db.commit()
        client_id = c.id

        token = _get_csrf(auth_client, f"/clients/{client_id}/edit")
        resp = auth_client.post(
            f"/clients/{client_id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 200)

        db.expire_all()
        c_refreshed = db.query(Client).filter(Client.id == client_id).first()
        assert c_refreshed is not None
        assert not c_refreshed.is_active

    def test_delete_without_login_rejected(self, client, db, admin_user):
        c = Client(name="عميل محمي", type="company", created_by=admin_user.id)
        db.add(c)
        db.commit()
        resp = client.post(f"/clients/{c.id}/delete",
                           data={"csrf_token": "fake"}, follow_redirects=False)
        assert resp.status_code in (302, 307, 403)
