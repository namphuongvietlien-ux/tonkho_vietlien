"""
Script chuyển đổi file Excel sang JSON để quản lý tồn kho
Hỗ trợ cập nhật thường xuyên bằng cách thay đổi tên file Excel
"""

import pandas as pd
import json
from datetime import datetime, timedelta
import os
import glob
import re

def find_excel_file():
    """Tự động tìm file Excel trong thư mục hiện tại"""
    excel_files = glob.glob("*.xlsx") + glob.glob("*.xls")
    
    # Loại bỏ file tạm (bắt đầu với ~$)
    excel_files = [f for f in excel_files if not os.path.basename(f).startswith('~$')]
    
    if not excel_files:
        raise FileNotFoundError("Không tìm thấy file Excel nào trong thư mục!")
    
    # Sắp xếp theo thời gian sửa đổi, lấy file mới nhất
    excel_files.sort(key=os.path.getmtime, reverse=True)
    return excel_files[0]

def find_data_start_row(df):
    """
    Tìm dòng bắt đầu có 'mã' và 'tên sản phẩm' hoặc 'Item Code' và 'Products'
    """
    for idx, row in df.iterrows():
        row_str = ' '.join([str(val).lower() for val in row if pd.notna(val)])
        if ('mã' in row_str and ('tên' in row_str or 'sản phẩm' in row_str)) or \
           ('item code' in row_str and 'products' in row_str) or \
           ('no.' in row_str and 'lot' in row_str):
            return idx
    return 0

def clean_column_name(col_name):
    """
    Làm sạch tên cột, loại bỏ các ký tự không cần thiết
    """
    if pd.isna(col_name) or str(col_name).strip() == '':
        return None
    
    col_name = str(col_name).strip()
    # Loại bỏ các tên cột dạng "Column_X"
    if col_name.startswith('Column_'):
        return None
    
    return col_name

def analyze_column_importance(df, col):
    """
    Phân tích độ quan trọng của cột dựa trên:
    - Tỷ lệ giá trị không null
    - Tên cột có chứa từ khóa quan trọng
    """
    if col is None:
        return 0
    
    col_lower = col.lower()
    
    # Từ khóa quan trọng
    important_keywords = ['mã', 'tên', 'sản phẩm', 'product', 'tồn', 'số lượng', 
                          'lot', 'lô', 'item', 'code', 'qty', 'quantity', 
                          'expired', 'date', 'ngày', 'đvt', 'unit', 'warehouse',
                          'kho', 'closing stock', 'goods issue', 'goods receipt']
    
    # Tính điểm cho tên cột
    name_score = sum(1 for keyword in important_keywords if keyword in col_lower) * 100
    
    # Tính tỷ lệ dữ liệu không null
    non_null_ratio = df[col].notna().sum() / len(df) * 100
    
    return name_score + non_null_ratio

