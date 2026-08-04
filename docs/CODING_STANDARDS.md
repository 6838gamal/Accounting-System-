# معايير الكود

## Python
- PEP 8 لأسلوب الكود
- Type hints إلزامية لجميع الدوال
- Docstrings لجميع الكلاسات والدوال
- حد أقصى 100 حرف في السطر

## تسمية المتغيرات
- المتغيرات والدوال: snake_case
- الكلاسات: PascalCase
- الثوابت: UPPER_SNAKE_CASE
- الملفات: snake_case.py

## هيكل الـ Router
```python
@router.get("/", response_class=HTMLResponse)
async def list_items(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
```

## هيكل الـ Service
```python
class ClientService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Client]:
        return self.db.query(Client).offset(skip).limit(limit).all()
```

## قواعد عامة
- لا تكرار (DRY)
- وظيفة واحدة لكل دالة (SRP)
- لا magic numbers — استخدم ثوابت أو Enum
- معالجة الأخطاء في كل مكان
- سجل العمليات (logging) للأحداث المهمة
