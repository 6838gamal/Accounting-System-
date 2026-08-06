"""
اختبارات وحدة — الحالات الحافة والموثوقية
"""
import pytest
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta


# ──────────────────────────────────────────────────────────────
# InvoiceService — حالات حافة
# ──────────────────────────────────────────────────────────────

class TestInvoiceTotalsEdgeCases:
    def test_zero_tax_rate(self, db):
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        result = svc.calculate_totals(
            [{"quantity": 1, "unit_price": 1000}],
            tax_rate=Decimal("0"), discount=Decimal("0"),
        )
        assert result["tax_amount"] == Decimal("0")
        assert result["total"] == Decimal("1000")

    def test_100_percent_tax(self, db):
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        result = svc.calculate_totals(
            [{"quantity": 1, "unit_price": 500}],
            tax_rate=Decimal("100"), discount=Decimal("0"),
        )
        assert result["total"] == Decimal("1000.00")

    def test_tax_rate_over_100_rejected(self, db):
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        with pytest.raises(ValueError):
            svc.calculate_totals(
                [{"quantity": 1, "unit_price": 100}],
                tax_rate=Decimal("101"), discount=Decimal("0"),
            )

    def test_negative_tax_rate_rejected(self, db):
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        with pytest.raises(ValueError):
            svc.calculate_totals(
                [{"quantity": 1, "unit_price": 100}],
                tax_rate=Decimal("-1"), discount=Decimal("0"),
            )

    def test_discount_exceeds_subtotal_rejected(self, db):
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        with pytest.raises(ValueError):
            svc.calculate_totals(
                [{"quantity": 1, "unit_price": 100}],
                tax_rate=Decimal("0"), discount=Decimal("200"),
            )

    def test_total_never_negative(self, db):
        """المجموع يجب ألا يكون سالباً حتى مع خصم كبير."""
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        # discount == subtotal → total should be 0
        result = svc.calculate_totals(
            [{"quantity": 1, "unit_price": 100}],
            tax_rate=Decimal("0"), discount=Decimal("100"),
        )
        assert result["total"] >= Decimal("0")

    def test_decimal_precision_rounding(self, db):
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        result = svc.calculate_totals(
            [{"quantity": 3, "unit_price": "0.10"}],
            tax_rate=Decimal("0"), discount=Decimal("0"),
        )
        assert result["subtotal"] == Decimal("0.30")

    def test_large_amounts(self, db):
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        result = svc.calculate_totals(
            [{"quantity": 1000, "unit_price": 9999999.99}],
            tax_rate=Decimal("15"), discount=Decimal("0"),
        )
        assert result["total"] > 0

    def test_fractional_quantity(self, db):
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        result = svc.calculate_totals(
            [{"quantity": "0.5", "unit_price": "100"}],
            tax_rate=Decimal("0"), discount=Decimal("0"),
        )
        assert result["subtotal"] == Decimal("50.00")

    def test_empty_items_raises(self, db):
        from app.services.invoice_service import InvoiceService
        svc = InvoiceService(db)
        with pytest.raises(ValueError):
            svc.create(
                {"client_id": 1, "issue_date": date.today(),
                 "tax_rate": 0, "discount": 0},
                items_data=[],
                created_by=1,
            )

    def test_invoice_number_unique_consecutive(self, db):
        """رقم الفاتورة يجب أن يكون فريداً لكل فاتورة متتالية."""
        from app.services.auth_service import AuthService
        from app.services.client_service import ClientService
        from app.services.invoice_service import InvoiceService

        admin = AuthService(db).create_default_admin()
        c = ClientService(db).create({"name": "عميل", "type": "company"}, created_by=admin.id)
        svc = InvoiceService(db)
        nums = set()
        for _ in range(5):
            inv = svc.create(
                {"client_id": c.id, "issue_date": date.today(),
                 "tax_rate": 0, "discount": 0},
                [{"description": "x", "quantity": 1, "unit_price": 10}],
                created_by=admin.id,
            )
            nums.add(inv.invoice_number)
        assert len(nums) == 5, "أرقام الفواتير يجب أن تكون فريدة"


# ──────────────────────────────────────────────────────────────
# ReportService — حالات حافة
# ──────────────────────────────────────────────────────────────

class TestReportServiceEdgeCases:
    def test_empty_db_all_zeros(self, db):
        from app.services.report_service import ReportService
        svc = ReportService(db)
        result = svc.get_profit_loss(date(2026, 1, 1), date(2026, 12, 31))
        assert result["revenue"] == 0.0
        assert result["expenses"] == 0.0
        assert result["profit"] == 0.0

    def test_same_start_end_date_ok(self, db):
        from app.services.report_service import ReportService
        svc = ReportService(db)
        today = date.today()
        result = svc.get_sales_report(today, today)
        assert result is not None

    def test_end_before_start_raises(self, db):
        from app.services.report_service import ReportService
        svc = ReportService(db)
        with pytest.raises(ValueError):
            svc.get_sales_report(date(2026, 12, 1), date(2026, 1, 1))

    def test_invalid_year_raises(self, db):
        from app.services.report_service import ReportService
        svc = ReportService(db)
        with pytest.raises(ValueError):
            svc.get_monthly_revenue(1999)

    def test_monthly_revenue_returns_12_months(self, db):
        from app.services.report_service import ReportService
        svc = ReportService(db)
        result = svc.get_monthly_revenue(2026)
        assert len(result) == 12
        for m in result:
            assert "month" in m
            assert "revenue" in m
            assert "expenses" in m
            assert "profit" in m


