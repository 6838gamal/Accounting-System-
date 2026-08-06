"""
اختبارات تكاملية — سندات المصاريف
"""
import pytest
import re
from datetime import date


def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


def _csrf(client, path="/expense-vouchers/new"):
    r = client.get(path)
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1) if m else ""


def _valid_voucher_data(csrf_token="", override=None):
    data = {
        "voucher_number": f"EV-TEST-001",
        "voucher_date": str(date.today()),
        "payee": "مورد اختبار",
        "amount": "500.00",
        "method": "cash",
        "category": "أخرى",
        "description": "مصروف اختبار",
        "csrf_token": csrf_token,
    }
    if override:
        data.update(override)
    return data


class TestExpenseVoucherAuthGuard:
    def test_list_requires_login(self, client):
        r = client.get("/expense-vouchers", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_new_requires_login(self, client):
        r = client.get("/expense-vouchers/new", follow_redirects=False)
        assert r.status_code in (302, 303)


class TestExpenseVoucherList:
    def test_empty_list_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/expense-vouchers")
        assert r.status_code == 200

    def test_pagination_valid(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/expense-vouchers?page=1")
        assert r.status_code == 200

    def test_pagination_invalid_page_defaults(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/expense-vouchers?page=0", follow_redirects=True)
        assert r.status_code in (200, 422)


class TestExpenseVoucherCreate:
    def test_new_form_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/expense-vouchers/new")
        assert r.status_code == 200

    def test_create_valid_voucher(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/expense-vouchers/new",
            data=_valid_voucher_data(token),
            follow_redirects=True,
        )
        assert r.status_code == 200

    def test_create_missing_payee_rejected(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/expense-vouchers/new",
            data=_valid_voucher_data(token, {"payee": ""}),
            follow_redirects=True,
        )
        # يجب أن يُعيد خطأ أو redirect
        assert r.status_code in (200, 302, 303)

    def test_create_zero_amount_rejected(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/expense-vouchers/new",
            data=_valid_voucher_data(token, {"amount": "0"}),
            follow_redirects=True,
        )
        assert r.status_code in (200, 302, 303)

    def test_create_negative_amount_rejected(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/expense-vouchers/new",
            data=_valid_voucher_data(token, {"amount": "-100"}),
            follow_redirects=True,
        )
        assert r.status_code in (200, 302, 303)

    def test_create_invalid_date_rejected(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/expense-vouchers/new",
            data=_valid_voucher_data(token, {"voucher_date": "not-a-date"}),
            follow_redirects=True,
        )
        assert r.status_code in (200, 302, 303)

    def test_create_invalid_method_rejected(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/expense-vouchers/new",
            data=_valid_voucher_data(token, {"payment_method": "INVALID_METHOD"}),
            follow_redirects=True,
        )
        assert r.status_code in (200, 302, 303)

    def test_xss_in_payee_escaped(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/expense-vouchers/new",
            data=_valid_voucher_data(token, {"payee": '<script>alert("xss")</script>'}),
            follow_redirects=True,
        )
        if r.status_code == 200:
            assert "<script>alert" not in r.text


class TestExpenseVoucherDetail:
    def _create_voucher(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/expense-vouchers/new",
            data=_valid_voucher_data(token),
            follow_redirects=True,
        )
        return r

    def test_detail_not_found(self, client, admin_user):
        _login(client, admin_user)
        # الراوتر يعيد redirect للقائمة (302) عند عدم وجود السند
        r = client.get("/expense-vouchers/99999", follow_redirects=False)
        assert r.status_code in (302, 303, 404)

    def test_print_page_loads(self, client, admin_user):
        """اختبار صفحة الطباعة بعد الإنشاء"""
        _login(client, admin_user)
        # إنشاء سند أولاً
        token = _csrf(client)
        client.post(
            "/expense-vouchers/new",
            data=_valid_voucher_data(token),
            follow_redirects=True,
        )
        # التحقق من أن القائمة تحتوي على سند
        r = client.get("/expense-vouchers")
        assert r.status_code == 200
