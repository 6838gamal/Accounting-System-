"""
اختبارات تكاملية — إدارة المستخدمين
"""
import pytest


def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


def _csrf(client, path="/users"):
    r = client.get(path)
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1) if m else ""


def _create_user(db, username="testuser", role="ACCOUNTANT"):
    from app.models.user import User, UserRole
    from app.services.auth_service import AuthService
    svc = AuthService(db)
    user = User(
        username=username,
        email=f"{username}@test.com",
        password_hash=svc.get_password_hash("Test1234!"),
        full_name="مستخدم اختبار",
        role=getattr(UserRole, role.upper()),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestUserAuthGuard:
    def test_list_requires_login(self, client):
        r = client.get("/users", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_non_admin_redirected(self, client, db, admin_user):
        """مستخدم غير مشرف لا يجب أن يصل لصفحة المستخدمين."""
        accountant = _create_user(db, "acc01", "ACCOUNTANT")
        client.post("/auth/login", data={"username": "acc01", "password": "Test1234!"})
        r = client.get("/users", follow_redirects=False)
        assert r.status_code in (302, 303)


class TestUserList:
    def test_admin_can_list_users(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/users")
        assert r.status_code == 200
        assert "admin" in r.text


class TestUserCreate:
    def test_new_form_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/users/new")
        assert r.status_code == 200

    def test_create_valid_user(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client)
        r = client.post("/users/new", data={
            "username": "newuser1",
            "email": "newuser1@test.com",
            "full_name": "مستخدم جديد",
            "role": "accountant",
            "password": "SecurePass123",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_create_short_username_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client)
        r = client.post("/users/new", data={
            "username": "ab", "email": "ab@test.com",
            "full_name": "مستخدم", "role": "accountant",
            "password": "SecurePass123", "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_invalid_username_chars_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client)
        r = client.post("/users/new", data={
            "username": "user name!", "email": "u@test.com",
            "full_name": "مستخدم", "role": "accountant",
            "password": "SecurePass123", "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_duplicate_username_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client)
        # admin already exists
        r = client.post("/users/new", data={
            "username": "admin", "email": "another@test.com",
            "full_name": "مكرر", "role": "accountant",
            "password": "SecurePass123", "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_empty_password_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client)
        r = client.post("/users/new", data={
            "username": "validuser", "email": "v@test.com",
            "full_name": "مستخدم", "role": "accountant",
            "password": "", "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_short_password_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client)
        r = client.post("/users/new", data={
            "username": "validuser2", "email": "v2@test.com",
            "full_name": "مستخدم", "role": "accountant",
            "password": "1234567", "csrf_token": csrf,
        })
        assert r.status_code == 200


class TestUserDelete:
    def test_cannot_delete_self(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client)
        r = client.post(f"/users/{admin_user.id}/delete",
                        data={"csrf_token": csrf}, follow_redirects=False)
        assert r.status_code in (302, 303)
        # Verify admin still exists
        r2 = client.get("/users")
        assert "admin" in r2.text

    def test_cannot_delete_last_admin(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client)
        r = client.post(f"/users/{admin_user.id}/delete",
                        data={"csrf_token": csrf}, follow_redirects=True)
        # Should show error or redirect back
        assert r.status_code == 200

    def test_delete_nonexistent_user(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client)
        r = client.post("/users/99999/delete", data={"csrf_token": csrf})
        assert r.status_code == 404

    def test_can_delete_non_admin_user(self, client, admin_user, db):
        _login(client, admin_user)
        user = _create_user(db, "deleteme", "ACCOUNTANT")
        csrf = _csrf(client)
        r = client.post(f"/users/{user.id}/delete",
                        data={"csrf_token": csrf}, follow_redirects=False)
        assert r.status_code in (302, 303)
