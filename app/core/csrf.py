"""
CSRF Protection Utilities
حماية CSRF بتوكن مخزون في الجلسة
"""
import hmac
import hashlib
import secrets
import logging
from fastapi import Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger("security")

CSRF_TOKEN_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"


def generate_csrf_token(request: Request) -> str:
    """توليد أو استرجاع توكن CSRF من الجلسة."""
    token = request.session.get(CSRF_TOKEN_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_TOKEN_KEY] = token
    return token


def validate_csrf_token(request: Request, submitted_token: str | None) -> bool:
    """التحقق من توكن CSRF بمقارنة ثابتة الزمن."""
    session_token = request.session.get(CSRF_TOKEN_KEY)
    if not session_token or not submitted_token:
        return False
    return hmac.compare_digest(session_token, submitted_token)


def get_csrf_input(request: Request) -> str:
    """إرجاع حقل hidden HTML يحتوي التوكن."""
    token = generate_csrf_token(request)
    return f'<input type="hidden" name="{CSRF_FORM_FIELD}" value="{token}">'
