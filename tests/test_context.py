"""Measured Adaptive Context Intelligence contracts. Providers are explicitly mocked."""
import copy,io,json,os,subprocess,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from context_optimization import ContextOptimizationRequest as Request,Policy,optimize
from context_optimization.serializers import json_candidate,toon_candidate,hybrid_candidate,decode_hybrid,codec
from context_optimization.integrity_guard import validate,anchors
from context_optimization.profiler import profile
from context_optimization.tokenizer import tokenizer
from context_optimization.token_budget import budget
from context_optimization.safety import sanitize
from context_optimization.fixtures import fixtures,uniform_records

def req(payload,**kwargs):return Request(payload,'RCA','payflow','INC-1',**kwargs)

class Serializers(unittest.TestCase):
 def test_all_json_types_unicode_and_round_trips(self):
  cases=[{},[],{'id':'E-001'},uniform_records(6),{'text':'தமிழ் English, "quoted"\nnext\\line: yes','null':None,'bool':False,'float':-1.125},[True,None,-4,2.5,'false','012'],{'nested':[{'spans':[{'span_id':'span-1','latency':12.5}]}]}, {'empty':{},'array':[],'numeric_string':'1e3'}, {'timestamp':'2026-09-19T00:00:00Z','a:b':' comma, quoted '}, {'diff':'@@ -1 +1 @@\n-old\n+new\n','evidence':uniform_records(6)}]
  for name,serializer in [('JSON',json_candidate),('TOON',toon_candidate),('HYBRID',hybrid_candidate)]:
   for value in cases:
    with self.subTest(serializer=name,value=str(value)[:60]):
     text,decoded=serializer(value);self.assertEqual(validate(value,decoded)['status'],'PASS');self.assertEqual(text,serializer(value)[0])
 def test_malformed_toon_and_hybrid_rejected(self):
  for text in ['items[2]: a','items[1]{id,name}:\n  a,b,c']:
   with self.subTest(text=text),self.assertRaises(ValueError):codec([text],'decode')
  with self.assertRaises(ValueError):decode_hybrid('HYBRID/1\nnull\n{"path":[],"characters":100}\nx\n')
 def test_hybrid_keeps_diff_prose_and_anchors(self):
  value=fixtures()['mixed'];text,decoded=hybrid_candidate(value)
  self.assertEqual(value,decoded);self.assertEqual(decoded['source']['diff'],value['source']['diff']);self.assertIn('HYBRID/1',text)
 def test_no_invalid_json_values_or_cross_app(self):
  for value in [float('nan'),float('inf'),{1:'key'},object(),{'application_id':'converselab'}]:
   with self.subTest(value=str(value)),self.assertRaises(ValueError):optimize(req(value))
 def test_redaction_does_not_change_audit_evidence(self):
  value={'api_key':'hidden','nested':{'password':'secret','scenario':'leak','expected_rca':'answer'},'message':'Authorization: Bearer sk-abcdefghijklmnop','diff':'ordinary diff'};before=copy.deepcopy(value)
  clean=sanitize(value,'payflow');self.assertEqual(value,before);self.assertNotIn('hidden',json.dumps(clean));self.assertNotIn('answer',json.dumps(clean));self.assertNotIn('abcdefghijklmnop',json.dumps(clean));self.assertEqual(clean['diff'],'ordinary diff')