# ──────────────────────────────────────────────────────────────
# RateLimiter — حالات حافة
# ──────────────────────────────────────────────────────────────

class TestRateLimiterEdgeCases:
    def test_allows_within_limit(self):
        from app.core.rate_limiter import RateLimiter
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.is_allowed("test_key") is True

    def test_blocks_over_limit(self):
        from app.core.rate_limiter import RateLimiter
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("test_key")
        assert limiter.is_allowed("test_key") is False

    def test_different_keys_independent(self):
        from app.core.rate_limiter import RateLimiter
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("key1")
        limiter.is_allowed("key1")
        assert limiter.is_allowed("key1") is False
        assert limiter.is_allowed("key2") is True

    def test_remaining_count(self):
        from app.core.rate_limiter import RateLimiter
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.remaining("new_key") == 5
        limiter.is_allowed("new_key")
        assert limiter.remaining("new_key") == 4

    def test_cleanup_removes_old_keys(self):
        from app.core.rate_limiter import RateLimiter
        import time
        limiter = RateLimiter(max_requests=5, window_seconds=1)
        limiter.is_allowed("cleanup_key")
        time.sleep(1.1)
        limiter.cleanup()
        assert "cleanup_key" not in limiter._store


# ──────────────────────────────────────────────────────────────
# CSRF — حالات حافة
# ──────────────────────────────────────────────────────────────

class TestCSRFEdgeCases:
    def test_validate_empty_token_fails(self, client, admin_user):
        """توكن CSRF فارغ يجب أن يُرفض."""
        client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        r = client.post("/clients/new", data={
            "name": "عميل", "type": "company", "csrf_token": "",
        })
        assert r.status_code == 403

    def test_validate_wrong_token_fails(self, client, admin_user):
        """توكن CSRF خاطئ يجب أن يُرفض."""
        client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        r = client.post("/clients/new", data={
            "name": "عميل", "type": "company",
            "csrf_token": "wrong_token_12345",
        })
        assert r.status_code == 403


# ──────────────────────────────────────────────────────────────
# ClientService — حالات حافة
# ──────────────────────────────────────────────────────────────

class TestClientServiceEdgeCases:
    def test_search_with_special_chars(self, db):
        from app.services.client_service import ClientService
        from app.services.auth_service import AuthService
        admin = AuthService(db).create_default_admin()
        svc = ClientService(db)
        # إدخال رموز خاصة في البحث — يجب أن لا يُعطل قاعدة البيانات
        clients, total = svc.get_all(search="'; DROP TABLE clients;--")
        assert total == 0

    def test_search_with_xss_payload(self, db):
        from app.services.client_service import ClientService
        from app.services.auth_service import AuthService
        admin = AuthService(db).create_default_admin()
        svc = ClientService(db)
        clients, total = svc.get_all(search="<script>alert(1)</script>")
        assert total == 0

    def test_get_nonexistent_client_returns_none(self, db):
        from app.services.client_service import ClientService
        svc = ClientService(db)
        assert svc.get_by_id(99999) is None

    def test_delete_nonexistent_returns_false(self, db):
        from app.services.client_service import ClientService
        svc = ClientService(db)
        assert svc.delete(99999) is False

    def test_soft_delete_hides_client(self, db):
        from app.services.client_service import ClientService
        from app.services.auth_service import AuthService
        admin = AuthService(db).create_default_admin()
        svc = ClientService(db)
        c = svc.create({"name": "عميل محذوف", "type": "company"}, created_by=admin.id)
        svc.delete(c.id)
        # يجب أن يختفي من القائمة النشطة
        clients, total = svc.get_all(is_active=True)
        ids = [cl.id for cl in clients]
        assert c.id not in ids

    def test_stats_for_nonexistent_client(self, db):
        from app.services.client_service import ClientService
        svc = ClientService(db)
        stats = svc.get_stats(99999)
        assert stats["total_invoices"] == 0
        assert stats["total_revenue"] == 0.0


# ──────────────────────────────────────────────────────────────
# AuthService — حالات حافة
# ──────────────────────────────────────────────────────────────

class TestAuthServiceEdgeCases:
    def test_authenticate_nonexistent_user(self, db):
        from app.services.auth_service import AuthService
        svc = AuthService(db)
        result = svc.authenticate_user("nonexistent", "anypassword")
        assert result is None

    def test_authenticate_empty_credentials(self, db):
        from app.services.auth_service import AuthService
        svc = AuthService(db)
        result = svc.authenticate_user("", "")
        assert result is None

    def test_create_default_admin_idempotent(self, db):
        """استدعاء create_default_admin مرتين يجب ألا يُنشئ مشرفين مكررين."""
        from app.services.auth_service import AuthService
        svc = AuthService(db)
        admin1 = svc.create_default_admin()
        admin2 = svc.create_default_admin()
        assert admin1.id == admin2.id

    def test_password_hash_is_bcrypt(self, db):
        from app.services.auth_service import AuthService
        svc = AuthService(db)
        hashed = svc.get_password_hash("TestPassword123")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_wrong_password_returns_none(self, db):
        from app.services.auth_service import AuthService
        svc = AuthService(db)
        svc.create_default_admin()
        result = svc.authenticate_user("admin", "wrongpassword")
        assert result is None
