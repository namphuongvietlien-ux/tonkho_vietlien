from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            product_code = data.get('product_code')
            lot_number = data.get('lot_number')
            shelf_life_months = data.get('shelf_life_months')
            
            if not all([product_code, lot_number, shelf_life_months]):
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'success': False, 'message': 'Missing required fields'})
                self.wfile.write(response.encode())
                return
            
            # Get the directory of the current script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            config_path = os.path.join(parent_dir, 'product_config.json')
            
            # Load existing config
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {
                    "shelf_life_months": {
                        "BAKING SODA": 36,
                        "AZARINE": 36,
                        "PIN FUJITSU": {}
                    },
                    "product_specific_shelf_life": {}
                }
            
            # Create unique key
            unique_key = f"{product_code}_{lot_number}"
            
            # Update product-specific shelf life
            if "product_specific_shelf_life" not in config:
                config["product_specific_shelf_life"] = {}
            
            config["product_specific_shelf_life"][unique_key] = int(shelf_life_months)
            
            # Save config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # Run conversion
            try:
                import convert_to_json
                
                # Change to parent directory temporarily
                old_cwd = os.getcwd()
                os.chdir(parent_dir)
                
                convert_to_json.convert_excel_to_json()
                
                os.chdir(old_cwd)
            except Exception as e:
                print(f"Conversion error: {e}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'success': True, 'message': 'Shelf life saved successfully'})
            self.wfile.write(response.encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'success': False, 'message': f'Error: {str(e)}'})
            self.wfile.write(response.encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
