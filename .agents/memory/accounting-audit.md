---
name: Accounting System Audit
description: ملاحظات دائمة عن مشروع نظام المحاسبة السحابي بعد المراجعة الشاملة
---

# نظام المحاسبة السحابي — ملاحظات المراجعة

**Why:** مشروع حكومي يحتاج مراجعة كاملة قبل الإنتاج.

## نتائج الاختبارات
- 282 اختبار — 100% ناجح
- تشغيل الاختبارات يتطلب: `SECRET_KEY=... SESSION_SECRET=... python -m pytest tests/`

## إصلاحات مُطبَّقة
- `init_db()` في `app/database.py` كان يُغفل استيراد expense_voucher و receipt_voucher — أُصلح
- `import logging` كان في منتصف `app/routers/reports.py` — نُقل للأعلى
- إضافة email regex validation في `app/routers/clients.py`

## قرارات تصميمية مهمة
- `lazy="dynamic"` مُبقَّى في جميع النماذج — القوالب تستخدم `.limit()/.filter()` على العلاقات؛ تغييره لـ `lazy="select"` يكسر الواجهة
- Rate Limiter in-memory — مقبول للـ single-instance؛ يحتاج Redis للنشر الموزع
- expense_voucher/receipt_voucher detail يُعيد 302 (redirect) عند عدم وجود السند — هذا تصميم الراوتر

**How to apply:** راجع هذه الملاحظات عند إجراء أي تغيير على النماذج أو إضافة جداول جديدة.
