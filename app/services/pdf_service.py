"""
خدمة إنشاء ملفات PDF بدعم كامل للغة العربية
"""
import base64
import re
from io import BytesIO
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─── تسجيل خطوط أميري العربية ───────────────────────────────────────────────
_FONTS_DIR = Path(__file__).parent.parent / "static" / "fonts"

def _register_fonts():
    try:
        pdfmetrics.registerFont(TTFont("Amiri", str(_FONTS_DIR / "Amiri-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Amiri-Bold", str(_FONTS_DIR / "Amiri-Bold.ttf")))
    except Exception:
        pass  # سيستخدم Helvetica كبديل إن لم يوجد الخط

_register_fonts()

# ─── دوال مساعدة ────────────────────────────────────────────────────────────

def ar(text: str) -> str:
    """إعادة تشكيل النص العربي وتحويله لعرض صحيح في PDF"""
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


def _hex_to_color(hex_str: str):
    """تحويل لون hex إلى كائن Color لـ ReportLab"""
    try:
        hex_str = hex_str.strip().lstrip("#")
        if len(hex_str) == 3:
            hex_str = "".join(c * 2 for c in hex_str)
        r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
        return colors.Color(r / 255, g / 255, b / 255)
    except Exception:
        return colors.HexColor("#2563eb")


def _lighten(color, factor=0.9):
    """تفتيح اللون للخلفيات"""
    return colors.Color(
        min(1.0, color.red + (1 - color.red) * factor),
        min(1.0, color.green + (1 - color.green) * factor),
        min(1.0, color.blue + (1 - color.blue) * factor),
    )


def _get_logo_image(settings: dict, width_cm=3.5) -> Image | None:
    """تحميل شعار الشركة من الإعدادات"""
    logo_b64 = settings.get("company_logo", "")
    if not logo_b64:
        return None
    try:
        # إزالة رأس data URL إن وُجد
        if "," in logo_b64:
            logo_b64 = logo_b64.split(",", 1)[1]
        data = base64.b64decode(logo_b64)
        buf = BytesIO(data)
        img = Image(buf, width=width_cm * cm)
        img.hAlign = "RIGHT"
        return img
    except Exception:
        return None


def _styles(primary_color):
    """مجموعة الأنماط المشتركة"""
    font = "Amiri"
    bold = "Amiri-Bold"
    return {
        "font": font,
        "bold": bold,
        "primary": primary_color,
        "light_bg": _lighten(primary_color, 0.92),
        "very_light": _lighten(primary_color, 0.97),
        "text": colors.HexColor("#1e293b"),
        "muted": colors.HexColor("#64748b"),
        "border": colors.HexColor("#e2e8f0"),
        "white": colors.white,
    }


# ─── قالب مشترك: إنشاء المستند ───────────────────────────────────────────────

def _make_doc(buffer):
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )


def _para(text, font="Amiri", size=10, align=TA_RIGHT, color=None, leading=None):
    style = ParagraphStyle(
        "p",
        fontName=font,
        fontSize=size,
        alignment=align,
        textColor=color or colors.HexColor("#1e293b"),
        leading=leading or (size * 1.6),
        wordWrap="RTL",
    )
    return Paragraph(ar(text), style)


def _bold_para(text, size=10, align=TA_RIGHT, color=None):
    return _para(text, font="Amiri-Bold", size=size, align=align, color=color)


# ─── ترويسة مشتركة (شعار + اسم الشركة + بيانات الوثيقة) ─────────────────────