def smart_filter_columns(df, headers, sheet_name=None):
    """
    Lọc các cột theo logic: Mã/Item Code, Tên/Products, Lot, Tồn đầu kỳ, Tồn cuối kỳ/CLOSING STOCK/Số lượng tồn
    Sheet COLEMAN: Dùng cột A (Mã)
    Các sheet khác: Ưu tiên cột E (Item Code)
    """
    selected_cols = []
    
    # 1. Tìm cột Mã
    ma_col = None
    
    # Nếu KHÔNG phải sheet COLEMAN, ưu tiên cột "Item Code"
    if sheet_name and sheet_name.upper() != 'COLEMAN':
        # Tìm cột có tên chứa "Item Code"
        for i, col in enumerate(headers):
            if col:
                col_lower = str(col).lower()
                # Tìm cột có tên chính xác là "Item Code"
                if col_lower == 'item code' or ('item' in col_lower and 'code' in col_lower):
                    if df[col].notna().sum() > 0:
                        ma_col = col
                        print(f"  ✓ Tìm thấy cột Mã (Item Code) tại index {i}: {col}")
                        break
    
    # Nếu không tìm thấy Item Code hoặc là sheet COLEMAN, tìm theo cách cũ
    if not ma_col:
        for col in headers:
            if col:
                col_lower = col.lower()
                # Kiểm tra tên cột
                if ('mã' in col_lower or 'item code' in col_lower or col_lower == 'ad' or col_lower == 'no.') and \
                   not any(x in col_lower for x in ['cus', 'customer', 'warehouse', 'thông tin']):
                    if df[col].notna().sum() > 0:
                        ma_col = col
                        print(f"  ✓ Tìm thấy cột Mã: {col}")
                        break
                # Kiểm tra nội dung cột - nếu nhiều giá trị có dạng số-chữ (mã sản phẩm)
                elif col.startswith('Column_'):
                    sample_values = df[col].dropna().head(10)
                    if len(sample_values) > 0:
                        # Kiểm tra xem có phải cột chứa mã không (có số ở đầu)
                        has_code_pattern = sum(1 for v in sample_values if str(v).strip() and str(v)[0].isdigit()) > len(sample_values) * 0.3
                        if has_code_pattern:
                            ma_col = col
                            break
    
    # 2. Tìm cột Tên / Products (cho phép cả Column_X nếu chứa tên dài)
    ten_col = None
    for col in headers:
        if col and col != ma_col:
            col_lower = col.lower()
            # Kiểm tra tên cột
            if 'tên' in col_lower or 'products' in col_lower or 'product' in col_lower:
                if df[col].notna().sum() > 0:
                    ten_col = col
                    break
            # Kiểm tra nội dung - nếu có text dài (tên sản phẩm thường dài)
            elif col.startswith('Column_'):
                sample_values = df[col].dropna().head(10)
                if len(sample_values) > 0:
                    avg_length = sum(len(str(v)) for v in sample_values) / len(sample_values)
                    # Tên sản phẩm thường dài hơn 15 ký tự
                    if avg_length > 15:
                        ten_col = col
                        break
    
    # 3. Tìm cột LOT / Lô
    lot_col = None
    for col in headers:
        if col:
            col_lower = col.lower()
            if 'lot' in col_lower or col_lower == 'lô':
                if df[col].notna().sum() > 0:
                    lot_col = col
                    break
    
    # 4. Tìm cột Tồn đầu kỳ
    ton_dau_col = None
    for col in headers:
        if col:
            col_lower = col.lower()
            if 'tồn đầu' in col_lower or 'đầu kỳ' in col_lower or 'opening' in col_lower or col_lower == 'tồn đầu kỳ':
                if df[col].notna().sum() > 0:
                    ton_dau_col = col
                    break
    
    # 5. Tìm cột Tồn cuối kỳ / CLOSING STOCK / Số lượng tồn
    ton_cuoi_col = None
    for col in headers:
        if col:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['closing stock', 'tồn cuối', 'cuối kỳ', 'số lượng tồn', 'closing']):
                if df[col].notna().sum() > 0:
                    ton_cuoi_col = col
                    break
    
    # Bỏ cột EXPIRED DATE vì đã có cột "Ngày hết hạn" tính từ LOT
    
    # Sắp xếp các cột theo thứ tự logic và đặt tên đẹp hơn
    renamed_cols = []
    if ma_col:
        # Đổi tên cột mã cho đẹp - LUÔN dùng "Mã" để thống nhất
        if ma_col == 'No.' or ma_col == 'AD' or ma_col == 'Item Code':
            renamed_cols.append(('Mã', ma_col))
        else:
            renamed_cols.append((ma_col, ma_col))
    if ten_col:
        # Đổi tên cột tên cho đẹp
        if ten_col.startswith('Column_'):
            renamed_cols.append(('Tên sản phẩm', ten_col))
        else:
            renamed_cols.append((ten_col, ten_col))
    if lot_col:
        renamed_cols.append((lot_col, lot_col))
    if ton_dau_col:
        renamed_cols.append((ton_dau_col, ton_dau_col))
    if ton_cuoi_col:
        renamed_cols.append((ton_cuoi_col, ton_cuoi_col))
    
    return renamed_cols

def load_product_config():
    """
    Load cấu hình thời hạn sử dụng từ product_config.json
    """
    try:
        with open('product_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "shelf_life_months": {
                "BAKING SODA": 36,
                "AZARINE": 36,
                "PIN FUJITSU": {}
            },
            "product_specific_shelf_life": {}
        }

