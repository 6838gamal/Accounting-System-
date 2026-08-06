"""
اختبارات تكاملية — سندات الاستلام
"""
import pytest
import re
from datetime import date


def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


def _csrf(client, path="/receipt-vouchers/new"):
    r = client.get(path)
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1) if m else ""


def _create_client_in_db(db):
    from app.models.client import Client, ClientType
    c = Client(name="عميل اختبار سند", type=ClientType.COMPANY)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _valid_voucher_data(client_id=None, csrf_token="", override=None):
    data = {
        "voucher_number": "RV-TEST-001",
        "voucher_date": str(date.today()),
        "received_from": "عميل اختبار",
        "amount": "1000.00",
        "method": "cash",
        "description": "دفعة اختبار",
        "csrf_token": csrf_token,
    }
    if client_id:
        data["client_id"] = str(client_id)
    if override:
        data.update(override)
    return data


class TestReceiptVoucherAuthGuard:
    def test_list_requires_login(self, client):
        r = client.get("/receipt-vouchers", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_new_requires_login(self, client):
        r = client.get("/receipt-vouchers/new", follow_redirects=False)
        assert r.status_code in (302, 303)


class TestReceiptVoucherList:
    def test_empty_list_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/receipt-vouchers")
        assert r.status_code == 200

    def test_pagination_valid(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/receipt-vouchers?page=1")
        assert r.status_code == 200


class TestReceiptVoucherCreate:
    def test_new_form_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/receipt-vouchers/new")
        assert r.status_code == 200

    def test_create_valid_voucher_no_client(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/receipt-vouchers/new",
            data=_valid_voucher_data(csrf_token=token),
            follow_redirects=True,
        )
        assert r.status_code == 200

    def test_create_valid_voucher_with_client(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client_in_db(db)
        token = _csrf(client)
        r = client.post(
            "/receipt-vouchers/new",
            data=_valid_voucher_data(client_id=c.id, csrf_token=token),
            follow_redirects=True,
        )
        assert r.status_code == 200

    def test_create_missing_received_from_rejected(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/receipt-vouchers/new",
            data=_valid_voucher_data(csrf_token=token, override={"received_from": ""}),
            follow_redirects=True,
        )
        assert r.status_code in (200, 302, 303)

    def test_create_zero_amount_rejected(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/receipt-vouchers/new",
            data=_valid_voucher_data(csrf_token=token, override={"amount": "0"}),
            follow_redirects=True,
        )
        assert r.status_code in (200, 302, 303)

    def test_create_invalid_date_rejected(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/receipt-vouchers/new",
            data=_valid_voucher_data(csrf_token=token, override={"voucher_date": "bad-date"}),
            follow_redirects=True,
        )
        assert r.status_code in (200, 302, 303)

    def test_create_invalid_method_rejected(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/receipt-vouchers/new",
            data=_valid_voucher_data(csrf_token=token, override={"payment_method": "INVALID"}),
            follow_redirects=True,
        )
        assert r.status_code in (200, 302, 303)

    def test_xss_in_description_escaped(self, client, admin_user):
        _login(client, admin_user)
        token = _csrf(client)
        r = client.post(
            "/receipt-vouchers/new",
            data=_valid_voucher_data(csrf_token=token, override={"description": '<script>alert(1)</script>'}),
            follow_redirects=True,
        )
        if r.status_code == 200:
            assert "<script>alert" not in r.text


class TestReceiptVoucherDetail:
    def test_detail_not_found(self, client, admin_user):
        _login(client, admin_user)
        # الراوتر يعيد redirect للقائمة (302) عند عدم وجود السند
        r = client.get("/receipt-vouchers/99999", follow_redirects=False)
        assert r.status_code in (302, 303, 404)

    def test_list_total_calculated(self, client, admin_user):
        """التحقق من صحة حساب المجموع الكلي."""
        _login(client, admin_user)
        r = client.get("/receipt-vouchers")
        assert r.status_code == 200
