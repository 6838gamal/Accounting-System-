"""
اختبارات تكاملية — المصروفات
"""
import pytest
from datetime import date


def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


def _csrf(client, path="/dashboard"):
    r = client.get(path)
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1) if m else ""


class TestExpenseAuthGuard:
    def test_list_requires_login(self, client):
        r = client.get("/expenses", follow_redirects=False)
        assert r.status_code in (302, 303)


class TestExpenseList:
    def test_empty_list_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/expenses")
        assert r.status_code == 200

    def test_filter_by_status(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/expenses?status=pending")
        assert r.status_code == 200

    def test_filter_by_invalid_status(self, client, admin_user):
        """حالة غير صالحة يجب أن تُعامَل بشكل آمن."""
        _login(client, admin_user)
        r = client.get("/expenses?status=INVALID")
        assert r.status_code == 200


class TestExpenseCreate:
    def test_new_form_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/expenses/new")
        assert r.status_code == 200

    def test_create_valid_expense(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client, "/expenses/new")
        r = client.post("/expenses/new", data={
            "title": "إيجار المكتب",
            "category": "إيجار",
            "amount": "5000",
            "expense_date": str(date.today()),
            "description": "إيجار شهر أغسطس",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_create_empty_title_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client, "/expenses/new")
        r = client.post("/expenses/new", data={
            "title": "", "category": "إيجار",
            "amount": "100", "expense_date": str(date.today()),
            "csrf_token": csrf,
        })
        assert r.status_code == 200
        assert "مطلوب" in r.text or "خطأ" in r.text

    def test_create_invalid_category_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client, "/expenses/new")
        r = client.post("/expenses/new", data={
            "title": "مصروف", "category": "INVALID_CAT",
            "amount": "100", "expense_date": str(date.today()),
            "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_zero_amount_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client, "/expenses/new")
        r = client.post("/expenses/new", data={
            "title": "مصروف", "category": "إيجار",
            "amount": "0", "expense_date": str(date.today()),
            "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_negative_amount_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client, "/expenses/new")
        r = client.post("/expenses/new", data={
            "title": "مصروف", "category": "إيجار",
            "amount": "-100", "expense_date": str(date.today()),
            "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_invalid_date_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client, "/expenses/new")
        r = client.post("/expenses/new", data={
            "title": "مصروف", "category": "إيجار",
            "amount": "100", "expense_date": "not-a-date",
            "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_long_title_rejected(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client, "/expenses/new")
        r = client.post("/expenses/new", data={
            "title": "أ" * 300,
            "category": "إيجار",
            "amount": "100",
            "expense_date": str(date.today()),
            "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_xss_in_title_safe(self, client, admin_user):
        """XSS في عنوان المصروف يجب أن يُخزَّن بشكل آمن."""
        _login(client, admin_user)
        csrf = _csrf(client, "/expenses/new")
        r = client.post("/expenses/new", data={
            "title": "<script>alert(1)</script>",
            "category": "أخرى",
            "amount": "1",
            "expense_date": str(date.today()),
            "csrf_token": csrf,
        }, follow_redirects=True)
        assert "<script>alert(1)</script>" not in r.text


class TestExpenseApproval:
    def _make_expense(self, db, user_id):
        from app.models.expense import Expense
        exp = Expense(
            title="مصروف اختبار",
            category="أخرى",
            amount=100,
            expense_date=date.today(),
            created_by=user_id,
        )
        db.add(exp)
        db.commit()
        db.refresh(exp)
        return exp

    def test_approve_expense(self, client, admin_user, db):
        _login(client, admin_user)
        exp = self._make_expense(db, admin_user.id)
        csrf = _csrf(client, "/expenses")
        r = client.post(f"/expenses/{exp.id}/approve", data={"csrf_token": csrf},
                        follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_reject_expense(self, client, admin_user, db):
        _login(client, admin_user)
        exp = self._make_expense(db, admin_user.id)
        csrf = _csrf(client, "/expenses")
        r = client.post(f"/expenses/{exp.id}/reject", data={"csrf_token": csrf},
                        follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_approve_nonexistent_expense(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client, "/expenses")
        r = client.post("/expenses/99999/approve", data={"csrf_token": csrf},
                        follow_redirects=False)
        assert r.status_code in (302, 303, 404)
