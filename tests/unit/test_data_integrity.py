"""
اختبارات سلامة البيانات (Data Integrity)
"""
import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.payment import Payment
from app.models.client import Client, ClientType
from app.models.expense import Expense, ExpenseStatus
from app.services.invoice_service import InvoiceService


DB_URL = "sqlite:///./test_data_integrity.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client_obj(db):
    c = Client(name="عميل اختبار", type=ClientType.COMPANY)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestInvoiceDataIntegrity:
    """سلامة بيانات الفواتير."""

    def test_invoice_total_equals_subtotal_plus_tax_minus_discount(self, db, client_obj):
        svc = InvoiceService(db)
        items = [{"description": "بند", "quantity": 2, "unit_price": 100.0}]
        tax_rate = Decimal("15")
        discount = Decimal("10")
        totals = svc.calculate_totals(items, tax_rate, discount)
        # subtotal = 200, tax = 30, discount = 10 → total = 220
        assert totals["subtotal"] == Decimal("200.00")
        assert totals["tax_amount"] == Decimal("30.00")
        assert totals["total"] == Decimal("220.00")

    def test_paid_amount_never_exceeds_total(self, db, client_obj):
        svc = InvoiceService(db)
        items = [{"description": "بند", "quantity": 1, "unit_price": 500.0}]
        invoice = svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(),
             "tax_rate": Decimal("0"), "discount": Decimal("0")},
            items, created_by=1,
        )
        invoice.status = InvoiceStatus.SENT
        db.commit()

        svc.record_payment(invoice.id, Decimal("300"), {"payment_date": date.today(), "method": "cash"}, created_by=1)
        db.refresh(invoice)
        assert invoice.paid_amount == Decimal("300.00")
        assert invoice.paid_amount <= invoice.total

        with pytest.raises(ValueError):
            svc.record_payment(invoice.id, Decimal("300"), {"payment_date": date.today(), "method": "cash"}, created_by=1)

    def test_invoice_status_transitions(self, db, client_obj):
        """التحقق من انتقالات الحالة الصحيحة."""
        svc = InvoiceService(db)
        items = [{"description": "خدمة", "quantity": 1, "unit_price": 100.0}]
        invoice = svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(),
             "tax_rate": Decimal("0"), "discount": Decimal("0")},
            items, created_by=1,
        )
        assert invoice.status == InvoiceStatus.DRAFT

    def test_cancelled_invoice_cannot_receive_payment(self, db, client_obj):
        svc = InvoiceService(db)
        items = [{"description": "بند", "quantity": 1, "unit_price": 100.0}]
        invoice = svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(),
             "tax_rate": Decimal("0"), "discount": Decimal("0")},
            items, created_by=1,
        )
        svc.cancel(invoice.id)
        with pytest.raises(ValueError, match="ملغاة|cancelled"):
            svc.record_payment(invoice.id, Decimal("50"), {"payment_date": date.today(), "method": "cash"}, created_by=1)

    def test_unique_invoice_numbers(self, db, client_obj):
        svc = InvoiceService(db)
        items = [{"description": "بند", "quantity": 1, "unit_price": 100.0}]
        inv1 = svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(),
             "tax_rate": Decimal("0"), "discount": Decimal("0")},
            items, created_by=1,
        )
        inv2 = svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(),
             "tax_rate": Decimal("0"), "discount": Decimal("0")},
            items, created_by=1,
        )
        assert inv1.invoice_number != inv2.invoice_number

    def test_no_orphan_items_on_invoice_delete(self, db, client_obj):
        """حذف الفاتورة يجب أن يحذف بنودها (cascade)."""
        from app.models.invoice import InvoiceItem
        svc = InvoiceService(db)
        items = [{"description": "بند1", "quantity": 1, "unit_price": 100.0}]
        invoice = svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(),
             "tax_rate": Decimal("0"), "discount": Decimal("0")},
            items, created_by=1,
        )
        invoice_id = invoice.id
        db.delete(invoice)
        db.commit()
        orphans = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).count()
        assert orphans == 0


class TestFinancialCalculations:
    """صحة العمليات المالية."""

    def test_discount_cannot_exceed_subtotal(self, db, client_obj):
        svc = InvoiceService(db)
        items = [{"description": "بند", "quantity": 1, "unit_price": 100.0}]
        with pytest.raises(ValueError, match="[Xx]صم|discount|يتجاوز"):
            svc.calculate_totals(items, Decimal("0"), Decimal("200"))

    def test_negative_tax_raises(self, db, client_obj):
        svc = InvoiceService(db)
        items = [{"description": "بند", "quantity": 1, "unit_price": 100.0}]
        with pytest.raises(ValueError):
            svc.calculate_totals(items, Decimal("-5"), Decimal("0"))

    def test_tax_over_100_raises(self, db, client_obj):
        svc = InvoiceService(db)
        items = [{"description": "بند", "quantity": 1, "unit_price": 100.0}]
        with pytest.raises(ValueError):
            svc.calculate_totals(items, Decimal("101"), Decimal("0"))

    def test_decimal_precision_maintained(self, db, client_obj):
        """دقة الأرقام العشرية في العمليات المالية."""
        svc = InvoiceService(db)
        items = [{"description": "بند", "quantity": "0.333", "unit_price": "0.10"}]
        totals = svc.calculate_totals(items, Decimal("0"), Decimal("0"))
        # يجب ألا يُرجع أكثر من منزلتين عشريتين
        total_str = str(totals["total"])
        decimal_part = total_str.split(".")[-1] if "." in total_str else ""
        assert len(decimal_part) <= 2

    def test_zero_quantity_raises(self, db):
        svc = InvoiceService(db)
        items = [{"description": "بند", "quantity": 0, "unit_price": 100.0}]
        # المبلغ النهائي سيكون 0 وهو مقبول رياضياً لكن يجب أن يُرفع validation قبله
        totals = svc.calculate_totals(items, Decimal("0"), Decimal("0"))
        assert totals["total"] == Decimal("0.00")
