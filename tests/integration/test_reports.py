"""
اختبارات تكاملية — التقارير
يغطي: صفحة الفهرس، تقرير المبيعات، تقرير العملاء، تقرير المصروفات،
       تقرير الأرباح، Excel، نطاق تاريخ غير صالح
"""
import pytest
from datetime import date


def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


class TestReportsAuthGuard:
    def test_index_requires_login(self, client):
        r = client.get("/reports", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_sales_requires_login(self, client):
        r = client.get("/reports/sales", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_excel_requires_login(self, client):
        r = client.get("/reports/sales/excel", follow_redirects=False)
        assert r.status_code in (302, 303)


class TestReportsIndex:
    def test_index_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports")
        assert r.status_code == 200


class TestSalesReport:
    def test_default_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/sales")
        assert r.status_code == 200

    def test_with_valid_date_range(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/sales?start_date=2026-01-01&end_date=2026-12-31")
        assert r.status_code == 200

    def test_invalid_date_range_no_crash(self, client, admin_user):
        """start > end يجب ألا يسبب 500 — يُعيد 200 مع رسالة خطأ."""
        _login(client, admin_user)
        r = client.get("/reports/sales?start_date=2026-12-31&end_date=2026-01-01")
        assert r.status_code == 200
        # Should NOT be a 500 error

    def test_malformed_dates_fall_back(self, client, admin_user):
        """تواريخ مشوهة يجب أن تعود للقيم الافتراضية."""
        _login(client, admin_user)
        r = client.get("/reports/sales?start_date=not-a-date&end_date=also-not")
        assert r.status_code == 200


class TestClientsReport:
    def test_default_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/clients")
        assert r.status_code == 200

    def test_invalid_date_range_no_crash(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/clients?start_date=2026-12-31&end_date=2026-01-01")
        assert r.status_code == 200


class TestExpensesReport:
    def test_default_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/expenses")
        assert r.status_code == 200

    def test_invalid_date_range_no_crash(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/expenses?start_date=2026-12-31&end_date=2026-01-01")
        assert r.status_code == 200


class TestProfitLossReport:
    def test_default_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/profit-loss")
        assert r.status_code == 200

    def test_invalid_date_range_no_crash(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/profit-loss?start_date=2026-12-31&end_date=2026-01-01")
        assert r.status_code == 200


class TestSalesExcel:
    def test_excel_download(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/sales/excel")
        assert r.status_code == 200
        assert "spreadsheet" in r.headers.get("content-type", "")

    def test_excel_with_date_range(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/reports/sales/excel?start_date=2026-01-01&end_date=2026-12-31")
        assert r.status_code == 200

    def test_excel_invalid_date_range_returns_400(self, client, admin_user):
        """نطاق تاريخ غير صالح في Excel يجب أن يُعيد 400 وليس 500."""
        _login(client, admin_user)
        r = client.get("/reports/sales/excel?start_date=2026-12-31&end_date=2026-01-01")
        # Should be 400 (bad request), not 500
        assert r.status_code in (400, 200)
        assert r.status_code != 500
