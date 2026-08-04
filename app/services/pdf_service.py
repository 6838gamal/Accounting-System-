"""
خدمة إنشاء ملفات PDF
"""
from io import BytesIO
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def _build_invoice_pdf(invoice, company_settings: dict) -> bytes:
    """بناء PDF للفاتورة"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    elements = []

    # معلومات الشركة
    company_name = company_settings.get("company_name", "اسم الشركة")
    header_data = [
        [company_name, f"فاتورة رقم: {invoice.invoice_number}"],
        [company_settings.get("company_address", ""), f"التاريخ: {invoice.issue_date}"],
        [company_settings.get("company_phone", ""), f"تاريخ الاستحقاق: {invoice.due_date or '-'}"],
    ]
    header_table = Table(header_data, colWidths=[10 * cm, 8 * cm])
    header_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#2563eb")),
        ("FONTSIZE", (1, 0), (1, 0), 14),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5 * cm))

    # معلومات العميل
    client_info = f"العميل: {invoice.client.name}\n"
    if invoice.client.email:
        client_info += f"البريد: {invoice.client.email}\n"
    if invoice.client.phone:
        client_info += f"الهاتف: {invoice.client.phone}"
    elements.append(Paragraph(client_info, normal))
    elements.append(Spacer(1, 0.5 * cm))

    # بنود الفاتورة
    items_data = [["الوصف", "الكمية", "سعر الوحدة", "الإجمالي"]]
    for item in invoice.items:
        items_data.append([
            str(item.description),
            str(item.quantity),
            f"{float(item.unit_price):,.2f}",
            f"{float(item.total):,.2f}",
        ])

    items_table = Table(items_data, colWidths=[9 * cm, 2 * cm, 3 * cm, 3 * cm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.3 * cm))

    # الملخص
    summary_data = [
        ["المجموع الفرعي:", f"{float(invoice.subtotal):,.2f}"],
        [f"الضريبة ({invoice.tax_rate}%):", f"{float(invoice.tax_amount):,.2f}"],
        ["الخصم:", f"{float(invoice.discount):,.2f}"],
        ["الإجمالي:", f"{float(invoice.total):,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[13 * cm, 4 * cm])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eff6ff")),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#2563eb")),
    ]))
    elements.append(summary_table)

    if invoice.notes:
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph(f"ملاحظات: {invoice.notes}", normal))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def generate_invoice_pdf(invoice, company_settings: dict) -> bytes:
    """إنشاء PDF للفاتورة"""
    return _build_invoice_pdf(invoice, company_settings)
