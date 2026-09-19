"""Existing PayFlow integration extracted without changing its runtime protocols."""
import ast,copy,json,time
from common import now,request
from source_provider import digest
from reporting import summarize
from application import ApplicationAdapter,MonitoredApplication
from investigator import RUNBOOKS

class PayFlowAdapter(ApplicationAdapter):
    scenarios=('leak','bank','timeout','latency','database','code','order','endpoint','pool','gateway','processing')
    runbooks=RUNBOOKS
    verification_description='18 fresh checkout requests in two batches; zero failures, p95 below 500 ms, pool below 80%, and healthy database/bank.'
    def __init__(self,base):
        self.base=base;self.pay=base+2;self.bank=base+3;self.control_url=f'http://127.0.0.1:{self.pay}'
        self.application=MonitoredApplication('payflow','PayFlow','PAYMENT_PLATFORM','Payment and order processing',f'http://127.0.0.1:{base+1}',
          [{'id':n,'name':label,'role':role} for n,label,role in [('api-gateway','API gateway','gateway'),('order-service','Order service','orders'),('payment-service','Payment service','processing'),('database','SQLite database','database'),('bank-api','Bank API','provider')]],
          [['api-gateway','order-service'],['api-gateway','payment-service'],['payment-service','database'],['payment-service','bank-api']],
          ['metrics','logs','traces','database','dependencies','source_changes','config_changes','local_git','deployment'],
          ['METRIC','LOG','TRACE','GIT','DEPLOYMENT','DEPENDENCY','DATABASE','CONFIG','RUNBOOK','HISTORY'],
          ['restore_cleanup','restore_code','restore_timeout','restore_bank','restore_latency','restore_database','restore_order','restore_endpoint','restore_pool','restore_gateway','restore_processing','apply_ai_patch'])
        self.application.ui={'request': 'payment', 'plural': 'payments', 'http_services': 4, 'scenarios': [['01', 'FEATURED SCENARIO', 'Connection leak', 'A release stops returning database connections. Watch the pool fill and checkout fail.', 'leak', 'Source change → pool saturation → failed payments', 'Restore cleanup + recycle connections'], ['02', 'DEPENDENCY FAILURE', 'Bank unavailable', 'The payment provider stops responding successfully. Can the agent identify the real boundary?', 'bank', 'Provider 503s → failed traces → healthy database', 'Restore the local bank simulator'], ['03', 'CONFIGURATION DRIFT', 'Timeout too short', 'A 20 ms timeout meets a 90 ms bank response. Healthy services, unsuccessful payments.', 'timeout', 'Config diff → timeouts → healthy provider', 'Restore the 800 ms timeout budget'], ['04', 'PROVIDER LATENCY', 'Bank latency', 'The bank takes 1.6 seconds to respond. Traces and an independent probe distinguish latency from a low timeout.', 'latency', 'Slow provider response → timed-out checkout', 'Restore simulator response latency'], ['05', 'DATABASE DEPENDENCY', 'Database unavailable', 'The local database access layer refuses connections. This is separate from pool exhaustion.', 'database', 'Failed DB health → acquisition errors', 'Restore sandbox database availability'], ['06', 'CODE REGRESSION', 'Missing optional field', 'A source change dereferences an optional value while it is None. Inspect the exception location and source.', 'code', 'Source diff → AttributeError → failed payment', 'Repair the narrow source regression'], ['07', 'ORDER BOUNDARY', 'Order service failure', 'Order creation fails before charging the customer. Healthy payment dependencies do not make checkout healthy.', 'order', 'Order HTTP 500 → checkout stopped', 'Restore order service availability'], ['08', 'ENDPOINT CONFIG', 'Wrong bank endpoint', 'Payments are routed to a missing bank path. The correct provider endpoint remains healthy.', 'endpoint', 'Config diff → HTTP 404 → payment failure', 'Restore the configured bank path'], ['09', 'POOL CAPACITY', 'Pool too small', 'One available connection faces six concurrent requests. Cleanup works, but capacity is insufficient.', 'pool', 'Contention → acquisition timeout → healthy DB', 'Restore six-connection capacity'], ['10', 'GATEWAY ROUTING', 'Wrong payment route', 'The gateway points to a nonexistent payment endpoint while the real service stays responsive.', 'gateway', 'Gateway HTTP 404 → no payment span', 'Restore gateway payment path'], ['11', 'LOCAL PROCESSING', 'Slow payment processing', 'A local processing delay increases checkout latency even when the provider and database remain healthy.', 'processing', 'Long processing span → slow checkout', 'Remove the sandbox processing delay']]}
    def telemetry(self):return request(self.control_url+'/telemetry')
    def probe(self,origin='manual'):return request(self.application.url+'/api/pay',{'origin':origin})
    def get_health(self):return {n['id']:request(f'http://127.0.0.1:{p}/health') for n,p in zip([self.application.services[i] for i in (0,1,2,4)],[self.base+1,self.base+4,self.base+2,self.base+3])}
    def present_metrics(self,t):
        m=t['metrics'];return [{'label':'Payment error rate','value':m['error_rate'],'unit':'%','note':f"{m['failures']} failures / {m['requests']} recent requests",'bad':m['error_rate']>0}, {'label':'Payment latency','value':m['p95'],'unit':'ms','note':'p95 · recent requests','bad':m['p95']>=500}, {'label':'Connection pool','value':m['pool']['utilization'],'unit':'%','note':f"{m['pool']['used']} of {m['pool']['size']} in use",'bad':m['pool']['utilization']>=80}, {'label':'Payments observed','value':m['total_requests'],'unit':'','note':'Current process · real HTTP','bad':False}]
    def topology_health(self,t):
        c=t['config'];m=t['metrics'];return {'api-gateway':'DEGRADED' if m['error_rate'] else 'HEALTHY','order-service':'HEALTHY' if c['order_available'] else 'CRITICAL','payment-service':'DEGRADED' if m['error_rate'] or m['p95']>=500 else 'HEALTHY','database':'HEALTHY' if t['database']['healthy'] else 'CRITICAL','bank-api':'CRITICAL' if not c['bank_available'] else 'DEGRADED' if c['bank_latency_ms']>=500 else 'HEALTHY'}
    def collect(self,inc,t,history):
        evidence=[]
        def add(kind,name,summary,metadata,service='payment-service'):
            e={'id':f'E-{len(evidence)+1:03}','incident_id':inc['id'],'source_type':kind,'source_name':name,'service':service,'timestamp':now(),'summary':summary,'metadata':metadata,'raw_reference':f'{name} snapshot at {t["timestamp"]}','relevance':'supporting'}
            evidence.append(e)
        m=t['metrics']; failures=[x for x in t['events'] if (not x['ok'] or x['latency']>=500) and x['timestamp']>=inc['onset']-1]
        filtered=[x for x in t['logs'] if x['severity']=='ERROR' and x['timestamp']>=inc['onset']-1][-12:]
        add('METRIC','Metrics investigator',f'{m["error_rate"]}% of the last {m["requests"]} payments failed. Pool utilization is {m["pool"]["utilization"]}%.',m)
        add('LOG','Logs investigator',f'{len(filtered)} correlated error records collected.',{'records':filtered})
        add('TRACE','Trace investigator','Followed failed requests across the payment path.',{'traces':failures[-4:]})
        add('GIT','Local Git investigator','Inspected the actual deployed payment source and commit diff.',{'diff':t['change'],'source':t['source'],'sha':t['deployment']['sha'],'local':t.get('local_source',{}),'reload_error':t.get('reload_error')})
        add('DEPLOYMENT','Deployment investigator',f'Release {t["deployment"]["version"]} deployed at commit {t["deployment"]["sha"]}.',t['deployment'])
        try: bank=request(f'http://127.0.0.1:{self.bank}/probe',timeout=4)
        except OSError: bank={'healthy':False,'unreachable':True}
        bank['payment_healthy']=request(f'http://127.0.0.1:{self.pay}/health').get('healthy',False)
        bank['order_healthy']=request(f'http://127.0.0.1:{self.base+4}/health').get('healthy',False)
        add('DEPENDENCY','Dependency investigator','Sandbox bank health: '+('healthy' if bank.get('healthy') else 'unavailable')+'.',bank,'bank-api')
        add('DATABASE','Database investigator','Independent database probe: '+('healthy' if t['database']['healthy'] else 'failed')+'.',t['database'],'database')
        add('CONFIG','Configuration investigator',f'Bank request timeout is {t["config"]["bank_timeout_ms"]} ms.',t['config'])
        query=json.dumps(filtered).lower()
        ranked=sorted(self.runbooks,key=lambda b:sum(term.lower() in query for term in b['terms']),reverse=True)
        ranked[0]={**ranked[0],'matched':any(term.lower() in query for term in ranked[0]['terms'])}
        add('RUNBOOK','Knowledge retriever',f'Matched {ranked[0]["id"]}: {ranked[0]["title"]}.',ranked[0])
        relevant=[x for x in history if x.get('rca',{}).get('title') and set(x.get('error_codes',[])) & {v['code'] for v in filtered}]
        add('HISTORY','Incident memory',f'{len(relevant)} matching completed sandbox incidents found.',{'matches':[{'id':x['id'],'application_id':self.application.id,'service':x['rca'].get('affected_component'),'title':x['rca']['title'],'status':x['status'],'resolution':(x.get('plan') or {}).get('title'),'evidence_ids':x['rca'].get('citations',[]),'timestamp':x.get('resolved_at')} for x in relevant[-3:]]})
        return evidence

    def propose(self,rca,t):
        action=rca['action'];edits=[]
        hypothesis=rca.get('hypothesis',{})
        files=t.get('local_source',{}).get('files',{})
        if not action and hypothesis.get('patch') and not hypothesis.get('requires_more_evidence'):
            edits=hypothesis['patch'];title='AI-proposed local source repair';action='apply_ai_patch';origin='OpenAI structured patch'
        elif not action:return None
        else:
            origin='Evidence-driven restricted repair';config=dict(t['config'])
            repairs={'restore_timeout':('bank_timeout_ms',800),'restore_bank':('bank_available',True),'restore_latency':('bank_latency_ms',90),'restore_database':('database_available',True),'restore_order':('order_available',True),'restore_endpoint':('bank_path','/charge'),'restore_pool':('pool_size',6),'restore_gateway':('gateway_path','/pay'),'restore_processing':('processing_delay_ms',0)}
            if action in ('restore_cleanup','restore_code'):
                name='payment_logic.py';current=files.get(name,t['source'])
                if action=='restore_code':
                    target=current.replace("        optional = None\n        optional.get('reference')\n",'')
                else:
                    # Repair the supported small missing-cleanup shape, retaining charge/save body.
                    import ast
                    tree=ast.parse(current);fn=tree.body[0]
                    if len(fn.body)<2:raise ValueError('Source shape requires engineer review')
                    first=ast.get_source_segment(current,fn.body[0])
                    if first!='connection = pool.acquire()':raise ValueError('Connection ownership is unclear')
                    body=fn.body[1:]
                    if len(body)==1 and isinstance(body[0],ast.Try):
                        body[0].finalbody=[ast.Expr(ast.Call(ast.Attribute(ast.Name('pool',ast.Load()),'release',ast.Load()),[ast.Name('connection',ast.Load())],[]))]
                    else:
                        fn.body=[fn.body[0],ast.Try(body=body,handlers=[],orelse=[],finalbody=[ast.Expr(ast.Call(ast.Attribute(ast.Name('pool',ast.Load()),'release',ast.Load()),[ast.Name('connection',ast.Load())],[]))])]
                    target=ast.unparse(ast.fix_missing_locations(tree))+'\n'
                title='Restore connection cleanup' if action=='restore_cleanup' else 'Repair optional-field handling'
            else:
                key,value=repairs[action];config[key]=value;name='config.json';current=files[name];target=json.dumps(config,indent=2)+'\n';title='Restore '+key.replace('_',' ')
            edits=[{'path':name,'original_hash':digest(current),'content':target}]
        return {'action':action,'edits':edits,'title':title,'origin':origin}


    def verify(self,inc,emit):
        batches=[]
        for n in (12,6):
            results=[self.probe('verification') for _ in range(n)]
            batches.extend(results)
            emit(inc,f'Fresh verification batch: {sum(bool(x.get("ok")) for x in results)}/{n} payments succeeded.','verification')
            if n==12: time.sleep(2)
        t=self.telemetry(); bank=request(f'http://127.0.0.1:{self.bank}/health')
        latencies=sorted(x.get('latency') or 0 for x in batches)
        p95=latencies[min(len(latencies)-1,int(len(latencies)*.95))]
        checks=[{'label':'Fresh payments','value':f'{sum(bool(x.get("ok")) for x in batches)}/18 successful','pass':all(x.get('ok') for x in batches)},
            {'label':'Payment p95','value':f'{p95} ms / <500 ms','pass':p95<500},
            {'label':'Connection pool','value':f'{t["metrics"]["pool"]["utilization"]}% / <80%','pass':t['metrics']['pool']['utilization']<80},
            {'label':'Dependency probes','value':'Database + sandbox bank','pass':t['database']['healthy'] and bank.get('healthy',False)}]
        return {'timestamp':now(),'checks':checks,'traces':[x['trace_id'] for x in batches],'passed':all(c['pass'] for c in checks),'observation_seconds':2,'fresh_requests':18,'measured':{**summarize(batches),'pool_utilization':t['metrics']['pool']['utilization'],'database_healthy':t['database']['healthy'],'bank_healthy':bank.get('healthy',False)}}