class ProfilingAndIntegrity(unittest.TestCase):
 def test_profiles_are_measured_and_deterministic(self):
  count,_=tokenizer()
  for value in [{},[],fixtures()['small'],uniform_records(100),[{'a':1},{'b':2}],{'a':{'b':{'c':None}}},{'message':'தமிழ் English'*1000,'diff':'@@\n-old\n+new'}, {'metrics':[{'latency':3.1,'ok':True}]}]:
   with self.subTest(value=str(value)[:60]):
    p=profile(value,count);self.assertEqual(p,profile(value,count));self.assertEqual(p['token_count'],count(json_candidate(value)[0]));self.assertAlmostEqual(p['scalar_percentage']+p['nested_percentage'],100,places=1)
  self.assertEqual(profile(uniform_records(10),count)['uniform_records'],10)
 def test_every_anchor_and_intentional_failures(self):
  value={'id':'E-019','incident_id':'INC-1','application_id':'payflow','service':'payment-service','trace_id':'T-1','span_id':'S-1','request_id':'R-1','conversation_id':'C-1','error_code':'POOL','sha':'abc123','deployment_id':'D-1','config_version':'v2','dependency_name':'bank','status':'failed','timestamp':123.5,'metric':12,'path':'payment_logic.py','diff':'@@ -1 +1 @@\n-old\n+new'}
  self.assertTrue(all(v['status']=='PASS' for v in validate(value,value)['details'].values() if v['required']))
  for key in value:
   bad=copy.deepcopy(value);bad.pop(key)
   with self.subTest(key=key):self.assertEqual(validate(value,bad)['status'],'FAIL')
  changed={'records':[{'id':'E-1','value':1},{'id':'E-2','value':2}]};bad={'records':list(reversed(changed['records']))};self.assertEqual(validate(changed,bad)['status'],'FAIL')
 def test_tiny_json_and_repetitive_toon_measured(self):
  a=optimize(req(fixtures()['small']));b=optimize(req(fixtures()['uniform']))
  self.assertEqual(a.selected_strategy,'JSON');self.assertEqual(b.selected_strategy,'TOON');self.assertLess(b.metrics['optimized_tokens'],b.metrics['original_tokens']);self.assertIn('tiktoken',b.metrics['tokenizer_name'])
 def test_mixed_selects_by_utility(self):
  r=optimize(req(fixtures()['mixed']));candidates=[c for c in r.metrics['candidate_results'] if c['valid'] and (c['strategy']=='JSON' or c['token_reduction']>=5)]
  self.assertEqual(r.selected_strategy,max(candidates,key=lambda c:c['strategy_score'])['strategy'])
 def test_threshold_and_larger_candidates_keep_json(self):
  r=optimize(req(uniform_records(10),policy=Policy(minimum_expected_token_saving=.99)));self.assertEqual(r.selected_strategy,'JSON');self.assertTrue(r.metrics['fallback_triggered'])
  def larger(x):return ' '*10000+json.dumps(x),x
  with patch('context_optimization.router.toon_candidate',side_effect=larger),patch('context_optimization.router.hybrid_candidate',side_effect=larger):
   r=optimize(req(uniform_records(10)));self.assertEqual(r.selected_strategy,'JSON')
 def test_corrupted_candidates_and_profiler_fail_safely(self):
  for target in ['toon_candidate','hybrid_candidate']:
   with patch('context_optimization.router.'+target,return_value=('missing',{})):
    r=optimize(req(uniform_records(10)));self.assertEqual(r.selected_strategy,'JSON');self.assertTrue(r.metrics['fallback_triggered']);self.assertIn('rejected',r.metrics['fallback_reason'])
  with patch('context_optimization.router.profile',side_effect=RuntimeError()):
   self.assertEqual(optimize(req({'healthy':True})).selected_strategy,'JSON')
 def test_serializer_error_isolated(self):
  with patch('context_optimization.router.toon_candidate',side_effect=OSError('unavailable')):
   r=optimize(req(uniform_records(6)));self.assertEqual(r.selected_strategy,'JSON');self.assertEqual(r.metrics['integrity_status'],'PASS')
 def test_exact_budget_reservations_and_unknown(self):
  base=req({},model_context_limit=1000,system_prompt_tokens=100,tool_definition_tokens=100,reserved_output_tokens=200,policy=Policy(safety_margin_tokens=100))
  for tokens,expected in [(1,True),(499,True),(500,True),(501,False)]:self.assertEqual(budget(base,tokens)['fits_context_budget'],expected)
  self.assertIsNone(budget(replace(base,model_context_limit=None),1)['fits_context_budget'])
  for field in ['system_prompt_tokens','tool_definition_tokens','reserved_output_tokens']:
   self.assertFalse(budget(replace(base,**{field:1000}),1)['fits_context_budget'])
  self.assertFalse(budget(replace(base,policy=Policy(safety_margin_tokens=1000)),1)['fits_context_budget'])
 def test_budget_can_choose_fitting_representation_and_block_all(self):
  a=optimize(req(uniform_records(20)));small=a.metrics['optimized_tokens']
  r=optimize(req(uniform_records(20),model_context_limit=small,reserved_output_tokens=0,policy=Policy(safety_margin_tokens=0)))
  self.assertTrue(r.metrics['fits_context_budget']);self.assertGreater(r.metrics['original_tokens'],small)
  r=optimize(req(uniform_records(20),model_context_limit=1,reserved_output_tokens=0,policy=Policy(safety_margin_tokens=0)))
  self.assertFalse(r.metrics['fits_context_budget']);self.assertEqual(r.metrics['budget']['status'],'EXCEEDED')
 def test_memory_shapes_and_provenance(self):
  for records in [[],[{'id':'INC-1'}],[{'id':f'INC-{i}','service':'bank','resolution':'restored','evidence_ids':['E-1']} for i in range(8)],[{'id':'INC-1'},{'id':'INC-2','text':'mixed'}],[{'runbook':'தமிழ் English\n'*200}]]:
   r=optimize(Request({'matches':records},'INCIDENT_MEMORY','payflow','INC-1'));self.assertEqual(r.metrics['integrity_status'],'PASS');self.assertEqual(r.public()['application_id'],'payflow')

