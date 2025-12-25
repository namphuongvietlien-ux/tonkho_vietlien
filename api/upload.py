from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import tempfile
from datetime import datetime

# Add parent directory to path to import convert module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Get content length
            content_length = int(self.headers['Content-Length'])
            
            # Read the multipart data
            content = self.rfile.read(content_length)
            
            # Parse multipart form data
            content_type = self.headers['Content-Type']
            if 'boundary' not in content_type:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'success': False, 'message': 'No boundary in Content-Type'})
                self.wfile.write(response.encode())
                return
            
            boundary = content_type.split('boundary=')[1].encode()
            
            # Split by boundary
            parts = content.split(b'--' + boundary)
            
            file_data = None
            filename = None
            
            for part in parts:
                if b'Content-Disposition' in part and b'filename=' in part:
                    # Extract filename
                    disposition_line = part.split(b'\r\n')[1].decode()
                    filename_start = disposition_line.find('filename="') + 10
                    filename_end = disposition_line.find('"', filename_start)
                    filename = disposition_line[filename_start:filename_end]
                    
                    # Extract file data
                    file_start = part.find(b'\r\n\r\n') + 4
                    file_end = part.rfind(b'\r\n')
                    file_data = part[file_start:file_end]
                    break
            
            if not file_data or not filename:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'success': False, 'message': 'No file uploaded'})
                self.wfile.write(response.encode())
                return
            
            # Import conversion function
            try:
                import convert_to_json
            except ImportError as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'success': False, 'message': f'Import error: {str(e)}'})
                self.wfile.write(response.encode())
                return
            
            # Get the /tmp directory for Vercel
            tmp_dir = tempfile.gettempdir()
            
            # Add timestamp to filename to avoid conflicts
            timestamp = int(datetime.now().timestamp())
            base_name, ext = os.path.splitext(filename)
            new_filename = f"{base_name}_{timestamp}{ext}"
            
            # Save file to /tmp
            file_path = os.path.join(tmp_dir, new_filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Run conversion directly
            try:
                # Get parent directory and temp directory
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                # On Vercel, we can only write to /tmp
                # So we'll generate JSON and return it directly
                output_path = os.path.join(tmp_dir, 'inventory_data.json')
                
                # Change to parent directory temporarily (for config file access)
                current_dir = os.getcwd()
                os.chdir(parent_dir)
                
                # Run conversion with the uploaded file path
                result_data = convert_to_json.convert_excel_to_json(excel_file=file_path, output_file=output_path)
                
                os.chdir(current_dir)
                
                # Try to copy to parent directory (will work locally, fail on Vercel)
                try:
                    final_output = os.path.join(parent_dir, 'inventory_data.json')
                    with open(output_path, 'r', encoding='utf-8') as src:
                        with open(final_output, 'w', encoding='utf-8') as dst:
                            dst.write(src.read())
                except:
                    pass  # Silently fail on Vercel
                
                # Read the generated JSON
                with open(output_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                # Read the generated JSON
                with open(output_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({
                    'success': True,
                    'message': 'File uploaded and converted successfully',
                    'filename': new_filename,
                    'data': json_data
                })
                self.wfile.write(response.encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({
                    'success': False,
                    'message': f'Conversion failed: {str(e)}'
                })
                self.wfile.write(response.encode())
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({
                'success': False,
                'message': f'Error: {str(e)}'
            })
            self.wfile.write(response.encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
