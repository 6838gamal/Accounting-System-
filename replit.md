# نظام المحاسبة السحابي

نظام محاسبي ويب احترافي مبني بـ FastAPI و SQLAlchemy و Bootstrap 5 (واجهة عربية).

## تشغيل التطبيق

```bash
python main.py
```

التطبيق يعمل على المنفذ **5000**.

## بيانات الدخول الافتراضية

- **المستخدم:** admin
- **كلمة المرور:** admin123

## المكدس التقني

| المكون | التقنية |
|--------|---------|
| Backend | Python 3.12 + FastAPI |
| Templates | Jinja2 + Bootstrap 5 |
| Database | SQLite + SQLAlchemy 2.x |
| Migrations | Alembic |
| Auth | Session-based (itsdangerous) |
| PDF | ReportLab |
| Excel | OpenPyXL |
| Charts | Chart.js |

## هيكل المشروع

```
app/
├── routers/          # مسارات الصفحات وAPI
├── templates/        # قوالب HTML (Jinja2)
├── models/           # نماذج قاعدة البيانات
├── services/         # منطق الأعمال
├── templates_config.py  # قالب مشترك مع حقن إعدادات تلقائي
├── main.py           # تهيئة FastAPI
├── database.py       # اتصال قاعدة البيانات
└── config.py         # إعدادات التطبيق
main.py               # نقطة دخول uvicorn
```

## الإصلاحات المُطبَّقة

- **حقن الإعدادات تلقائياً**: `app/templates_config.py` يوفّر `AppTemplates` التي تُدرج إعدادات الشركة (اسم، عملة، لون...) في كل صفحة دون الحاجة لتمريرها يدوياً في كل route.
- **نموذج العقد**: أضيف عرض رمز العملة في حقل القيمة، وكتلة عرض رسائل الخطأ.
- **الطباعة A4**: إزالة `min-height: 297mm` في وضع `@media print` بحيث لا تمتد الصفحة قسراً، مع الإبقاء على padding مناسب.

## User preferences

- اللغة العربية في الواجهة والكود.
