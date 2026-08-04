/**
 * نظام المحاسبة - JavaScript الرئيسي
 */

// تبديل الشريط الجانبي
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// إغلاق الشريط الجانبي عند النقر خارجه
document.addEventListener('click', function(e) {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.querySelector('.sidebar-toggle');
    if (sidebar && toggle && window.innerWidth <= 992) {
        if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
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
    renderItems();
    calculateTotals();
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
            <td style="width:100px">
                <input type="number" class="form-control form-control-sm"
                    value="${item.quantity}" min="0.01" step="0.01"
                    oninput="updateItem(${i}, 'quantity', this.value)">
            </td>
            <td style="width:140px">
                <input type="number" class="form-control form-control-sm"
                    value="${item.unit_price}" min="0" step="0.01"
                    oninput="updateItem(${i}, 'unit_price', this.value)">
            </td>
            <td style="width:130px" class="text-end fw-semibold">
                ${formatNumber((item.quantity || 0) * (item.unit_price || 0))}
            </td>
            <td style="width:50px" class="text-center">
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
    if (el('tax-display')) el('tax-display').textContent = formatNumber(taxAmount);
    if (el('total-display')) el('total-display').textContent = formatNumber(total);
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
