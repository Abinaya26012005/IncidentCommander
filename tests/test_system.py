"""Integration suite uses separate ports and a temporary runtime, never the demo data."""
import json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from common import request
from investigator import diagnose, validate_analysis

BASE=8897
URL=f'http://127.0.0.1:{BASE}'
def api(path,body=None): return request(URL+'/api/'+path,body)
def wait_for(predicate,timeout=60):
    end=time.time()+timeout
    while time.time()<end:
        value=api('state')
        if predicate(value): return value
        time.sleep(.2)
    raise AssertionError('State timeout: '+json.dumps(value.get('incident'))[:500])

class SystemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='ic-tests-')
        cls.env={**os.environ,'IC_BASE_PORT':str(BASE),'IC_DATA_DIR':cls.tmp.name,'OPENAI_API_KEY':'','OPENAI_MODEL':''}
        cls.output=open(Path(cls.tmp.name)/'server.log','w')
        cls.proc=subprocess.Popen([sys.executable,str(ROOT/'run.py')],env=cls.env,stdout=cls.output,stderr=cls.output,cwd=ROOT)
        for _ in range(80):
            try:
                if api('state')['connected']: return
            except OSError: pass
            time.sleep(.2)
        raise RuntimeError('Test services did not start')
    @classmethod
    def tearDownClass(cls):
        # On Windows kill only this test runner's process tree, not the live demo.
        if os.name=='nt': subprocess.run(['taskkill','/PID',str(cls.proc.pid),'/T','/F'],capture_output=True)
        else: cls.proc.terminate()
        cls.proc.wait(timeout=10);cls.output.close();cls.tmp.cleanup()
    def setUp(self):
        wait_for(lambda s:not s['busy'] and (not s['incident'] or s['incident']['status']!='investigating'))
        api('traffic',{'enabled':False}); self.assertTrue(api('reset',{})['ok'])
    def test_01_healthy_payment_is_real_and_releases_pool(self):
        r=api('pay',{});self.assertTrue(r['ok']);self.assertTrue(r['id'].startswith('TXN-'))
        import sqlite3
        with closing(sqlite3.connect(str(Path(self.tmp.name)/'payments.db'))) as db:
            self.assertEqual(db.execute('SELECT amount FROM payments WHERE id=?',(r['id'],)).fetchone()[0],3599)
        t=request(f'http://127.0.0.1:{BASE+2}/telemetry')
        self.assertEqual(t['metrics']['pool']['used'],0)
        self.assertEqual(t['events'][-1]['trace_id'],r['trace_id'])
        self.assertNotIn('scenario',t)
    def scenario_roundtrip(self,kind,expected):
        self.assertTrue(api('scenario',{'scenario':kind})['ok'])
        s=wait_for(lambda s:s['incident'] and s['incident']['status']=='awaiting_approval')
        i=s['incident']; self.assertEqual(i['plan']['action'],expected)
        self.assertEqual(len(i['evidence']),10)
        self.assertTrue(set(i['rca']['citations']).issubset({e['id'] for e in i['evidence']}))
        self.assertFalse(api('pay',{})['ok'])
        self.assertEqual(api('approve',{'plan_id':'invalid'})['_status'],409)
        self.assertTrue(api('approve',{'plan_id':i['plan']['id']})['ok'])
        self.assertEqual(api('approve',{'plan_id':i['plan']['id']})['_status'],409)
        resolved=wait_for(lambda s:s['incident']['status'] in ('resolved','verification_failed'))['incident']
        self.assertEqual(resolved['status'],'resolved',json.dumps(resolved.get('verification') or resolved['timeline'][-2:]))
        self.assertTrue(resolved['verification']['passed'])
        self.assertEqual(len(set(resolved['verification']['traces'])),18)
        self.assertTrue(api('pay',{})['ok'])
        self.assertIn('Recovery verified',api('report')['markdown'])
    def test_02_connection_leak_full_lifecycle(self): self.scenario_roundtrip('leak','restore_cleanup')
    def test_03_bank_failure_full_lifecycle(self): self.scenario_roundtrip('bank','restore_bank')
    def test_04_timeout_failure_full_lifecycle(self): self.scenario_roundtrip('timeout','restore_timeout')
    def test_05_stale_deployment_cannot_be_changed(self):
        api('scenario',{'scenario':'leak'})
        i=wait_for(lambda s:s['incident'] and s['incident']['status']=='awaiting_approval')['incident']
        request(f'http://127.0.0.1:{BASE+2}/control',{'action':'timeout'})
        api('approve',{'plan_id':i['plan']['id']})
        i=wait_for(lambda s:s['incident']['status']=='verification_failed')['incident']
        self.assertIn('Deployment changed',i['timeline'][-1]['text'])
        self.assertIsNone(i['verification'])
    def test_06_failed_live_payments_fail_verification(self):
        request(f'http://127.0.0.1:{BASE+2}/control',{'action':'bank'})
        with patch.dict(os.environ,self.env):
            import commander
        inc={'timeline':[]}
        result=commander.verify(inc)
        self.assertFalse(result['passed']);self.assertFalse(result['checks'][0]['pass'])
        self.assertFalse(result['checks'][3]['pass'])
    def test_07_unknown_or_invented_evidence_is_rejected(self):
        with self.assertRaises(ValueError): validate_analysis({'title':'Cause','explanation':'Claim','citations':['E-999']},{'E-001'})
        with self.assertRaises(ValueError): validate_analysis({'title':'Cause','explanation':'Claim E-999','citations':['E-001']},{'E-001'})
        self.assertIsNone(diagnose([])['action'])
    def test_08_cross_origin_writes_are_rejected(self):
        import urllib.request, urllib.error
        req=urllib.request.Request(URL+'/api/reset',b'{}',{'Content-Type':'application/json','Origin':'https://untrusted.example'})
        with self.assertRaises(urllib.error.HTTPError) as c: urllib.request.urlopen(req)
        self.assertEqual(c.exception.code,409)

if __name__=='__main__': unittest.main(verbosity=2)
