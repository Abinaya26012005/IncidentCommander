"""Public gateway acceptance against real, isolated application processes."""
import http.client
import json
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
import test_system as system
from deploy.gateway import DemoServer, DemoState, adapt, route
from deploy.launch import child_environment


class DeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        system.SystemTest.setUpClass.__func__(cls)
        cls.demo = DemoState('http://127.0.0.1', 'demo', 'test-only-placeholder-password', system.BASE, system.BASE + 10)
        cls.server = DemoServer(('127.0.0.1', 0), cls.demo)
        cls.port = cls.server.server_address[1]
        cls.demo.origin = f'http://127.0.0.1:{cls.port}'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        system.SystemTest.tearDownClass.__func__(cls)

    def request(self, path, payload=None, authenticated=True, origin=True, form=False):
        headers = {}
        if authenticated: headers['Cookie'] = getattr(self, 'cookie', '')
        body = None
        if payload is not None:
            body = urlencode(payload) if form else json.dumps(payload)
            headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
            if origin: headers['Origin'] = self.demo.origin
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=35)
        try:
            conn.request('GET' if payload is None else 'POST', path, body, headers)
            response = conn.getresponse()
            raw = response.read()
            return response.status, dict(response.getheaders()), raw
        finally: conn.close()

    def api(self, path, payload=None):
        code, _, body = self.request(path, payload)
        value = json.loads(body)
        value['_status'] = code
        return value

    def wait(self, app, status):
        deadline = time.monotonic() + 65
        while time.monotonic() < deadline:
            state = self.api('/api/state?application_id=' + app)
            incident = state.get('incident')
            if incident and incident['status'] == status: return incident
            time.sleep(.25)
        self.fail(f'{app} did not reach {status}')

    def test_01_routes_and_evidence_adaptation(self):
        for path in ('/.env', '/.git/config', '/patch/apply', '/telemetry', '/payflow/../.env', '/converselab/%2e%2e/x'):
            self.assertIsNone(route(path, 'GET'))
            self.assertIsNone(route(path, 'POST'))
        evidence = {'url': f'http://127.0.0.1:{system.BASE+1}/', 'evidence': [{'url': f'http://127.0.0.1:{system.BASE+1}/'}]}
        changed = json.loads(adapt(json.dumps(evidence).encode(), 'application/json', 'commander', '/', self.demo.ports))
        self.assertEqual(changed['url'], '/payflow/')
        self.assertEqual(changed['evidence'], evidence['evidence'])
        html = b'<body><a href="http://127.0.0.1:8788">Open PayFlow</a></body>'
        self.assertNotIn(b'127.0.0.1', adapt(html, 'text/html', 'commander', '/', self.demo.ports))

    def test_02_authentication_and_full_hero_flows(self):
        self.assertEqual(self.request('/api/state', authenticated=False)[0], 401)
        self.assertEqual(self.request('/healthz', authenticated=False)[0], 200)
        credentials = {'username': 'demo', 'password': 'test-only-placeholder-password'}
        self.assertEqual(self.request('/login', credentials, form=True, origin=False)[0], 403)
        self.assertEqual(self.request('/login', {'username':'demo','password':'wrong'}, form=True)[0], 401)
        code, headers, _ = self.request('/login', credentials, form=True)
        self.assertEqual(code, 200)
        self.cookie = headers['Set-Cookie'].split(';')[0]
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        self.assertEqual(self.request('/login', credentials, form=True, authenticated=False)[0], 409)
        self.assertEqual(self.request('/api/reset', {}, origin=False)[0], 403)
        self.assertEqual(self.request('/patch/apply', {})[0], 404)
        self.assertEqual(self.request('/converselab/control', {'action':'shell'})[0], 403)
        self.assertEqual(self.request('/api/approve', {'path':'/etc/passwd'})[0], 403)
        for path in ('/', '/payflow/', '/converselab/', '/api/applications', '/api/incidents', '/api/runbooks'):
            self.assertEqual(self.request(path)[0], 200, path)
        for path, prefix in [('/payflow/payflow.js', b"fetch('/payflow/api/"), ('/converselab/app.js', b"fetch('/converselab/'+path")]:
            code, _, body = self.request(path)
            self.assertEqual(code, 200)
            self.assertIn(prefix, body)
        self.assertEqual(self.api('/api/state')['application_url'], '/payflow/')
        self.assertTrue(self.api('/payflow/api/pay', {})['ok'])
        self.assertTrue(self.api('/api/scenario?application_id=payflow', {'scenario':'leak'})['ok'])
        incident = self.wait('payflow', 'awaiting_approval')
        failed = self.api('/payflow/api/pay', {})
        self.assertEqual(failed['_status'], 503)
        self.assertIn('trace_id', failed)
        self.assertFalse(failed['ok'])
        context_path = '/api/context-optimization/incidents/' + incident['id'] + '/latest?application_id=payflow'
        code, _, proxied = self.request(context_path)
        direct_code, _, direct = self.demo.upstream('commander', context_path)
        self.assertEqual(code, 200)
        self.assertEqual(direct_code, 200)
        self.assertEqual(json.loads(proxied), json.loads(direct))
        self.assertTrue(self.api('/api/approve?application_id=payflow', {'plan_id':incident['plan']['id']})['ok'])
        done = self.wait('payflow', 'resolved')
        self.assertTrue(done['verification']['passed'])
        self.assertEqual(len(set(done['verification']['traces'])), 18)
        self.assertTrue(self.api('/payflow/api/pay', {})['ok'])
        self.assertEqual(self.request('/api/report?application_id=payflow')[0], 200)
        voice = {'channel':'voice','text':'When is my payment due?'}
        self.assertTrue(self.api('/converselab/api/converse', voice)['ok'])
        self.assertTrue(self.api('/converselab/control', {'action':'tts'})['ok'])
        failed = self.api('/converselab/api/converse', voice)
        self.api('/converselab/api/converse', voice)
        self.assertEqual(failed['_status'], 503)
        self.assertTrue(failed['answer'])
        self.assertEqual(next(s for s in failed['spans'] if s['service']=='tts-service')['status_code'], 503)
        incident = self.wait('converselab', 'awaiting_approval')
        self.assertTrue(self.api('/api/approve?application_id=converselab', {'plan_id':incident['plan']['id']})['ok'])
        done = self.wait('converselab', 'resolved')
        self.assertEqual(done['verification']['fresh_requests'], 8)
        self.assertTrue(self.api('/converselab/api/converse', voice)['ok'])
        self.assertEqual(self.request('/demo/end', {})[0], 200)
        self.assertEqual(self.request('/api/state')[0], 401)
        for app in ('payflow', 'converselab'):
            _, _, raw = self.demo.upstream('commander', '/api/state?application_id=' + app)
            self.assertIsNone(json.loads(raw)['incident'])

    def test_03_fail_closed_and_lease_expiration(self):
        with self.assertRaises(ValueError): DemoState('http://public.example', 'demo', 'long-test-password')
        with self.assertRaises(ValueError): DemoState('https://public.example', 'demo', 'short')
        self.demo.sid = 'expired-test-session'
        self.demo.expires = time.monotonic() - 1
        self.cookie = 'ic_demo=expired-test-session'
        self.assertEqual(self.request('/api/state')[0], 401)
        for _ in range(5): self.demo.limited('test-bucket', 5)
        self.assertTrue(self.demo.limited('test-bucket', 5))

    def test_04_supervisor_environment_keeps_tokenizer_without_credentials(self):
        with patch.dict('os.environ', {'DEMO_PASSWORD':'not-a-real-secret', 'RENDER_API_KEY':'test-only', 'OPENAI_API_KEY':'test-only'}):
            environment = child_environment(system.BASE, system.BASE + 10)
        self.assertNotIn('DEMO_PASSWORD', environment)
        self.assertNotIn('RENDER_API_KEY', environment)
        self.assertEqual(environment['OPENAI_API_KEY'], '')
        result = subprocess.run([sys.executable, '-c', 'from context_optimization.tokenizer import tokenizer; print(tokenizer()[1])'],
                                env=environment, cwd=system.ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0)
        self.assertIn('tiktoken:o200k_base', result.stdout)


if __name__ == '__main__': unittest.main(verbosity=2)
