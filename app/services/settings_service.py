"""
خدمة إعدادات النظام
"""
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models.settings import AppSetting

DEFAULT_SETTINGS = {
    "company_name": ("اسم الشركة", "اسم الشركة أو المؤسسة"),
    "company_address": ("", "عنوان الشركة"),
    "company_phone": ("", "رقم هاتف الشركة"),
    "company_email": ("", "البريد الإلكتروني للشركة"),
    "company_tax_number": ("", "الرقم الضريبي للشركة"),
    "default_tax_rate": ("15", "نسبة الضريبة الافتراضية (%)"),
    "currency": ("SAR", "رمز العملة"),
    "currency_name": ("ريال سعودي", "اسم العملة"),
    "invoice_prefix": ("INV", "بادئة رقم الفاتورة"),
    "quote_prefix": ("QT", "بادئة رقم عرض السعر"),
    "contract_prefix": ("CNT", "بادئة رقم العقد"),
    "invoice_notes": ("", "ملاحظات افتراضية للفواتير"),
    # هوية المؤسسة في الوثائق
    "company_logo": ("", "شعار الشركة (base64)"),
    "pdf_primary_color": ("#2563eb", "لون العلامة التجارية في الوثائق"),
    "pdf_footer_text": ("", "نص التذييل في الوثائق"),
    "pdf_signatory_title": ("المدير العام", "لقب الموقِّع الأول"),
}


class SettingsService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> Dict[str, str]:
        """الحصول على جميع الإعدادات"""
        settings = self.db.query(AppSetting).all()
        result = {k: v[0] for k, v in DEFAULT_SETTINGS.items()}
        for s in settings:
            result[s.key] = s.value or ""
        return result

    def get(self, key: str, default: str = "") -> str:
        setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        return setting.value if setting else DEFAULT_SETTINGS.get(key, ("",))[0] or default

    def set(self, key: str, value: str) -> AppSetting:
        setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            desc = DEFAULT_SETTINGS.get(key, ("", ""))[1]
            setting = AppSetting(key=key, value=value, description=desc)
            self.db.add(setting)
        self.db.commit()
        return setting

    def save_all(self, data: dict) -> None:
        for key, value in data.items():
            if key in DEFAULT_SETTINGS:
                self.set(key, value)

    def init_defaults(self) -> None:
        """تهيئة الإعدادات الافتراضية"""
        for key, (default_value, description) in DEFAULT_SETTINGS.items():
            existing = self.db.query(AppSetting).filter(AppSetting.key == key).first()
            if not existing:
                self.db.add(AppSetting(key=key, value=default_value, description=description))
        self.db.commit()
