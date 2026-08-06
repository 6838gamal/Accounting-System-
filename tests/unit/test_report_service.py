"""
اختبارات وحدة خدمة التقارير — تغطي التحقق من التواريخ والاستعلامات المحسّنة
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.expense import Expense, ExpenseStatus
from app.services.report_service import ReportService
from app.services.auth_service import AuthService
from app.services.invoice_service import InvoiceService

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
def client_obj(db):
    admin = AuthService(db).create_default_admin()
    c = Client(name="عميل التقرير", type="company", created_by=admin.id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestDateValidation:
    def test_invalid_date_range_raises(self, db):
        svc = ReportService(db)
        with pytest.raises(ValueError):
            svc.get_sales_report(date(2024, 12, 31), date(2024, 1, 1))

    def test_same_date_ok(self, db):
        svc = ReportService(db)
        result = svc.get_sales_report(date.today(), date.today())
        assert result["total_invoices"] == 0

    def test_invalid_year_raises(self, db):
        svc = ReportService(db)
        with pytest.raises(ValueError):
            svc.get_monthly_revenue(1999)

    def test_profit_loss_invalid_range(self, db):
        svc = ReportService(db)
        with pytest.raises(ValueError):
            svc.get_profit_loss(date(2024, 6, 1), date(2024, 1, 1))

    def test_client_report_invalid_range(self, db):
        svc = ReportService(db)
        with pytest.raises(ValueError):
            svc.get_client_report(date(2025, 12, 31), date(2025, 1, 1))


class TestSalesReport:
    def test_empty_db_returns_zeros(self, db):
        svc = ReportService(db)
        result = svc.get_sales_report(date(2024, 1, 1), date(2024, 12, 31))
        assert result["total_invoices"] == 0
        assert result["total_invoiced"] == 0.0

    def test_excludes_cancelled_invoices(self, db, client_obj):
        admin = db.query(__import__('app.models.user', fromlist=['User']).User).first()
        inv_svc = InvoiceService(db)
        # فاتورة ملغاة
        inv = inv_svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(), "tax_rate": 0, "discount": 0},
            [{"description": "X", "quantity": 1, "unit_price": 1000}],
            created_by=admin.id,
        )
        inv.status = InvoiceStatus.CANCELLED
        db.commit()

        svc = ReportService(db)
        result = svc.get_sales_report(date.today(), date.today())
        assert result["total_invoices"] == 0

    def test_excludes_draft_invoices(self, db, client_obj):
        admin = db.query(__import__('app.models.user', fromlist=['User']).User).first()
        inv_svc = InvoiceService(db)
        inv_svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(), "tax_rate": 0, "discount": 0},
            [{"description": "X", "quantity": 1, "unit_price": 500}],
            created_by=admin.id,
        )  # DRAFT by default

        svc = ReportService(db)
        result = svc.get_sales_report(date.today(), date.today())
        assert result["total_invoices"] == 0

    def test_includes_sent_invoices(self, db, client_obj):
        admin = db.query(__import__('app.models.user', fromlist=['User']).User).first()
        inv_svc = InvoiceService(db)
        inv = inv_svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(), "tax_rate": 0, "discount": 0},
            [{"description": "X", "quantity": 1, "unit_price": 1000}],
            created_by=admin.id,
        )
        inv.status = InvoiceStatus.SENT
        db.commit()

        svc = ReportService(db)
        result = svc.get_sales_report(date.today(), date.today())
        assert result["total_invoices"] == 1
        assert result["total_invoiced"] == 1000.0


class TestMonthlyRevenue:
    def test_returns_12_months(self, db):
        svc = ReportService(db)
        result = svc.get_monthly_revenue(2024)
        assert len(result) == 12
        assert result[0]["month"] == 1
        assert result[11]["month"] == 12

    def test_empty_months_return_zero(self, db):
        svc = ReportService(db)
        result = svc.get_monthly_revenue(2024)
        for month_data in result:
            assert month_data["revenue"] == 0.0
            assert month_data["expenses"] == 0.0
            assert month_data["profit"] == 0.0


class TestClientReport:
    def test_includes_active_clients_with_zero_invoices(self, db, client_obj):
        """يجب أن يظهر العميل حتى لو ليس لديه فواتير."""
        svc = ReportService(db)
        result = svc.get_client_report(date(2020, 1, 1), date(2020, 12, 31))
        assert any(r["id"] == client_obj.id for r in result)

    def test_excludes_cancelled_in_totals(self, db, client_obj):
        admin = db.query(__import__('app.models.user', fromlist=['User']).User).first()
        inv_svc = InvoiceService(db)
        inv = inv_svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(), "tax_rate": 0, "discount": 0},
            [{"description": "X", "quantity": 1, "unit_price": 1000}],
            created_by=admin.id,
        )
        inv.status = InvoiceStatus.CANCELLED
        db.commit()

        svc = ReportService(db)
        result = svc.get_client_report(date.today(), date.today())
        client_data = next((r for r in result if r["id"] == client_obj.id), None)
        assert client_data is not None
        assert client_data["invoice_count"] == 0  # ملغاة تُستثنى
        assert client_data["total_amount"] == 0.0


class TestExpenseReport:
    def test_only_approved_expenses(self, db):
        admin = AuthService(db).create_default_admin()
        pending = Expense(
            title="مصروف معلق", category="أخرى", amount=Decimal("500"),
            expense_date=date.today(), status=ExpenseStatus.PENDING, created_by=admin.id
        )
        approved = Expense(
            title="مصروف معتمد", category="رواتب", amount=Decimal("1000"),
            expense_date=date.today(), status=ExpenseStatus.APPROVED, created_by=admin.id
        )
        db.add_all([pending, approved])
        db.commit()

        svc = ReportService(db)
        result = svc.get_expense_report(date.today(), date.today())
        assert result["total"] == 1000.0
        assert len(result["expenses"]) == 1

    def test_by_category_grouping(self, db):
        admin = AuthService(db).create_default_admin()
        for i in range(3):
            db.add(Expense(
                title=f"راتب {i}", category="رواتب", amount=Decimal("1000"),
                expense_date=date.today(), status=ExpenseStatus.APPROVED, created_by=admin.id
            ))
        db.commit()

        svc = ReportService(db)
        result = svc.get_expense_report(date.today(), date.today())
        assert result["by_category"]["رواتب"]["count"] == 3
        assert result["by_category"]["رواتب"]["total"] == 3000.0


class TestProfitLoss:
    def test_cash_basis_profit_calculation(self, db, client_obj):
        admin = AuthService(db).create_default_admin()
        # دفعة مستلمة
        inv_svc = InvoiceService(db)
        inv = inv_svc.create(
            {"client_id": client_obj.id, "issue_date": date.today(), "tax_rate": 0, "discount": 0},
            [{"description": "X", "quantity": 1, "unit_price": 5000}],
            created_by=admin.id,
        )
        inv.status = InvoiceStatus.SENT
        db.commit()
        inv_svc.record_payment(inv.id, Decimal("5000"),
                               {"payment_date": date.today(), "method": "cash"}, admin.id)

        # مصروف معتمد
        db.add(Expense(
            title="إيجار", category="إيجار", amount=Decimal("2000"),
            expense_date=date.today(), status=ExpenseStatus.APPROVED, created_by=admin.id
        ))
        db.commit()

        svc = ReportService(db)
        result = svc.get_profit_loss(date.today(), date.today())
        assert result["revenue"] == 5000.0
        assert result["expenses"] == 2000.0
        assert result["profit"] == 3000.0
