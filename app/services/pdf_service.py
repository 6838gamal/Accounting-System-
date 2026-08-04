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


def generate_contract_pdf(contract, company_settings: dict) -> bytes:
    """إنشاء PDF للعقد"""
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

    # ترويسة الشركة والعقد
    company_name = company_settings.get("company_name", "اسم الشركة")
    header_data = [
        [company_name, f"عقد رقم: {contract.contract_number}"],
        [company_settings.get("company_address", ""), f"تاريخ الإنشاء: {contract.created_at.strftime('%Y-%m-%d')}"],
        [company_settings.get("company_phone", ""), ""],
    ]
    header_table = Table(header_data, colWidths=[10 * cm, 8 * cm])
    header_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#2563eb")),
        ("FONTSIZE", (1, 0), (1, 0), 14),
        ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5 * cm))

    # عنوان العقد
    title_style = ParagraphStyle(
        "ContractTitle",
        parent=styles["Normal"],
        fontSize=14,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    elements.append(Paragraph(contract.title, title_style))
    elements.append(Spacer(1, 0.3 * cm))

    # معلومات أطراف العقد
    status_labels = {"draft": "مسودة", "active": "نشط", "expired": "منتهي", "cancelled": "ملغي"}
    status_label = status_labels.get(contract.status.value, contract.status.value)

    details_data = [
        ["طرف العقد (العميل)", contract.client.name if contract.client else "-"],
        ["قيمة العقد", f"{float(contract.amount):,.2f} {company_settings.get('currency', 'SAR')}"],
        ["تاريخ البداية", str(contract.start_date) if contract.start_date else "-"],
        ["تاريخ النهاية", str(contract.end_date) if contract.end_date else "-"],
        ["الحالة", status_label],
    ]
    details_table = Table(details_data, colWidths=[5 * cm, 13 * cm])
    details_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 0.5 * cm))

    # الوصف
    if contract.description:
        desc_style = ParagraphStyle("SectionHeader", parent=styles["Normal"],
                                    fontSize=11, fontName="Helvetica-Bold", spaceAfter=4)
        elements.append(Paragraph("الوصف:", desc_style))
        elements.append(Paragraph(contract.description, normal))
        elements.append(Spacer(1, 0.4 * cm))

    # الملاحظات
    if contract.notes:
        notes_style = ParagraphStyle("SectionHeader2", parent=styles["Normal"],
                                     fontSize=11, fontName="Helvetica-Bold", spaceAfter=4)
        elements.append(Paragraph("ملاحظات:", notes_style))
        elements.append(Paragraph(contract.notes, normal))
        elements.append(Spacer(1, 0.4 * cm))

    # مساحة التوقيعات
    elements.append(Spacer(1, 1.5 * cm))
    sig_data = [
        ["توقيع الطرف الأول", "توقيع الطرف الثاني (العميل)"],
        ["\n\n________________________", "\n\n________________________"],
        [company_name, contract.client.name if contract.client else ""],
    ]
    sig_table = Table(sig_data, colWidths=[9 * cm, 9 * cm])
    sig_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def generate_quotation_pdf(quotation, company_settings: dict) -> bytes:
    """إنشاء PDF لعرض السعر"""
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

    # ترويسة الشركة والعرض
    company_name = company_settings.get("company_name", "اسم الشركة")
    header_data = [
        [company_name, f"عرض سعر رقم: {quotation.quote_number}"],
        [company_settings.get("company_address", ""), f"تاريخ الإنشاء: {quotation.created_at.strftime('%Y-%m-%d')}"],
        [company_settings.get("company_phone", ""), f"صالح حتى: {quotation.valid_until or '-'}"],
    ]
    header_table = Table(header_data, colWidths=[10 * cm, 8 * cm])
    header_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#2563eb")),
        ("FONTSIZE", (1, 0), (1, 0), 14),
        ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5 * cm))

    # معلومات العميل
    client_info = f"مقدم إلى: {quotation.client.name if quotation.client else '-'}"
    if quotation.client and quotation.client.email:
        client_info += f"\nالبريد: {quotation.client.email}"
    if quotation.client and quotation.client.phone:
        client_info += f"\nالهاتف: {quotation.client.phone}"
    elements.append(Paragraph(client_info, normal))
    elements.append(Spacer(1, 0.3 * cm))

    # عنوان العرض
    title_style = ParagraphStyle(
        "QuoteTitle",
        parent=styles["Normal"],
        fontSize=12,
        fontName="Helvetica-Bold",
        spaceAfter=6,
    )
    elements.append(Paragraph(f"الموضوع: {quotation.title}", title_style))
    elements.append(Spacer(1, 0.3 * cm))

    # بنود العرض
    items_data = [["الوصف", "الكمية", "سعر الوحدة", "الإجمالي"]]
    for item in quotation.items:
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

    # الملخص المالي
    currency = company_settings.get("currency", "SAR")
    summary_data = [
        ["المجموع الفرعي:", f"{float(quotation.subtotal):,.2f} {currency}"],
        [f"الضريبة ({quotation.tax_rate}%):", f"{float(quotation.tax_amount):,.2f} {currency}"],
        ["الخصم:", f"{float(quotation.discount):,.2f} {currency}"],
        ["الإجمالي:", f"{float(quotation.total):,.2f} {currency}"],
    ]
    summary_table = Table(summary_data, colWidths=[13 * cm, 4 * cm])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eff6ff")),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#2563eb")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(summary_table)

    if quotation.notes:
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph(f"ملاحظات: {quotation.notes}", normal))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
