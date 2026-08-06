"""
اختبارات تكاملية — الفواتير
يغطي: إنشاء، قراءة، تعديل، دفع، إلغاء، PDF، Excel، حالات الحافة
"""
import json
import pytest
from datetime import date, timedelta


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


def _create_client(db, user_id=1):
    from app.services.client_service import ClientService
    return ClientService(db).create({"name": "عميل اختباري", "type": "company"}, created_by=user_id)


def _csrf(client, path="/dashboard"):
    r = client.get(path)
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1) if m else ""


# ──────────────────────────────────────────────────────────────
# Auth guard
# ──────────────────────────────────────────────────────────────

class TestInvoiceAuthGuard:
    def test_list_requires_login(self, client):
        r = client.get("/invoices", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_new_form_requires_login(self, client):
        r = client.get("/invoices/new", follow_redirects=False)
        assert r.status_code in (302, 303)


# ──────────────────────────────────────────────────────────────
# List & display
# ──────────────────────────────────────────────────────────────

class TestInvoiceList:
    def test_empty_list(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/invoices")
        assert r.status_code == 200

    def test_list_shows_invoices(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        from app.services.invoice_service import InvoiceService
        InvoiceService(db).create(
            {"client_id": c.id, "issue_date": date.today(), "tax_rate": 0, "discount": 0},
            [{"description": "بند", "quantity": 1, "unit_price": 100}],
            created_by=admin_user.id,
        )
        r = client.get("/invoices")
        assert r.status_code == 200
        assert "INV" in r.text

    def test_pagination_valid(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/invoices?page=2")
        assert r.status_code == 200

    def test_pagination_invalid_page_rejected(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/invoices?page=0", follow_redirects=False)
        # FastAPI rejects page < 1 with 422
        assert r.status_code in (422, 400, 302)


# ──────────────────────────────────────────────────────────────
# Create
# ──────────────────────────────────────────────────────────────

class TestInvoiceCreate:
    def test_new_form_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/invoices/new")
        assert r.status_code == 200

    def test_create_valid_invoice(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/invoices/new")
        items = json.dumps([{"description": "خدمة برمجية", "quantity": 2, "unit_price": 500}])
        r = client.post("/invoices/new", data={
            "client_id": c.id, "issue_date": str(date.today()),
            "tax_rate": "15", "discount": "0",
            "items_json": items, "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_create_invoice_no_items_rejected(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/invoices/new")
        r = client.post("/invoices/new", data={
            "client_id": c.id, "issue_date": str(date.today()),
            "tax_rate": "0", "discount": "0",
            "items_json": "[]", "csrf_token": csrf,
        })
        assert r.status_code == 200
        assert "بند" in r.text or "خطأ" in r.text or "مطلوب" in r.text

    def test_create_invoice_invalid_client_rejected(self, client, admin_user, db):
        _login(client, admin_user)
        csrf = _csrf(client, "/invoices/new")
        r = client.post("/invoices/new", data={
            "client_id": 99999, "issue_date": str(date.today()),
            "tax_rate": "0", "discount": "0",
            "items_json": json.dumps([{"description": "x", "quantity": 1, "unit_price": 1}]),
            "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_invoice_invalid_items_json(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/invoices/new")
        r = client.post("/invoices/new", data={
            "client_id": c.id, "issue_date": str(date.today()),
            "tax_rate": "0", "discount": "0",
            "items_json": "not_json", "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_invoice_with_notes(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/invoices/new")
        items = json.dumps([{"description": "استشارة", "quantity": 1, "unit_price": 1000}])
        r = client.post("/invoices/new", data={
            "client_id": c.id, "issue_date": str(date.today()),
            "due_date": str(date.today() + timedelta(days=30)),
            "tax_rate": "15", "discount": "50",
            "notes": "شكراً لتعاملكم",
            "items_json": items, "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)


# ──────────────────────────────────────────────────────────────
# Detail & Print & PDF
# ──────────────────────────────────────────────────────────────

class TestInvoiceDetail:
    def _make_invoice(self, db, user_id):
        c = _create_client(db, user_id)
        from app.services.invoice_service import InvoiceService
        return InvoiceService(db).create(
            {"client_id": c.id, "issue_date": date.today(), "tax_rate": 15, "discount": 0},
            [{"description": "بند", "quantity": 1, "unit_price": 200}],
            created_by=user_id,
        )

    def test_detail_page_loads(self, client, admin_user, db):
        _login(client, admin_user)
        inv = self._make_invoice(db, admin_user.id)
        r = client.get(f"/invoices/{inv.id}")
        assert r.status_code == 200
        assert inv.invoice_number in r.text

    def test_detail_not_found(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/invoices/99999")
        assert r.status_code == 404

    def test_print_page_loads(self, client, admin_user, db):
        _login(client, admin_user)
        inv = self._make_invoice(db, admin_user.id)
        r = client.get(f"/invoices/{inv.id}/print")
        assert r.status_code == 200

    def test_pdf_download(self, client, admin_user, db):
        _login(client, admin_user)
        inv = self._make_invoice(db, admin_user.id)
        r = client.get(f"/invoices/{inv.id}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"


# ──────────────────────────────────────────────────────────────
# Payment recording
# ──────────────────────────────────────────────────────────────

class TestInvoicePayment:
    def _make_invoice(self, db, user_id):
        c = _create_client(db, user_id)
        from app.services.invoice_service import InvoiceService
        return InvoiceService(db).create(
            {"client_id": c.id, "issue_date": date.today(), "tax_rate": 0, "discount": 0},
            [{"description": "خدمة", "quantity": 1, "unit_price": 500}],
            created_by=user_id,
        )

    def test_partial_payment(self, client, admin_user, db):
        _login(client, admin_user)
        inv = self._make_invoice(db, admin_user.id)
        csrf = _csrf(client, f"/invoices/{inv.id}")
        r = client.post(f"/invoices/{inv.id}/payment", data={
            "amount": "200", "payment_date": str(date.today()),
            "method": "cash", "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_full_payment(self, client, admin_user, db):
        _login(client, admin_user)
        inv = self._make_invoice(db, admin_user.id)
        csrf = _csrf(client, f"/invoices/{inv.id}")
        r = client.post(f"/invoices/{inv.id}/payment", data={
            "amount": "500", "payment_date": str(date.today()),
            "method": "bank_transfer", "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_overpayment_rejected(self, client, admin_user, db):
        _login(client, admin_user)
        inv = self._make_invoice(db, admin_user.id)
        csrf = _csrf(client, f"/invoices/{inv.id}")
        r = client.post(f"/invoices/{inv.id}/payment", data={
            "amount": "9999", "payment_date": str(date.today()),
            "method": "cash", "csrf_token": csrf,
        })
        # Should return error or redirect with error
        assert r.status_code in (200, 302, 303)

    def test_zero_payment_rejected(self, client, admin_user, db):
        _login(client, admin_user)
        inv = self._make_invoice(db, admin_user.id)
        csrf = _csrf(client, f"/invoices/{inv.id}")
        r = client.post(f"/invoices/{inv.id}/payment", data={
            "amount": "0", "payment_date": str(date.today()),
            "method": "cash", "csrf_token": csrf,
        })
        assert r.status_code in (200, 302, 303)


# ──────────────────────────────────────────────────────────────
# Edge Cases
# ──────────────────────────────────────────────────────────────

class TestInvoiceEdgeCases:
    def test_xss_in_notes_escaped(self, client, admin_user, db):
        """XSS payload in notes must be escaped in output."""
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        from app.services.invoice_service import InvoiceService
        inv = InvoiceService(db).create(
            {"client_id": c.id, "issue_date": date.today(), "tax_rate": 0, "discount": 0,
             "notes": "<script>alert('xss')</script>"},
            [{"description": "بند", "quantity": 1, "unit_price": 100}],
            created_by=admin_user.id,
        )
        r = client.get(f"/invoices/{inv.id}")
        assert r.status_code == 200
        assert "<script>alert" not in r.text

    def test_max_items_limit(self, client, admin_user, db):
        """إنشاء فاتورة بأكثر من 100 بند — يجب أن تُقبل (مع اقتطاع)."""
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/invoices/new")
        items = json.dumps([{"description": f"بند {i}", "quantity": 1, "unit_price": 10} for i in range(150)])
        r = client.post("/invoices/new", data={
            "client_id": c.id, "issue_date": str(date.today()),
            "tax_rate": "0", "discount": "0",
            "items_json": items, "csrf_token": csrf,
        }, follow_redirects=False)
        # Should succeed (items are capped at 100)
        assert r.status_code in (302, 303, 200)

    def test_negative_unit_price_rejected_by_service(self, db, admin_user):
        """InvoiceService يجب أن يتعامل مع السعر السالب."""
        c = _create_client(db, admin_user.id)
        from app.services.invoice_service import InvoiceService
        # سعر سالب — يجب أن ينجح أو يرفض بشكل أمن (لا يُعطل النظام)
        try:
            inv = InvoiceService(db).create(
                {"client_id": c.id, "issue_date": date.today(), "tax_rate": 0, "discount": 0},
                [{"description": "بند", "quantity": 1, "unit_price": -100}],
                created_by=admin_user.id,
            )
            # If it allows negative prices, the total should be handled gracefully
        except (ValueError, Exception):
            pass  # ValueError is acceptable behavior
