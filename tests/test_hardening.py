"""Hardening contracts plus real HTTP heroes; external-model responses are explicitly mocked."""
import copy,io,json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import test_system as system
from test_system import request,BASE
from test_multiapp import api,voice,wait
from investigator import diagnose,enrich_with_ai
from ai_reasoning import bounded_input,validate
from reporting import report,recovery
from application import build_plan
from patch_safety import PatchExecutor
from source_provider import digest
from test_upgrade import HEALTHY

class ReasoningContracts(unittest.TestCase):
 def setUp(self):
  self.evidence=[{'id':'E-001','application_id':'demo','incident_id':'INC-1','source_type':'LOG','metadata':{'records':[{'code':'ERROR','scenario':'SECRET_SCENARIO'}]}}]
  self.context={'application_id':'demo','incident_id':'INC-1','services':['payment-service'],'allowed_files':['payment_logic.py'],'expected_repair':'DO_NOT_SEND'}
  self.rca={'primary_hypothesis':'Observed processing failure','affected_services':['payment-service'],'supporting_evidence_ids':['E-001'],'contradicting_evidence_ids':[],'alternative_hypotheses':[],'eliminated_hypotheses':[],'recommended_action':'Review the bounded edit','requires_more_evidence':False}
  self.fallback={'action':'restore_cleanup','title':'EXPECTED_RCA_MUST_NOT_BE_SENT','confidence':95,'affected_component':'payment-service','requires_more_evidence':False}
 def response(self,value,status='completed'):
  return io.BytesIO(json.dumps({'id':'mock-response','status':status,'output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}]}).encode())
 def test_bounded_input_excludes_labels_and_expected_answers(self):
  encoded=bounded_input(self.evidence,self.context)
  for text in ('SECRET_SCENARIO','expected_repair','DO_NOT_SEND','EXPECTED_RCA_MUST_NOT_BE_SENT'):self.assertNotIn(text,encoded)
  self.assertIn('ERROR',encoded)
  with self.assertRaises(ValueError):bounded_input([{'id':str(i),'metadata':{'a':'x'*24000,'b':'y'*24000}} for i in range(4)],self.context)
 def test_live_contract_primary_provenance_and_real_patch_validation(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory);broken='def process(pool, charge, save):\n    connection = pool.acquire()\n    return charge()\n';(path/'payment_logic.py').write_text(broken)
   edit={'path':'payment_logic.py','original_hash':digest(broken),'content':HEALTHY};value={'rca':self.rca,'patch':[edit]};seen=[]
   def provider(req,**kwargs):seen.append(json.loads(req.data));return self.response(value)
   with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_MODEL':'mock-model'}),patch('urllib.request.urlopen',side_effect=provider):r=enrich_with_ai(self.evidence,self.fallback,self.context)
   self.assertEqual(r['ai_mode'],'LIVE AI');self.assertEqual(r['title'],self.rca['primary_hypothesis']);self.assertEqual(r['action'],'apply_ai_patch')
   self.assertNotIn(self.fallback['title'],seen[0]['input']);self.assertEqual(r['ai_audit']['patch_source'],'AI GENERATED');self.assertTrue(r['ai_audit']['response_validated'])
   from payflow_adapter import PayFlowAdapter
   adapter=PayFlowAdapter(BASE);executor=PatchExecutor(path,path/'audit')
   with patch.object(adapter,'validate_patch',side_effect=executor.validate),patch.object(adapter,'propose',side_effect=AssertionError('Deterministic proposal must not replace valid AI patch')):
    plan=build_plan(adapter,r,{'deployment':{'sha':'abc'},'local_source':{'hashes':{'payment_logic.py':digest(broken)}}})
   self.assertEqual(plan['patch_source'],'AI GENERATED');self.assertEqual(plan['risk'],'HIGH');self.assertEqual((path/'payment_logic.py').read_text(),broken)
   with self.assertRaises(ValueError):executor.apply([edit])
   executor.apply([edit],approved=True);self.assertEqual((path/'payment_logic.py').read_text(),HEALTHY)
 def test_invalid_ids_refusal_and_provider_failure_are_explicit_fallback(self):
  value={'rca':copy.deepcopy(self.rca),'patch':[]};value['rca']['eliminated_hypotheses']=[{'title':'Other cause','reason':'No match','evidence_ids':['E-999']}]
  with self.assertRaises(ValueError):validate(value,{'E-001'},{'payment-service'},{'payment_logic.py'})
  with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_MODEL':'mock-model'}):
   for response in (self.response(value),self.response({'rca':self.rca,'patch':[]},'incomplete'),io.BytesIO(json.dumps({'output':[{'content':[{'type':'refusal','refusal':'No'}]}]}).encode())):
    with patch('urllib.request.urlopen',return_value=response):r=enrich_with_ai(self.evidence,self.fallback,self.context)
    self.assertEqual(r['ai_mode'],'DETERMINISTIC FALLBACK');self.assertEqual(r['ai_status'],'FAILED');self.assertNotIn('test-only',json.dumps(r))
   with patch('urllib.request.urlopen',side_effect=OSError('test-only secret')):r=enrich_with_ai(self.evidence,self.fallback,self.context)
   self.assertNotIn('test-only',json.dumps(r))
 def test_insufficient_live_proposal_cannot_patch_and_contradictions_reduce_score(self):
  values=[]
  with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_MODEL':'mock-model'}):
   for contradict in ([],['E-001']):
    rca={**self.rca,'contradicting_evidence_ids':contradict,'requires_more_evidence':True}
    with patch('urllib.request.urlopen',return_value=self.response({'rca':rca,'patch':[]})):values.append(enrich_with_ai(self.evidence,self.fallback,self.context))
  self.assertIsNone(values[0]['action']);self.assertTrue(values[0]['requires_more_evidence']);self.assertLess(values[1]['confidence'],values[0]['confidence'])
  with patch.dict(os.environ,{'OPENAI_API_KEY':'','OPENAI_MODEL':''}),patch('urllib.request.urlopen',side_effect=AssertionError('No credential means no request')):
   result=enrich_with_ai(self.evidence,self.fallback,self.context)
  self.assertEqual(result['ai_status'],'NOT_CONFIGURED');self.assertEqual(result['ai_mode'],'DETERMINISTIC FALLBACK')

class HardeningHTTP(unittest.TestCase):
 setUpClass=classmethod(system.SystemTest.setUpClass.__func__)
 tearDownClass=classmethod(system.SystemTest.tearDownClass.__func__)
 def setUp(self):
  for app in ('payflow','converselab'):
   wait(lambda s:s['connected'] and not s['busy'] and (not s['incident'] or s['incident']['status']!='investigating'),app)
   api('traffic',{'enabled':False},app);api('reset',{},app)
 def approve(self,i,app):
  self.assertEqual(i['status'],'awaiting_approval');api('approve',{'plan_id':i['plan']['id']},app)
  done=wait(lambda s:s['incident']['status'] in ('resolved','verification_failed'),app)['incident'];self.assertEqual(done['status'],'resolved');return done
 def test_payflow_manual_hero_comparison_copilot_and_shared_report(self):
  self.assertTrue(api('pay',{},'payflow')['ok']);p=Path(self.tmp.name)/'payflow-repo'/'payment_logic.py';original=p.read_text()
  broken=original.replace('    try:\n','').replace('    finally:\n        pool.release(connection)\n','').replace('        ','    ');p.write_text(broken)
  wait(lambda s:s['telemetry']['local_source']['hashes']['payment_logic.py']==digest(broken),'payflow')
  responses=[api('pay',{},'payflow') for _ in range(9)];self.assertTrue(any(not r['ok'] for r in responses))
  i=wait(lambda s:s['incident'] and s['incident']['status']=='awaiting_approval','payflow')['incident']
  self.assertEqual(i['failure_type'],'UNKNOWN');self.assertEqual(i['rca']['ai_mode'],'DETERMINISTIC FALLBACK');self.assertEqual(i['plan']['patch_source'],'DETERMINISTIC FALLBACK');self.assertEqual(p.read_text(),broken)
  questions={'What changed?':'pool.release','Why does this need approval?':'Risk:','Show evidence':'E-001','What alternatives were eliminated?':'Bank outage','Why this RCA?':'connections'}
  for q,expected in questions.items():self.assertIn(expected,api('chat',{'message':q},'payflow')['answer'])
  done=self.approve(i,'payflow');self.assertEqual(done['verification']['fresh_requests'],18);self.assertTrue(api('pay',{},'payflow')['ok'])
  values={r['label']:r for r in done['recovery_comparison']};self.assertEqual(values['DB pool']['before'],'100%');self.assertEqual(values['DB pool']['after'],'0%');self.assertEqual(values['Success']['after'],'100.0%')
  exported=api('report',app='payflow');self.assertTrue({'Recovery metrics','Verification'}.issubset({s['title'] for s in exported['sections']}));self.assertIn('Recovery metrics',exported['markdown']);self.assertIn('Human approval recorded',exported['markdown']);self.assertIn('connection release',exported['markdown'])
 def test_converselab_hero_comparison_report_and_scope(self):
  self.assertTrue(voice()['ok']);request(f'http://127.0.0.1:{BASE+10}/control',{'action':'tts'});self.assertEqual(voice()['_status'],503);voice();self.assertTrue(voice('chat')['ok'])
  i=wait(lambda s:s['incident'] and s['incident']['status']=='awaiting_approval')['incident'];done=self.approve(i,'converselab')
  self.assertEqual(done['verification']['fresh_requests'],8);self.assertTrue(voice()['ok']);values={r['label']:r for r in done['recovery_comparison']};self.assertEqual(values['tts-service']['before'],'UNHEALTHY');self.assertEqual(values['tts-service']['after'],'HEALTHY')
  data=api('report');self.assertIn('speech-delivery',data['markdown']);self.assertNotIn('pool pressure',data['markdown']);self.assertNotIn('connection release',data['markdown'])
  report_url=f'http://127.0.0.1:{BASE}/api/report?application_id=payflow&incident_id='+done['id'];self.assertEqual(request(report_url)['_status'],404)
 def test_failed_recovery_stays_open_and_local_escalation_records_no_notification(self):
  api('scenario',{'scenario':'leak'},'payflow');i=wait(lambda s:s['incident'] and s['incident']['status']=='awaiting_approval','payflow')['incident']
  p=Path(self.tmp.name)/'payflow-repo'/'payment_logic.py';p.write_text(p.read_text()+'\n# newer human edit\n')
  api('approve',{'plan_id':i['plan']['id']},'payflow');done=wait(lambda s:s['incident']['status']=='verification_failed','payflow')['incident']
  self.assertNotIn('resolved_at',done);self.assertTrue(api('escalate',{},'payflow')['ok']);done=api('state',app='payflow')['incident']
  self.assertEqual(done['status'],'verification_failed');self.assertIn('No external notification',done['escalation']['note'])
  self.assertIn('Recovery not verified; incident remains open',api('report',app='payflow')['markdown'])
