"""
إعدادات التطبيق
"""
from pydantic_settings import BaseSettings
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # التطبيق
    APP_NAME: str = "نظام المحاسبة"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # الأمان
    SECRET_KEY: str = "change-this-in-production-to-a-long-random-string"
    SESSION_SECRET: str = ""  # يُقرأ من متغير البيئة SESSION_SECRET إن وُجد
    SESSION_MAX_AGE: int = 60 * 60 * 8  # 8 ساعات

    # قاعدة البيانات (SQLite — مُعرَّف باسم مختلف لتجنب تعارض DATABASE_URL في البيئة)
    SQLITE_URL: str = f"sqlite:///{BASE_DIR}/accounting.db"

    # الرفع
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # الترقيم الافتراضي
    INVOICE_PREFIX: str = "INV"
    QUOTE_PREFIX: str = "QT"
    CONTRACT_PREFIX: str = "CNT"

    class Config:
        env_file = ".env"


settings = Settings()
