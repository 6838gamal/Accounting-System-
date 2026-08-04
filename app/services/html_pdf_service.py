"""
خدمة توليد PDF من قوالب Jinja2 HTML
——————————————————————————————————————
كيفية العمل:
  1. يُقرأ قالب HTML من app/templates/pdf/<name>.html
  2. يُعرض بـ Jinja2 مع بيانات الوثيقة وإعدادات الشركة
  3. يُحوَّل الناتج إلى PDF بـ xhtml2pdf

لتغيير تخطيط أي وثيقة: عدِّل الملف المقابل في app/templates/pdf/
لتغيير الأنماط المشتركة: عدِّل app/templates/pdf/_styles.html
للتخصيص السريع عبر الإعدادات: استخدم حقل "CSS مخصص"
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from xhtml2pdf import pisa
from jinja2 import Environment, FileSystemLoader, select_autoescape

# مسار مجلد قوالب PDF
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_FONTS_PATH    = Path(__file__).parent.parent / "static" / "fonts"

# بيئة Jinja2 مخصصة لقوالب PDF (مستقلة عن بيئة FastAPI)
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _lighten_hex(hex_color: str, factor: float = 0.92) -> str:
    """تفتيح لون hex للخلفيات الفاتحة"""
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r2 = min(255, int(r + (255 - r) * factor))
        g2 = min(255, int(g + (255 - g) * factor))
        b2 = min(255, int(b + (255 - b) * factor))
        return f"#{r2:02x}{g2:02x}{b2:02x}"
    except Exception:
        return "#eff6ff"


def _render_html(template_name: str, context: dict) -> str:
    """تصيير قالب Jinja2 HTML"""
    tmpl = _env.get_template(f"pdf/{template_name}")
    return tmpl.render(**context)


def _html_to_pdf(html: str) -> bytes:
    """تحويل HTML إلى PDF باستخدام xhtml2pdf"""
    buf = BytesIO()
    result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"خطأ في توليد PDF: {result.err}")
    buf.seek(0)
    return buf.read()


def _base_context(settings: dict) -> dict:
    """السياق المشترك لجميع القوالب"""
    primary = settings.get("pdf_primary_color", "#2563eb")
    return {
        "settings":        settings,
        "primary_color":   primary,
        "primary_light":   _lighten_hex(primary, 0.92),
        "currency":        settings.get("currency", "SAR"),
        "fonts_path":      str(_FONTS_PATH.resolve()),
        "custom_css":      settings.get("pdf_custom_css", ""),
        "watermark":       settings.get("pdf_watermark", ""),
        "show_signatures": settings.get("pdf_show_signatures", "1") == "1",
    }


# ─── واجهات عامة ─────────────────────────────────────────────────────────────

def generate_invoice_pdf(invoice, company_settings: dict) -> bytes:
    ctx = _base_context(company_settings)
    ctx["invoice"] = invoice
    html = _render_html("invoice.html", ctx)
    return _html_to_pdf(html)


def generate_contract_pdf(contract, company_settings: dict) -> bytes:
    ctx = _base_context(company_settings)
    ctx["contract"] = contract
    html = _render_html("contract.html", ctx)
    return _html_to_pdf(html)


def generate_quotation_pdf(quotation, company_settings: dict) -> bytes:
    ctx = _base_context(company_settings)
    ctx["quotation"] = quotation
    html = _render_html("quotation.html", ctx)
    return _html_to_pdf(html)
