"""Existing real heroes, additionally asserting attached context measurements and scoped APIs."""
import unittest
import test_hardening as hardening
from test_multiapp import api
from test_system import request,BASE

class ContextHeroes(unittest.TestCase):
 setUpClass=hardening.HardeningHTTP.__dict__['setUpClass']
 tearDownClass=hardening.HardeningHTTP.__dict__['tearDownClass']
 setUp=hardening.HardeningHTTP.setUp
 approve=hardening.HardeningHTTP.approve
 def check_context(self,app):
  import urllib.request
  for path in ('context-ui.js','context.css'):
   with urllib.request.urlopen(f'http://127.0.0.1:{BASE}/'+path) as asset:self.assertEqual(asset.status,200)
  i=api('state',app=app)['incident'];rows=i['context_optimization'];self.assertEqual(len(rows),3)
  for row in rows:
   self.assertEqual(row['application_id'],app);self.assertEqual(row['incident_id'],i['id']);self.assertGreater(row['original_tokens'],0);self.assertEqual(row['integrity_status'],'PASS');self.assertNotIn('serialized_context',row)
  self.assertEqual(rows[-1]['delivery'],'PREPARED — NOT SENT');self.assertEqual(i['rca']['ai_mode'],'DETERMINISTIC FALLBACK')
  url=f'http://127.0.0.1:{BASE}/api/context-optimization/incidents/'+i['id']
  self.assertEqual(len(request(url+'?application_id='+app)['operations']),3)
  other='payflow' if app=='converselab' else 'converselab'
  self.assertEqual(request(url+'?application_id='+other)['_status'],404)
  self.assertIn('AI Context Optimization',api('report',app=app)['markdown'])
  for q in ['How was AI context optimized?','Why was TOON selected?','Why was JSON selected?','Why was Hybrid selected?','How many tokens were saved?','Did optimization lose any evidence?']:
   answer=api('chat',{'message':q},app)['answer'];self.assertIn(rows[-1]['selected_strategy']+' selected',answer);self.assertIn(str(rows[-1]['original_tokens']),answer)
  stats=request(f'http://127.0.0.1:{BASE}/api/context-optimization/stats?application_id={app}');self.assertGreaterEqual(stats['original_tokens'],rows[-1]['original_tokens'])
 def test_payflow_manual_hero_with_context(self):
  hardening.HardeningHTTP.test_payflow_manual_hero_comparison_copilot_and_shared_report(self);self.check_context('payflow')
 def test_converselab_tts_hero_with_context(self):
  hardening.HardeningHTTP.test_converselab_hero_comparison_report_and_scope(self);self.check_context('converselab')
