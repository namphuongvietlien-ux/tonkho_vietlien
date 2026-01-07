// Biến toàn cục
let inventoryData = null;
let allSheets = [];
let currentSheetIndex = 0;
let currentSheetProducts = [];
let filteredProducts = [];
let selectedFile = null;

// Load dữ liệu khi trang được tải
document.addEventListener('DOMContentLoaded', () => {
    loadInventoryData();
    setupEventListeners();
    setupFileUpload();
});

// Thiết lập các event listeners
function setupEventListeners() {
    // Tìm kiếm
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterProducts(e.target.value);
    });

    // Làm mới dữ liệu
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadInventoryData();
    });

    // Lọc theo cột
    document.getElementById('column-filter').addEventListener('change', (e) => {
        const searchValue = document.getElementById('search-input').value;
        filterProducts(searchValue);
    });
}

// Thiết lập upload file
function setupFileUpload() {
    const fileUpload = document.getElementById('file-upload');
    const fileName = document.getElementById('file-name');
    const processBtn = document.getElementById('process-btn');
    
    fileUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            selectedFile = file;
            fileName.textContent = file.name;
            processBtn.disabled = false;
        }
    });
    
    processBtn.addEventListener('click', async () => {
        if (!selectedFile) return;
        
        processBtn.disabled = true;
        processBtn.textContent = '⏳ Đang xử lý...';
        
        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            // Tự động detect môi trường: local dùng /upload, Vercel dùng /api/upload
            const uploadUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
                ? '/upload' 
                : '/api/upload';
            
            const response = await fetch(uploadUrl, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `Upload thất bại (${response.status})`);
            }
            
            const result = await response.json();
            
            // If data is returned, use it directly (for Vercel deployment)
            if (result.data) {
                inventoryData = result.data;
                allSheets = inventoryData.sheets || [];
                
                if (allSheets.length > 0) {
                    currentSheetIndex = 0;
                    displayMetadata();
                    createTabs();
                    switchToSheet(0);
                    document.getElementById('no-data').classList.add('hidden');
                }
                
                alert('✓ Xử lý thành công!');
            } else {
                // Otherwise reload from file (for local deployment)
                alert('✓ Xử lý thành công! Đang tải dữ liệu...');
                await loadInventoryData();
            }
            
        } catch (error) {
            alert('✗ Lỗi: ' + error.message);
        } finally {
            processBtn.disabled = false;
            processBtn.textContent = '⚡ Xử Lý File';
        }
    });
}

// Load dữ liệu từ file JSON
async function loadInventoryData(preserveCurrentSheet = false) {
    try {
        // Lưu sheet index hiện tại nếu cần preserve
        const savedSheetIndex = preserveCurrentSheet ? currentSheetIndex : 0;
        
        const response = await fetch('inventory_data.json?' + new Date().getTime());
        
        if (!response.ok) {
            throw new Error('Không thể tải file dữ liệu');
        }

        inventoryData = await response.json();
        allSheets = inventoryData.sheets || [];

        if (allSheets.length === 0) {
            throw new Error('Không có sheet nào trong dữ liệu');
        }

        // Hiển thị metadata
        displayMetadata();
        
        // Tạo tabs cho các sheet
        createTabs();
        
        // Hiển thị sheet đã lưu hoặc sheet đầu tiên
        switchToSheet(savedSheetIndex);
        
        // Ẩn thông báo không có dữ liệu
        document.getElementById('no-data').classList.add('hidden');
        
    } catch (error) {
        console.error('Lỗi khi load dữ liệu:', error);
        document.getElementById('no-data').classList.remove('hidden');
        document.getElementById('sheet-contents').classList.add('hidden');
    }
}

// Hiển thị metadata
function displayMetadata() {
    const metadata = inventoryData.metadata;
    
    document.getElementById('date-ton-kho').textContent = metadata.date_ton_kho || '--';
    document.getElementById('total-products').textContent = metadata.total_products || 0;
    document.getElementById('total-sheets').textContent = metadata.total_sheets || 0;
    document.getElementById('last-updated').textContent = metadata.last_updated || '--';
    document.getElementById('source-file').textContent = metadata.source_file || '--';
}

