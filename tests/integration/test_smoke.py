"""
Smoke Tests — تأكيد أن جميع الصفحات الأساسية تعمل بعد تسجيل الدخول
"""
import pytest


def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


# قائمة جميع المسارات الأساسية والكود المتوقع
PAGES = [
    ("/dashboard", 200),
    ("/clients", 200),
    ("/clients/new", 200),
    ("/contracts", 200),
    ("/contracts/new", 200),
    ("/quotations", 200),
    ("/quotations/new", 200),
    ("/invoices", 200),
    ("/invoices/new", 200),
    ("/payments", 200),
    ("/expenses", 200),
    ("/expenses/new", 200),
    ("/expense-vouchers", 200),
    ("/expense-vouchers/new", 200),
    ("/receipt-vouchers", 200),
    ("/receipt-vouchers/new", 200),
    ("/reports", 200),
    ("/reports/sales", 200),
    ("/reports/clients", 200),
    ("/reports/expenses", 200),
    ("/reports/profit-loss", 200),
    ("/settings", 200),
    ("/users", 200),
    ("/users/new", 200),
    ("/activity-log", 200),
]

PROTECTED_PAGES = [
    "/dashboard",
    "/clients",
    "/invoices",
    "/payments",
    "/reports",
    "/settings",
    "/users",
    "/activity-log",
]

NOT_FOUND_PAGES = [
    "/clients/99999",
    "/invoices/99999",
    "/contracts/99999",
    "/quotations/99999",
]

# هذه الصفحات تُعيد redirect (302) بدلاً من 404 عند عدم الوجود (تصميم الراوتر)
REDIRECT_ON_NOT_FOUND = [
    "/expense-vouchers/99999",
    "/receipt-vouchers/99999",
]


class TestSmoke:
    """اختبارات دخان لجميع الصفحات."""

    def test_all_pages_load_when_logged_in(self, client, admin_user):
        _login(client, admin_user)
        for path, expected_status in PAGES:
            r = client.get(path)
            assert r.status_code == expected_status, (
                f"الصفحة {path} أرجعت {r.status_code} بدلاً من {expected_status}"
            )

    def test_protected_pages_redirect_when_not_logged_in(self, client):
        for path in PROTECTED_PAGES:
            r = client.get(path, follow_redirects=False)
            assert r.status_code in (302, 303), (
                f"الصفحة {path} يجب أن تحوّل غير المصادق إلى تسجيل الدخول"
            )

    def test_not_found_pages_return_404(self, client, admin_user):
        _login(client, admin_user)
        for path in NOT_FOUND_PAGES:
            r = client.get(path)
            assert r.status_code == 404, (
                f"الصفحة {path} يجب أن تُعيد 404 وليس {r.status_code}"
            )

    def test_redirect_on_not_found_vouchers(self, client, admin_user):
        _login(client, admin_user)
        for path in REDIRECT_ON_NOT_FOUND:
            r = client.get(path, follow_redirects=False)
            assert r.status_code in (302, 303), (
                f"الصفحة {path} يجب أن تُعيد redirect وليس {r.status_code}"
            )

    def test_no_stack_trace_on_404(self, client):
        r = client.get("/this-path-does-not-exist-xyz-abc-123")
        assert r.status_code == 404
        assert "Traceback" not in r.text
        assert "sqlalchemy" not in r.text.lower()

    def test_excel_export_smoke(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/sales/excel")
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
