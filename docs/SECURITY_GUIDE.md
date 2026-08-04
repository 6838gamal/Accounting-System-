# دليل الأمان

## المصادقة
- تشفير كلمات المرور باستخدام bcrypt
- انتهاء صلاحية الجلسة بعد 8 ساعات من عدم النشاط
- تأمين ضد Brute Force (تحديد محاولات الدخول)

## حماية النماذج
- CSRF token في جميع نماذج POST
- التحقق من المدخلات (Pydantic schemas)
- Sanitization لمنع XSS

## قاعدة البيانات
- Parameterized queries (عبر SQLAlchemy ORM)
- لا SQL injection ممكن
- نسخ احتياطي منتظم

## الملفات المرفوعة
- التحقق من نوع الملف (MIME type)
- حد أقصى لحجم الملف (10MB)
- حفظ خارج مجلد static العام

## الصلاحيات
- التحقق من الدور في كل endpoint
- مبدأ أقل الصلاحيات (Principle of Least Privilege)

## الإعدادات الآمنة
- SECRET_KEY قوي ومعقد
- DEBUG=False في الإنتاج
- HTTPS إلزامي في الإنتاج
