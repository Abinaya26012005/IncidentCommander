"""Telemetry and controlled operations only; diagnosis lives in the shared investigator."""
import copy,json
from concurrent.futures import ThreadPoolExecutor
from reporting import summarize
from application import ApplicationAdapter,MonitoredApplication
from common import request,now
from source_provider import digest

BOOKS=[
 {'id':'RB-CONV-001','title':'Knowledge retrieval failure','terms':['knowledge-service','DEPENDENCY_HTTP_FAILURE'],'steps':['Inspect retrieval spans and HTTP errors.','Probe Knowledge and generation services independently.','Review the smallest local recovery change; verify both channels.']},
 {'id':'RB-CONV-002','title':'Speech recognition latency','terms':['stt-service'],'steps':['Compare voice and chat results.','Measure STT span duration against its latency budget.','Restore bounded local latency only after approval.']},
 {'id':'RB-CONV-003','title':'Speech synthesis failure','terms':['tts-service','DEPENDENCY_HTTP_FAILURE'],'steps':['Confirm valid text was generated before voice delivery failed.','Check STT, Knowledge, LLM and TTS independently.','After approved recovery, require five fresh voice pipelines to finish.']},
 {'id':'RB-CONV-004','title':'Conversation configuration regression','terms':['OUTPUT_VALIDATION_FAILED','prompt_version'],'steps':['Inspect the output contract error and configuration diff.','Confirm the LLM endpoint is available.','Review a config rollback and verify fresh valid responses.']}
]