def save_product_config(config):
    """
    Lưu cấu hình thời hạn sử dụng vào product_config.json
    """
    with open('product_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def parse_lot_to_date(lot_value):
    """
    Parse LOT thành ngày hết hạn (ngày cuối cùng của tháng)
    LOT format: YYMM (ví dụ: 2805 = tháng 05 năm 2028 -> ngày hết hạn = 31/05/2028)
    """
    if pd.isna(lot_value):
        return None
    
    lot_str = str(lot_value).strip().upper().replace('LOT', '').replace('/', '').replace('-', '').replace('.', '')
    
    # Loại bỏ chữ cái, chỉ giữ số
    lot_str = ''.join(c for c in lot_str if c.isdigit())
    
    if not lot_str:
        return None
    
    try:
        # Format YYYYMMDD (8 chữ số) - ngày cụ thể
        if len(lot_str) == 8:
            year = int(lot_str[0:4])
            month = int(lot_str[4:6])
            day = int(lot_str[6:8])
            return datetime(year, month, day)
        
        # Format YYMMDD (6 chữ số) - ngày cụ thể
        elif len(lot_str) == 6:
            year = int(lot_str[0:2])
            year = 2000 + year if year < 50 else 1900 + year
            month = int(lot_str[2:4])
            day = int(lot_str[4:6])
            return datetime(year, month, day)
        
        # Format YYMM (4 chữ số) - ngày cuối cùng của tháng (NGÀY HẾT HẠN)
        elif len(lot_str) == 4:
            year = int(lot_str[0:2])
            month = int(lot_str[2:4])
            year = 2000 + year if year < 50 else 1900 + year
            
            # Tìm ngày cuối cùng của tháng
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)
            last_day = next_month - timedelta(days=1)
            return last_day
    except:
        pass
    
    return None

def calculate_remaining_percentage(lot_value, shelf_life_months):
    """
    Tính phần trăm hạn sử dụng còn lại
    lot_value: Số LOT (ví dụ: "2805" = ngày hết hạn 31/05/2028)
    shelf_life_months: Thời hạn sử dụng (tháng)
    
    Logic:
    - LOT = ngày hết hạn
    - Ngày sản xuất = ngày hết hạn - shelf_life_months
    - % còn lại = (ngày hết hạn - hôm nay) / (ngày hết hạn - ngày sản xuất) * 100
    
    Returns: (remaining_percentage, expiry_date_str)
    """
    if not shelf_life_months or pd.isna(lot_value):
        return None, None
    
    # Parse LOT -> ngày hết hạn
    expiry_date = parse_lot_to_date(lot_value)
    if not expiry_date:
        return None, None
    
    # Tính ngày sản xuất = EDATE(ngày hết hạn, -shelf_life_months)
    production_date = expiry_date - timedelta(days=shelf_life_months * 30.44)
    
    # Ngày hiện tại
    today = datetime.now()
    
    # Tính tổng số ngày thời hạn sử dụng
    total_days = (expiry_date - production_date).days
    
    # Tính số ngày còn lại
    days_remaining = (expiry_date - today).days
    
    # Tính phần trăm
    if days_remaining <= 0:
        percentage = 0
    elif total_days > 0:
        percentage = (days_remaining / total_days) * 100
    else:
        percentage = 0
    
    expiry_str = expiry_date.strftime("%d/%m/%Y")
    
    return round(percentage, 1), expiry_str

