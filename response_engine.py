"""Shared incident lifecycle for every registered application. No application-name branches."""
import copy,json,os,threading,uuid
from concurrent.futures import ThreadPoolExecutor
from common import now
from application import normalize_evidence,build_plan
from investigator import diagnose,enrich_with_ai
from ai_reasoning import configured
from reporting import report,recovery

def event(inc,text,kind='info'):inc['timeline'].append({'timestamp':now(),'text':text,'kind':kind})

class ResponseEngine:
 def __init__(self,adapter,path):
  self.adapter=adapter;self.path=path;self.lock=threading.RLock();self.operation=threading.Lock();self.stop=threading.Event()
  self.state={'application_id':adapter.application.id,'connected':False,'telemetry':None,'history':[],'incident':None,'traffic':False,'busy':False,'samples':[],'notice':None,'ignore_before':now()}
  if path.exists():
   try:
    for i in json.loads(path.read_text(encoding='utf-8'))[-30:]:
     if i.get('application_id',adapter.application.id)!=adapter.application.id:continue
     i['application_id']=adapter.application.id
     for e in i.get('evidence',[]):e['application_id']=adapter.application.id
     self.state['history'].append(i)
   except (ValueError,OSError):pass
 def persist(self):
  self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(self.state['history'],indent=2),encoding='utf-8');tmp.replace(self.path)
 def snapshot(self):
  with self.lock:value=copy.deepcopy(self.state)
  value['application']=self.adapter.application.to_dict();value['application']['status']='DISCONNECTED' if not value['connected'] else 'DEGRADED' if value['incident'] and value['incident']['status']!='resolved' else 'HEALTHY'
  rca=(value.get('incident') or {}).get('rca') or {}
  value['mode']=rca.get('ai_mode','DETERMINISTIC FALLBACK')
  value['ai_configuration']='CONFIGURED · awaiting validated response' if configured() else 'LIVE AI — NOT CONFIGURED'
  if value.get('incident'):value['incident']['recovery_comparison']=recovery(value['incident'])
  value['application_url']=self.adapter.application.url;value['payflow_url']=self.adapter.application.url
  value['verification_description']=self.adapter.verification_description
  if value['telemetry']:
   value['metric_cards']=self.adapter.present_metrics(value['telemetry']);value['service_health']=self.adapter.topology_health(value['telemetry'])
   if value['connected'] and any(status!='HEALTHY' for status in value['service_health'].values()):value['application']['status']='DEGRADED'
  return value
 def collect(self,inc,t):
  evidence=normalize_evidence(self.adapter.collect(inc,t,self.state['history']),inc,self.adapter.application.id)
  with self.lock:
   inc['evidence']=evidence
   for e in evidence:event(inc,e['summary'],'evidence')
  return evidence
 def investigate(self,inc,t,release=False):
  try:
   event(inc,'Starting from UNKNOWN. Inspecting measured runtime signals and changes, without a fault label.')
   evidence=self.collect(inc,t);rca=diagnose(evidence)
   if rca['requires_more_evidence']:
    event(inc,'Insufficient evidence. Refreshing available observations once.');t=self.adapter.telemetry();evidence=self.collect(inc,t);rca=diagnose(evidence)
   rca=enrich_with_ai(evidence,rca,{'application_id':self.adapter.application.id,'incident_id':inc['id'],'created':inc['created'],'onset':inc['onset'],'services':[x['id'] for x in self.adapter.application.services],'allowed_files':list(t['local_source']['files'])})
   deterministic=diagnose(evidence)
   try:plan=build_plan(self.adapter,rca,t)
   except Exception as exc:plan={'title':'Patch validation failed','validation':{'passed':False,'error':str(exc)[:300]}}
   if rca.get('ai_mode')=='LIVE AI' and not rca['requires_more_evidence'] and (not plan or not plan.get('validation',{}).get('passed')):
    audit=rca['ai_audit'];audit.update(status='PATCH_REJECTED',patch_source='DETERMINISTIC FALLBACK')
    rca={**deterministic,'context_optimization':rca.get('context_optimization',[]),'ai_status':'PATCH_REJECTED','ai_mode':'DETERMINISTIC FALLBACK','engine':'DETERMINISTIC FALLBACK','ai_audit':audit,'ai_error':'AI reasoning validated, but no executable safe patch was established. Using the deterministic proposal.'}
    try:plan=build_plan(self.adapter,rca,t)
    except Exception:plan=None
   event(inc,'Reasoning mode: '+rca.get('ai_mode','DETERMINISTIC FALLBACK')+'; provider status: '+rca.get('ai_status','NOT_CONFIGURED'))
   inc['context_optimization']=rca.pop('context_optimization',[])
   for operation in inc['context_optimization']:
    event(inc,operation['purpose']+' context: '+operation.get('selected_strategy','JSON')+'; integrity '+operation.get('integrity_status','FAIL')+'; '+operation.get('delivery','NOT SENT'),'context')
   with self.lock:
    inc.update(rca=rca,plan=plan,application_name=self.adapter.application.name,affected_services=rca.get('affected_services',[rca['affected_component']]),affected_capabilities=rca.get('affected_capabilities',[]),error_codes=list({x['code'] for x in t['logs'] if x['severity']=='ERROR'}))
    inc['status']='awaiting_approval' if plan and plan['validation']['passed'] else 'needs_attention'
    event(inc,'Evidence correlation complete. '+('Review the validated patch before approval.' if inc['status']=='awaiting_approval' else 'No executable repair established. Engineer review or more evidence is required.'))
  except Exception as exc:
   with self.lock:inc['status']='needs_attention';event(inc,'Investigation stopped: '+str(exc)[:200],'error')
  finally:
   if release:
    with self.lock:self.state['busy']=False
    self.operation.release()
 def monitor(self):
  while not self.stop.wait(.75):
   try:
    t=self.adapter.telemetry()
    if t.get('application_id',self.adapter.application.id)!=self.adapter.application.id:raise ValueError('Unexpected telemetry application')
    with self.lock:
     s=self.state;s['telemetry']=t;s['connected']=True;s['samples']=(s['samples']+[{'time':now(),**self.adapter.sample(t)}])[-90:];inc=s['incident']
     failing=[e for e in t['events'] if now()-e['timestamp']<15 and e['timestamp']>=s['ignore_before'] and (not e['ok'] or e['latency']>=self.adapter.slow_ms)]
     if len(failing)>=2 and not s['busy'] and (not inc or inc['status']=='resolved' and any(e['timestamp']>inc.get('resolved_at',0) for e in failing)):
      inc={'id':'INC-'+uuid.uuid4().hex[:8].upper(),'application_id':self.adapter.application.id,'status':'investigating','failure_type':'UNKNOWN','severity':'SEV-2','affected_services':[],'created':now(),'onset':failing[0]['timestamp'],'evidence':[],'timeline':[],'rca':None,'plan':None,'verification':None}
      s['incident']=inc;event(inc,'Runtime degradation detected from live requests.','alert');threading.Thread(target=self.investigate,args=(inc,t),daemon=True).start()
   except Exception:
    with self.lock:self.state['connected']=False
 def traffic_loop(self):
  while not self.stop.wait(1):
   if self.state['traffic'] and not self.state['busy']:
    try:self.adapter.probe('background')
    except OSError:pass
 def start(self):
  for fn in (self.monitor,self.traffic_loop):threading.Thread(target=fn,daemon=True).start()
 def experiment(self,kind):
  try:
   self.adapter.control(kind)
   with ThreadPoolExecutor(max_workers=6) as workers:list(workers.map(lambda _:self.adapter.probe('demo'),range(14)))
  except Exception as exc:self.state['notice']='Experiment stopped: '+str(exc)[:160]
  finally:
   with self.lock:self.state['busy']=False
   self.operation.release()
 def execute(self,inc):
  try:
   r=self.adapter.apply(inc['plan']);inc['patch_audit_id']=r['audit_id']
   with self.lock:inc['status']='verifying';event(inc,'Approved patch applied. Running fresh application-specific verification.','action')
   result=self.adapter.get_verification_strategy()(inc,event);result['application_id']=self.adapter.application.id
   with self.lock:
    inc['verification']=result
    if result['passed']:
     inc['status']='resolved';inc['resolved_at']=now();event(inc,'Recovery verified using fresh requests and independent health probes.','success');self.state['history'].append(copy.deepcopy(inc));self.state['history']=self.state['history'][-30:];self.persist()
    else:inc['status']='verification_failed';event(inc,'Fresh recovery checks failed. Incident remains open.','error')
  except Exception as exc:
   with self.lock:inc['status']='verification_failed';event(inc,'Execution stopped: '+str(exc)[:200],'error')
  finally:
   with self.lock:self.state['busy']=False
   self.operation.release()
 def command(self,action,body):
  if action=='traffic':
   if type(body.get('enabled')) is not bool:raise ValueError('Boolean required')
   self.state['traffic']=body['enabled'];return {'ok':True}
  if action in ('pay','probe'):return self.adapter.probe('manual')
  if action=='chat':return self.chat(body.get('message',''))
  if action not in ('scenario','reset','approve','reinvestigate','reject','rollback','escalate'):raise ValueError('Unknown action')
  if not self.operation.acquire(False):raise ValueError('Another operation is running for this application')
  asynchronous=False
  try:
   with self.lock:
    inc=self.state['incident']
    if action in ('reset','scenario'):
     if inc and inc['status']=='investigating':raise ValueError('Wait for investigation to finish')
     if action=='scenario' and (body.get('scenario') not in self.adapter.scenarios or inc and inc['status']!='resolved'):raise ValueError('Resolve/reset the incident and select a supported experiment')
    elif action=='approve':
     if not inc or inc['status']!='awaiting_approval' or body.get('plan_id')!=inc['plan']['id']:raise ValueError('No matching current approval plan')
     if inc['plan'].get('application_id')!=self.adapter.application.id:raise ValueError('Cross-application approval blocked')
     inc['status']='executing';event(inc,'Human approval recorded for plan '+inc['plan']['id'][:8]+'.','approval')
    elif action=='reject':
     if not inc or inc['status']!='awaiting_approval':raise ValueError('No proposal to reject')
     inc['status']='needs_attention';inc['rejected']=True;event(inc,'Human rejected the patch. No source changed.','approval');return {'ok':True}
    elif action=='escalate':
     if not inc or inc['status'] not in ('verification_failed','needs_attention'):raise ValueError('Only open incidents needing review can be escalated')
     inc['escalation']={'timestamp':now(),'note':'Escalated for local engineer review. Incident remains OPEN. No external notification was sent.'}
     event(inc,inc['escalation']['note'],'escalation');return {'ok':True}
    elif action=='rollback':
     if not inc or not inc.get('patch_audit_id') or inc['status'] in ('executing','verifying','investigating'):raise ValueError('No applied patch to roll back')
    elif not inc or inc['status'] not in ('verification_failed','needs_attention','awaiting_approval'):raise ValueError('Cannot reinvestigate now')
    self.state['busy']=True
   if action=='reset':
    self.adapter.control('reset')
    with self.lock:self.state.update(incident=None,samples=[],notice=None,ignore_before=now())
   elif action=='rollback':
    self.adapter.rollback(inc);inc.update(status='needs_attention',verification=None,plan=None);event(inc,'Previous source restored after human rollback; review required.','action')
   else:
    if action=='scenario':target=self.experiment;args=(body['scenario'],)
    elif action=='approve':target=self.execute;args=(inc,)
    else:
     inc.update(status='investigating',evidence=[],plan=None);target=self.investigate;args=(inc,self.adapter.telemetry(),True)
    threading.Thread(target=target,args=args,daemon=True).start();asynchronous=True
   return {'ok':True}
  finally:
   if not asynchronous:
    with self.lock:self.state['busy']=False
    self.operation.release()
 def chat(self,message):
  with self.lock:inc=copy.deepcopy(self.state['incident'])
  q=str(message).lower()[:1500];name=self.adapter.application.name
  if not inc:answer=name+' has no active incident. Send a fresh request to observe its current behavior.'
  elif not inc.get('rca'):answer='Collecting evidence for '+name+'. Follow the investigation timeline.'
  elif any(k in q for k in ('context','toon','hybrid','json selected','tokens','optimization','lose any evidence')):
   row=next((r for r in reversed(inc.get('context_optimization',[])) if r['purpose']=='RCA'),None)
   answer=('No context optimization measurements recorded.' if not row else row['selected_strategy']+' selected. '+str(row.get('original_tokens','N/A'))+' → '+str(row.get('optimized_tokens','N/A'))+' measured tokens; '+str(row.get('token_reduction','N/A'))+'% reduction. Evidence integrity '+row.get('integrity_status','N/A')+' (structural validation, not model-quality assurance). '+ ' '.join(row.get('strategy_reasons',[]))+' '+row.get('delivery','NOT SENT'))
  elif any(k in q for k in ('changed','change','diff','deployment')):
   selected=[e for e in inc['evidence'] if e['source_type'] in ('GIT','CONFIG','DEPLOYMENT')]
   answer='\n\n'.join(e['id']+' ['+e['source_type']+'] '+e['summary']+'\n'+((e['metadata'].get('local',{}).get('working_diff') or e['metadata'].get('diff') or 'No source diff observed') if e['source_type']=='GIT' else json.dumps(e['metadata'],indent=2)) for e in selected)[:12000] or 'No change evidence collected.'
  elif 'evidence' in q:answer='\n'.join(e['id']+': '+e['summary'] for e in inc['evidence'])
  elif any(k in q for k in ('safe','risk','approv','fix','remediation')):answer='Risk: '+(inc.get('plan') or {}).get('risk','Not assessed')+'. '+(inc.get('plan') or {}).get('impact','No executable change established')+'. '+(inc.get('plan') or {}).get('policy','No safe action is established.')+' Approval is available only through Review fix; chat cannot authorize a change.'
  elif any(k in q for k in ('ruled','alternative','eliminated')):answer=' '.join(a['title']+': '+a['reason']+' ['+a['evidence']+']' for a in inc['rca']['alternatives'])
  elif any(k in q for k in ('verify','verification','recover')):answer=self.adapter.verification_description+' '+('Checks passed.' if (inc.get('verification') or {}).get('passed') else 'Recovery is not yet verified.')
  else:answer=inc['rca']['explanation']+' Evidence: '+', '.join(inc['rca']['citations'])+'.'
  return {'answer':name+': '+answer,'application_id':self.adapter.application.id,'incident_id':inc['id'] if inc else None,'mode':'Evidence assistant - guided answers'}

def postmortem(inc):return report(inc)['markdown']
