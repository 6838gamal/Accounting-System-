# نظام المحاسبة السحابي

نظام محاسبي ويب احترافي مبني بـ Python 3.12 / FastAPI مع واجهة عربية كاملة.

## Stack التقني

| المكون | التقنية |
|--------|---------|
| Backend | Python 3.12 + FastAPI |
| Templates | Jinja2 + Bootstrap 5 |
| Database | SQLite + SQLAlchemy 2.x |
| Migrations | Alembic |
| Auth | Session-based + bcrypt |
| PDF | ReportLab |
| Excel | OpenPyXL |
| Charts | Chart.js |
| Tests | Pytest (236 tests) |

## تشغيل التطبيق

```bash
# تثبيت المتطلبات
pip install -r requirements.txt

# تشغيل التطبيق (يهيئ قاعدة البيانات تلقائياً)
python main.py
```

التطبيق يعمل على: http://0.0.0.0:5000

## بيانات الدخول الافتراضية

- **المستخدم:** `admin`
- **كلمة المرور:** `admin123` ← **يجب تغييرها فور التشغيل**

## متغيرات البيئة المطلوبة

يجب توفير المتغيرات التالية (عبر `.env` أو بيئة النظام):

```
SECRET_KEY=<سلسلة عشوائية ≥32 حرف>
SESSION_SECRET=<سلسلة عشوائية ≥32 حرف>
DEBUG=false
```

## تشغيل الاختبارات

```bash
python -m pytest tests/ -v
# 236 tests — 100% نجاح
```

## هيكل المشروع

```
├── app/
│   ├── models/         — نماذج SQLAlchemy
│   ├── routers/        — FastAPI endpoints
│   ├── schemas/        — Pydantic schemas
│   ├── services/       — Business logic
│   ├── templates/      — Jinja2 HTML (RTL/Arabic)
│   ├── static/         — CSS/JS/Images
│   ├── core/           — Exceptions, CSRF, Rate Limiting, Logging
│   ├── middleware/      — Security Headers, CSRF, Request Size
│   ├── config.py       — Settings (Pydantic)
│   ├── database.py     — SQLAlchemy engine + WAL mode
│   └── main.py         — FastAPI app + middleware
├── tests/
│   ├── unit/           — خدمات + حالات حافة
│   └── integration/    — كل الوحدات الوظيفية
├── alembic/            — Database migrations
├── AUDIT_REPORT.md     — تقرير المراجعة الشاملة
├── requirements.txt
└── main.py             — Entry point (port 5000)
```

## الميزات الأمنية

- CSRF protection على كل form
- Session fixation protection
- bcrypt password hashing
- Rate limiting (5 محاولات/5 دقائق للدخول)
- Security headers (CSP, X-Frame-Options, HSTS, nosniff)
- لا stack traces للمستخدم النهائي
- XSS protection (Jinja2 auto-escaping)
- SQL Injection protection (SQLAlchemy ORM)

## User Preferences

- اللغة العربية (RTL) هي اللغة الأساسية للواجهة والتعليقات
- يفضل المستخدم المراجعات الشاملة والتقارير التفصيلية
