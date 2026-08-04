# دليل الاختبارات

## هيكل الاختبارات

```
tests/
├── conftest.py          # إعداد مشترك
├── unit/
│   ├── test_services.py
│   ├── test_models.py
│   └── test_schemas.py
└── integration/
    ├── test_auth.py
    ├── test_clients.py
    ├── test_invoices.py
    └── test_reports.py
```

## تشغيل الاختبارات

```bash
# جميع الاختبارات
pytest

# مع التغطية
pytest --cov=app --cov-report=html

# وحدة محددة
pytest tests/unit/test_services.py -v
```

## معايير النجاح
- تغطية الكود: 80%+
- جميع الاختبارات تعمل قبل كل deployment
- اختبار كل endpoint رئيسي