// Tạo tabs cho các sheet
function createTabs() {
    const tabsContainer = document.getElementById('tabs-container');
    tabsContainer.innerHTML = '';
    
    allSheets.forEach((sheet, index) => {
        const tab = document.createElement('button');
        tab.className = 'tab';
        tab.textContent = sheet.sheet_name;
        tab.onclick = () => switchToSheet(index);
        
        if (index === 0) {
            tab.classList.add('active');
        }
        
        tabsContainer.appendChild(tab);
    });
}

// Chuyển đổi giữa các sheet
function switchToSheet(sheetIndex) {
    currentSheetIndex = sheetIndex;
    const sheet = allSheets[sheetIndex];
    currentSheetProducts = sheet.products || [];
    filteredProducts = [...currentSheetProducts];
    
    // Cập nhật active tab
    document.querySelectorAll('.tab').forEach((tab, index) => {
        if (index === sheetIndex) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Hiển thị nội dung sheet
    displaySheetContent(sheet);
    
    // Reset tìm kiếm
    document.getElementById('search-input').value = '';
    document.getElementById('column-filter').value = 'all';
}

// Hiển thị nội dung sheet
function displaySheetContent(sheet) {
    const sheetContents = document.getElementById('sheet-contents');
    sheetContents.innerHTML = '';
    
    // Tạo container cho sheet
    const sheetDiv = document.createElement('div');
    sheetDiv.className = 'sheet-content active';
    
    // Tạo header cho sheet
    const header = document.createElement('div');
    header.className = 'sheet-header';
    header.innerHTML = `
        <h2>📄 ${sheet.sheet_name}</h2>
        <div class="sheet-stats">Tổng số sản phẩm: <strong>${sheet.total_products}</strong></div>
    `;
    sheetDiv.appendChild(header);
    
    // Tạo container cho bảng
    const tableContainer = document.createElement('div');
    tableContainer.className = 'table-container';
    
    const table = document.createElement('table');
    table.id = 'inventory-table';
    
    const thead = document.createElement('thead');
    thead.id = 'table-head';
    
    const tbody = document.createElement('tbody');
    tbody.id = 'table-body';
    
    table.appendChild(thead);
    table.appendChild(tbody);
    tableContainer.appendChild(table);
    sheetDiv.appendChild(tableContainer);
    
    sheetContents.appendChild(sheetDiv);
    
    // Hiển thị dữ liệu
    if (currentSheetProducts.length > 0) {
        const columns = Object.keys(currentSheetProducts[0]);
        
        // Tạo header
        const headerRow = document.createElement('tr');
        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        
        // Cập nhật filter dropdown
        updateColumnFilter(columns);
        
        // Hiển thị body
        displayTableBody();
    }
}

// Hiển thị nội dung bảng
function displayTableBody() {
    const tbody = document.getElementById('table-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (filteredProducts.length === 0) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = Object.keys(currentSheetProducts[0] || {}).length;
        cell.textContent = '⚠️ Không tìm thấy sản phẩm phù hợp';
        cell.className = 'no-results-cell';
        row.appendChild(cell);
        tbody.appendChild(row);
        return;
    }

    filteredProducts.forEach(product => {
        const row = document.createElement('tr');
        
        Object.entries(product).forEach(([key, value]) => {
            const cell = document.createElement('td');
            
            // Xử lý cột % Còn lại - thêm highlight màu
            if (key === '% Còn lại' && value !== null && value !== undefined) {
                const percentage = parseFloat(value);
                cell.textContent = percentage.toFixed(1) + '%';
                
                // Highlight theo phần trăm
                if (percentage <= 0) {
                    cell.classList.add('expired');  // Hết hạn - đỏ
                } else if (percentage < 50) {
                    cell.classList.add('low-shelf-life');  // Dưới 50% - cam đậm
                } else if (percentage < 70) {
                    cell.classList.add('medium-shelf-life');  // Dưới 70% - vàng
                }
            }
            // Xử lý cột Thời hạn (tháng) cho PIN FUJITSU - dropdown
            else if (key === 'Thời hạn (tháng)' && allSheets[currentSheetIndex].sheet_name === 'PIN FUJITSU') {
                const select = document.createElement('select');
                select.className = 'shelf-life-selector';
                
                // Danh sách thời hạn: 36, 40, 84 (7 năm), 120 (10 năm), 999 (vô thời hạn)
                const shelfLifeOptions = [
                    { value: 36, label: '36 tháng (3 năm)' },
                    { value: 40, label: '40 tháng' },
                    { value: 84, label: '84 tháng (7 năm)' },
                    { value: 120, label: '120 tháng (10 năm)' },
                    { value: 999, label: 'Vô thời hạn' }
                ];
                
                shelfLifeOptions.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt.value;
                    option.textContent = opt.label;
                    if (value === opt.value) option.selected = true;
                    select.appendChild(option);
                });
                
                // Lưu thời hạn khi thay đổi
                select.addEventListener('change', async (e) => {
                    const newShelfLife = parseInt(e.target.value);
                    const productCode = product['Mã'];
                    const lotNumber = product['LOT'] || '';
                    
                    // Disable dropdown và hiển thị loading
                    select.disabled = true;
                    const originalText = e.target.options[e.target.selectedIndex].text;
                    e.target.options[e.target.selectedIndex].text = '⏳ Đang lưu...';
                    
                    try {
                        // Lưu thời hạn vào server với key = Mã + LOT
                        const success = await saveProductShelfLife(productCode, lotNumber, newShelfLife);
                        
                        if (success) {
                            // Reload dữ liệu và giữ nguyên sheet hiện tại
                            await loadInventoryData(true);
                        } else {
                            alert('❌ Không thể lưu thời hạn. Vui lòng thử lại!');
                            e.target.options[e.target.selectedIndex].text = originalText;
                            select.disabled = false;
                        }
                    } catch (error) {
                        alert('❌ Lỗi: ' + error.message);
                        e.target.options[e.target.selectedIndex].text = originalText;
                        select.disabled = false;
                    }
                });
                
                cell.appendChild(select);
            }
            else {
                cell.textContent = value !== null && value !== undefined ? value : '--';
            }
            
            row.appendChild(cell);
        });
        
        tbody.appendChild(row);
    });
}

