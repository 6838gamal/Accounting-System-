"""
إعدادات التطبيق — آمنة للإنتاج
"""

import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ---------------------------------------------------------------------
    # إعدادات Pydantic
    # ---------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ---------------------------------------------------------------------
    # التطبيق
    # ---------------------------------------------------------------------
    APP_NAME: str = "نظام المحاسبة"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ---------------------------------------------------------------------
    # الأمان
    # ---------------------------------------------------------------------
    # يجب توفيرهما من متغيرات البيئة
    SECRET_KEY: str = Field(..., validation_alias="SECRET_KEY")
    SESSION_SECRET: str = Field(..., validation_alias="SESSION_SECRET")

    SESSION_MAX_AGE: int = 60 * 60 * 8  # 8 ساعات

    @property
    def effective_session_key(self) -> str:
        """
        المفتاح المستخدم لتوقيع جلسات المستخدم.
        """
        if len(self.SESSION_SECRET) < 32:
            raise RuntimeError(
                "SESSION_SECRET يجب أن يكون بطول 32 حرفًا على الأقل."
            )

        return self.SESSION_SECRET

    # ---------------------------------------------------------------------
    # قاعدة البيانات
    # ---------------------------------------------------------------------
    DATABASE_URL_OVERRIDE: str = ""
    SQLITE_URL: str = f"sqlite:///{BASE_DIR / 'accounting.db'}"

    @property
    def effective_db_url(self) -> str:
        return self.DATABASE_URL_OVERRIDE or self.SQLITE_URL

    # ---------------------------------------------------------------------
    # الرفع
    # ---------------------------------------------------------------------
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5 MB

    # ---------------------------------------------------------------------
    # الترقيم الافتراضي
    # ---------------------------------------------------------------------
    INVOICE_PREFIX: str = "INV"
    QUOTE_PREFIX: str = "QT"
    CONTRACT_PREFIX: str = "CNT"


settings = Settings()
