# 📦 Hệ Thống Quản Lý Tồn Kho

Dự án website quản lý tồn kho với khả năng tự động chuyển đổi dữ liệu từ Excel sang JSON và hiển thị trực quan.

## ✨ Tính năng

- ✅ **Tự động chuyển đổi Excel sang JSON** - Hỗ trợ file .xlsx và .xls
- ✅ **Tự động phát hiện file Excel mới nhất** - Không cần chỉ định tên file cụ thể
- ✅ **Theo dõi ngày tồn kho** - Tự động lấy từ tên file (ví dụ: 22.12.xlsx)
- ✅ **Giao diện web đẹp mắt** - Responsive, dễ sử dụng
- ✅ **Tìm kiếm và lọc dữ liệu** - Tìm kiếm theo tất cả cột hoặc cột cụ thể
- ✅ **Cập nhật thường xuyên** - Chỉ cần thay đổi file Excel và chạy lại script

## 📁 Cấu trúc thư mục

```
ton_kho/
├── convert_to_json.py      # Script chuyển đổi Excel sang JSON
├── index.html              # Trang web chính
├── style.css               # File CSS cho giao diện
├── script.js               # File JavaScript xử lý logic
├── 22.12.xlsx             # File Excel mẫu (có thể thay đổi tên)
├── inventory_data.json    # File JSON được tạo tự động
└── README.md              # File hướng dẫn này
```

## 🚀 Cách sử dụng

### Bước 1: Cài đặt thư viện Python

Mở Terminal và chạy lệnh sau:

```bash
pip install pandas openpyxl
```

### Bước 2: Chuyển đổi Excel sang JSON

Đặt file Excel của bạn vào thư mục dự án (ví dụ: `23.12.xlsx`, `24.12.xlsx`, v.v.)

Chạy script Python:

```bash
python convert_to_json.py
```

Script sẽ:
- Tự động tìm file Excel mới nhất trong thư mục
- Đọc dữ liệu và chuyển đổi sang JSON
- Tạo file `inventory_data.json`
- Hiển thị thông tin về ngày tồn kho và số lượng sản phẩm

### Bước 3: Mở website

Mở file `index.html` bằng trình duyệt web hoặc sử dụng Live Server trong VS Code.

## 📝 Quy tắc đặt tên file Excel

Để hệ thống tự động nhận diện ngày tồn kho, đặt tên file theo format:

- `DD.MM.xlsx` - Ví dụ: `22.12.xlsx` (22/12/2025)
- `DD-MM.xlsx` - Ví dụ: `22-12.xlsx`

Nếu tên file không theo format này, hệ thống sẽ sử dụng ngày hiện tại.

## 🔄 Cập nhật dữ liệu thường xuyên

### Cách 1: Thay đổi tên file Excel

1. Đổi tên file Excel hiện tại (ví dụ: `22.12.xlsx` → `23.12.xlsx`)
2. Cập nhật nội dung file
3. Chạy lại: `python convert_to_json.py`
4. Nhấn nút "🔄 Làm mới dữ liệu" trên website

### Cách 2: Thêm file Excel mới

1. Thêm file Excel mới vào thư mục
2. Chạy: `python convert_to_json.py` (sẽ tự động chọn file mới nhất)
3. Nhấn nút "🔄 Làm mới dữ liệu" trên website

### Cách 3: Chỉ định file cụ thể

Mở file `convert_to_json.py` và sửa dòng cuối:

```python
convert_excel_to_json('ten_file_cu_the.xlsx')
```

## 🎨 Tính năng website

### Tìm kiếm
- Gõ từ khóa vào ô tìm kiếm để lọc sản phẩm
- Tìm kiếm trong tất cả các cột hoặc chỉ cột cụ thể

### Lọc theo cột
- Chọn cột từ dropdown để tìm kiếm trong cột đó
- Chọn "Tất cả" để tìm kiếm toàn bộ bảng

### Làm mới dữ liệu
- Nhấn nút "🔄 Làm mới dữ liệu" để tải lại dữ liệu mới nhất
- Không cần reload trang

### Thông tin hiển thị
- 📅 Ngày tồn kho
- 📊 Tổng số sản phẩm
- 🕐 Thời gian cập nhật
- 📄 Tên file nguồn

## ⚙️ Tùy chỉnh

### Thay đổi tên file JSON output

Mở `convert_to_json.py` và sửa:

```python
convert_excel_to_json(output_file='ten_file_moi.json')
```

Sau đó cập nhật `script.js` dòng fetch:

```javascript
const response = await fetch('ten_file_moi.json?' + new Date().getTime());
```

### Tùy chỉnh giao diện

Chỉnh sửa file `style.css` để thay đổi màu sắc, font chữ, layout.

### Thêm tính năng mới

Chỉnh sửa file `script.js` để thêm các tính năng như:
- Export sang Excel
- In báo cáo
- Thống kê biểu đồ
- v.v.

## ❗ Xử lý lỗi

### Lỗi: "Không tìm thấy file Excel"
- Đảm bảo có file .xlsx hoặc .xls trong thư mục
- Kiểm tra quyền truy cập file

### Lỗi: "Module 'pandas' not found"
- Chạy: `pip install pandas openpyxl`

### Website không hiển thị dữ liệu
- Kiểm tra xem file `inventory_data.json` đã được tạo chưa
- Mở Console trong trình duyệt (F12) để xem lỗi
- Đảm bảo website được mở từ server (không phải file:// protocol)

## 📞 Hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra lại các bước trong hướng dẫn
2. Xem phần "Xử lý lỗi" ở trên
3. Kiểm tra Console của trình duyệt (F12)

## 📄 License

Dự án này được phát triển để sử dụng nội bộ. Bạn có thể tự do sửa đổi và mở rộng theo nhu cầu.

---

**Lưu ý:** Dự án này yêu cầu Python 3.6+ và trình duyệt web hiện đại (Chrome, Firefox, Edge).
