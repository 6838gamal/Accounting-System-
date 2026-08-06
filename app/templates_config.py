"""
قالب موحّد مع حقن تلقائي لإعدادات النظام وتوكن CSRF في كل صفحة.
"""
from fastapi.templating import Jinja2Templates
from app.database import SessionLocal
from app.services.settings_service import SettingsService
from app.core.csrf import generate_csrf_token, get_csrf_input


class AppTemplates(Jinja2Templates):
    """نسخة مخصصة من Jinja2Templates تحقن إعدادات النظام وCSSRF تلقائياً."""

    def TemplateResponse(self, *args, **kwargs):
        # دعم كلا واجهتَي Starlette القديمة والجديدة
        # الجديدة: TemplateResponse(request, name, context, ...)
        # القديمة: TemplateResponse(name, context, ...)
        if args and hasattr(args[0], 'session'):
            # واجهة Starlette الجديدة: أول arg هو request
            request = args[0]
            context = args[2] if len(args) > 2 else kwargs.get('context', {})
        elif len(args) >= 2 and isinstance(args[1], dict):
            # واجهة قديمة: (name, context)
            request = args[1].get('request')
            context = args[1]
        else:
            # fall-through
            return super().TemplateResponse(*args, **kwargs)

        # حقن الإعدادات
        if request and "settings" not in context:
            db = SessionLocal()
            try:
                context["settings"] = SettingsService(db).get_all()
            except Exception:
                context.setdefault("settings", {})
            finally:
                db.close()

        # حقن توكن CSRF
        if request:
            try:
                context["csrf_token"] = generate_csrf_token(request)
                context["csrf_input"] = get_csrf_input(request)
            except Exception:
                context.setdefault("csrf_token", "")
                context.setdefault("csrf_input", "")

        return super().TemplateResponse(*args, **kwargs)


# نسخة واحدة مشتركة بين جميع الـ routers
templates = AppTemplates(directory="app/templates")
