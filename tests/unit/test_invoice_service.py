"""
اختبارات وحدة خدمة الفواتير — تغطي المنطق المالي، edge cases، والحمايات
"""
import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.client import Client
from app.models.user import User, UserRole
from app.models.invoice import Invoice, InvoiceStatus
from app.services.invoice_service import InvoiceService
from app.services.auth_service import AuthService

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    s = TestSession()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def admin_user(db):
    user = AuthService(db).create_default_admin()
    return user


@pytest.fixture
def sample_client(db, admin_user):
    client = Client(name="عميل الاختبار", type="company", created_by=admin_user.id)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


SAMPLE_ITEMS = [
    {"description": "خدمة استشارية", "quantity": 2, "unit_price": 500},
    {"description": "دعم فني", "quantity": 1, "unit_price": 200},
]


class TestCalculateTotals:
    def test_basic_calculation(self, db):
        svc = InvoiceService(db)
        items = [{"description": "X", "quantity": 10, "unit_price": 100}]
        result = svc.calculate_totals(items, Decimal("15"), Decimal("0"))
        assert result["subtotal"] == Decimal("1000.00")
        assert result["tax_amount"] == Decimal("150.00")
        assert result["total"] == Decimal("1150.00")

    def test_with_discount(self, db):
        svc = InvoiceService(db)
        items = [{"description": "X", "quantity": 1, "unit_price": 1000}]
        result = svc.calculate_totals(items, Decimal("0"), Decimal("100"))
        assert result["total"] == Decimal("900.00")

    def test_discount_exceeds_subtotal_raises(self, db):
        svc = InvoiceService(db)
        items = [{"description": "X", "quantity": 1, "unit_price": 100}]
        with pytest.raises(ValueError, match="يتجاوز"):
            svc.calculate_totals(items, Decimal("0"), Decimal("200"))

    def test_negative_tax_raises(self, db):
        svc = InvoiceService(db)
        items = [{"description": "X", "quantity": 1, "unit_price": 100}]
        with pytest.raises(ValueError, match="الضريبة"):
            svc.calculate_totals(items, Decimal("-5"), Decimal("0"))

    def test_tax_over_100_raises(self, db):
        svc = InvoiceService(db)
        items = [{"description": "X", "quantity": 1, "unit_price": 100}]
        with pytest.raises(ValueError):
            svc.calculate_totals(items, Decimal("101"), Decimal("0"))

    def test_zero_total_floor(self, db):
        """المجموع لا يصبح سالباً."""
        svc = InvoiceService(db)
        items = [{"description": "X", "quantity": 1, "unit_price": 100}]
        result = svc.calculate_totals(items, Decimal("0"), Decimal("100"))
        assert result["total"] == Decimal("0")

    def test_decimal_precision(self, db):
        """التقريب المالي صحيح."""
        svc = InvoiceService(db)
        items = [{"description": "X", "quantity": 3, "unit_price": "33.33"}]
        result = svc.calculate_totals(items, Decimal("0"), Decimal("0"))
        assert result["subtotal"] == Decimal("99.99")


class TestInvoiceCreate:
    def test_create_invoice(self, db, sample_client, admin_user):
        svc = InvoiceService(db)
        inv = svc.create(
            data={"client_id": sample_client.id, "issue_date": date.today(),
                  "tax_rate": 15, "discount": 0},
            items_data=SAMPLE_ITEMS,
            created_by=admin_user.id,
        )
        assert inv.id is not None
        assert inv.invoice_number.startswith("INV-")
        assert inv.status == InvoiceStatus.DRAFT

    def test_create_empty_items_raises(self, db, sample_client, admin_user):
        svc = InvoiceService(db)
        with pytest.raises(ValueError, match="بند"):
            svc.create(
                data={"client_id": sample_client.id, "issue_date": date.today(),
                      "tax_rate": 0, "discount": 0},
                items_data=[],
                created_by=admin_user.id,
            )

    def test_unique_invoice_numbers(self, db, sample_client, admin_user):
        svc = InvoiceService(db)
        inv1 = svc.create(
            data={"client_id": sample_client.id, "issue_date": date.today(),
                  "tax_rate": 0, "discount": 0},
            items_data=[{"description": "A", "quantity": 1, "unit_price": 100}],
            created_by=admin_user.id,
        )
        inv2 = svc.create(
            data={"client_id": sample_client.id, "issue_date": date.today(),
                  "tax_rate": 0, "discount": 0},
            items_data=[{"description": "B", "quantity": 1, "unit_price": 200}],
            created_by=admin_user.id,
        )
        assert inv1.invoice_number != inv2.invoice_number

    def test_totals_stored_correctly(self, db, sample_client, admin_user):
        svc = InvoiceService(db)
        inv = svc.create(
            data={"client_id": sample_client.id, "issue_date": date.today(),
                  "tax_rate": "10", "discount": "50"},
            items_data=[{"description": "X", "quantity": 2, "unit_price": 500}],
            created_by=admin_user.id,
        )
        assert inv.subtotal == Decimal("1000.00")
        assert inv.tax_amount == Decimal("100.00")
        assert inv.total == Decimal("1050.00")


