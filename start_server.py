"""
Server đơn giản để chạy website quản lý tồn kho
Hỗ trợ API để lưu thời hạn sử dụng sản phẩm và upload file Excel
"""
import http.server
import socketserver
import webbrowser
import os
import json
import io
from urllib.parse import urlparse
from email import message_from_bytes
from email.parser import BytesParser

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Thêm CORS headers để tránh lỗi khi load JSON
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    
    def do_POST(self):
        """Xử lý POST request để lưu thời hạn sử dụng hoặc upload file"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/upload':
            # Xử lý upload file Excel  
            try:
                content_type = self.headers.get('Content-Type', '')
                
                if 'multipart/form-data' not in content_type:
                    raise ValueError('Invalid content type')
                
                # Đọc toàn bộ dữ liệu
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # Lấy boundary
                boundary = content_type.split('boundary=')[1]
                boundary_bytes = ('--' + boundary).encode()
                
                # Tìm file data
                parts = post_data.split(boundary_bytes)
                
                file_data = None
                file_name = None
                
                for part in parts:
                    if b'filename=' in part and b'Content-Type:' in part:
                        # Tìm tên file
                        filename_match = part.find(b'filename="')
                        if filename_match != -1:
                            start = filename_match + 10
                            end = part.find(b'"', start)
                            file_name = part[start:end].decode('utf-8')
                        
                        # Tìm dữ liệu file (sau 2 CRLF)
                        data_start = part.find(b'\r\n\r\n')
                        if data_start != -1:
                            file_data = part[data_start + 4:]
                            # Loại bỏ trailing CRLF
                            if file_data.endswith(b'\r\n'):
                                file_data = file_data[:-2]
                            break
                
                if not file_data or not file_name:
                    raise ValueError('No file found in request')
                
                # Lưu file với tên mới để tránh conflict
                import time
                timestamp = int(time.time())
                base_name, ext = os.path.splitext(file_name)
                new_file_name = f"{base_name}_{timestamp}{ext}"
                file_path = os.path.join(os.getcwd(), new_file_name)
                
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                
                # Chạy conversion
                import subprocess
                result = subprocess.run(
                    ['python', 'convert_to_json.py'],
                    capture_output=True,
                    timeout=60,
                    cwd=os.getcwd(),
                    text=True
                )
                
                if result.returncode == 0:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'status': 'success',
                        'message': 'File đã được xử lý thành công'
                    }).encode())
                else:
                    raise Exception(result.stderr or result.stdout or 'Conversion failed')
                    
            except Exception as e:
                print(f"ERROR in upload: {e}")
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': str(e)
                }).encode())
        
        elif parsed_path.path == '/save_shelf_life':
            # Đọc dữ liệu từ request
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            product_code = data.get('product_code')
            lot_number = data.get('lot_number', '')
            shelf_life_months = data.get('shelf_life_months')
            
            # Tạo unique key từ product_code + lot_number
            unique_key = f"{product_code}_{lot_number}" if lot_number else str(product_code)
            
            # Load config
            try:
                with open('product_config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                config = {
                    "shelf_life_months": {
                        "BAKING SODA": 36,
                        "AZARINE": 36,
                        "PIN FUJITSU": {}
                    },
                    "product_specific_shelf_life": {}
                }
            
            # Lưu thời hạn cho sản phẩm với unique key
            config['product_specific_shelf_life'][unique_key] = shelf_life_months
            
            # Ghi vào file
            with open('product_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # Chạy lại conversion để tính toán lại % còn lại
            import subprocess
            try:
                result = subprocess.run(['python', 'convert_to_json.py'], 
                             capture_output=True, 
                             timeout=30,
                             cwd=os.getcwd(),
                             text=True)
                
                if result.returncode != 0:
                    print(f"Lỗi khi chạy conversion: {result.stderr}")
                else:
                    print(f"✓ Conversion thành công cho {unique_key}")
            except Exception as e:
                print(f"Lỗi khi chạy conversion: {e}")
            
            # Trả về response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'message': 'Đã lưu thời hạn thành công'
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Xử lý OPTIONS request cho CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

# Đổi thư mục làm việc
os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = MyHTTPRequestHandler

print(f"🚀 Đang khởi động server...")
print(f"📂 Thư mục: {os.getcwd()}")
print(f"🌐 Địa chỉ: http://localhost:{PORT}")
print(f"\n✓ Server đã sẵn sàng!")
print(f"👉 Mở trình duyệt và truy cập: http://localhost:{PORT}")
print(f"\n⚠️  Nhấn Ctrl+C để dừng server\n")

# Tự động mở trình duyệt
webbrowser.open(f'http://localhost:{PORT}')

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✓ Đã dừng server!")
