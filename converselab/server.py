"""Independent conversational application: six real loopback HTTP services."""
import copy,json,os,sys,threading,time,uuid
from pathlib import Path
from collections import deque
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Handler,ROOT,now,request,server
from source_provider import LocalSourceChangeProvider,digest
from patch_safety import PatchExecutor
from converselab.config import DEFAULT,validate
from converselab.providers import DemoSTTProvider,DemoLLMProvider,DemoTTSProvider,DOCUMENTS,retrieve

BASE=int(os.environ.get('CL_BASE_PORT',int(os.environ.get('IC_BASE_PORT','8787'))+10))
NAMES=('conversation-gateway','conversation-service','stt-service','knowledge-service','llm-service','tts-service')
PORTS={name:BASE+i for i,name in enumerate(NAMES)}
DATA=Path(os.environ.get('IC_DATA_DIR',ROOT/'runtime'))/'converselab';REPO=DATA/'repo'
lock=threading.RLock();mutation=threading.Lock();events=deque(maxlen=500);logs=deque(maxlen=2000);jobs={};deployments=[]
configuration=dict(DEFAULT);observation={};reload_error=None
source=LocalSourceChangeProvider(REPO,('config.json',));patcher=PatchExecutor(REPO,DATA/'patch-audit',('config.json',),validate)
stt=DemoSTTProvider();llm=DemoLLMProvider();tts=DemoTTSProvider()

def reload(force=False):
 global configuration,observation,reload_error
 with mutation:
  changed=source.scan(force)
  if not changed:return
  with lock:
   observation=changed
   try:configuration=validate(changed['files']['config.json']);reload_error=None
   except ValueError as e:reload_error=str(e)
   deployments.append({'sha':changed['sha'],'timestamp':now(),'version':str(len(deployments)+1),'message':'Local configuration reload','hashes':changed['hashes'],'reload_error':reload_error})

def initialize():
 REPO.mkdir(parents=True,exist_ok=True)
 if not (REPO/'.git').exists():
  source.git('init');source.git('config','user.name','ConverseLab Demo');source.git('config','user.email','demo@localhost')
 if not (REPO/'config.json').exists():
  (REPO/'config.json').write_text(json.dumps(DEFAULT,indent=2)+'\n',encoding='utf-8');source.git('add','config.json');source.git('commit','-m','Initialize local configuration')
 reload(True)
 def watch():
  previous=None
  while True:
   time.sleep(.3)
   try:
    current=source.read()
    if current==previous:reload()
    previous=current
   except (OSError,ValueError):pass
 threading.Thread(target=watch,daemon=True).start()

def health(name):
 with lock:cfg=dict(configuration);error=reload_error
 key=name.removesuffix('-service')+'_available'
 healthy=not error and cfg.get(key,True)
 labels={'stt-service':'Speech recognition','knowledge-service':'Knowledge retrieval','llm-service':'Response generation','tts-service':'Speech synthesis'}
 return {'service':name,'display_name':labels.get(name,name),'healthy':bool(healthy),'simulated_provider':name in ('stt-service','llm-service','tts-service'),'latency_ms':cfg.get(name.removesuffix('-service')+'_latency_ms',0),'latency_budget_ms':500,'reload_error':error}

def log(name,body,ok,code,ms,status):
 with lock:logs.append({'timestamp':now(),'application_id':'converselab','service':name,'severity':'INFO' if ok else 'ERROR','trace_id':body['trace_id'],'request_id':body['request_id'],'conversation_id':body['conversation_id'],'message':code,'code':code,'latency_ms':ms,'status_code':status})

def ids(body):
 return {k:body[k] for k in ('trace_id','request_id','conversation_id')}

def stage(body,name,status,span=None):
 with lock:
  job=jobs.get(body['request_id'])
  if job is not None:
   job['stage']=name;job['stage_status']=status
   if span:job['pipeline'].append(span)

def call_service(name,body):
 stage(body,name,'running');start=now()
 try:r=request(f'http://127.0.0.1:{PORTS[name]}/process',body,timeout=14)
 except OSError:r={'ok':False,'error':'DEPENDENCY_UNREACHABLE','_status':503,**ids(body)}
 span={'service':name,'ms':round((now()-start)*1000),'status':'ok' if r.get('ok') else 'error','status_code':r.get('_status',200),'trace_id':body['trace_id'], 'output_valid':r.get('output_valid',r.get('ok',False))}
 if r.get('error'):span['error']=r['error']
 stage(body,name,span['status'],span)
 return r,span