class TestPaymentRecording:
    @pytest.fixture
    def paid_invoice(self, db, sample_client, admin_user):
        svc = InvoiceService(db)
        inv = svc.create(
            data={"client_id": sample_client.id, "issue_date": date.today(),
                  "tax_rate": 0, "discount": 0},
            items_data=[{"description": "X", "quantity": 1, "unit_price": 1000}],
            created_by=admin_user.id,
        )
        # تغيير الحالة إلى sent للسماح بالدفع
        inv.status = InvoiceStatus.SENT
        db.commit()
        return inv

    def test_partial_payment(self, db, paid_invoice, admin_user):
        svc = InvoiceService(db)
        p = svc.record_payment(
            paid_invoice.id, Decimal("400"),
            {"payment_date": date.today(), "method": "cash"},
            created_by=admin_user.id,
        )
        assert p.amount == Decimal("400")
        db.refresh(paid_invoice)
        assert paid_invoice.status == InvoiceStatus.PARTIAL
        assert paid_invoice.paid_amount == Decimal("400.00")

    def test_full_payment_changes_status_to_paid(self, db, paid_invoice, admin_user):
        svc = InvoiceService(db)
        svc.record_payment(
            paid_invoice.id, Decimal("1000"),
            {"payment_date": date.today(), "method": "bank_transfer"},
            created_by=admin_user.id,
        )
        db.refresh(paid_invoice)
        assert paid_invoice.status == InvoiceStatus.PAID

    def test_overpayment_raises(self, db, paid_invoice, admin_user):
        svc = InvoiceService(db)
        with pytest.raises(ValueError, match="يتجاوز"):
            svc.record_payment(
                paid_invoice.id, Decimal("1500"),
                {"payment_date": date.today(), "method": "cash"},
                created_by=admin_user.id,
            )

    def test_zero_payment_raises(self, db, paid_invoice, admin_user):
        svc = InvoiceService(db)
        with pytest.raises(ValueError, match="أكبر"):
            svc.record_payment(
                paid_invoice.id, Decimal("0"),
                {"payment_date": date.today(), "method": "cash"},
                created_by=admin_user.id,
            )

    def test_negative_payment_raises(self, db, paid_invoice, admin_user):
        svc = InvoiceService(db)
        with pytest.raises(ValueError):
            svc.record_payment(
                paid_invoice.id, Decimal("-100"),
                {"payment_date": date.today(), "method": "cash"},
                created_by=admin_user.id,
            )

    def test_payment_on_cancelled_invoice_raises(self, db, paid_invoice, admin_user):
        svc = InvoiceService(db)
        paid_invoice.status = InvoiceStatus.CANCELLED
        db.commit()
        with pytest.raises(ValueError, match="ملغاة"):
            svc.record_payment(
                paid_invoice.id, Decimal("100"),
                {"payment_date": date.today(), "method": "cash"},
                created_by=admin_user.id,
            )

    def test_nonexistent_invoice_raises(self, db, admin_user):
        svc = InvoiceService(db)
        with pytest.raises(ValueError, match="غير موجودة"):
            svc.record_payment(
                9999, Decimal("100"),
                {"payment_date": date.today(), "method": "cash"},
                created_by=admin_user.id,
            )


class TestUpdateOverdue:
    def test_overdue_status_updated(self, db, sample_client, admin_user):
        svc = InvoiceService(db)
        from datetime import timedelta
        past_date = date.today() - timedelta(days=10)
        inv = svc.create(
            data={"client_id": sample_client.id, "issue_date": past_date,
                  "due_date": past_date, "tax_rate": 0, "discount": 0},
            items_data=[{"description": "X", "quantity": 1, "unit_price": 100}],
            created_by=admin_user.id,
        )
        inv.status = InvoiceStatus.SENT
        db.commit()
        svc.update_overdue()
        db.refresh(inv)
        assert inv.status == InvoiceStatus.OVERDUE

    def test_null_due_date_not_overdue(self, db, sample_client, admin_user):
        """الفواتير بلا تاريخ استحقاق لا تُعدّ متأخرة."""
        svc = InvoiceService(db)
        from datetime import timedelta
        inv = svc.create(
            data={"client_id": sample_client.id, "issue_date": date.today(),
                  "due_date": None, "tax_rate": 0, "discount": 0},
            items_data=[{"description": "X", "quantity": 1, "unit_price": 100}],
            created_by=admin_user.id,
        )
        inv.status = InvoiceStatus.SENT
        db.commit()
        svc.update_overdue()
        db.refresh(inv)
        assert inv.status == InvoiceStatus.SENT


class TestInvoiceSummary:
    def test_summary_excludes_drafts_and_cancelled(self, db, sample_client, admin_user):
        svc = InvoiceService(db)
        # فاتورة draft
        inv_draft = svc.create(
            data={"client_id": sample_client.id, "issue_date": date.today(),
                  "tax_rate": 0, "discount": 0},
            items_data=[{"description": "X", "quantity": 1, "unit_price": 1000}],
            created_by=admin_user.id,
        )
        # فاتورة sent
        inv_sent = svc.create(
            data={"client_id": sample_client.id, "issue_date": date.today(),
                  "tax_rate": 0, "discount": 0},
            items_data=[{"description": "Y", "quantity": 1, "unit_price": 500}],
            created_by=admin_user.id,
        )
        inv_sent.status = InvoiceStatus.SENT
        db.commit()

        summary = svc.get_summary()
        assert summary["total_invoiced"] == 500.0  # draft excluded
        assert summary["pending_count"] == 1
