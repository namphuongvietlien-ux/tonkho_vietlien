from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import subprocess
import tempfile
from datetime import datetime

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
                self.send_error(400, "No boundary in Content-Type")
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
            
            # Get the directory of the current script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            
            # Path to conversion script
            conversion_script = os.path.join(parent_dir, 'convert_to_json.py')
            
            # Run conversion
            try:
                result = subprocess.run(
                    [sys.executable, conversion_script, file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = json.dumps({
                        'success': True,
                        'message': 'File uploaded and converted successfully',
                        'filename': new_filename
                    })
                    self.wfile.write(response.encode())
                else:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = json.dumps({
                        'success': False,
                        'message': f'Conversion failed: {result.stderr}'
                    })
                    self.wfile.write(response.encode())
            except subprocess.TimeoutExpired:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({
                    'success': False,
                    'message': 'Conversion timeout'
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
