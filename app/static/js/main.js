/**
 * نظام المحاسبة - JavaScript الرئيسي
 */

// ===== القائمة الجانبية =====

function getSidebarOverlay() {
    let overlay = document.getElementById('sidebar-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'sidebar-overlay';
        overlay.className = 'sidebar-overlay';
        overlay.addEventListener('click', closeSidebar);
        document.body.appendChild(overlay);
    }
    return overlay;
}

function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    sidebar.classList.add('open');
    getSidebarOverlay().classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    sidebar.classList.remove('open');
    const overlay = document.getElementById('sidebar-overlay');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    if (sidebar.classList.contains('open')) {
        closeSidebar();
    } else {
        openSidebar();
    }
}

// إغلاق القائمة عند النقر على رابط داخلها (موبايل فقط)
document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.querySelectorAll('.nav-link').forEach(function (link) {
            link.addEventListener('click', function () {
                if (window.innerWidth <= 992) {
                    closeSidebar();
                }
            });
        });
    }

    // إغلاق القائمة عند ضغط Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeSidebar();
    });

    // لف الجداول داخل بطاقات بحاوية قابلة للتمرير (للشاشات الصغيرة)
    // يُطبَّق عبر CSS عبر overflow-x على .card-body مباشرة
});

// إعادة ضبط القائمة عند تكبير الشاشة
window.addEventListener('resize', function () {
    if (window.innerWidth > 992) {
        closeSidebar();
    }
});

// تنسيق الأرقام
function formatNumber(num) {
    return new Intl.NumberFormat('ar-SA', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(num);
}

// ===== نظام بنود الفاتورة / عرض الأسعار =====
let itemsData = [];

function initItems(initial = []) {
    itemsData = initial.length ? initial : [{ description: '', quantity: 1, unit_price: 0 }];
    renderItems();
}

function addItem() {
    itemsData.push({ description: '', quantity: 1, unit_price: 0 });
    renderItems();
}

function removeItem(index) {
    if (itemsData.length > 1) {
        itemsData.splice(index, 1);
        renderItems();
    }
}

function updateItem(index, field, value) {
    itemsData[index][field] = field === 'description' ? value : parseFloat(value) || 0;
    itemsData[index].total = itemsData[index].quantity * itemsData[index].unit_price;
    // تحديث خلية الإجمالي فقط لهذا البند — لا إعادة رسم كاملة حتى لا يضيع تركيز الحقل على الجوال
    const rows = document.querySelectorAll('#items-tbody tr');
    if (rows[index]) {
        const totalCell = rows[index].querySelector('.item-total');
        if (totalCell) totalCell.textContent = formatNumber(itemsData[index].total);
    }
    updateItemsJson();
}

function renderItems() {
    const tbody = document.getElementById('items-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    itemsData.forEach((item, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <input type="text" class="form-control form-control-sm"
                    value="${escapeHtml(item.description || '')}"
                    onchange="updateItem(${i}, 'description', this.value)"
                    placeholder="وصف البند" required>
            </td>
            <td style="width:90px;min-width:80px">
                <input type="number" class="form-control form-control-sm"
                    value="${item.quantity}" min="0.01" step="0.01"
                    inputmode="decimal"
                    onchange="updateItem(${i}, 'quantity', this.value)">
            </td>
            <td style="width:130px;min-width:110px">
                <input type="number" class="form-control form-control-sm"
                    value="${item.unit_price}" min="0" step="0.01"
                    inputmode="decimal"
                    onchange="updateItem(${i}, 'unit_price', this.value)">
            </td>
            <td style="width:120px;min-width:100px" class="text-end fw-semibold item-total">
                ${formatNumber((item.quantity || 0) * (item.unit_price || 0))}
            </td>
            <td style="width:46px;min-width:40px" class="text-center">
                <button type="button" class="btn btn-sm btn-outline-danger p-1"
                    onclick="removeItem(${i})">
                    <i class="bi bi-trash"></i>
                </button>
            </td>`;
        tbody.appendChild(tr);
    });
    updateItemsJson();
}

function calculateTotals() {
    const taxRateEl = document.getElementById('tax_rate');
    const discountEl = document.getElementById('discount');
    const taxRate = parseFloat(taxRateEl?.value || 0);
    const discount = parseFloat(discountEl?.value || 0);

    const subtotal = itemsData.reduce((s, i) => s + (i.quantity || 0) * (i.unit_price || 0), 0);
    const taxAmount = subtotal * (taxRate / 100);
    const total = Math.max(0, subtotal + taxAmount - discount);

    const el = (id) => document.getElementById(id);
    if (el('subtotal-display')) el('subtotal-display').textContent = formatNumber(subtotal);
    if (el('tax-display'))      el('tax-display').textContent      = formatNumber(taxAmount);
    if (el('total-display'))    el('total-display').textContent    = formatNumber(total);
}

function updateItemsJson() {
    const field = document.getElementById('items_json');
    if (field) field.value = JSON.stringify(itemsData);
    calculateTotals();
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// تأكيد الحذف
function confirmDelete(msg, formId) {
    if (confirm(msg || 'هل أنت متأكد من الحذف؟')) {
        document.getElementById(formId).submit();
    }
}
