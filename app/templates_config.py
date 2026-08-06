"""
قالب موحّد مع حقن تلقائي لإعدادات النظام في كل صفحة.
بدلاً من أن يمرر كل router الإعدادات يدوياً، يتولى هذا الملف
استرجاعها وإضافتها لسياق القالب تلقائياً.
"""
from fastapi.templating import Jinja2Templates
from app.database import SessionLocal
from app.services.settings_service import SettingsService


class AppTemplates(Jinja2Templates):
    """نسخة مخصصة من Jinja2Templates تحقن إعدادات النظام تلقائياً."""

    def TemplateResponse(self, name, context, status_code=200, headers=None,
                         media_type=None, background=None):
        # إذا لم يُمرَّر settings من الـ router، نجلبها من قاعدة البيانات
        if "settings" not in context:
            db = SessionLocal()
            try:
                context["settings"] = SettingsService(db).get_all()
            except Exception:
                context.setdefault("settings", {})
            finally:
                db.close()
        return super().TemplateResponse(
            name, context,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )


# نسخة واحدة مشتركة بين جميع الـ routers
templates = AppTemplates(directory="app/templates")
