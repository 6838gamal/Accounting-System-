"""
اختبارات تكاملية — عروض الأسعار
"""
import json
import pytest
from datetime import date, timedelta


def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


def _create_client(db, user_id=1):
    from app.services.client_service import ClientService
    return ClientService(db).create({"name": "عميل عروض", "type": "company"}, created_by=user_id)


def _csrf(client, path="/quotations"):
    r = client.get(path)
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1) if m else ""


def _make_quotation(db, user_id, client_id):
    from app.models.quotation import Quotation, QuotationItem, QuotationStatus
    from datetime import datetime
    from app.config import settings
    q = Quotation(
        quote_number=f"QT-2026-TEST-{id(db)}",
        client_id=client_id,
        title="عرض سعر اختبار",
        subtotal=1000,
        tax_rate=15,
        tax_amount=150,
        discount=0,
        total=1150,
        created_by=user_id,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    item = QuotationItem(
        quotation_id=q.id, description="خدمة",
        quantity=1, unit_price=1000, total=1000, sort_order=1,
    )
    db.add(item)
    db.commit()
    return q


class TestQuotationAuthGuard:
    def test_list_requires_login(self, client):
        r = client.get("/quotations", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_new_requires_login(self, client):
        r = client.get("/quotations/new", follow_redirects=False)
        assert r.status_code in (302, 303)


class TestQuotationList:
    def test_empty_list_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/quotations")
        assert r.status_code == 200

    def test_pagination(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/quotations?page=1")
        assert r.status_code == 200


class TestQuotationCreate:
    def test_new_form_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/quotations/new")
        assert r.status_code == 200

    def test_create_valid_quotation(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/quotations/new")
        items = json.dumps([{"description": "استشارة", "quantity": 2, "unit_price": 500}])
        r = client.post("/quotations/new", data={
            "client_id": c.id, "title": "عرض تطوير نظام",
            "tax_rate": "15", "discount": "0",
            "valid_until": str(date.today() + timedelta(days=30)),
            "items_json": items, "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_create_empty_items_rejected(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/quotations/new")
        r = client.post("/quotations/new", data={
            "client_id": c.id, "title": "عرض",
            "tax_rate": "0", "discount": "0",
            "items_json": "[]", "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_invalid_json_rejected(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/quotations/new")
        r = client.post("/quotations/new", data={
            "client_id": c.id, "title": "عرض",
            "tax_rate": "0", "discount": "0",
            "items_json": "not_json", "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_zero_quantity_rejected(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/quotations/new")
        items = json.dumps([{"description": "خدمة", "quantity": 0, "unit_price": 500}])
        r = client.post("/quotations/new", data={
            "client_id": c.id, "title": "عرض",
            "tax_rate": "0", "discount": "0",
            "items_json": items, "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_missing_description_rejected(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/quotations/new")
        items = json.dumps([{"description": "", "quantity": 1, "unit_price": 500}])
        r = client.post("/quotations/new", data={
            "client_id": c.id, "title": "عرض",
            "tax_rate": "0", "discount": "0",
            "items_json": items, "csrf_token": csrf,
        })
        assert r.status_code == 200


class TestQuotationDetail:
    def test_detail_loads(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        q = _make_quotation(db, admin_user.id, c.id)
        r = client.get(f"/quotations/{q.id}")
        assert r.status_code == 200

    def test_detail_not_found(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/quotations/99999")
        assert r.status_code == 404

    def test_print_page(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        q = _make_quotation(db, admin_user.id, c.id)
        r = client.get(f"/quotations/{q.id}/print")
        assert r.status_code == 200

    def test_pdf_generation(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        q = _make_quotation(db, admin_user.id, c.id)
        r = client.get(f"/quotations/{q.id}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"

    def test_convert_to_invoice(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        q = _make_quotation(db, admin_user.id, c.id)
        csrf = _csrf(client, f"/quotations/{q.id}")
        r = client.post(f"/quotations/{q.id}/to-invoice",
                        data={"csrf_token": csrf}, follow_redirects=False)
        assert r.status_code in (302, 303)
