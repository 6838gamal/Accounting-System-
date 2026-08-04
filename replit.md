# نظام المحاسبة السحابي

نظام محاسبي ويب احترافي مبني بـ FastAPI و SQLAlchemy و Bootstrap 5، مع دعم كامل للغة العربية.

## تشغيل التطبيق

```bash
python main.py
```

التطبيق يعمل على المنفذ **5000**.  
بيانات الدخول الافتراضية: `admin` / `admin123`

## الإعداد الأولي (مرة واحدة)

```bash
pip install -r requirements.txt
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
python -c "from app.database import SessionLocal; from app.services.settings_service import SettingsService; db=SessionLocal(); SettingsService(db).init_defaults(); db.close()"
```

## المكدس التقني

| المكون | التقنية |
|--------|---------|
| Backend | Python 3.13 + FastAPI |
| Templates | Jinja2 + Bootstrap 5 |
| Database | SQLite + SQLAlchemy 2.x |
| Auth | Session-based (itsdangerous) |
| PDF | ReportLab + WeasyPrint |
| Arabic | arabic-reshaper + python-bidi |
| Charts | Chart.js |

## هيكل المشروع

```
app/
├── models/         نماذج قاعدة البيانات
├── routers/        مسارات API والصفحات
├── schemas/        مخططات Pydantic
├── services/       منطق الأعمال
├── templates/      قوالب HTML (Jinja2)
│   └── contracts/  قوالب العقود (list, form, detail, layout_editor)
└── static/         CSS / JS / خطوط
```

## الميزات الرئيسية

- لوحة تحكم مع رسوم بيانية
- إدارة العملاء والعقود والفواتير وعروض الأسعار
- تتبع المدفوعات والمصروفات
- تقارير مع تصدير PDF و Excel
- **محرر تخطيط العقود قبل الطباعة** (layout editor) — `/contracts/{id}/layout-editor`
  - رفع وتعديل الشعار
  - ثلاثة قوالب تصميم (عصري / كلاسيكي / مبسط)
  - اختيار الألوان
  - لوح توقيع رقمي لطرفَي العقد
  - معاينة A4 لحظية وطباعة مباشرة

## User preferences

- المستخدم يريد محرر تخطيط (layout editor) للعقود قبل الطباعة بدل الطباعة المباشرة.
