"""
إعدادات التطبيق — آمنة للإنتاج
"""
import secrets
import logging
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
logger = logging.getLogger(__name__)

# المفتاح الافتراضي الضعيف (للكشف فقط)
_WEAK_KEY = "change-this-in-production-to-a-long-random-string"


class Settings(BaseSettings):
    # ─── التطبيق ──────────────────────────────────────────────────────────
    APP_NAME: str = "نظام المحاسبة"
    APP_VERSION: str = "1.0.0"
    # DEBUG=False في الإنتاج دائماً — القيمة الافتراضية هنا False
    DEBUG: bool = False

    # ─── الأمان ───────────────────────────────────────────────────────────
    SECRET_KEY: str = _WEAK_KEY
    # SESSION_SECRET يُقرأ من متغير البيئة SESSION_SECRET
    SESSION_SECRET: str = ""
    SESSION_MAX_AGE: int = 60 * 60 * 8  # 8 ساعات

    # ─── قاعدة البيانات ───────────────────────────────────────────────────
    DATABASE_URL_OVERRIDE: str = ""
    SQLITE_URL: str = f"sqlite:///{BASE_DIR}/accounting.db"

    @property
    def effective_db_url(self) -> str:
        return self.DATABASE_URL_OVERRIDE or self.SQLITE_URL

    # ─── الرفع ────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024   # 5 MB (تقليل من 10)

    # ─── الترقيم الافتراضي ────────────────────────────────────────────────
    INVOICE_PREFIX: str = "INV"
    QUOTE_PREFIX: str = "QT"
    CONTRACT_PREFIX: str = "CNT"

    @property
    def effective_session_key(self) -> str:
        """المفتاح الفعلي للجلسات — SESSION_SECRET يُقدَّم على SECRET_KEY."""
        key = self.SESSION_SECRET or self.SECRET_KEY
        if key == _WEAK_KEY or len(key) < 32:
            if self.DEBUG:
                # في التطوير نولّد مفتاحاً مؤقتاً ونحذّر
                logger.warning(
                    "⚠️  SECRET_KEY ضعيف أو افتراضي — استخدم مفتاحاً عشوائياً قوياً في الإنتاج. "
                    "أنشئه بـ: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
                return key  # نقبل في التطوير
            else:
                # في الإنتاج نرفض المفاتيح الضعيفة تماماً
                raise RuntimeError(
                    "SECRET_KEY ضعيف أو افتراضي — يُمنع تشغيل التطبيق في الإنتاج بمفتاح غير آمن. "
                    "عيّن SESSION_SECRET في متغيرات البيئة."
                )
        return key

    class Config:
        env_file = ".env"


settings = Settings()
