"""
Rate Limiter — حماية من Brute Force وFlood.
استخدام: Sliding Window Counter مخزّن في الذاكرة (مناسب لخادم واحد).
"""
import time
import threading
import logging
from collections import defaultdict

sec_logger = logging.getLogger("security")


class RateLimiter:
    """
    Sliding Window Rate Limiter thread-safe.
    يتتبع الطلبات بمفتاح (IP + endpoint) خلال نافذة زمنية.
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """إرجاع True إذا كان الطلب مسموحاً، False إذا تجاوز الحد."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._store[key]
            # إزالة الطوابع القديمة
            self._store[key] = [t for t in timestamps if t > cutoff]
            if len(self._store[key]) >= self.max_requests:
                return False
            self._store[key].append(now)
            return True

    def remaining(self, key: str) -> int:
        """عدد الطلبات المتبقية المسموحة."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            active = [t for t in self._store.get(key, []) if t > cutoff]
            return max(0, self.max_requests - len(active))

    def cleanup(self) -> None:
        """تنظيف المفاتيح المنتهية — استدعاؤها دورياً اختياري."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            expired = [k for k, ts in self._store.items() if not any(t > cutoff for t in ts)]
            for k in expired:
                del self._store[k]


# ─── Instances عامة ─────────────────────────────────────────────────────────

# حد تسجيل الدخول: 5 محاولات خلال 5 دقائق لكل IP
login_limiter = RateLimiter(max_requests=5, window_seconds=300)

# حد عام للصفحات: 120 طلب / دقيقة لكل IP
general_limiter = RateLimiter(max_requests=120, window_seconds=60)


def get_client_ip(request) -> str:
    """استخراج IP العميل مع دعم Reverse Proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_login_rate_limit(request) -> bool:
    """
    التحقق من حد تسجيل الدخول.
    يُسجّل في security.log عند الحظر.
    """
    ip = get_client_ip(request)
    key = f"login:{ip}"
    allowed = login_limiter.is_allowed(key)
    if not allowed:
        sec_logger.warning(
            "Rate limit exceeded on login | ip=%s | key=%s",
            ip, key,
        )
    return allowed
