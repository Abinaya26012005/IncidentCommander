"""One control plane; registered applications share ResponseEngine and investigator."""
import os,json
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from common import Handler,ROOT,server
from response_engine import ResponseEngine,event,postmortem
from reporting import report
from payflow_adapter import PayFlowAdapter
from converselab_adapter import ConverseLabAdapter

BASE=int(os.environ.get('IC_BASE_PORT','8787'))
DATA=Path(os.environ.get('IC_DATA_DIR',ROOT/'runtime'))
adapters=[PayFlowAdapter(BASE),ConverseLabAdapter(int(os.environ.get('CL_BASE_PORT',BASE+10)))]
# Explicit registry is the only onboarding point. No application-name dispatch in the engine.
engines={a.application.id:ResponseEngine(a,DATA/('incidents.json' if index==0 else a.application.id+'-incidents.json')) for index,a in enumerate(adapters)}
default_engine=next(iter(engines.values()))
state=default_engine.state
def verify(inc):return default_engine.adapter.verify(inc,event) # Legacy PayFlow test/API compatibility.

class CommanderHandler(Handler):
 def route(self):
  url=urlsplit(self.path);query=parse_qs(url.query);aid=query.get('application_id',[default_engine.adapter.application.id])[0]
  if aid not in engines:raise ValueError('Unknown application_id')
  return url.path,engines[aid]
 def do_GET(self):
  try:
   path,engine=self.route()
   if path in ('/context-ui.js','/context.css'):
    data=(ROOT/'web'/path[1:]).read_bytes();self.send_response(200)
    self.send_header('Content-Type','application/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
   if path=='/api/applications':return self.json({'applications':[e.snapshot()['application'] for e in engines.values()]})
   if path=='/api/incidents':
    return self.json({'incidents':[e.snapshot()['incident'] for e in engines.values() if e.snapshot()['incident']],'history':[i for e in engines.values() for i in e.snapshot()['history']]})
   if path=='/api/state':
    value=engine.snapshot();value['applications']=[e.snapshot()['application'] for e in engines.values()];value['all_incidents']=[e.snapshot()['incident'] for e in engines.values() if e.snapshot()['incident']];return self.json(value)
   if path=='/api/runbooks':return self.json(engine.adapter.runbooks)
   if path.startswith('/api/context-optimization/incidents/'):
    wanted=path.split('/')[4];snapshot=engine.snapshot()
    incident=next((i for i in [snapshot['incident']]+snapshot['history'] if i and i['id']==wanted),None)
    if not incident:return self.json({'error':'No incident in selected application'},404)
    operations=incident.get('context_optimization',[])
    return self.json({'application_id':engine.adapter.application.id,'incident_id':wanted,'operations':operations[-1:] if path.endswith('/latest') else operations})
   if path=='/api/context-optimization/stats':
    snapshot=engine.snapshot();incidents={i['id']:i for i in snapshot['history']+[snapshot['incident']] if i};rows=[r for i in incidents.values() for r in i.get('context_optimization',[]) if r.get('purpose')=='RCA']
    return self.json({'application_id':engine.adapter.application.id,'incidents':len(rows),'original_tokens':sum(r.get('original_tokens',0) for r in rows),'optimized_tokens':sum(r.get('optimized_tokens',0) for r in rows),'scope':'Final RCA contexts only; subset counts are not added twice'})
   if path=='/api/tests':
    p=ROOT/'test-results.json';return self.json(json.loads(p.read_text()) if p.exists() else {'tests':[],'timestamp':None})
   if path=='/api/report':
    snapshot=engine.snapshot();wanted=parse_qs(urlsplit(self.path).query).get('incident_id',['current'])[0]
    inc=snapshot['incident'] if wanted=='current' else next((i for i in [snapshot['incident']]+snapshot['history'] if i and i['id']==wanted),None)
    return self.json(report(inc) if inc else {'error':'No incident in selected application'},200 if inc else 404)
   if path=='/health':return self.json({'healthy':True,'applications':list(engines)})
   self.static('index.html' if path=='/' else path.lstrip('/'))
  except ValueError as e:self.json({'error':str(e)},400)
 def do_POST(self):
  try:
   body=self.body();path,engine=self.route()
   if body.get('application_id',engine.adapter.application.id)!=engine.adapter.application.id:raise ValueError('Application context mismatch')
   if not path.startswith('/api/'):return self.json({'error':'Not found'},404)
   self.json(engine.command(path[5:],body))
  except (ValueError,KeyError) as e:self.json({'error':str(e)},409)
  except OSError:self.json({'error':'Application unavailable. Check its local services.'},503)

if __name__=='__main__':
 for engine in engines.values():engine.start()
 print(f'IncidentCommander ready: http://127.0.0.1:{BASE}',flush=True)
 server(BASE,CommanderHandler).serve_forever()