// Lưu thời hạn sử dụng của sản phẩm
async function saveProductShelfLife(productCode, lotNumber, shelfLifeMonths) {
    try {
        // Tự động detect môi trường
        const saveUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? '/save_shelf_life'
            : '/api/save_shelf_life';
        
        console.log('Đang lưu thời hạn:', { productCode, lotNumber, shelfLifeMonths });
        
        const response = await fetch(saveUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_code: productCode,
                lot_number: lotNumber,
                shelf_life_months: shelfLifeMonths
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('Không thể lưu thời hạn sử dụng:', errorData.message || response.statusText);
            return false;
        }
        
        const result = await response.json();
        console.log('Lưu thành công:', result);
        return true;
    } catch (error) {
        console.error('Lỗi khi lưu:', error.message);
        return false;
    }
}

// Lọc sản phẩm theo từ khóa tìm kiếm
function filterProducts(searchTerm) {
    const columnFilter = document.getElementById('column-filter').value;
    searchTerm = searchTerm.toLowerCase().trim();

    if (!searchTerm) {
        filteredProducts = [...currentSheetProducts];
    } else {
        filteredProducts = currentSheetProducts.filter(product => {
            if (columnFilter === 'all') {
                // Tìm kiếm trong tất cả các cột
                return Object.values(product).some(value => {
                    if (value === null || value === undefined) return false;
                    return String(value).toLowerCase().includes(searchTerm);
                });
            } else {
                // Tìm kiếm trong cột cụ thể
                const value = product[columnFilter];
                if (value === null || value === undefined) return false;
                return String(value).toLowerCase().includes(searchTerm);
            }
        });
    }

    displayTableBody();
    updateProductCount();
}

// Cập nhật số lượng sản phẩm
function updateProductCount() {
    const sheet = allSheets[currentSheetIndex];
    const sheetStats = document.querySelector('.sheet-stats strong');
    if (sheetStats) {
        sheetStats.textContent = `${filteredProducts.length} / ${sheet.total_products}`;
    }
}

// Cập nhật dropdown lọc theo cột
function updateColumnFilter(columns) {
    const select = document.getElementById('column-filter');
    select.innerHTML = '<option value="all">Tất cả</option>';
    
    columns.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = col;
        select.appendChild(option);
    });
}

// Export functions for external use
window.inventoryManager = {
    refresh: loadInventoryData,
    getSheets: () => allSheets,
    getCurrentSheet: () => allSheets[currentSheetIndex],
    getCurrentProducts: () => currentSheetProducts,
    getFilteredProducts: () => filteredProducts,
    switchSheet: (index) => switchToSheet(index)
};