class ConverseLabAdapter(ApplicationAdapter):
 slow_ms=1800
 scenarios=('knowledge','stt','tts','prompt')
 runbooks=BOOKS
 verification_description='Five fresh voice and three fresh chat conversations; valid responses, complete required spans, p95 below 1800 ms, and healthy STT/Knowledge/LLM/TTS probes.'
 seed_history=[{'id':'SEED-CONV-001','application_id':'converselab','seeded':True,'status':'EXAMPLE','error_codes':['DEPENDENCY_HTTP_FAILURE'],'service':'tts-service','rca':{'title':'Illustrative speech synthesis outage'},'summary':'SIMULATED historical example: generated text could not be delivered as voice. An approved local provider reset followed by fresh voice checks is the suggested procedure. Not an executed incident.'}]
 def __init__(self,base):
  self.base=base;self.control_url=f'http://127.0.0.1:{base}'
  self.application=MonitoredApplication('converselab','ConverseLab','CONVERSATIONAL_AI_PLATFORM','Customer support chat and simulated voice',self.control_url,
   [{'id':n,'name':label,'role':role} for n,label,role in [('conversation-gateway','Gateway','gateway'),('conversation-service','Conversation','orchestration'),('stt-service','Speech recognition','transcription'),('knowledge-service','Knowledge / RAG','retrieval'),('llm-service','Language model','generation'),('tts-service','Speech synthesis','synthesis')]],
   [['conversation-gateway','conversation-service']]+[['conversation-service',n] for n in ('stt-service','knowledge-service','llm-service','tts-service')],
   ['metrics','logs','traces','health','dependencies','source_changes','config_changes','local_git','deployment','chat','voice'],
   ['METRIC','LOG','TRACE','GIT','DEPLOYMENT','DEPENDENCY','HEALTH','CONFIG','RUNBOOK','HISTORY'],
   ['restore_dependency','restore_latency','restore_configuration','apply_ai_patch'])
  self.application.ui={'request': 'voice conversation', 'plural': 'conversations', 'http_services': 6, 'scenarios': [['01', 'RETRIEVAL', 'Knowledge API failure', 'Retrieval returns HTTP 500; both channels lose required context.', 'knowledge', 'Failed retrieval spans + independent health', 'Restore local Knowledge availability'], ['02', 'VOICE LATENCY', 'STT high latency', 'Speech recognition takes 2.4 seconds; chat skips this stage.', 'stt', 'Long STT spans + healthy chat', 'Restore STT latency'], ['03', 'VOICE DELIVERY', 'TTS failure', 'Valid generated text cannot be delivered as simulated speech.', 'tts', 'Upstream success + TTS HTTP 503', 'Restore local TTS availability'], ['04', 'CONFIGURATION', 'Bad prompt deployment', 'A changed prompt version produces invalid output.', 'prompt', 'Output validation errors + source diff', 'Restore prompt configuration']]}
 def telemetry(self):return request(self.control_url+'/telemetry')
 def get_health(self):
  names=[x['id'] for x in self.application.services]
  def probe(pair):
   index,name=pair
   try:return name,request(f'http://127.0.0.1:{self.base+index}/health',timeout=2)
   except OSError:return name,{'healthy':False,'service':name,'unreachable':True}
  with ThreadPoolExecutor(max_workers=6) as pool:return dict(pool.map(probe,enumerate(names)))
 def get_dependencies(self):return {k:v for k,v in self.get_health().items() if k in ('stt-service','knowledge-service','llm-service','tts-service')}
 def probe(self,origin='manual',channel='voice'):
  return request(self.control_url+'/api/converse',{'channel':channel,'text':'When is my payment due?','origin':origin},timeout=18)
 def collect(self,inc,t,history):
  result=[]
  def add(kind,name,summary,data,service='conversation-service'):
   result.append({'id':f'E-{len(result)+1:03}','incident_id':inc['id'],'application_id':self.application.id,'source_type':kind,'source_name':name,'service':service,'timestamp':now(),'summary':summary,'metadata':data,'raw_reference':f'{name} observed at {t["timestamp"]}','relevance':'supporting'})
  traces=[e for e in t['events'] if e['timestamp']>=inc['onset']-1][-8:]
  logs=[e for e in t['logs'] if e['timestamp']>=inc['onset']-1][-80:]
  probes=self.get_health();dependencies={k:v for k,v in probes.items() if k in ('stt-service','knowledge-service','llm-service','tts-service')}
  add('METRIC','Metrics investigator',f"Voice: {t['metrics']['channels']['voice']['error_rate']}% errors, p95 {t['metrics']['channels']['voice']['p95']} ms. Chat: {t['metrics']['channels']['chat']['error_rate']}% errors.",t['metrics'])
  add('LOG','Logs investigator','Correlated service logs with conversation, request and trace IDs.',{'records':logs})
  add('TRACE','Trace investigator','Actual chat/voice HTTP spans, including upstream successes and terminal errors.',{'traces':traces})
  add('GIT','Local Git investigator','Observed local configuration diff and reload fingerprint.',{'diff':t['change'],'source':'','sha':t['deployment']['sha'],'local':t['local_source'],'reload_error':t['reload_error']})
  add('DEPLOYMENT','Deployment investigator','Configuration reload at revision '+t['deployment']['sha'],t['deployment'])
  add('DEPENDENCY','Dependency investigator','Independent HTTP probes for STT, Knowledge, LLM and TTS.',{'services':dependencies})
  add('HEALTH','Service health investigator','Independent health of all six HTTP services.',{'services':probes})
  add('CONFIG','Configuration investigator','Observed latency budgets, dependency availability and prompt version.',t['config'])
  problem_logs=[r for r in logs if r['severity']=='ERROR' or r.get('latency_ms',0)>=self.slow_ms]
  problem_spans=[s for t in traces for s in t.get('spans',[]) if s['status']!='ok' or s.get('ms',0)>=self.slow_ms]
  query=json.dumps(problem_logs+problem_spans).lower();book=max(self.runbooks,key=lambda b:sum(x.lower() in query for x in b['terms']))
  add('RUNBOOK','Knowledge retriever','Retrieved '+book['id']+': '+book['title'],{**book,'matched':any(x.lower() in query for x in book['terms'])})
  codes={r['code'] for r in logs if r['severity']=='ERROR'}
  components={s['service'] for s in problem_spans}
  relevant=[i for i in history+self.seed_history if i.get('application_id')==self.application.id and codes&set(i.get('error_codes',[])) and (i.get('service') or i.get('rca',{}).get('affected_component')) in components]
  add('HISTORY','Incident memory',f'{len(relevant)} matching records; seeded examples are explicitly labeled.',{'matches':[{'id':i['id'],'application_id':i['application_id'],'service':i.get('service') or i['rca'].get('affected_component'),'title':i['rca']['title'],'status':i['status'],'seeded':i.get('seeded',False),'summary':i.get('summary','Actual completed incident'),'resolution':(i.get('plan') or {}).get('title'),'evidence_ids':i['rca'].get('citations',[]),'timestamp':i.get('resolved_at')} for i in relevant[-4:]]})
  return result
 def propose(self,rca,t):
  action=rca.get('action');component=rca.get('affected_component');cfg=dict(t['config']);origin='Evidence-driven restricted repair'
  if action=='restore_dependency':
   key={'knowledge-service':'knowledge_available','tts-service':'tts_available','llm-service':'llm_available'}.get(component)
   if not key:return None
   cfg[key]=True;title='Restore local '+component+' availability'
  elif action=='restore_latency':
   key={'stt-service':'stt_latency_ms'}.get(component)
   if not key:return None
   cfg[key]=120;title='Restore speech recognition latency budget'
  elif action=='restore_configuration':cfg['prompt_version']='v1';title='Restore validated prompt configuration'
  elif rca.get('hypothesis',{}).get('patch') and not rca['hypothesis']['requires_more_evidence']:
   return {'action':'apply_ai_patch','edits':rca['hypothesis']['patch'],'title':'AI-proposed restricted configuration repair','origin':'OpenAI structured patch'}
  else:return None
  original=t['local_source']['files']['config.json'];content=json.dumps(cfg,indent=2)+'\n'
  return {'action':action,'edits':[{'path':'config.json','original_hash':digest(original),'content':content}],'title':title,'origin':origin}
 def verify(self,inc,emit):
  rows=[]
  for channel,count in [('voice',5),('chat',3)]:
   batch=[self.probe('verification',channel) for _ in range(count)];rows+=batch
   emit(inc,f'Fresh {channel} verification: {sum(bool(r.get("ok")) for r in batch)}/{count} succeeded.','verification')
  required={'voice':{'stt-service','knowledge-service','llm-service','tts-service'},'chat':{'knowledge-service','llm-service'}}
  complete=all(required[r['channel']].issubset({s['service'] for s in r.get('spans',[]) if s['status']=='ok' and s.get('output_valid',True)}) and bool(r.get('answer')) and (r['channel']!='voice' or r.get('speech',{}).get('delivered')) for r in rows)
  health=self.get_dependencies();lat=max(r.get('latency',0) for r in rows)
  checks=[{'label':'Fresh voice conversations','value':f'{sum(r.get("ok",False) for r in rows[:5])}/5 successful','pass':all(r.get('ok') for r in rows[:5])},{'label':'Fresh chat conversations','value':f'{sum(r.get("ok",False) for r in rows[5:])}/3 successful','pass':all(r.get('ok') for r in rows[5:])},{'label':'Complete valid pipelines','value':'STT → Knowledge → LLM → TTS; chat skips speech stages','pass':bool(complete)},{'label':'Conversation latency','value':f'{lat} ms / <1800 ms','pass':lat<1800},{'label':'Dependency probes','value':'STT + Knowledge + LLM + TTS','pass':all(x['healthy'] for x in health.values())}]
  return {'timestamp':now(),'checks':checks,'traces':[r['trace_id'] for r in rows],'passed':all(x['pass'] for x in checks),'fresh_requests':8,'observation_seconds':0,'strategy':'5 voice + 3 chat','application_id':self.application.id,'measured':{**summarize(rows),'channels':{c:summarize([r for r in rows if r['channel']==c]) for c in ('voice','chat')},'dependencies':health}}
 def present_metrics(self,t):
  m=t['metrics'];return [{'label':c.title()+' success','value':m['channels'][c]['success_rate'],'unit':'%','note':str(m['channels'][c]['requests'])+' recent conversations','bad':m['channels'][c]['failures']>0} for c in ('chat','voice')]+[{'label':'Conversation p95','value':m['p95'],'unit':'ms','note':'Recent chat + voice requests','bad':m['p95']>=self.slow_ms},{'label':'Conversations observed','value':m['total_requests'],'unit':'','note':'Actual HTTP pipelines','bad':False}]
 def topology_health(self,t):
  result={s['id']:'HEALTHY' for s in self.application.services}
  for key,service in [('tts_available','tts-service'),('knowledge_available','knowledge-service'),('llm_available','llm-service')]:
   if not t['config'][key]:result[service]='CRITICAL'
  if t['config']['stt_latency_ms']>=500:result['stt-service']='DEGRADED'
  if t['config']['prompt_version']!='v1':result['llm-service']='DEGRADED'
  if t['metrics']['failures'] or t['metrics']['p95']>=self.slow_ms:result['conversation-gateway']=result['conversation-service']='DEGRADED'
  return result