def conversation(body):
 start=now();spans=[];text=body['text'];answer=None;citations=[];speech=None;error=None
 for name in (['stt-service'] if body['channel']=='voice' else [])+['knowledge-service','llm-service']+(['tts-service'] if body['channel']=='voice' else []):
  payload={**body,'text':text,'documents':citations,'answer':answer}
  result,span=call_service(name,payload);spans.append(span)
  if not result.get('ok'):error=result.get('error','DEPENDENCY_FAILURE');break
  if name=='stt-service':text=result['transcript']
  elif name=='knowledge-service':citations=result['documents']
  elif name=='llm-service':answer=result['answer']
  elif name=='tts-service':speech=result['speech']
 ok=error is None
 ms=round((now()-start)*1000);log('conversation-service',body,ok,error or 'CONVERSATION_COMPLETED',ms,200 if ok else 503)
 return {**ids(body),'application_id':'converselab','ok':ok,'error':error,'channel':body['channel'],'text':body['text'],'answer':answer,'citations':[{'id':d['id'],'title':d['title']} for d in citations],'speech':speech,'latency':ms,'spans':[{'service':'conversation-service','ms':ms,'status':'ok' if ok else 'error','trace_id':body['trace_id']}]+spans}

def gateway(body):
 start=now()
 try:result=request(f'http://127.0.0.1:{PORTS["conversation-service"]}/process',body,timeout=18)
 except OSError:result={**ids(body),'ok':False,'error':'CONVERSATION_UNREACHABLE','channel':body['channel'],'spans':[]}
 elapsed=round((now()-start)*1000);result.update(timestamp=now(),latency=elapsed,application_id='converselab')
 result['spans'].insert(0,{'service':'conversation-gateway','ms':elapsed,'status':'ok' if result.get('ok') else 'error','trace_id':body['trace_id']})
 with lock:
  result['sha']=deployments[-1]['sha'];events.append(copy.deepcopy(result))
  if body['request_id'] in jobs:jobs[body['request_id']].update(status='completed' if result['ok'] else 'failed',result=result)
 log('conversation-gateway',body,result['ok'],result.get('error') or 'REQUEST_COMPLETED',elapsed,200 if result['ok'] else 503)
 return result

def metric(rows):
 lat=sorted(r['latency'] for r in rows);fail=sum(not r['ok'] for r in rows)
 return {'requests':len(rows),'failures':fail,'error_rate':round(100*fail/len(rows),1) if rows else 0,'success_rate':round(100*(len(rows)-fail)/len(rows),1) if rows else 0,'p95':lat[min(len(lat)-1,int(len(lat)*.95))] if lat else 0}

def snapshot():
 with lock:
  rows=[e for e in events if now()-e['timestamp']<60][-60:];recentlogs=list(logs)[-120:]
  metrics={**metric(rows),'total_requests':len(events),'channels':{c:metric([r for r in rows if r['channel']==c]) for c in ('chat','voice')},'services':{}}
  for name in NAMES:
   records=[r for r in recentlogs if r['service']==name]
   metrics['services'][name]={'requests':len(records),'error_rate':round(100*sum(r['severity']=='ERROR' for r in records)/len(records),1) if records else 0,'latency_ms':round(sum(r['latency_ms'] for r in records)/len(records)) if records else 0}
  return {'timestamp':now(),'application_id':'converselab','metrics':metrics,'events':copy.deepcopy(list(events)[-60:]),'logs':copy.deepcopy(recentlogs),'config':dict(configuration),'deployment':deployments[-1],'deployments':deployments[-8:],'local_source':copy.deepcopy(observation),'change':observation.get('working_diff') or observation.get('commit_diff',''),'reload_error':reload_error,'source_path':str(REPO/'config.json'),'providers':{'stt':'SIMULATED','llm':'SIMULATED','tts':'SIMULATED'}}

def inject(action):
 changes={'knowledge':{'knowledge_available':False},'stt':{'stt_latency_ms':2400},'tts':{'tts_available':False},'prompt':{'prompt_version':'v2-broken'}}
 if action not in (*changes,'reset'):raise ValueError('Unknown experiment')
 with mutation:
  (REPO/'config.json').write_text(json.dumps({**DEFAULT,**changes.get(action,{})},indent=2)+'\n',encoding='utf-8')
  source.git('add','config.json');source.git('commit','--allow-empty','-m','Update local configuration')
 reload(True)
 if action=='reset':
  with lock:events.clear();logs.clear();jobs.clear()
 return {'ok':True}