def _build_header(elements, doc_type: str, doc_number: str, doc_date: str,
                  settings: dict, s: dict, extra_lines: list = None):
    """
    ترويسة الوثيقة: شعار على اليمين، معلومات الشركة في الوسط، بيانات الوثيقة على اليسار
    """
    page_width = A4[0] - 3.6 * cm  # العرض المتاح بعد الهوامش

    # عمود الشعار
    logo = _get_logo_image(settings, width_cm=3.0)
    logo_cell = logo if logo else Paragraph("", ParagraphStyle("e", fontSize=10))

    # عمود معلومات الشركة
    company_lines = [ar(settings.get("company_name", "اسم الشركة"))]
    if settings.get("company_address"):
        company_lines.append(ar(settings["company_address"]))
    if settings.get("company_phone"):
        company_lines.append(ar(f"هاتف: {settings['company_phone']}"))
    if settings.get("company_email"):
        company_lines.append(ar(settings["company_email"]))
    if settings.get("company_tax_number"):
        company_lines.append(ar(f"الرقم الضريبي: {settings['company_tax_number']}"))

    company_para = Paragraph(
        "<br/>".join(company_lines),
        ParagraphStyle("co", fontName="Amiri", fontSize=9, alignment=TA_RIGHT,
                       textColor=s["text"], leading=15, wordWrap="RTL"),
    )

    # عمود بيانات الوثيقة
    doc_lines = [
        f'<font color="#{_color_hex(s["primary"])}" size="14"><b>{ar(doc_number)}</b></font>',
        f'<font size="9" color="#64748b">{ar(doc_type)}</font>',
        f'<font size="9" color="#64748b">{ar(f"التاريخ: {doc_date}")}</font>',
    ]
    if extra_lines:
        for line in extra_lines:
            doc_lines.append(f'<font size="9" color="#64748b">{ar(line)}</font>')

    doc_para = Paragraph(
        "<br/>".join(doc_lines),
        ParagraphStyle("dp", fontName="Amiri-Bold", fontSize=11, alignment=TA_LEFT,
                       textColor=s["text"], leading=16, wordWrap="RTL"),
    )

    header_data = [[doc_para, company_para, logo_cell]]
    col_widths = [5.5 * cm, page_width - 5.5 * cm - 3.5 * cm, 3.5 * cm]

    header_table = Table(header_data, colWidths=col_widths)
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=2, color=s["primary"], spaceAfter=10))


def _color_hex(c) -> str:
    """استخراج hex من كائن Color"""
    try:
        return f"{int(c.red*255):02x}{int(c.green*255):02x}{int(c.blue*255):02x}"
    except Exception:
        return "2563eb"


# ─── قسم أطراف الوثيقة ───────────────────────────────────────────────────────

def _build_parties(elements, from_name: str, to_name: str, to_details: list,
                   settings: dict, s: dict, page_width: float):
    """مربعا الطرف الأول والطرف الثاني"""
    from_details = []
    if settings.get("company_tax_number"):
        from_details.append(ar(f"الرقم الضريبي: {settings['company_tax_number']}"))
    if settings.get("company_phone"):
        from_details.append(ar(f"هاتف: {settings['company_phone']}"))

    def party_cell(label, name, details):
        lines = [
            f'<font size="8" color="#64748b">{ar(label)}</font>',
            f'<font size="11"><b>{ar(name)}</b></font>',
        ]
        lines += [f'<font size="8.5" color="#475569">{d}</font>' for d in details]
        return Paragraph(
            "<br/>".join(lines),
            ParagraphStyle("pc", fontName="Amiri", fontSize=10, alignment=TA_RIGHT,
                           leading=15, wordWrap="RTL"),
        )

    half = (page_width - 0.4 * cm) / 2
    data = [[party_cell("الطرف الثاني (العميل)", to_name, to_details),
             party_cell("الطرف الأول", from_name, from_details)]]
    t = Table(data, colWidths=[half, half])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 0.5, s["border"]),
        ("BOX", (1, 0), (1, 0), 0.5, s["border"]),
        ("BACKGROUND", (0, 0), (-1, -1), s["very_light"]),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.4 * cm))


# ─── قسم التوقيعات ──────────────────────────────────────────────────────────

def _build_signatures(elements, party1_name: str, party1_title: str,
                      party2_name: str, s: dict, page_width: float):
    """مربعات التوقيع بتصميم واضح"""
    elements.append(Spacer(1, 1.2 * cm))

    title_style = ParagraphStyle(
        "sig_title", fontName="Amiri-Bold", fontSize=10,
        alignment=TA_CENTER, textColor=s["text"], leading=14, wordWrap="RTL",
    )
    name_style = ParagraphStyle(
        "sig_name", fontName="Amiri", fontSize=9,
        alignment=TA_CENTER, textColor=s["muted"], leading=13, wordWrap="RTL",
    )

    sig_space = Paragraph(" ", ParagraphStyle("sp", fontSize=10, leading=38))
    line = Paragraph(
        "___________________________",
        ParagraphStyle("ln", fontName="Amiri", fontSize=9,
                       alignment=TA_CENTER, textColor=s["muted"]),
    )

    half = (page_width - 0.8 * cm) / 2

    def sig_cell(title, name, job_title=""):
        inner = [
            Paragraph(ar(title), title_style),
            Spacer(1, 0.4 * cm),
            sig_space,
            line,
            Spacer(1, 0.15 * cm),
            Paragraph(ar(name), name_style),
        ]
        if job_title:
            inner.append(Paragraph(ar(job_title), name_style))
        return inner

    data = [[sig_cell("التوقيع والختم\n(الطرف الثاني - العميل)", party2_name),
             sig_cell("التوقيع والختم\n(الطرف الأول)", party1_name, party1_title)]]

    t = Table(data, colWidths=[half, half])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 1, s["border"]),
        ("BOX", (1, 0), (1, 0), 1, s["border"]),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 12),
        ("LINEBELOW", (0, 0), (0, 0), 2.5, s["primary"]),
        ("LINEBELOW", (1, 0), (1, 0), 2.5, s["primary"]),
    ]))
    elements.append(t)


