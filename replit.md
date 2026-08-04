# نظام المحاسبة السحابي

## نظرة عامة
نظام محاسبي ويب متكامل مبني بـ Python + FastAPI مع واجهة Bootstrap 5 عربية RTL.

## كيفية التشغيل
```bash
python main.py
```
التطبيق يعمل على المنفذ 8000.

## بيانات الدخول الافتراضية
- **المستخدم:** `admin`
- **كلمة المرور:** `admin123`

## التقنيات
- Python 3.13 + FastAPI
- SQLAlchemy 2.x + SQLite
- Jinja2 + Bootstrap 5
- ReportLab (PDF) + OpenPyXL (Excel)
- Chart.js (الرسوم البيانية)

## تشغيل الاختبارات
```bash
pytest tests/ -v
```

## تفضيلات المستخدم
- اللغة: العربية (RTL)
- قاعدة البيانات: SQLite
- لا Docker أو Microservices
- Monolithic application
