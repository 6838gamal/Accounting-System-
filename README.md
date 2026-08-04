# نظام المحاسبة السحابي

نظام محاسبي ويب احترافي مبني بـ FastAPI و SQLAlchemy و Bootstrap 5.

## المميزات

- 🔐 نظام مستخدمين وصلاحيات متكامل
- 📊 لوحة تحكم تفاعلية مع رسوم بيانية
- 👥 إدارة العملاء
- 📄 إدارة العقود
- 💰 عروض الأسعار والفواتير
- 💳 تتبع المدفوعات والمصروفات
- 📈 تقارير شاملة مع تصدير PDF و Excel
- 📋 سجل العمليات
- ⚙️ إعدادات النظام

## التقنيات

| المكون | التقنية |
|--------|---------|
| Backend | Python 3.13 + FastAPI |
| Templates | Jinja2 + Bootstrap 5 |
| Database | SQLite + SQLAlchemy 2.x |
| Migrations | Alembic |
| Auth | Session-based |
| PDF | ReportLab |
| Excel | OpenPyXL |
| Charts | Chart.js |
| Tests | Pytest |

## التثبيت والتشغيل

```bash
# تثبيت المتطلبات
pip install -r requirements.txt

# تهيئة قاعدة البيانات
alembic upgrade head

# تشغيل التطبيق
python main.py
```

التطبيق يعمل على: http://localhost:8000

## بيانات الدخول الافتراضية

- **المستخدم:** admin
- **كلمة المرور:** admin123

## هيكل المشروع

```
.
├── app/
│   ├── models/         # نماذج قاعدة البيانات
│   ├── routers/        # مسارات API والصفحات
│   ├── schemas/        # مخططات Pydantic
│   ├── services/       # منطق الأعمال
│   ├── templates/      # قوالب HTML
│   ├── static/         # ملفات CSS/JS/صور
│   ├── config.py       # إعدادات التطبيق
│   ├── database.py     # اتصال قاعدة البيانات
│   └── main.py         # نقطة دخول FastAPI
├── alembic/            # مايغريشن قاعدة البيانات
├── tests/              # الاختبارات
├── docs/               # التوثيق
├── alembic.ini
├── requirements.txt
└── main.py             # نقطة دخول التطبيق
```

## التوثيق

- [رؤية المشروع](docs/PROJECT_VISION.md)
- [متطلبات المنتج](docs/PRODUCT_REQUIREMENTS.md)
- [معمارية البرمجيات](docs/SOFTWARE_ARCHITECTURE.md)
- [تصميم قاعدة البيانات](docs/DATABASE_DESIGN.md)
- [الوحدات](docs/MODULES.md)
- [إرشادات واجهة المستخدم](docs/UI_GUIDELINES.md)
- [معايير الكود](docs/CODING_STANDARDS.md)
- [دليل الأمان](docs/SECURITY_GUIDE.md)
- [دليل الاختبارات](docs/TESTING_GUIDE.md)
- [خارطة الطريق](docs/ROADMAP.md)
