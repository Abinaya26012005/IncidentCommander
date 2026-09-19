import copy, json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
import test_system as system
from test_system import api, wait_for, request, BASE, ROOT
from patch_safety import PatchExecutor, validate_python, validate_config
from source_provider import digest
from investigator import validate_hypothesis, enrich_with_ai

HEALTHY='def process(pool, charge, save):\n    connection = pool.acquire()\n    try:\n        result = charge()\n        save(connection, result)\n        return result\n    finally:\n        pool.release(connection)\n'

class UpgradeIntegration(unittest.TestCase):
    setUpClass=classmethod(system.SystemTest.setUpClass.__func__)
    tearDownClass=classmethod(system.SystemTest.tearDownClass.__func__)
    setUp=system.SystemTest.setUp

    def approve(self,i):
        self.assertTrue(i['plan']['validation']['passed'])
        self.assertTrue(api('approve',{'plan_id':i['plan']['id']})['ok'])
        result=wait_for(lambda s:s['incident']['status'] in ('resolved','verification_failed'),35)['incident']
        self.assertEqual(result['status'],'resolved',json.dumps(result.get('verification') or result['timeline'][-1]))
        return result

    def test_manual_source_edit_unknown_patch_approval_recovery_and_rollback(self):
        self.assertTrue(api('pay',{})['ok'])
        source=Path(self.tmp.name)/'payflow-repo'/'payment_logic.py'
        original=source.read_text()
        changed=original.replace('    try:\n','').replace('    finally:\n        pool.release(connection)\n','').replace('        ','    ')
        source.write_text(changed)
        wait_for(lambda s:s['telemetry']['local_source']['hashes']['payment_logic.py']==digest(changed))
        for _ in range(9):api('pay',{})
        i=wait_for(lambda s:s['incident'] and s['incident']['status']=='awaiting_approval')['incident']
        self.assertEqual(i['failure_type'],'UNKNOWN')
        self.assertEqual(i['plan']['action'],'restore_cleanup')
        git=next(e for e in i['evidence'] if e['source_type']=='GIT')
        self.assertIn('-        pool.release(connection)',git['metadata']['local']['working_diff'])
        self.assertIn('M payment_logic.py',git['metadata']['local']['status'])
        def keys(obj):
            if isinstance(obj,dict):
                for k,v in obj.items():yield k;yield from keys(v)
            elif isinstance(obj,list):
                for v in obj:yield from keys(v)
        self.assertFalse({'scenario','scenario_id','injected_cause'}&set(keys(i)))
        self.assertEqual(source.read_text(),changed,'A proposal must not apply itself')
        self.assertEqual(api('approve',{'plan_id':'unapproved'})['_status'],409)
        done=self.approve(i)
        self.assertIn('finally:',source.read_text());self.assertTrue(api('pay',{})['ok'])
        self.assertTrue(api('rollback',{})['ok'])
        self.assertEqual(source.read_text(),changed)
        self.assertEqual(api('state')['incident']['status'],'needs_attention')
        audit=json.loads((Path(self.tmp.name)/'patch-audit'/(done['patch_audit_id']+'.json')).read_text())
        self.assertEqual(audit['result'],'rolled_back')

    def test_unexpected_runtime_exception_escalates_without_llm(self):
        source=Path(self.tmp.name)/'payflow-repo'/'payment_logic.py'
        content='def process(pool, charge, save):\n    raise RuntimeError("judge unexpected failure")\n'
        source.write_text(content)
        wait_for(lambda s:s['telemetry']['local_source']['hashes']['payment_logic.py']==digest(content))
        api('pay',{});api('pay',{})
        i=wait_for(lambda s:s['incident'] and s['incident']['status']=='needs_attention')['incident']
        self.assertEqual(i['failure_type'],'UNKNOWN');self.assertIsNone(i['plan'])
        self.assertEqual(i['rca']['status'],'INSUFFICIENT_EVIDENCE');self.assertEqual(i['rca']['ai_status'],'NOT_CONFIGURED')
        logs=next(e for e in i['evidence'] if e['source_type']=='LOG')['metadata']['records']
        self.assertTrue(any(r.get('detail',{}).get('frames') for r in logs if r.get('detail')))

    def test_eight_additional_observed_failure_classes(self):
        cases={'latency':'restore_latency','database':'restore_database','code':'restore_code','order':'restore_order','endpoint':'restore_endpoint','pool':'restore_pool','gateway':'restore_gateway','processing':'restore_processing'}
        for scenario,expected in cases.items():
            with self.subTest(scenario=scenario):
                self.setUp();self.assertTrue(api('scenario',{'scenario':scenario})['ok'])
                i=wait_for(lambda s:s['incident'] and s['incident']['status'] in ('awaiting_approval','needs_attention'),35)['incident']
                self.assertEqual(i['status'],'awaiting_approval',json.dumps(i.get('rca'))+json.dumps(i.get('plan')))
                self.assertEqual(i['plan']['action'],expected)
                self.approve(i)

    def test_reject_and_changed_source_cannot_apply(self):
        api('scenario',{'scenario':'leak'})
        i=wait_for(lambda s:s['incident'] and s['incident']['status']=='awaiting_approval')['incident']
        source=Path(self.tmp.name)/'payflow-repo'/'payment_logic.py';old=source.read_text()
        self.assertTrue(api('reject',{})['ok']);self.assertEqual(source.read_text(),old)
        self.assertEqual(api('approve',{'plan_id':i['plan']['id']})['_status'],409)
        api('reinvestigate',{})
        i=wait_for(lambda s:s['incident']['status']=='awaiting_approval')['incident']
        source.write_text(old+'\n# another human edit\n')
        api('approve',{'plan_id':i['plan']['id']})
        i=wait_for(lambda s:s['incident']['status']=='verification_failed')['incident']
        self.assertIn('Source changed',i['timeline'][-1]['text'])

class PatchSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.repo=Path(self.tmp.name)/'repo';self.repo.mkdir()
        (self.repo/'payment_logic.py').write_text('def process(pool, charge, save):\n    raise RuntimeError("broken")\n')
        self.executor=PatchExecutor(self.repo,Path(self.tmp.name)/'audit')
    def tearDown(self):self.tmp.cleanup()
    def edit(self,path='payment_logic.py',content=HEALTHY):return {'path':path,'original_hash':digest((self.repo/'payment_logic.py').read_text()),'content':content}
    def test_paths_and_secret_files_are_rejected(self):
        for path in ('../commander.py','/etc/passwd','C:\\Windows\\file','nested/../../payment_logic.py','.env','credentials.json','commander.py'):
            with self.subTest(path=path),self.assertRaises(ValueError):self.executor.validate([self.edit(path)])
    def test_commands_imports_and_indirect_execution_are_rejected(self):
        for content in ('import os\n'+HEALTHY,'def process(pool, charge, save):\n    __import__("os").system("bad")\n','def process(pool, charge, save):\n    open(".env")\n','def process(pool, charge, save):\n    while True: pass\n'):
            with self.assertRaises(ValueError):self.executor.validate([self.edit(content=content)])
        e=self.edit();e['command']='whoami'
        with self.assertRaises(ValueError):self.executor.validate([e])
    def test_functional_validation_rejects_leaks_and_invalid_returns(self):
        for source in ('def process(pool, charge, save):\n    connection = pool.acquire()\n    return charge()\n','def process(pool, charge, save):\n    return None\n'):
            with self.assertRaises(ValueError):self.executor.validate([self.edit(content=source)])
    def test_approval_hash_checks_and_exact_rollback(self):
        original=(self.repo/'payment_logic.py').read_text();edit=self.edit()
        self.assertTrue(self.executor.validate([edit])['passed'])
        with self.assertRaises(ValueError):self.executor.apply([edit])
        record=self.executor.apply([edit],approved=True)
        self.assertEqual((self.repo/'payment_logic.py').read_text(),HEALTHY)
        self.executor.rollback(record);self.assertEqual((self.repo/'payment_logic.py').read_text(),original)
        edit['original_hash']='stale'
        with self.assertRaises(ValueError):self.executor.apply([edit],approved=True)
    def test_rollback_refuses_new_human_changes(self):
        record=self.executor.apply([self.edit()],approved=True)
        (self.repo/'payment_logic.py').write_text(HEALTHY+'# new change\n')
        with self.assertRaises(ValueError):self.executor.rollback(record)
    def test_structured_ai_validation_and_mocked_adapter(self):
        value={'primary_hypothesis':'Small source regression','affected_component':'payment-service','suspected_file':'payment_logic.py','suspected_change':'A new exception precedes payment','supporting_evidence_ids':['E-001'],'contradicting_evidence_ids':[],'alternative_hypotheses':[],'recommended_action':'Review a patch','requires_more_evidence':False,'patch':[self.edit()]}
        self.assertEqual(validate_hypothesis(value,{'E-001'}),value)
        bad=copy.deepcopy(value);bad['supporting_evidence_ids']=['E-999']
        with self.assertRaises(ValueError):validate_hypothesis(bad,{'E-001'})
        bad=copy.deepcopy(value);bad['requires_more_evidence']=True
        with self.assertRaises(ValueError):validate_hypothesis(bad,{'E-001'})
        import io
        proposal={'rca':{'primary_hypothesis':'Small source regression','affected_services':['payment-service'],'supporting_evidence_ids':['E-001'],'contradicting_evidence_ids':[],'alternative_hypotheses':[],'eliminated_hypotheses':[],'recommended_action':'Review a bounded source edit','requires_more_evidence':False},'patch':[self.edit()]}
        response={'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(proposal)}]}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_MODEL':'test-only'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
            result=enrich_with_ai([{'id':'E-001','source_type':'LOG','metadata':{}}],{'action':None,'confidence':0},{'services':['payment-service'],'allowed_files':['payment_logic.py']})
        self.assertEqual(result['ai_status'],'VALIDATED');self.assertEqual(result['hypothesis']['patch'],value['patch'])

class UIStateTests(unittest.TestCase):
    def test_copilot_modes_escape_and_persistence_contract(self):
        code="""const assert=require('node:assert/strict');const u=require('./web/ux.js');let state='closed';for(const [event,expected] of [['open','panel'],['expand','expanded'],['restore','panel'],['expand','expanded'],['escape','panel'],['minimize','closed'],['open','panel'],['close','closed']]){state=u.transition(state,event);assert.equal(state,expected)}const conversation=['message'];u.transition('panel','close');u.transition('closed','open');assert.deepEqual(conversation,['message']);"""
        subprocess.run(['node','-e',code],cwd=ROOT,check=True,capture_output=True)
    def test_theme_selection_overrides_system_and_persists(self):
        code="""const assert=require('node:assert/strict');const u=require('./web/ux.js');let saved;const storage={getItem:()=>saved,setItem:(_,v)=>saved=v};assert.equal(u.preferred(storage,true),'dark');u.storeTheme(storage,'light');assert.equal(u.preferred(storage,true),'light');u.storeTheme(storage,'dark');assert.equal(u.preferred(storage,false),'dark');"""
        subprocess.run(['node','-e',code],cwd=ROOT,check=True,capture_output=True)
