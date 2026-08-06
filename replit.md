# نظام المحاسبة السحابي

نظام محاسبي ويب احترافي مبني بـ FastAPI و SQLAlchemy و Bootstrap 5 بدعم كامل للغة العربية.

## تشغيل المشروع

```bash
python main.py
```

التطبيق يعمل على المنفذ 5000.

**بيانات الدخول الافتراضية:**
- المستخدم: `admin`
- كلمة المرور: `admin123`
- **⚠️ يجب تغيير كلمة المرور فور التشغيل**

## تشغيل الاختبارات

```bash
SECRET_KEY=test-key-at-least-32-chars SESSION_SECRET=test-session-at-least-32 python -m pytest tests/ -v
```

**عدد الاختبارات:** 282 — 100% ناجحة

## هيكل المشروع

```
app/
├── models/         نماذج قاعدة البيانات (SQLAlchemy)
├── routers/        مسارات API والصفحات (FastAPI)
├── schemas/        مخططات Pydantic
├── services/       منطق الأعمال
├── templates/      قوالب HTML (Jinja2 + Bootstrap 5)
├── static/         CSS / JS / خطوط أميري
├── core/           CSRF، Rate Limiting، Logging، Exceptions
├── middleware/      Security Headers، Request Size، CSRF
├── config.py       إعدادات pydantic-settings
├── database.py     SQLAlchemy Engine + WAL mode
└── main.py         FastAPI app entry point

tests/
├── integration/    اختبارات تكاملية (21 ملف)
└── unit/           اختبارات الوحدات (4 ملفات)
```

## المتغيرات البيئية المطلوبة

| المتغير | الوصف | مطلوب |
|---------|-------|--------|
| `SECRET_KEY` | مفتاح التشفير (≥32 حرف) | نعم |
| `SESSION_SECRET` | مفتاح الجلسة (≥32 حرف) | نعم |
| `DEBUG` | وضع التطوير | اختياري (false) |

## الميزات الأمنية

- bcrypt لتشفير كلمات المرور
- CSRF protection في جميع نماذج POST
- Rate limiting (5 محاولات/دقيقة)
- Session fixation protection
- XSS protection عبر Jinja2 auto-escaping
- SQL Injection protection عبر SQLAlchemy ORM
- Security Headers: X-Frame-Options, CSP, HSTS
- Request size limit: 5MB

## توثيق المراجعة

انظر `AUDIT_REPORT.md` للتقرير الشامل (التقييم الكلي: 90.5/100).

## User Preferences

- اللغة العربية هي لغة الواجهة والكود التوثيقي
- تشغيل الاختبارات بمتغيرات البيئة الوهمية (SECRET_KEY + SESSION_SECRET)