class Service(Handler):
 def do_GET(self):
  name=self.server.service_name
  if self.path=='/health':return self.json(health(name))
  if name!='conversation-gateway':return self.json({'error':'Not found'},404)
  if self.path=='/api/state':return self.json({**snapshot(),'services':[health(n) for n in NAMES],'commander_url':f'http://127.0.0.1:{os.environ.get("IC_BASE_PORT","8787")}/?application_id=converselab'})
  if self.path=='/telemetry':return self.json(snapshot())
  if self.path=='/api/knowledge':return self.json({'documents':DOCUMENTS,'retrieval':'Deterministic keyword retrieval; no vector database'})
  if self.path.startswith('/api/jobs/'):
   with lock:value=copy.deepcopy(jobs.get(self.path.rsplit('/',1)[-1]))
   return self.json(value or {'error':'Unknown request'},200 if value else 404)
  path={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}.get(self.path)
  if not path:return self.json({'error':'Not found'},404)
  content=(Path(__file__).parent/'web'/path).read_bytes();self.send_response(200);self.send_header('Content-Type',{'html':'text/html; charset=utf-8','js':'application/javascript','css':'text/css'}[path.split('.')[-1]]);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)

 def do_POST(self):
  try:
   body=self.body();name=self.server.service_name
   if name=='conversation-gateway':
    if self.path=='/control':return self.json(inject(body['action']))
    if self.path=='/patch/validate':return self.json(patcher.validate(body['edits']))
    if self.path in ('/patch/apply','/patch/rollback'):
     if not os.environ.get('IC_CONTROL_TOKEN') or body.get('token')!=os.environ['IC_CONTROL_TOKEN']:raise ValueError('Authorized approval required')
     with mutation:
      if self.path=='/patch/apply':
       if body.get('expected_sha')!=source.git('rev-parse','--short','HEAD'):raise ValueError('Deployment changed')
       if body.get('expected_hashes')!={k:digest(v) for k,v in source.read().items()}:raise ValueError('Source changed; review again')
       record=patcher.apply(body['edits'],approved=True)
      else:
       aid=body.get('audit_id','')
       if len(aid)!=32 or any(c not in '0123456789abcdef' for c in aid):raise ValueError('Invalid audit ID')
       record=json.loads((DATA/'patch-audit'/(aid+'.json')).read_text());patcher.rollback(record)
     reload(True);return self.json({'ok':True,'audit_id':record['id']})
    if self.path not in ('/api/converse','/api/conversations'):return self.json({'error':'Not found'},404)
    channel=body.get('channel','chat');text=body.get('text','')
    if channel not in ('chat','voice') or not isinstance(text,str) or not text.strip() or len(text)>2000:raise ValueError('Choose chat/voice and enter 1–2000 characters')
    payload={'channel':channel,'text':text,'origin':str(body.get('origin','playground'))[:30],'conversation_id':'CONV-'+uuid.uuid4().hex[:10],'request_id':'REQ-'+uuid.uuid4().hex[:12],'trace_id':'TRACE-'+uuid.uuid4().hex[:12]}
    if self.path=='/api/conversations':
     with lock:
      if len(jobs)>200:jobs.pop(next(iter(jobs)))
      jobs[payload['request_id']]={**ids(payload),'status':'running','stage':'conversation-gateway','pipeline':[]}
     threading.Thread(target=gateway,args=(payload,),daemon=True).start();return self.json({**ids(payload),'status':'running'},202)
    result=gateway(payload);return self.json(result,200 if result['ok'] else 503)
   if self.path!='/process':return self.json({'error':'Not found'},404)
   if name=='conversation-service':
    result=conversation(body);return self.json(result,200 if result['ok'] else 503)
   start=now()
   with lock:cfg=dict(configuration);err=reload_error
   key=name.removesuffix('-service');time.sleep(cfg.get(key+'_latency_ms',0)/1000)
   code=None;status=200;output={}
   if err:code='CONFIG_RELOAD_FAILED';status=503
   elif not cfg.get(key+'_available',True):code='DEPENDENCY_HTTP_FAILURE';status=500 if key=='knowledge' else 503
   elif key=='stt':output=stt.transcribe(body['text'])
   elif key=='knowledge':output={'documents':retrieve(body['text'])}
   elif key=='llm':
    output=llm.generate(body['text'],body.get('documents',[]),cfg['prompt_version'])
    if not isinstance(output.get('answer'),str) or not output['answer'].strip():code='OUTPUT_VALIDATION_FAILED';status=502
   elif key=='tts':output={'speech':tts.synthesize(body['answer'])}
   ms=round((now()-start)*1000);log(name,body,code is None,code or 'STAGE_COMPLETED',ms,status)
   self.json({**output,**ids(body),'ok':code is None,'error':code,'service':name,'output_valid':code is None},status)
  except (ValueError,KeyError,TypeError) as e:self.json({'ok':False,'error':str(e)},409)

if __name__=='__main__':
 initialize()
 for name,port in PORTS.items():
  srv=server(port,Service);srv.service_name=name
  if name!='conversation-gateway':threading.Thread(target=srv.serve_forever,daemon=True).start()
  else:gateway_server=srv
 print(f'ConverseLab ready: http://127.0.0.1:{BASE}',flush=True);gateway_server.serve_forever()