class ProviderBoundary(unittest.TestCase):
 def call(self,**kwargs):
  from ai_reasoning import reason
  evidence=[{'id':'E-001','application_id':'payflow','source_type':'LOG','metadata':{'logs':uniform_records(30),'scenario':'secret-injector','expected_repair':'secret-answer'}}]
  context={'application_id':'payflow','incident_id':'INC-1','services':['payment-service'],'allowed_files':['payment_logic.py']}
  fallback={'title':'Fallback','action':None,'requires_more_evidence':True}
  value={'rca':{'primary_hypothesis':'Observed failure','affected_services':['payment-service'],'supporting_evidence_ids':['E-001'],'contradicting_evidence_ids':[],'alternative_hypotheses':[],'eliminated_hypotheses':[],'recommended_action':'Review','requires_more_evidence':True},'patch':[]}
  seen=[]
  def provider(request,**kw):seen.append(json.loads(request.data));return io.BytesIO(json.dumps({'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}]}).encode())
  with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_MODEL':'mock-model',**kwargs}),patch('urllib.request.urlopen',side_effect=provider):result=reason(evidence,fallback,context)
  return result,seen
 def test_real_boundary_sends_optimized_context_and_keeps_schema(self):
  r,seen=self.call();self.assertEqual(r['ai_mode'],'LIVE AI');self.assertEqual(len(seen),1);row=r['context_optimization'][-1]
  count,_=tokenizer('mock-model');self.assertEqual(count(seen[0]['input']),row['optimized_tokens']);self.assertIn('Do not execute anything',seen[0]['instructions']);self.assertEqual(seen[0]['text']['format']['type'],'json_schema')
  self.assertNotIn('secret-injector',seen[0]['input']);self.assertNotIn('secret-answer',seen[0]['input']);self.assertEqual({x['purpose'] for x in r['context_optimization']},{'RCA','INCIDENT_MEMORY','INVESTIGATOR_CONTEXT'})
 def test_budget_prevents_provider_request(self):
  r,seen=self.call(IC_MODEL_CONTEXT_LIMIT='10');self.assertEqual(seen,[]);self.assertEqual(r['ai_status'],'CONTEXT_BUDGET_EXCEEDED')
 def test_corrupted_toon_falls_back_and_provider_continues(self):
  with patch('context_optimization.router.toon_candidate',return_value=('bad',{})):
   r,seen=self.call();self.assertEqual(r['ai_mode'],'LIVE AI');self.assertEqual(r['context_optimization'][-1]['selected_strategy'],'JSON');self.assertEqual(len(seen),1)
 def test_pipeline_exception_safe_json_and_provider_continues(self):
  with patch('ai_reasoning.prepare',side_effect=RuntimeError('test exception')):
   r,seen=self.call();self.assertEqual(r['ai_mode'],'LIVE AI');self.assertEqual(r['context_optimization'][-1]['selected_strategy'],'JSON');self.assertEqual(len(seen),1)
 def test_no_credentials_prepares_but_does_not_send(self):
  r,seen=self.call(OPENAI_API_KEY='',OPENAI_MODEL='');self.assertEqual(seen,[]);self.assertEqual(r['ai_status'],'NOT_CONFIGURED');self.assertNotIn('request_timestamp',r['ai_audit']);self.assertEqual(r['context_optimization'][-1]['delivery'],'PREPARED — NOT SENT')

class FrontendContracts(unittest.TestCase):
 def test_ai_context_render_states(self):
  completed=subprocess.run(['node',str(Path(__file__).with_name('context_ui_test.cjs'))],capture_output=True,text=True);self.assertEqual(completed.returncode,0,completed.stderr)
