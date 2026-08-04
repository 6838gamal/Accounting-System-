FROM python:3.12-slim

# تثبيت المتطلبات الأساسية للنظام
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملف المتطلبات أولاً للاستفادة من cache الطبقات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ بقية الكود
COPY . .

# إنشاء المجلدات الضرورية
RUN mkdir -p uploads

# المنفذ الافتراضي
EXPOSE 8000

# متغيرات البيئة الافتراضية (قابلة للتجاوز)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# تشغيل التطبيق
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