# ─── تذييل الوثيقة ──────────────────────────────────────────────────────────

def _build_footer(elements, settings: dict, s: dict):
    footer_text = settings.get("pdf_footer_text", "")
    company = settings.get("company_name", "")
    phone = settings.get("company_phone", "")
    email = settings.get("company_email", "")

    parts = [p for p in [company, phone, email] if p]
    auto_footer = "  |  ".join(parts)
    text = footer_text or auto_footer
    if not text:
        return

    elements.append(Spacer(1, 0.4 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=s["border"], spaceAfter=6))
    elements.append(Paragraph(
        ar(text),
        ParagraphStyle("footer", fontName="Amiri", fontSize=8,
                       alignment=TA_CENTER, textColor=s["muted"], leading=12, wordWrap="RTL"),
    ))


# ─── جدول البنود المشترك ─────────────────────────────────────────────────────

def _build_items_table(elements, items_data: list, s: dict, page_width: float, currency: str):
    """
    بناء جدول البنود بترتيب RTL:
    الإجمالي | سعر الوحدة | الكمية | الوصف
    """
    headers = [ar("الإجمالي"), ar("سعر الوحدة"), ar("الكمية"), ar("الوصف")]
    rows = [headers]
    for item in items_data:
        rows.append([
            ar(f"{float(item['total']):,.2f}"),
            ar(f"{float(item['unit_price']):,.2f}"),
            ar(str(item["quantity"])),
            ar(str(item["description"])),
        ])

    col_widths = [3.2 * cm, 3.2 * cm, 2.0 * cm, page_width - 8.4 * cm]

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # رأس الجدول
        ("BACKGROUND", (0, 0), (-1, 0), s["primary"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), s["white"]),
        ("FONTNAME", (0, 0), (-1, 0), "Amiri-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        # بيانات الجدول
        ("FONTNAME", (0, 1), (-1, -1), "Amiri"),
        ("FONTSIZE", (0, 1), (-1, -1), 9.5),
        ("ALIGN", (0, 1), (-2, -1), "CENTER"),      # أعمدة الأرقام توسيط
        ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),      # عمود الوصف يمين
        ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        # تناوب ألوان الصفوف
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, s["very_light"]]),
        # حدود
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, s["border"]),
        ("LINEAFTER", (0, 0), (-1, -1), 0.5, s["border"]),
        ("BOX", (0, 0), (-1, -1), 1, s["border"]),
    ]))
    elements.append(t)


# ─── ملخص مالي مشترك ────────────────────────────────────────────────────────

def _build_summary(elements, subtotal, tax_rate, tax_amount, discount, total,
                   currency: str, s: dict, page_width: float):
    summary_rows = [
        [ar(f"{float(subtotal):,.2f} {currency}"), ar("المجموع الفرعي")],
        [ar(f"{float(tax_amount):,.2f} {currency}"), ar(f"الضريبة ({tax_rate}%)")],
        [ar(f"{float(discount):,.2f} {currency}"), ar("الخصم")],
        [ar(f"{float(total):,.2f} {currency}"), ar("الإجمالي")],
    ]

    val_w = 4.5 * cm
    lbl_w = 4.5 * cm
    summary_table = Table(summary_rows, colWidths=[val_w, lbl_w])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -2), "Amiri"),
        ("FONTNAME", (0, -1), (-1, -1), "Amiri-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TEXTCOLOR", (1, 0), (1, -2), s["muted"]),
        ("TEXTCOLOR", (0, -1), (-1, -1), s["primary"]),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("BACKGROUND", (0, -1), (-1, -1), s["light_bg"]),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, s["primary"]),
        ("BOX", (0, 0), (-1, -1), 0.5, s["border"]),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, s["border"]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))

    # محاذاة جدول الملخص إلى اليسار (عكس RTL = يظهر على اليمين البصري)
    wrapper_data = [["", summary_table]]
    filler_w = page_width - val_w - lbl_w
    wrapper = Table(wrapper_data, colWidths=[filler_w, val_w + lbl_w])
    wrapper.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(wrapper)


