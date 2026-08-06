"""
اختبارات تكاملية — العقود
"""
import pytest
from datetime import date, timedelta


def _login(client, admin_user):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})


def _create_client(db, user_id=1):
    from app.services.client_service import ClientService
    return ClientService(db).create({"name": "عميل العقود", "type": "company"}, created_by=user_id)


def _csrf(client, path="/dashboard"):
    r = client.get(path)
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1) if m else ""


class TestContractAuthGuard:
    def test_list_requires_login(self, client):
        r = client.get("/contracts", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_new_requires_login(self, client):
        r = client.get("/contracts/new", follow_redirects=False)
        assert r.status_code in (302, 303)


class TestContractList:
    def test_empty_list_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/contracts")
        assert r.status_code == 200

    def test_search_filter(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/contracts?search=اختبار")
        assert r.status_code == 200

    def test_pagination(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/contracts?page=1")
        assert r.status_code == 200


class TestContractCreate:
    def test_new_form_loads(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/contracts/new")
        assert r.status_code == 200

    def test_create_valid_contract(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/contracts/new")
        r = client.post("/contracts/new", data={
            "client_id": c.id,
            "title": "عقد صيانة سنوي",
            "amount": "12000",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=365)),
            "notes": "عقد صيانة",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_create_contract_empty_title_rejected(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/contracts/new")
        r = client.post("/contracts/new", data={
            "client_id": c.id, "title": "   ",
            "amount": "1000", "csrf_token": csrf,
        })
        assert r.status_code == 200
        assert "مطلوب" in r.text or "خطأ" in r.text

    def test_create_contract_invalid_amount(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/contracts/new")
        r = client.post("/contracts/new", data={
            "client_id": c.id, "title": "عقد",
            "amount": "abc", "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_contract_negative_amount(self, client, admin_user, db):
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/contracts/new")
        r = client.post("/contracts/new", data={
            "client_id": c.id, "title": "عقد",
            "amount": "-500", "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_contract_invalid_date_range(self, client, admin_user, db):
        """تاريخ النهاية قبل تاريخ البداية يجب أن يُرفض."""
        _login(client, admin_user)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, "/contracts/new")
        r = client.post("/contracts/new", data={
            "client_id": c.id, "title": "عقد",
            "amount": "1000",
            "start_date": str(date.today()),
            "end_date": str(date.today() - timedelta(days=1)),
            "csrf_token": csrf,
        })
        assert r.status_code == 200

    def test_create_contract_nonexistent_client(self, client, admin_user):
        _login(client, admin_user)
        csrf = _csrf(client, "/contracts/new")
        r = client.post("/contracts/new", data={
            "client_id": 99999, "title": "عقد",
            "amount": "1000", "csrf_token": csrf,
        })
        assert r.status_code == 200


class TestContractDetail:
    def _make_contract(self, db, user_id):
        from app.models.contract import Contract
        c = _create_client(db, user_id)
        from datetime import datetime
        from app.config import settings
        contract = Contract(
            contract_number=f"CNT-2026-0001",
            client_id=c.id,
            title="عقد اختبار",
            amount=5000,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            created_by=user_id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract

    def test_detail_loads(self, client, admin_user, db):
        _login(client, admin_user)
        contract = self._make_contract(db, admin_user.id)
        r = client.get(f"/contracts/{contract.id}")
        assert r.status_code == 200

    def test_detail_not_found(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/contracts/99999")
        assert r.status_code == 404

    def test_print_page(self, client, admin_user, db):
        _login(client, admin_user)
        contract = self._make_contract(db, admin_user.id)
        r = client.get(f"/contracts/{contract.id}/print")
        assert r.status_code == 200

    def test_pdf_generation(self, client, admin_user, db):
        _login(client, admin_user)
        contract = self._make_contract(db, admin_user.id)
        r = client.get(f"/contracts/{contract.id}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"

    def test_convert_to_invoice(self, client, admin_user, db):
        _login(client, admin_user)
        contract = self._make_contract(db, admin_user.id)
        csrf = _csrf(client, f"/contracts/{contract.id}")
        r = client.post(f"/contracts/{contract.id}/to-invoice", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)


class TestContractEdit:
    def _make_contract(self, db, user_id):
        from app.models.contract import Contract
        c = _create_client(db, user_id)
        contract = Contract(
            contract_number="CNT-2026-0002",
            client_id=c.id,
            title="عقد للتعديل",
            amount=3000,
            created_by=user_id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract

    def test_edit_form_loads(self, client, admin_user, db):
        _login(client, admin_user)
        contract = self._make_contract(db, admin_user.id)
        r = client.get(f"/contracts/{contract.id}/edit")
        assert r.status_code == 200

    def test_edit_updates_contract(self, client, admin_user, db):
        _login(client, admin_user)
        contract = self._make_contract(db, admin_user.id)
        c = _create_client(db, admin_user.id)
        csrf = _csrf(client, f"/contracts/{contract.id}/edit")
        r = client.post(f"/contracts/{contract.id}/edit", data={
            "client_id": c.id,
            "title": "عقد معدّل",
            "amount": "4000",
            "status": "active",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert r.status_code in (302, 303)
