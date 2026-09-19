"""Optional authenticated, single-session gateway. Existing services stay loopback-only."""
import hashlib
import hmac
import http.client
import json
import os
import re
import secrets
import threading
import time
from collections import deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

STATIC = {'/', '/index.html', '/app.js', '/style.css', '/favicon.svg', '/ux.js', '/theme.css', '/context-ui.js', '/context.css', '/payflow.js'}
READS = {'/health', '/api/applications', '/api/incidents', '/api/state', '/api/runbooks', '/api/tests', '/api/report', '/api/context-optimization/stats'}
WRITES = {'/api/pay', '/api/probe', '/api/chat', '/api/scenario', '/api/reset', '/api/approve', '/api/reinvestigate', '/api/reject', '/api/rollback', '/api/escalate', '/api/traffic'}

def route(path, method):
    if '%' in path or '\\' in path or '..' in path or '//' in path:
        return None
    app, local = 'commander', path
    for name in ('payflow', 'converselab'):
        if path.startswith('/' + name + '/'):
            app, local = name, path[len(name) + 1:]
    if method == 'GET':
        allowed = local in STATIC
        if app == 'commander':
            allowed |= local in READS or bool(re.fullmatch(r'/api/context-optimization/incidents/[A-Za-z0-9-]+(?:/latest)?', local))
        elif app == 'payflow':
            allowed |= local in {'/health', '/api/health', '/api/transactions'}
        else:
            allowed |= local in {'/health', '/api/state', '/api/knowledge'} or bool(re.fullmatch(r'/api/jobs/[A-Za-z0-9-]+', local))
    else:
        allowed = local in (WRITES if app == 'commander' else {'/api/pay'} if app == 'payflow' else {'/api/converse', '/api/conversations', '/control'})
    return (app, local) if allowed else None