def extract_date_from_lot(lot_value):
    """
    Trích xuất ngày sản xuất từ số lô nếu có format ngày
    Ví dụ: "LOT240512" -> "12/05/2024"
    """
    if pd.isna(lot_value):
        return None
    
    lot_str = str(lot_value).upper()
    
    # Thử pattern YYMMDD (6 số)
    match = re.search(r'(\d{6})', lot_str)
    if match:
        date_str = match.group(1)
        try:
            year = int('20' + date_str[0:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{day:02d}/{month:02d}/{year}"
        except:
            pass
    
    # Thử pattern YYYYMMDD (8 số)
    match = re.search(r'(\d{8})', lot_str)
    if match:
        date_str = match.group(1)
        try:
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{day:02d}/{month:02d}/{year}"
        except:
            pass
    
    return None

def process_sheet_data(df, start_row, sheet_name=None):
    """
    Xử lý dữ liệu từ một sheet, bắt đầu từ dòng chỉ định
    Mô phỏng quy trình: Copy > Paste Value > Xóa hàng trống > Xóa cột trống
    """
    # Kiểm tra xem có phải header nhiều dòng không
    first_header = df.iloc[start_row].tolist()
    second_row = df.iloc[start_row + 1].tolist() if start_row + 1 < len(df) else []
    third_row = df.iloc[start_row + 2].tolist() if start_row + 2 < len(df) else []
    
    # Nếu dòng tiếp theo có "Item Code" hoặc "Products", nghĩa là đây mới là header thực
    has_real_header_next = any(str(val).lower() in ['item code', 'products', 'cus code'] 
                                for val in second_row if pd.notna(val))
    
    if has_real_header_next:
        # Có 2 dòng header: dòng 1 là nhóm (TỒN ĐẦU KỲ, CLOSING STOCK/, ...), dòng 2 là chi tiết
        # Nhưng các cột "Q'TY/SL" ở dòng 2 cần được map với nhóm ở dòng 1
        
        # Tạo map vị trí cột -> tên nhóm
        group_map = {}
        current_group = None
        for i, val in enumerate(first_header):
            if pd.notna(val) and str(val).strip():
                current_group = str(val).strip()
            if current_group:
                group_map[i] = current_group
        
        # Merge header
        headers = []
        for i, h2 in enumerate(second_row):
            if pd.notna(h2) and str(h2).strip():
                h2_str = str(h2).strip()
                # Nếu là "Q'TY/SL" và có group, dùng tên group
                if h2_str.lower() in ["q'ty/sl", "qty/sl"] and i in group_map:
                    headers.append(group_map[i])
                else:
                    headers.append(h2_str)
            elif i < len(first_header) and pd.notna(first_header[i]) and str(first_header[i]).strip():
                headers.append(str(first_header[i]).strip())
            else:
                headers.append(f"Column_{i}")
        
        # Dữ liệu bắt đầu từ dòng start_row + 2
        data_df = df.iloc[start_row + 2:].reset_index(drop=True)
    else:
        # Header  bình thường
        headers = [clean_column_name(h) if clean_column_name(h) else f"Column_{i}" 
                   for i, h in enumerate(first_header)]
        data_df = df.iloc[start_row + 1:].reset_index(drop=True)
    
    data_df.columns = headers
    
    # BƯỚC 1: Tìm cột "Tên sản phẩm" hoặc "Products" 
    product_col = None
    for col in data_df.columns:
        if not col:
            continue
        col_lower = str(col).lower()
        # Tìm theo tên cột rõ ràng
        if 'product' in col_lower or 'tên' in col_lower:
            product_col = col
            break
    
    # Nếu không tìm thấy, tìm cột Column_X có nội dung giống tên sản phẩm (text dài có số-chữ)
    if not product_col:
        for col in data_df.columns:
            if col and col.startswith('Column_'):
                sample_values = data_df[col].dropna().head(20)
                if len(sample_values) >= 5:
                    # Kiểm tra pattern: số ở đầu, theo sau là dấu gạch và text
                    has_product_pattern = sum(1 for v in sample_values if 
                        str(v).strip() and '-' in str(v) and str(v)[0].isdigit()) > len(sample_values) * 0.5
                    if has_product_pattern:
                        product_col = col
                        break
    
    # BƯỚC 2: Xóa các hàng có cột "Tên sản phẩm" trống HOẶC các hàng hoàn toàn trống
    if product_col:
        # Chỉ xóa hàng nếu cột product trống
        data_df = data_df[data_df[product_col].notna() & (data_df[product_col].astype(str).str.strip() != '')]
    else:
        # Nếu không tìm thấy product col, chỉ xóa hàng hoàn toàn trống
        data_df = data_df.dropna(how='all')
    
    # BƯỚC 3: Xóa các cột hoàn toàn trống (giống Ctrl+G > Blanks > Delete Columns)
    data_df = data_df.dropna(axis=1, how='all')
    
    # Cập nhật lại headers sau khi xóa cột
    headers = data_df.columns.tolist()
    
    # Debug: In ra tất cả headers
    # print(f"DEBUG - All headers ({len(headers)}): {headers[:20]}")
    
    # BƯỚC 4: Tự động xác định và đặt tên cho cột LOT và Units nếu thiếu tiêu đề
    renamed_headers = []
    for i, col in enumerate(headers):
        if col.startswith('Column_'):
            # Kiểm tra nội dung để xác định loại cột
            sample_values = data_df[col].dropna().head(20)
            if len(sample_values) > 0:
                # Kiểm tra xem có phải LOT không (có pattern số + chữ)
                has_lot_pattern = sum(1 for v in sample_values if 
                    str(v).strip() and len(str(v)) <= 10 and 
                    any(c.isdigit() for c in str(v))) > len(sample_values) * 0.5
                
                # Kiểm tra xem có phải Units không (text ngắn như "Chai", "Hộp", "Cái")
                avg_length = sum(len(str(v)) for v in sample_values) / len(sample_values)
                has_unit_pattern = avg_length < 10 and all(not str(v)[0].isdigit() if str(v).strip() else True for v in sample_values)
                
                if has_lot_pattern and avg_length < 15:
                    renamed_headers.append('LOT')
                elif has_unit_pattern and avg_length < 10:
                    renamed_headers.append('ĐVT')
                else:
                    renamed_headers.append(col)
            else:
                renamed_headers.append(col)
        else:
            renamed_headers.append(col)
    
    data_df.columns = renamed_headers
    headers = renamed_headers
    
    # Reset index sau khi xóa hàng
    data_df = data_df.reset_index(drop=True)
    
    # BƯỚC 5: Lọc và sắp xếp các cột theo logic
    column_mapping = smart_filter_columns(data_df, headers, sheet_name)
    
    if not column_mapping:
        # Fallback: giữ tất cả cột có dữ liệu
        column_mapping = [(col, col) for col in headers if data_df[col].notna().any()]
    
    # Tạo dict để map tên cột cũ sang tên mới
    col_rename_dict = {old_name: new_name for new_name, old_name in column_mapping}
    selected_columns = [old_name for _, old_name in column_mapping]
    display_columns = [new_name for new_name, _ in column_mapping]
    
    # Chỉ giữ các cột đã chọn
    data_df = data_df[selected_columns]
    
    # Chuyển đổi thành list of dictionaries với tên cột mới
    products = []
    for _, row in data_df.iterrows():
        product = {}
        has_data = False
        
        for old_col, new_col in zip(selected_columns, display_columns):
            value = row[old_col]
            if pd.isna(value):
                product[new_col] = None
            elif isinstance(value, (pd.Timestamp, datetime)):
                product[new_col] = value.strftime("%d/%m/%Y")
                has_data = True
            elif isinstance(value, (int, float)):
                product[new_col] = float(value) if value % 1 else int(value)
                has_data = True
            else:
                value_str = str(value).strip()
                if value_str:  # Chỉ thêm nếu không rỗng
                    product[new_col] = value_str
                    has_data = True
                else:
                    product[new_col] = None
            
            # Thêm cột "Ngày SX từ Lô" nếu có cột LOT/Lô
            if new_col and ('lot' in new_col.lower() or 'lô' in new_col.lower()) and value:
                extracted_date = extract_date_from_lot(value)
                if extracted_date and 'Ngày SX từ Lô' not in product:
                    product['Ngày SX từ Lô'] = extracted_date
                    has_data = True
        
        # Chỉ thêm dòng có dữ liệu thực sự
        if has_data:
            # Kiểm tra xem có ít nhất 1 cột quan trọng không null
            important_values = [v for k, v in product.items() if k in ['Mã', 'Tên sản phẩm', 'Tên', 'LOT', 'Số lượng tồn', 'CLOSING STOCK/']]
            if any(v is not None for v in important_values):
                products.append(product)
    
    return products, display_columns

def convert_excel_to_json(excel_file=None, output_file='inventory_data.json'):
    """
    Chuyển đổi file Excel sang JSON (tất cả các sheet)
    
    Parameters:
    - excel_file: Tên file Excel (nếu None, sẽ tự động tìm file mới nhất)
    - output_file: Tên file JSON output
    """
    
    try:
        # Load cấu hình thời hạn sử dụng
        config = load_product_config()
        
        # Tự động tìm file Excel nếu không được chỉ định
        if excel_file is None:
            excel_file = find_excel_file()
            print(f"Đã tìm thấy file: {excel_file}")
        
        # Lấy ngày từ tên file (ví dụ: 22.12.xlsx -> 22/12/2025)
        try:
            file_name = os.path.splitext(excel_file)[0]
            date_parts = file_name.split('.')
            if len(date_parts) == 2:
                day, month = date_parts
                current_year = datetime.now().year
                date_ton_kho = f"{day.zfill(2)}/{month.zfill(2)}/{current_year}"
            else:
                date_ton_kho = datetime.now().strftime("%d/%m/%Y")
        except:
            date_ton_kho = datetime.now().strftime("%d/%m/%Y")
        
        # Đọc tất cả các sheet
        excel_file_obj = pd.ExcelFile(excel_file)
        sheet_names = excel_file_obj.sheet_names
        
        print(f"\nĐang xử lý {len(sheet_names)} sheet(s)...")
        
        sheets_data = []
        total_products = 0
        
        for sheet_name in sheet_names:
            print(f"\n  📄 Đang xử lý sheet: {sheet_name}")
            
            # Đọc sheet với header=None để tự xử lý
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
            
            # Tìm dòng bắt đầu có "mã" và "tên sản phẩm"
            start_row = find_data_start_row(df)
            print(f"     - Dòng bắt đầu dữ liệu: {start_row + 1}")
            
            # Xử lý dữ liệu từ sheet
            products, selected_columns = process_sheet_data(df, start_row, sheet_name)
            
            # Thêm cột % Còn lại và Hạn sử dụng cho các sheet có hạn
            if products and sheet_name in config['shelf_life_months']:
                # Lấy thời hạn mặc định cho sheet
                default_shelf_life = config['shelf_life_months'].get(sheet_name)
                
                # Nếu là dict (PIN FUJITSU), xử lý riêng
                if isinstance(default_shelf_life, dict):
                    # Thêm cột "Thời hạn (tháng)" để người dùng có thể chọn
                    if 'Thời hạn (tháng)' not in selected_columns:
                        selected_columns.insert(3, 'Thời hạn (tháng)')  # Chèn sau LOT
                    if '% Còn lại' not in selected_columns:
                        selected_columns.insert(4, '% Còn lại')
                    if 'Ngày hết hạn' not in selected_columns:
                        selected_columns.insert(5, 'Ngày hết hạn')
                    
                    for product in products:
                        product_code = str(product.get('Mã', '')).strip()  # Chuyển sang string và trim
                        
                        # Xử lý lot_number: None -> rỗng
                        lot_value = product.get('LOT')
                        lot_number = str(lot_value).strip() if lot_value not in [None, '', 'None', 'nan'] else ''
                        
                        # Tạo unique key: LUÔN dùng format product_code_lot_number
                        unique_key = f"{product_code}_{lot_number}"
                        
                        # Lấy thời hạn đã lưu hoặc mặc định 36 tháng
                        shelf_life = config['product_specific_shelf_life'].get(unique_key, 36)
                        product['Thời hạn (tháng)'] = shelf_life
                        
                        # Tính % còn lại
                        lot_value = product.get('LOT')
                        if lot_value:
                            percentage, expiry_date = calculate_remaining_percentage(lot_value, shelf_life)
                            product['% Còn lại'] = percentage
                            product['Ngày hết hạn'] = expiry_date
                        else:
                            product['% Còn lại'] = None
                            product['Ngày hết hạn'] = None
                else:
                    # Sheet khác (BAKING SODA, AZARINE): thời hạn cố định
                    if '% Còn lại' not in selected_columns:
                        selected_columns.insert(3, '% Còn lại')  # Chèn sau LOT
                    if 'Ngày hết hạn' not in selected_columns:
                        selected_columns.insert(4, 'Ngày hết hạn')
                    
                    for product in products:
                        lot_value = product.get('LOT')
                        if lot_value:
                            percentage, expiry_date = calculate_remaining_percentage(lot_value, default_shelf_life)
                            product['% Còn lại'] = percentage
                            product['Ngày hết hạn'] = expiry_date
                        else:
                            product['% Còn lại'] = None
                            product['Ngày hết hạn'] = None
            
            if products:
                sheets_data.append({
                    "sheet_name": sheet_name,
                    "products": products,
                    "total_products": len(products),
                    "columns": selected_columns
                })
                total_products += len(products)
                print(f"     - Số sản phẩm: {len(products)}")
                print(f"     - Các cột hiển thị: {', '.join(selected_columns[:5])}{'...' if len(selected_columns) > 5 else ''}")
            else:
                print(f"     ⚠ Không có dữ liệu")
        
        # Tạo cấu trúc JSON với metadata
        inventory_data = {
            "metadata": {
                "date_ton_kho": date_ton_kho,
                "source_file": excel_file,
                "last_updated": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "total_sheets": len(sheets_data),
                "total_products": total_products
            },
            "sheets": sheets_data
        }
        
        # Lưu vào file JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(inventory_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Đã chuyển đổi thành công!")
        print(f"  - File nguồn: {excel_file}")
        print(f"  - File đích: {output_file}")
        print(f"  - Ngày tồn kho: {date_ton_kho}")
        print(f"  - Tổng số sheet: {len(sheets_data)}")
        print(f"  - Tổng số sản phẩm: {total_products}")
        
        return inventory_data
        
    except Exception as e:
        print(f"✗ Lỗi khi chuyển đổi: {str(e)}")
        raise

if __name__ == "__main__":
    # Chạy chuyển đổi - tự động tìm file Excel mới nhất
    convert_excel_to_json()