# ══════════════════════════════════════════════════════════════════════════════
#  PDF الفاتورة
# ══════════════════════════════════════════════════════════════════════════════

def generate_invoice_pdf(invoice, company_settings: dict) -> bytes:
    buffer = BytesIO()
    doc = _make_doc(buffer)
    page_width = A4[0] - 3.6 * cm
    primary = _hex_to_color(company_settings.get("pdf_primary_color", "#2563eb"))
    s = _styles(primary)
    currency = company_settings.get("currency", "SAR")
    elements = []

    # الترويسة
    _build_header(
        elements, ar("فاتورة"), ar(invoice.invoice_number),
        str(invoice.issue_date), company_settings, s,
        extra_lines=[f"تاريخ الاستحقاق: {invoice.due_date or '-'}"],
    )

    # الطرف الثاني
    client = invoice.client
    to_details = []
    if client and client.email:
        to_details.append(ar(client.email))
    if client and client.phone:
        to_details.append(ar(client.phone))

    _build_parties(elements, company_settings.get("company_name", ""), 
                   client.name if client else "-", to_details, company_settings, s, page_width)

    # حالة الفاتورة
    status_labels = {"draft": "مسودة", "sent": "مرسلة", "partial": "دفع جزئي",
                     "paid": "مدفوعة", "overdue": "متأخرة", "cancelled": "ملغاة"}
    status_text = ar(f"الحالة: {status_labels.get(invoice.status.value, invoice.status.value)}")
    elements.append(Paragraph(
        status_text,
        ParagraphStyle("st", fontName="Amiri-Bold", fontSize=9.5, alignment=TA_RIGHT,
                       textColor=s["muted"], leading=14, wordWrap="RTL"),
    ))
    elements.append(Spacer(1, 0.3 * cm))

    # بنود الفاتورة
    items_data = [
        {"description": i.description, "quantity": i.quantity,
         "unit_price": i.unit_price, "total": i.total}
        for i in invoice.items
    ]
    _build_items_table(elements, items_data, s, page_width, currency)
    elements.append(Spacer(1, 0.3 * cm))

    # الملخص المالي
    _build_summary(elements, invoice.subtotal, invoice.tax_rate, invoice.tax_amount,
                   invoice.discount, invoice.total, currency, s, page_width)

    # ملاحظات
    if invoice.notes:
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(_bold_para("ملاحظات:", size=9.5, color=s["text"]))
        elements.append(_para(invoice.notes, size=9))

    # التوقيعات
    _build_signatures(
        elements,
        company_settings.get("company_name", ""),
        company_settings.get("pdf_signatory_title", "المدير العام"),
        client.name if client else "",
        s, page_width,
    )

    _build_footer(elements, company_settings, s)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# ══════════════════════════════════════════════════════════════════════════════
#  PDF العقد
# ══════════════════════════════════════════════════════════════════════════════