def adapt(body, content_type, app, path, ports):
    """Rewrite presentation URLs only; evidence and optimizer records are untouched."""
    if 'json' in content_type:
        data = json.loads(body)
        def links(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {'url', 'application_url', 'payflow_url', 'commander_url'} and isinstance(item, str):
                        for name, port in ports.items():
                            origin = f'http://127.0.0.1:{port}'
                            if item == origin or item.startswith(origin + '/'):
                                prefix = '' if name == 'commander' else '/' + name
                                value[key] = prefix + (item[len(origin):] or '/')
                    elif key in {'application', 'applications'}:
                        links(item)
            elif isinstance(value, list):
                for item in value: links(item)
        links(data)
        return json.dumps(data).encode()
    if 'html' in content_type:
        text = body.decode('utf-8')
        if app == 'commander':
            text = text.replace('href="http://127.0.0.1:8788"', 'href="/payflow/"')
        if app != 'commander':
            text = re.sub(r'(\b(?:src|href)=[\"\'])/(?!/)', r'\1/' + app + '/', text)
        bar = '<nav style="padding:10px;background:#17243b;color:white;font:14px sans-serif"><a style="color:white" href="/demo">Demo home / End session</a> · One judge session · Simulated external providers</nav>'
        text = re.sub(r'(<body[^>]*>)', r'\1' + bar, text, count=1)
        return text.encode()
    if 'javascript' in content_type and app != 'commander':
        text = body.decode('utf-8')
        if app == 'payflow':
            text = text.replace("fetch('/api/", "fetch('/payflow/api/")
        else:
            text = text.replace("fetch('/'+path", "fetch('/converselab/'+path")
            text = text.replace("'http://127.0.0.1:'+(Number(location.port)-10)+'/?application_id=converselab'", "'/?application_id=converselab'")
        return text.encode()
    return body

class DemoState:
    def __init__(self, origin, username, password, base=8787, cl_base=8797, ttl=1200):
        parsed = urlsplit(origin)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError('PUBLIC_ORIGIN must be a bare origin')
        if parsed.scheme != 'https' and parsed.hostname not in {'127.0.0.1', 'localhost'}:
            raise ValueError('Public deployment requires HTTPS')
        if not username or len(password) < 16:
            raise ValueError('Set DEMO_USERNAME and a DEMO_PASSWORD of at least 16 characters')
        self.origin, self.username = origin, username
        self.password_hash = hashlib.sha256(password.encode()).digest()
        self.ports = {'commander': base, 'payflow': base + 1, 'converselab': cl_base}
        self.ttl, self.sid, self.expires = ttl, '', 0
        self.lock = threading.RLock()
        self.rates = {}

    def limited(self, bucket, count):
        with self.lock:
            q = self.rates.setdefault(bucket, deque())
            while q and q[0] < time.monotonic() - 60: q.popleft()
            if len(q) >= count: return True
            q.append(time.monotonic())
            return False

    def upstream(self, app, path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.ports[app], timeout=30)
        try:
            connection.request('GET' if body is None else 'POST', path, body=body,
                               headers={'Content-Type': 'application/json'} if body is not None else {})
            response = connection.getresponse()
            return response.status, response.getheader('Content-Type', 'application/json'), response.read(8_000_001)
        finally:
            connection.close()

    def reset(self):
        # Existing engine locks refuse reset during investigation or execution.
        for app in ('payflow', 'converselab'):
            _, _, raw = self.upstream('commander', '/api/state?application_id=' + app)
            state = json.loads(raw)
            if state['busy'] or (state.get('incident') or {}).get('status') in {'investigating', 'executing', 'verifying'}:
                raise RuntimeError('Busy')
        for app in ('payflow', 'converselab'):
            for action, value in [('traffic', {'enabled': False}), ('reset', {})]:
                code, _, raw = self.upstream('commander', '/api/' + action + '?application_id=' + app, json.dumps(value).encode())
                if code != 200 or not json.loads(raw).get('ok'): raise RuntimeError('Reset incomplete')

class Gateway(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def respond(self, status, body, kind='text/html; charset=utf-8', cookie=None):
        if isinstance(body, str): body = body.encode()
        self.send_response(status)
        for k, v in {'Content-Type': kind, 'Content-Length': str(len(body)), 'Cache-Control': 'no-store',
                     'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'same-origin',
                     'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                     'Connection': 'close'}.items(): self.send_header(k, v)
        if cookie: self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def page(self, title, content):
        return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>IncidentCommander demo</title></head><body style="background:#f3f5fb;font:17px system-ui;color:#17243b;max-width:680px;margin:8vh auto;padding:24px"><h1>' + title + '</h1>' + content + '</body></html>'

    def error(self, status, message):
        self.respond(status, json.dumps({'error': message}), 'application/json')

    def cookie(self, value, seconds):
        secure = '; Secure' if self.server.demo.origin.startswith('https:') else ''
        return f'ic_demo={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={seconds}' + secure

    def handle_request(self, method):
        state = self.server.demo
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc: return self.error(400, 'Invalid path')
        path = parsed.path
        if method == 'GET' and path == '/healthz':
            try:
                healthy = all(state.upstream(app, '/health')[0] == 200 for app in state.ports)
                return self.respond(200 if healthy else 503, json.dumps({'ready': healthy}), 'application/json')
            except Exception: return self.error(503, 'Services starting')
        if state.limited('requests', 600): return self.error(429, 'Please slow down')
        if method == 'POST':
            if self.headers.get('Origin') != state.origin: return self.error(403, 'Same-origin request required')
            if self.headers.get('Transfer-Encoding'): return self.error(400, 'Unsupported body framing')
            try: size = int(self.headers.get('Content-Length', '0'))
            except ValueError: return self.error(400, 'Invalid length')
            if not 0 <= size <= 65536: return self.error(413, 'Request too large')
            body = self.rfile.read(size)
        else: body = None
        if path == '/login':
            if method == 'GET':
                return self.respond(200, self.page('IncidentCommander AI', '<p>Private hackathon sandbox. One judge at a time; sessions last 20 minutes. Please use only fictional data.</p><form method="post"><label>Username <input name="username" autocomplete="username" required></label><p><label>Password <input type="password" name="password" autocomplete="current-password" required></label></p><button>Start demo session</button></form>'))
            if state.limited('login', 5): return self.error(429, 'Login limit reached; retry in one minute')
            try: form = parse_qs(body.decode())
            except UnicodeError: return self.error(400, 'Invalid form')
            valid = hmac.compare_digest(form.get('username', [''])[0].encode(), state.username.encode()) & hmac.compare_digest(hashlib.sha256(form.get('password', [''])[0].encode()).digest(), state.password_hash)
            if not valid: return self.error(401, 'Invalid demo credentials')
            with state.lock:
                if state.sid and time.monotonic() < state.expires:
                    return self.respond(409, self.page('Demo currently in use', '<p>Another judge has the sandbox. Please retry after they end their session or its 20-minute lease expires.</p>'))
                try: state.reset()
                except Exception: return self.error(503, 'Waiting for sandbox operations to finish; retry shortly')
                state.sid, state.expires = secrets.token_urlsafe(32), time.monotonic() + state.ttl
                return self.respond(200, self.home(), cookie=self.cookie(state.sid, state.ttl))
        cookies = SimpleCookie()
        try: cookies.load(self.headers.get('Cookie', ''))
        except Exception: return self.error(401, 'Login required')
        token = cookies.get('ic_demo')
        with state.lock:
            if not token or not state.sid or not hmac.compare_digest(token.value.encode(), state.sid.encode()) or time.monotonic() >= state.expires:
                if method == 'GET' and path in {'/', '/demo', '/payflow/', '/converselab/'}:
                    return self.respond(401, self.page('Demo access required', '<p><a href="/login">Sign in to start the demo</a></p>'))
                return self.error(401, 'Session expired or login required; open /login')
            if path == '/demo' and method == 'GET': return self.respond(200, self.home())
            if path == '/demo/end' and method == 'POST':
                try: state.reset()
                except Exception: return self.error(409, 'Operation in progress; wait and end the session again')
                state.sid = ''
                return self.respond(200, self.page('Session ended', '<p>The sandbox was reset. <a href="/login">Sign in again</a></p>'), cookie=self.cookie('', 0))
            target = route(path, method)
            if not target: return self.error(404, 'Not found')
            app, local = target
            if method == 'POST':
                if state.limited('writes', 90): return self.error(429, 'Action limit reached; retry shortly')
                if self.headers.get_content_type() != 'application/json': return self.error(415, 'JSON required')
                try: value = json.loads(body)
                except ValueError: return self.error(400, 'Invalid JSON')
                if not isinstance(value, dict): return self.error(400, 'JSON object required')
                if local == '/control' and value.get('action') not in {'tts', 'knowledge', 'stt', 'prompt', 'reset'}:
                    return self.error(403, 'Unsupported sandbox control')
                if any(k in value for k in ('edits', 'token', 'path', 'command', 'shell')):
                    return self.error(403, 'Direct execution is not exposed')
            try:
                code, kind, raw = state.upstream(app, local + ('?' + parsed.query if parsed.query else ''), body)
                if len(raw) > 8_000_000: return self.error(502, 'Response too large')
                # Expected sandbox failures contain real trace/voice results needed by the UI.
                if code >= 500 and local not in {'/api/pay', '/api/converse', '/api/health'}:
                    return self.error(502, 'Application temporarily unavailable')
                self.respond(code, adapt(raw, kind, app, local, state.ports), kind)
            except Exception: self.error(502, 'Application temporarily unavailable')

    def home(self):
        return self.page('IncidentCommander AI', '<p>Your exclusive demo session is active for up to 20 minutes. External providers are simulated; AI status remains visible in Commander.</p><p><a href="/">Commander</a> · <a href="/payflow/">PayFlow</a> · <a href="/converselab/">ConverseLab</a></p><ol><li>Make a healthy PayFlow payment.</li><li>Commander → Demo lab → Connection leak → Deploy experiment.</li><li>Mission control → evidence, RCA and AI Context.</li><li>Review fix → Approve sandbox fix → fresh verification.</li><li>Explore ConverseLab, then Incident reports.</li></ol><form method="post" action="/demo/end"><button>End session and reset sandbox</button></form>')

    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')

class DemoServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, demo):
        self.demo = demo
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(address, Gateway)
    def process_request(self, request, address):
        if not self.slots.acquire(False):
            request.close()
            return
        try: super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise
    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self.slots.release()

def main():
    if os.environ.get('DEMO_AUTH_ENABLED') != 'true': raise RuntimeError('Public gateway requires DEMO_AUTH_ENABLED=true')
    state = DemoState(os.environ['PUBLIC_ORIGIN'], os.environ['DEMO_USERNAME'], os.environ['DEMO_PASSWORD'],
                      int(os.environ.get('IC_BASE_PORT', '8787')), int(os.environ.get('CL_BASE_PORT', '8797')))
    DemoServer(('0.0.0.0', int(os.environ.get('PORT', '10000'))), state).serve_forever()

if __name__ == '__main__': main()
