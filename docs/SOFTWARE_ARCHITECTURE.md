# معمارية البرمجيات

## نمط المعمارية

**Monolithic MVC** — تطبيق موحد باستخدام نمط Model-View-Controller.

```
Browser ──► FastAPI Router ──► Service Layer ──► SQLAlchemy ORM ──► SQLite
                │                                                        │
                └──► Jinja2 Templates ◄─────────────────────────────────┘
```

## طبقات التطبيق

### 1. طبقة العرض (Presentation Layer)
- **Jinja2 Templates**: قوالب HTML ديناميكية
- **Bootstrap 5**: تصميم متجاوب
- **Chart.js**: رسوم بيانية تفاعلية
- **Static Files**: CSS/JS/صور

### 2. طبقة التوجيه (Routing Layer)
- **FastAPI Routers**: تعريف نقاط النهاية
- كل وحدة لها Router منفصل
- Authentication Middleware على المسارات المحمية

### 3. طبقة الخدمات (Service Layer)
- منطق الأعمال معزول عن الـ Routes
- يمكن اختباره بشكل مستقل
- يتعامل مع قاعدة البيانات عبر ORM

### 4. طبقة البيانات (Data Layer)
- **SQLAlchemy 2.x**: ORM متقدم
- **Alembic**: إدارة migrations
- **SQLite**: قاعدة البيانات

## هيكل الملفات

```
app/
├── __init__.py
├── main.py              # تهيئة FastAPI والـ middlewares
├── config.py            # إعدادات التطبيق
├── database.py          # اتصال قاعدة البيانات
├── dependencies.py      # Dependencies مشتركة
├── models/              # نماذج SQLAlchemy
│   ├── __init__.py
│   ├── user.py
│   ├── client.py
│   ├── contract.py
│   ├── quotation.py
│   ├── invoice.py
│   ├── payment.py
│   ├── expense.py
│   ├── settings.py
│   └── activity_log.py
├── routers/             # FastAPI Routers
│   ├── __init__.py
│   ├── auth.py
│   ├── dashboard.py
│   ├── users.py
│   ├── clients.py
│   ├── contracts.py
│   ├── quotations.py
│   ├── invoices.py
│   ├── payments.py
│   ├── expenses.py
│   ├── reports.py
│   ├── settings.py
│   └── activity_log.py
├── schemas/             # Pydantic Schemas
│   ├── __init__.py
│   ├── user.py
│   ├── client.py
│   ├── contract.py
│   ├── quotation.py
│   ├── invoice.py
│   ├── payment.py
│   └── expense.py
├── services/            # Business Logic
│   ├── __init__.py
│   ├── auth_service.py
│   ├── client_service.py
│   ├── contract_service.py
│   ├── quotation_service.py
│   ├── invoice_service.py
│   ├── payment_service.py
│   ├── expense_service.py
│   ├── report_service.py
│   └── pdf_service.py
├── templates/           # Jinja2 Templates
│   ├── base.html
│   ├── partials/
│   ├── auth/
│   ├── dashboard/
│   ├── users/
│   ├── clients/
│   ├── contracts/
│   ├── quotations/
│   ├── invoices/
│   ├── payments/
│   ├── expenses/
│   ├── reports/
│   ├── settings/
│   └── activity_log/
└── static/
    ├── css/
    ├── js/
    └── img/
```

## تدفق البيانات

1. المستخدم يرسل طلب HTTP
2. FastAPI يستقبل الطلب ويتحقق من الجلسة
3. Router يستدعي Service المناسب
4. Service ينفذ منطق الأعمال ويتعامل مع ORM
5. النتيجة تُعرض عبر Jinja2 Template أو تُرجع كـ JSON
