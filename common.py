"""Small HTTP toolkit; all services bind to loopback only."""
import json, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / 'web'
def now(): return time.time()
def request(url, data=None, timeout=8):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, body, {'Content-Type': 'application/json'} if body else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        with e:
            result = json.load(e)
            result['_status'] = e.code
        return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def json(self, obj, status=200):
        payload = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        try: self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass
    def body(self):
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
            raise ValueError('Cross-origin writes are not allowed')
        if self.headers.get_content_type() != 'application/json': raise ValueError('JSON required')
        size = int(self.headers.get('Content-Length', 0))
        if size > 65536: raise ValueError('Request too large')
        return json.loads(self.rfile.read(size) or b'{}')
    def static(self, name):
        allowed = {'index.html','payflow.html','app.js','style.css','payflow.js','favicon.svg','ux.js','theme.css'}
        if name not in allowed: return self.json({'error':'Not found'},404)
        path = WEB / name
        if not path.is_file(): return self.json({'error':'Not found'},404)
        data = path.read_bytes()
        mime = {'.html':'text/html; charset=utf-8','.css':'text/css','.js':'application/javascript','.svg':'image/svg+xml'}[path.suffix]
        self.send_response(200); self.send_header('Content-Type',mime)
        self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(data)))
        self.end_headers(); self.wfile.write(data)

class LocalHTTPServer(ThreadingHTTPServer):
    request_queue_size=64
    daemon_threads=True

def server(port, handler):
    return LocalHTTPServer(('127.0.0.1', port), handler)
