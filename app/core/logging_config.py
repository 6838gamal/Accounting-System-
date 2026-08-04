"""
إعداد نظام التسجيل الهيكلي (Structured Logging)
يستخدم ContextVar لنقل request_id عبر الطلبات بأمان.
"""
import logging
import logging.handlers
import sys
from contextvars import ContextVar
from pathlib import Path

# ─── Request-ID ContextVar ─────────────────────────────────────────────────
# يُضبط في middleware ويُقرأ تلقائياً في كل سجل
_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)


def get_request_id() -> str:
    return _request_id_var.get()


# ─── Filter يحقن request_id تلقائياً ──────────────────────────────────────

class RequestIdFilter(logging.Filter):
    """يضيف request_id لكل LogRecord من الـ ContextVar."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


# ─── مسار ملفات السجلات ────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class SafeFormatter(logging.Formatter):
    """مُنسِّق يُخفي البيانات الحساسة من السجلات تلقائياً."""

    SENSITIVE = {"password", "token", "secret", "key", "authorization",
                 "passwd", "pwd", "credit_card", "card_number", "cvv"}

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.args, dict):
            record.args = {
                k: ("***" if any(s in k.lower() for s in self.SENSITIVE) else v)
                for k, v in record.args.items()
            }
        return super().format(record)


def _build_formatter() -> SafeFormatter:
    fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)s | "
        "req_id=%(request_id)s | %(message)s"
    )
    return SafeFormatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S")


def setup_logging(debug: bool = False) -> None:
    """تهيئة نظام التسجيل — يُستدعى مرة واحدة عند بدء التطبيق."""
    level = logging.DEBUG if debug else logging.INFO
    formatter = _build_formatter()
    req_filter = RequestIdFilter()

    # ─── Console Handler ──────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.addFilter(req_filter)
    console.setLevel(level)

    # ─── Rotating File Handler (app.log) ──────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(req_filter)
    file_handler.setLevel(level)

    # ─── Security Log ─────────────────────────────────────────────────────
    security_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "security.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    security_handler.setFormatter(formatter)
    security_handler.addFilter(req_filter)
    security_handler.setLevel(logging.WARNING)

    # ─── Root Logger ──────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    # ─── Security Logger ──────────────────────────────────────────────────
    sec_logger = logging.getLogger("security")
    sec_logger.addHandler(security_handler)
    sec_logger.propagate = True

    # تخفيت SQLAlchemy في الإنتاج
    if not debug:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logging.info("Logging initialized | level=%s", logging.getLevelName(level))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