def generate_contract_pdf(contract, company_settings: dict) -> bytes:
    buffer = BytesIO()
    doc = _make_doc(buffer)
    page_width = A4[0] - 3.6 * cm
    primary = _hex_to_color(company_settings.get("pdf_primary_color", "#2563eb"))
    s = _styles(primary)
    currency = company_settings.get("currency", "SAR")
    elements = []

    # الترويسة
    status_labels = {"draft": "مسودة", "active": "نشط", "expired": "منتهي", "cancelled": "ملغي"}
    _build_header(
        elements, ar("عقد"), ar(contract.contract_number),
        str(contract.created_at.strftime("%Y-%m-%d")), company_settings, s,
        extra_lines=[
            f"تاريخ البداية: {contract.start_date or '-'}",
            f"تاريخ النهاية: {contract.end_date or '-'}",
            f"الحالة: {status_labels.get(contract.status.value, contract.status.value)}",
        ],
    )

    # عنوان العقد
    elements.append(Paragraph(
        ar(contract.title),
        ParagraphStyle("ct", fontName="Amiri-Bold", fontSize=14, alignment=TA_CENTER,
                       textColor=s["text"], leading=22, wordWrap="RTL",
                       borderPad=10, backColor=s["very_light"],
                       borderColor=s["border"], borderWidth=0.5, borderRadius=4),
    ))
    elements.append(Spacer(1, 0.5 * cm))

    # أطراف العقد
    client = contract.client
    to_details = []
    if client and client.phone:
        to_details.append(ar(client.phone))
    if client and client.email:
        to_details.append(ar(client.email))

    _build_parties(elements, company_settings.get("company_name", ""),
                   client.name if client else "-", to_details, company_settings, s, page_width)

    # قيمة العقد
    amount_text = ar(f"قيمة العقد:  {float(contract.amount):,.2f} {currency}")
    elements.append(Paragraph(
        amount_text,
        ParagraphStyle("amt", fontName="Amiri-Bold", fontSize=13, alignment=TA_RIGHT,
                       textColor=primary, leading=20, wordWrap="RTL"),
    ))
    elements.append(Spacer(1, 0.4 * cm))

    # الوصف
    if contract.description:
        elements.append(HRFlowable(width="100%", thickness=0.5, color=s["border"], spaceAfter=6))
        elements.append(_bold_para("الوصف:", size=10, color=s["text"]))
        elements.append(Spacer(1, 0.1 * cm))
        elements.append(_para(contract.description, size=10))
        elements.append(Spacer(1, 0.4 * cm))

    # الملاحظات
    if contract.notes:
        elements.append(HRFlowable(width="100%", thickness=0.5, color=s["border"], spaceAfter=6))
        elements.append(_bold_para("ملاحظات:", size=10, color=s["text"]))
        elements.append(Spacer(1, 0.1 * cm))
        elements.append(_para(contract.notes, size=10))
        elements.append(Spacer(1, 0.4 * cm))

    # التوقيعات
    _build_signatures(
        elements,
        company_settings.get("company_name", ""),
        company_settings.get("pdf_signatory_title", "المدير العام"),
        client.name if client else "",
        s, page_width,
    )

    _build_footer(elements, company_settings, s)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# ══════════════════════════════════════════════════════════════════════════════
#  PDF عرض السعر
# ══════════════════════════════════════════════════════════════════════════════

def generate_quotation_pdf(quotation, company_settings: dict) -> bytes:
    buffer = BytesIO()
    doc = _make_doc(buffer)
    page_width = A4[0] - 3.6 * cm
    primary = _hex_to_color(company_settings.get("pdf_primary_color", "#2563eb"))
    s = _styles(primary)
    currency = company_settings.get("currency", "SAR")
    elements = []

    # الترويسة
    status_labels = {"draft": "مسودة", "sent": "مرسل", "accepted": "مقبول",
                     "rejected": "مرفوض", "expired": "منتهي"}
    _build_header(
        elements, ar("عرض سعر"), ar(quotation.quote_number),
        str(quotation.created_at.strftime("%Y-%m-%d")), company_settings, s,
        extra_lines=[
            f"صالح حتى: {quotation.valid_until or '-'}",
            f"الحالة: {status_labels.get(quotation.status.value, quotation.status.value)}",
        ],
    )

    # موضوع العرض
    elements.append(Paragraph(
        ar(f"الموضوع: {quotation.title}"),
        ParagraphStyle("qt", fontName="Amiri-Bold", fontSize=11, alignment=TA_RIGHT,
                       textColor=s["text"], leading=18, wordWrap="RTL",
                       borderPad=8, backColor=s["very_light"],
                       borderColor=s["border"], borderWidth=0.5, borderRadius=4),
    ))
    elements.append(Spacer(1, 0.4 * cm))

    # أطراف العرض
    client = quotation.client
    to_details = []
    if client and client.phone:
        to_details.append(ar(client.phone))
    if client and client.email:
        to_details.append(ar(client.email))

    _build_parties(elements, company_settings.get("company_name", ""),
                   client.name if client else "-", to_details, company_settings, s, page_width)

    # بنود العرض
    items_data = [
        {"description": i.description, "quantity": i.quantity,
         "unit_price": i.unit_price, "total": i.total}
        for i in quotation.items
    ]
    _build_items_table(elements, items_data, s, page_width, currency)
    elements.append(Spacer(1, 0.3 * cm))

    # الملخص المالي
    _build_summary(elements, quotation.subtotal, quotation.tax_rate, quotation.tax_amount,
                   quotation.discount, quotation.total, currency, s, page_width)

    # الملاحظات
    if quotation.notes:
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(_bold_para("ملاحظات:", size=9.5, color=s["text"]))
        elements.append(_para(quotation.notes, size=9))

    # التوقيعات
    _build_signatures(
        elements,
        company_settings.get("company_name", ""),
        company_settings.get("pdf_signatory_title", "المدير العام"),
        client.name if client else "",
        s, page_width,
    )

    _build_footer(elements, company_settings, s)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
