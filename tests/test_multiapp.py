"""Real HTTP two-application acceptance and shared-core isolation checks."""
import copy,json,time,unittest
from pathlib import Path
import test_system as system
from test_system import ROOT,BASE,request
from investigator import diagnose
from application import normalize_evidence,build_plan

def api(path,body=None,app='converselab'):
 return request(f'http://127.0.0.1:{BASE}/api/{path}?application_id={app}',body,timeout=20)
def voice(channel='voice'):
 return request(f'http://127.0.0.1:{BASE+10}/api/converse',{'channel':channel,'text':'When is my payment due?'},timeout=20)
def wait(predicate,app='converselab',timeout=45):
 end=time.time()+timeout
 while time.time()<end:
  s=api('state',app=app)
  if predicate(s):return s
  time.sleep(.15)
 raise AssertionError('State timeout: '+json.dumps(s.get('incident'))[:1400])

class MultiApplicationTests(unittest.TestCase):
 setUpClass=classmethod(system.SystemTest.setUpClass.__func__)
 tearDownClass=classmethod(system.SystemTest.tearDownClass.__func__)
 def setUp(self):
  for app in ('payflow','converselab'):
   wait(lambda s:s['connected'] and not s['busy'] and (not s['incident'] or s['incident']['status']!='investigating'),app)
   api('traffic',{'enabled':False},app);self.assertTrue(api('reset',{},app)['ok'])
 def inject(self,kind):
  self.assertTrue(request(f'http://127.0.0.1:{BASE+10}/control',{'action':kind})['ok'])
 def incident(self):return wait(lambda s:s['incident'] and s['incident']['status'] in ('awaiting_approval','needs_attention'))['incident']
 def approve(self,i):
  self.assertEqual(i['status'],'awaiting_approval',json.dumps(i.get('rca')))
  self.assertTrue(api('approve',{'plan_id':i['plan']['id']})['ok'])
  done=wait(lambda s:s['incident']['status'] in ('resolved','verification_failed'))['incident']
  self.assertEqual(done['status'],'resolved',json.dumps(done.get('verification') or done['timeline'][-1]))
  self.assertEqual(done['application_id'],'converselab');self.assertEqual(done['verification']['fresh_requests'],8)
  self.assertEqual(len(set(done['verification']['traces'])),8)
  return done
 def test_01_healthy_chat_voice_and_trace_continuity(self):
  chat=voice('chat');v=voice();self.assertTrue(chat['ok']);self.assertTrue(v['ok']);self.assertIn('September 25',chat['answer'])
  self.assertEqual({s['service'] for s in chat['spans']},{'conversation-gateway','conversation-service','knowledge-service','llm-service'})
  self.assertEqual(len(v['spans']),6);self.assertTrue(v['speech']['delivered']);self.assertTrue(v['speech']['simulated']);self.assertFalse(v['speech']['audio_available'])
  self.assertTrue(all(s['trace_id']==v['trace_id'] for s in v['spans']))
  t=request(f'http://127.0.0.1:{BASE+10}/telemetry');records=[r for r in t['logs'] if r['trace_id']==v['trace_id']]
  self.assertEqual(len(records),6);self.assertTrue(all(r['conversation_id']==v['conversation_id'] and r['request_id']==v['request_id'] for r in records))
 def test_02_tts_failure_shared_investigation_and_recovery(self):
  self.inject('tts');failed=voice();voice();chat=voice('chat')
  self.assertFalse(failed['ok']);self.assertEqual(failed['_status'],503);self.assertTrue(failed['answer']);self.assertTrue(chat['ok'])
  stage=next(s for s in failed['spans'] if s['service']=='tts-service');self.assertEqual(stage['status_code'],503)
  i=self.incident();self.assertEqual(i['failure_type'],'UNKNOWN');self.assertEqual(i['rca']['affected_component'],'tts-service');self.assertEqual(i['affected_capabilities'],['voice'])
  self.assertEqual(i['plan']['action'],'restore_dependency')
  self.assertEqual(next(e for e in i['evidence'] if e['source_type']=='RUNBOOK')['metadata']['id'],'RB-CONV-003')
  self.assertGreaterEqual(len(i['rca']['alternatives']),3)
  self.assertTrue(all(e['application_id']=='converselab' for e in i['evidence']))
  self.assertTrue(any(m.get('seeded') for e in i['evidence'] if e['source_type']=='HISTORY' for m in e['metadata']['matches']))
  self.assertIsNone(api('state',app='payflow')['incident']);self.approve(i);self.assertTrue(voice()['ok'])
 def test_03_knowledge_failure_distinguished_from_generation(self):
  self.inject('knowledge');a=voice('chat');b=voice();self.assertFalse(a['ok']);self.assertFalse(b['ok'])
  self.assertNotIn('llm-service',{s['service'] for s in b['spans']})
  i=self.incident();self.assertEqual(i['rca']['affected_component'],'knowledge-service')
  self.assertEqual(next(e for e in i['evidence'] if e['source_type']=='RUNBOOK')['metadata']['id'],'RB-CONV-001')
  self.assertFalse(any(m.get('seeded') for e in i['evidence'] if e['source_type']=='HISTORY' for m in e['metadata']['matches']));self.approve(i)
 def test_04_stt_latency_leaves_chat_healthy(self):
  self.inject('stt');voice();voice();chat=voice('chat');self.assertTrue(chat['ok']);self.assertLess(chat['latency'],1800)
  i=self.incident();self.assertEqual(i['rca']['affected_component'],'stt-service');self.assertEqual(i['plan']['action'],'restore_latency');self.approve(i)
 def test_05_manual_prompt_change_diff_and_repair(self):
  path=Path(self.tmp.name)/'converselab'/'repo'/'config.json';cfg=json.loads(path.read_text());cfg['prompt_version']='v2-broken';path.write_text(json.dumps(cfg,indent=2)+'\n')
  wait(lambda s:s['telemetry']['config']['prompt_version']=='v2-broken')
  self.assertFalse(voice('chat')['ok']);voice()
  i=self.incident();self.assertEqual(i['rca']['affected_component'],'llm-service');self.assertEqual(i['plan']['action'],'restore_configuration')
  git=next(e for e in i['evidence'] if e['source_type']=='GIT');self.assertIn('v2-broken',git['metadata']['local']['working_diff']);self.approve(i)
  self.assertEqual(json.loads(path.read_text())['prompt_version'],'v1')
 def test_06_simultaneous_incidents_isolate_evidence_approval_copilot(self):
  api('scenario',{'scenario':'leak'},'payflow');self.inject('tts');voice();voice()
  p=wait(lambda s:s['incident'] and s['incident']['status']=='awaiting_approval','payflow')['incident'];c=self.incident()
  self.assertNotEqual(p['id'],c['id']);self.assertEqual(p['application_id'],'payflow')
  self.assertEqual(api('approve',{'plan_id':p['plan']['id']})['_status'],409)
  self.assertEqual(api('approve',{'plan_id':c['plan']['id']},'payflow')['_status'],409)
  for i,app in [(p,'payflow'),(c,'converselab')]:
   self.assertTrue(all(e['application_id']==app and e['incident_id']==i['id'] for e in i['evidence']))
   def keys(value):
    if isinstance(value,dict):
     for k,v in value.items():yield k;yield from keys(v)
    elif isinstance(value,list):
     for v in value:yield from keys(v)
   self.assertFalse({'scenario','scenario_id','injected_cause'}&set(keys(i)))
  self.assertIn('PayFlow',api('chat',{'message':'Why is it failing?'},'payflow')['answer']);self.assertIn('ConverseLab',api('chat',{'message':'Why is voice failing?'})['answer'])
  self.approve(c);self.assertEqual(api('state',app='payflow')['incident']['status'],'awaiting_approval');self.assertFalse(api('pay',{},'payflow')['ok'])
  api('approve',{'plan_id':p['plan']['id']},'payflow');wait(lambda s:s['incident']['status']=='resolved','payflow')
  history=api('incidents')['history'];self.assertTrue({'payflow','converselab'}.issubset({i['application_id'] for i in history}))
 def test_07_shared_core_rejects_mixed_evidence_and_unknown_actions(self):
  records=[{'id':'E-001','application_id':'a','incident_id':'one','source_type':'LOG','metadata':{'records':[]}}, {'id':'E-002','application_id':'b','incident_id':'two','source_type':'LOG','metadata':{'records':[]}}]
  with self.assertRaises(ValueError):diagnose(records)
  with self.assertRaises(ValueError):normalize_evidence(records,{'id':'one','application_id':'a'},'a')
  self.assertEqual(api('chat',{'application_id':'payflow','message':'show evidence'})['_status'],409)
  from converselab_adapter import ConverseLabAdapter
  from unittest.mock import patch
  adapter=ConverseLabAdapter(BASE+10)
  with patch.object(adapter,'propose',return_value={'action':'ARBITRARY_SHELL','edits':[]}):
   with self.assertRaises(ValueError):build_plan(adapter,{}, {})
 def test_08_async_playground_truth_and_config_patch_boundary(self):
  self.inject('tts')
  start=request(f'http://127.0.0.1:{BASE+10}/api/conversations',{'channel':'voice','text':'Where is my order?'})
  end=time.time()+12
  while time.time()<end:
   job=request(f'http://127.0.0.1:{BASE+10}/api/jobs/'+start['request_id'])
   if job['status']!='running':break
   time.sleep(.1)
  self.assertEqual(job['status'],'failed');self.assertEqual(job['pipeline'][-1]['service'],'tts-service');self.assertEqual(job['pipeline'][-1]['status_code'],503)
  denied=request(f'http://127.0.0.1:{BASE+10}/patch/validate',{'edits':[{'path':'../payflow-repo/config.json','original_hash':'x','content':'{}'}]})
  self.assertEqual(denied['_status'],409)
  self.assertEqual(request(f'http://127.0.0.1:{BASE+10}/patch/apply',{'edits':[]})['_status'],409)
 def test_09_generic_rca_survives_application_and_dependency_rename(self):
  self.inject('tts');voice();voice();i=self.incident();evidence=copy.deepcopy(i['evidence'])
  # An unrelated application with the same observation contract uses the same diagnosis function.
  for e in evidence:
   e['application_id']='travel-demo';e['incident_id']='INC-TRAVEL'
   if e['source_type']=='DEPENDENCY':e['metadata']['services']['delivery-service']=e['metadata']['services'].pop('tts-service')
   if e['source_type']=='LOG':
    for r in e['metadata']['records']:
     if r['service']=='tts-service':r['service']='delivery-service'
   if e['source_type']=='TRACE':
    for trace in e['metadata']['traces']:
     for span in trace['spans']:
      if span['service']=='tts-service':span['service']='delivery-service'
  r=diagnose(evidence);self.assertEqual(r['affected_component'],'delivery-service');self.assertEqual(r['action'],'restore_dependency')
