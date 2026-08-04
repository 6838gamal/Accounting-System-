# تصميم قاعدة البيانات

## الجداول الرئيسية

### users — المستخدمون
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| username | VARCHAR(50) UNIQUE | اسم المستخدم |
| email | VARCHAR(100) UNIQUE | البريد الإلكتروني |
| password_hash | VARCHAR(255) | كلمة المرور مشفرة |
| full_name | VARCHAR(100) | الاسم الكامل |
| role | ENUM | admin/manager/accountant/viewer |
| is_active | BOOLEAN | نشط/معطل |
| created_at | DATETIME | تاريخ الإنشاء |
| last_login | DATETIME | آخر دخول |

### clients — العملاء
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| name | VARCHAR(150) | الاسم |
| type | ENUM | company/individual |
| email | VARCHAR(100) | البريد |
| phone | VARCHAR(20) | الهاتف |
| address | TEXT | العنوان |
| tax_number | VARCHAR(50) | الرقم الضريبي |
| notes | TEXT | ملاحظات |
| is_active | BOOLEAN | نشط |
| created_at | DATETIME | تاريخ الإنشاء |
| created_by | FK(users) | من أنشأه |

### contracts — العقود
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| contract_number | VARCHAR(50) UNIQUE | رقم العقد |
| client_id | FK(clients) | العميل |
| title | VARCHAR(200) | عنوان العقد |
| description | TEXT | الوصف |
| amount | DECIMAL(15,2) | قيمة العقد |
| start_date | DATE | تاريخ البداية |
| end_date | DATE | تاريخ النهاية |
| status | ENUM | draft/active/expired/cancelled |
| created_at | DATETIME | تاريخ الإنشاء |
| created_by | FK(users) | من أنشأه |

### quotations — عروض الأسعار
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| quote_number | VARCHAR(50) UNIQUE | رقم العرض |
| client_id | FK(clients) | العميل |
| title | VARCHAR(200) | العنوان |
| subtotal | DECIMAL(15,2) | المجموع الفرعي |
| tax_rate | DECIMAL(5,2) | نسبة الضريبة |
| tax_amount | DECIMAL(15,2) | قيمة الضريبة |
| discount | DECIMAL(15,2) | الخصم |
| total | DECIMAL(15,2) | الإجمالي |
| status | ENUM | draft/sent/accepted/rejected/expired |
| valid_until | DATE | صالح حتى |
| notes | TEXT | ملاحظات |
| created_at | DATETIME | تاريخ الإنشاء |

### quotation_items — بنود عروض الأسعار
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| quotation_id | FK(quotations) | العرض |
| description | TEXT | الوصف |
| quantity | DECIMAL(10,2) | الكمية |
| unit_price | DECIMAL(15,2) | سعر الوحدة |
| total | DECIMAL(15,2) | الإجمالي |
| sort_order | INTEGER | الترتيب |

### invoices — الفواتير
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| invoice_number | VARCHAR(50) UNIQUE | رقم الفاتورة |
| client_id | FK(clients) | العميل |
| contract_id | FK(contracts) NULL | العقد (اختياري) |
| quotation_id | FK(quotations) NULL | العرض (اختياري) |
| issue_date | DATE | تاريخ الإصدار |
| due_date | DATE | تاريخ الاستحقاق |
| subtotal | DECIMAL(15,2) | المجموع الفرعي |
| tax_rate | DECIMAL(5,2) | نسبة الضريبة |
| tax_amount | DECIMAL(15,2) | قيمة الضريبة |
| discount | DECIMAL(15,2) | الخصم |
| total | DECIMAL(15,2) | الإجمالي |
| paid_amount | DECIMAL(15,2) | المدفوع |
| status | ENUM | draft/sent/partial/paid/overdue/cancelled |
| notes | TEXT | ملاحظات |
| created_at | DATETIME | تاريخ الإنشاء |

### invoice_items — بنود الفواتير
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| invoice_id | FK(invoices) | الفاتورة |
| description | TEXT | الوصف |
| quantity | DECIMAL(10,2) | الكمية |
| unit_price | DECIMAL(15,2) | سعر الوحدة |
| total | DECIMAL(15,2) | الإجمالي |
| sort_order | INTEGER | الترتيب |

### payments — المدفوعات
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| invoice_id | FK(invoices) | الفاتورة |
| client_id | FK(clients) | العميل |
| amount | DECIMAL(15,2) | المبلغ |
| payment_date | DATE | تاريخ الدفع |
| method | ENUM | cash/bank_transfer/check/card |
| reference | VARCHAR(100) | رقم مرجعي |
| notes | TEXT | ملاحظات |
| created_at | DATETIME | تاريخ الإنشاء |
| created_by | FK(users) | من سجله |

### expenses — المصروفات
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| title | VARCHAR(200) | العنوان |
| category | VARCHAR(100) | الفئة |
| amount | DECIMAL(15,2) | المبلغ |
| expense_date | DATE | التاريخ |
| description | TEXT | الوصف |
| receipt_path | VARCHAR(255) | مسار الإيصال |
| status | ENUM | pending/approved/rejected |
| created_at | DATETIME | تاريخ الإنشاء |
| created_by | FK(users) | من أنشأه |

### activity_logs — سجل العمليات
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| user_id | FK(users) | المستخدم |
| action | VARCHAR(50) | الإجراء |
| module | VARCHAR(50) | الوحدة |
| record_id | INTEGER | معرف السجل |
| details | TEXT | تفاصيل JSON |
| ip_address | VARCHAR(45) | عنوان IP |
| created_at | DATETIME | الوقت |

### app_settings — إعدادات النظام
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER PK | المعرف |
| key | VARCHAR(100) UNIQUE | المفتاح |
| value | TEXT | القيمة |
| description | VARCHAR(255) | الوصف |
