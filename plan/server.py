import glob
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, HTTPServer
from curl_cffi import requests

URL_CANVAS = 'https://intra.land/api/pixel/canvas?campus=Heilbronn'
ACCOUNTS_DIR = '../accounts'

def get_cookie_string():
    if not os.path.exists(ACCOUNTS_DIR):
        return None
    for filepath in glob.glob(os.path.join(ACCOUNTS_DIR, '*.json')):
        try:
            with open(filepath, 'r') as f:
                raw_cookies = json.load(f)
            return "; ".join([f'{c["name"]}={c["value"]}' for c in raw_cookies])
        except Exception:
            pass
    return None

class ProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/canvas':
            cookie_str = get_cookie_string()
            if not cookie_str:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"No accounts found")
                return
            
            headers = {
                'accept': '*/*',
                'cookie': cookie_str,
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
            }
            try:
                response = requests.get(URL_CANVAS, headers=headers, impersonate="chrome120", timeout=15)
                if response.status_code == 200:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.end_headers()
                    self.wfile.write(response.content)
                else:
                    self.send_response(response.status_code)
                    self.end_headers()
                    self.wfile.write(b"Error fetching canvas")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            super().do_GET()

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    port = 8080
    server = HTTPServer(('localhost', port), ProxyHandler)
    print(f"Starting server on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
