"""PayFlow: real HTTP gateway, payment, order and bank simulator, SQLite pool.
Fault controls only change source/configuration. Observability never exports a scenario ID.
"""
import json, os, sqlite3, subprocess, threading, time, uuid, traceback, copy
from source_provider import LocalSourceChangeProvider, digest
from patch_safety import PatchExecutor, validate_python, validate_config
from collections import deque
from contextlib import closing
from pathlib import Path
from common import Handler, ROOT, now, request, server

DATA = Path(os.environ.get('IC_DATA_DIR', ROOT / 'runtime'))
REPO = DATA / 'payflow-repo'
BASE = int(os.environ.get('IC_BASE_PORT', '8787'))
GATEWAY, PAYMENT, BANK, ORDER = [BASE+i for i in range(1,5)]
GOOD = '''def process(pool, charge, save):
    connection = pool.acquire()
    try:
        result = charge()
        save(connection, result)
        return result
    finally:
        pool.release(connection)
'''
BAD = '''def process(pool, charge, save):
    connection = pool.acquire()
    result = charge()
    save(connection, result)
    return result
'''
CONFIG = {'bank_timeout_ms':800, 'bank_available':True, 'bank_latency_ms':90, 'database_available':True, 'order_available':True, 'bank_path':'/charge', 'gateway_path':'/pay', 'pool_size':6, 'processing_delay_ms':0}
lock = threading.RLock()
events = deque(maxlen=1200)
logs = deque(maxlen=2000)
deployments = []
function = None
configuration = dict(CONFIG)
deployed_diff = ''

def git(*args):
    return subprocess.check_output(['git', '-C',str(REPO),*args],stderr=subprocess.STDOUT,text=True).strip()

class Pool:
    def __init__(self, size=6):
        self.size=size; self.connections=[]; self.free=[]; self.condition=threading.Condition()
        for _ in range(size):
            c=sqlite3.connect(str(DATA/'payments.db'),check_same_thread=False,timeout=2)
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('CREATE TABLE IF NOT EXISTS payments(id TEXT PRIMARY KEY, amount INTEGER, created REAL)');c.commit()
            self.connections.append(c);self.free.append(c)
    def acquire(self):
        if not configuration['database_available']:raise RuntimeError('DB_UNAVAILABLE')
        with self.condition:
            if not self.condition.wait_for(lambda:bool(self.free),timeout=.22):raise RuntimeError('DB_POOL_EXHAUSTED')
            return self.free.pop()
    def release(self,c):
        with self.condition:
            if c not in self.free:self.free.append(c);self.condition.notify()
    def recycle(self,size=None):
        for c in self.connections:c.close()
        self.__init__(size or self.size)
    def metrics(self):
        with self.condition:return {'used':self.size-len(self.free),'size':self.size,'utilization':round((self.size-len(self.free))/self.size*100)}

pool = None
provider=None
patcher=None
source_observation={}
reload_error=None
active=0
condition=threading.Condition(lock)
transactions=deque(maxlen=200)


def initialize():
    global pool,provider,patcher
    REPO.mkdir(parents=True,exist_ok=True)
    if not (REPO/'.git').exists():
        git('init');git('config','user.name','PayFlow Demo');git('config','user.email','demo@localhost')
    pool=Pool()
    provider=LocalSourceChangeProvider(REPO)
    patcher=PatchExecutor(REPO,DATA/'patch-audit')
    if not (REPO/'payment_logic.py').exists():
        deploy(GOOD,CONFIG,'Initialize PayFlow sandbox')
    else:
        # Migrate the old three-key configuration without erasing judge edits.
        try:
            old=json.loads((REPO/'config.json').read_text())
            if set(old).issubset(CONFIG) and set(old)!=set(CONFIG):
                (REPO/'config.json').write_text(json.dumps({**CONFIG,**old},indent=2)+'\n')
        except (OSError,ValueError):pass
        reload_source(force=True)
    threading.Thread(target=watch_source,daemon=True).start()


def reload_source(force=False):
    global function,configuration,source_observation,reload_error,deployed_diff
    with condition:
        if not condition.wait_for(lambda:active==0,timeout=5):raise ValueError('Requests still in flight; retry reload')
        observation=provider.scan(force)
        if not observation:return None
        source_observation=observation
        deployed_diff=observation['working_diff'] or observation['commit_diff']
        try:
            source=observation['files']['payment_logic.py'];validate_python(source)
            cfg=validate_config(observation['files']['config.json'])
            ns={'__builtins__':{'RuntimeError':RuntimeError,'ValueError':ValueError,'TypeError':TypeError,'Exception':Exception}}
            exec(compile(source,'payment_logic.py','exec'),ns)
            function=ns['process'];configuration=cfg;reload_error=None
            pool.recycle(cfg['pool_size'])
        except Exception as e:
            function=None;reload_error=type(e).__name__+': '+str(e)[:250]
        record={'sha':observation['sha'],'timestamp':now(),'message':'Local source reload','version':f'v2.{len(deployments)}','hashes':observation['hashes'],'reload_error':reload_error,'changed_files':observation['changed_files']}
        deployments.append(record)
        return record


def watch_source():
    previous=None
    while True:
        time.sleep(.35)
        try:
            # Two equal reads debounce ordinary editor saves. Never commit judge edits.
            hashes={k:digest(v) for k,v in provider.read().items()}
            if hashes==previous:reload_source()
            previous=hashes
        except Exception:
            continue


def deploy(source,config,message):
    with condition:
        if not condition.wait_for(lambda:active==0,timeout=5):raise ValueError('Requests still in flight')
        (REPO/'payment_logic.py').write_text(source,encoding='utf-8')
        (REPO/'config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
        git('add','payment_logic.py','config.json');git('commit','--allow-empty','-m',message)
        return reload_source(force=True)


def control(kind,expected=None):
    with condition:
        if expected and git('rev-parse','--short','HEAD')!=expected:raise ValueError('Deployment changed. Investigate again before applying a fix.')
        if kind=='reset':
            record=deploy(GOOD,CONFIG,'Restore healthy baseline');events.clear();logs.clear();return record
        # Scenario names stop at the control plane. Telemetry only contains source/config/runtime observations.
        if kind=='leak':return deploy(BAD,CONFIG,'Update payment source')
        if kind=='code':return deploy(GOOD.replace('result = charge()',"optional = None\n        optional.get('reference')\n        result = charge()"),CONFIG,'Update payment source')
        changes={'bank':{'bank_available':False},'timeout':{'bank_timeout_ms':20},'latency':{'bank_latency_ms':1600},'database':{'database_available':False},'order':{'order_available':False},'endpoint':{'bank_path':'/missing'},'pool':{'pool_size':1},'gateway':{'gateway_path':'/missing'},'processing':{'processing_delay_ms':700}}
        if kind in changes:return deploy(GOOD,{**CONFIG,**changes[kind]},'Update service configuration')
        # Legacy repair controls retained for API compatibility; main workflow uses validated patches.
        if kind=='restore_cleanup':return deploy(GOOD,configuration,'Restore connection cleanup')
        if kind=='restore_timeout':return deploy((REPO/'payment_logic.py').read_text(),{**configuration,'bank_timeout_ms':800},'Restore timeout budget')
        if kind=='restore_bank':return deploy((REPO/'payment_logic.py').read_text(),{**configuration,'bank_available':True},'Restore bank availability')
        raise ValueError('Unknown control')

def snapshot():
    with lock:
        recent=[e for e in events if now()-e['timestamp']<30][-30:]
        latency=sorted(e['latency'] for e in recent)
        failed=sum(not e['ok'] for e in recent)
        return {'timestamp':now(),'metrics':{'requests':len(recent),'total_requests':len(events),'failures':failed,'error_rate':round(100*failed/len(recent),1) if recent else 0,'p95':latency[min(len(latency)-1,int(len(latency)*.95))] if latency else 0,'pool':pool.metrics()},
            'events':list(events)[-80:],'logs':list(logs)[-80:],'deployment':deployments[-1],
            'deployments':deployments[-8:],'config':dict(configuration),
            'change':deployed_diff,
            'source':source_observation.get('files',{}).get('payment_logic.py',''),'local_source':copy.deepcopy(source_observation),'source_path':str(REPO/'payment_logic.py'),'reload_error':reload_error, 'database':{'healthy':database_health(),'engine':'SQLite','pool':pool.metrics()}}

def database_health():
    if not configuration['database_available']:return False
    try:
        with closing(sqlite3.connect(str(DATA/'payments.db'),timeout=.2)) as c: c.execute('SELECT 1').fetchone()
        return True
    except sqlite3.Error: return False

class BankHandler(Handler):
    def do_GET(self):
        if self.path not in ('/health','/probe'):return self.json({'error':'Not found'},404)
        start=now()
        if self.path=='/probe':time.sleep(configuration['bank_latency_ms']/1000)
        self.json({'healthy':configuration['bank_available'],'service':'bank-api','simulator':True,'latency_ms':round((now()-start)*1000)})
    def do_POST(self):
        try:body=self.body()
        except ValueError as e:return self.json({'error':str(e)},400)
        if self.path!='/charge':return self.json({'error':'BANK_ENDPOINT_NOT_FOUND'},404)
        time.sleep(configuration['bank_latency_ms']/1000)
        if not configuration['bank_available']:return self.json({'error':'BANK_UNAVAILABLE'},503)
        self.json({'ok':True,'id':'TXN-'+uuid.uuid4().hex[:8].upper(),'trace_id':body.get('trace_id')})

class OrderHandler(Handler):
    def do_GET(self):self.json({'healthy':configuration['order_available'],'service':'order-service'})
    def do_POST(self):
        try:body=self.body()
        except ValueError as e:return self.json({'error':str(e)},400)
        if not configuration['order_available']:return self.json({'error':'ORDER_UNAVAILABLE'},500)
        self.json({'ok':True,'order_id':'ORD-'+uuid.uuid4().hex[:6].upper(),'trace_id':body.get('trace_id'),'amount':3599})

class PaymentHandler(Handler):
    def do_GET(self):
        if self.path=='/health':return self.json({'healthy':function is not None and len(pool.free)>0,'service':'payment-service'})
        if self.path=='/telemetry':return self.json(snapshot())
        self.json({'error':'Not found'},404)
    def do_POST(self):
        global active
        try:
            body=self.body()
            if self.path=='/control':return self.json(control(body['action'],body.get('expected_sha')))
            if self.path=='/patch/validate':return self.json(patcher.validate(body['edits']))
            if self.path=='/patch/apply':
                with condition:
                    if not condition.wait_for(lambda:active==0,timeout=5):raise ValueError('Requests still in flight')
                    if body.get('expected_sha')!=git('rev-parse','--short','HEAD'):raise ValueError('Deployment changed. Investigate again before applying a fix.')
                    # This internal loopback endpoint also checks the private runner token.
                    if body.get('token')!=os.environ.get('IC_CONTROL_TOKEN') or not os.environ.get('IC_CONTROL_TOKEN'):raise ValueError('Authorized approval required')
                    if body.get('expected_hashes')!={k:digest(v) for k,v in provider.read().items()}:raise ValueError('Source changed. Review a fresh proposal.')
                    record=patcher.apply(body['edits'],approved=True);reload_source(force=True)
                return self.json({'audit_id':record['id'],'result':record['result']})
            if self.path=='/patch/rollback':
                with condition:
                    if body.get('token')!=os.environ.get('IC_CONTROL_TOKEN') or not os.environ.get('IC_CONTROL_TOKEN'):raise ValueError('Authorized approval required')
                    if not condition.wait_for(lambda:active==0,timeout=5):raise ValueError('Requests still in flight')
                    audit_id=body.get('audit_id','')
                    if len(audit_id)!=32 or any(c not in '0123456789abcdef' for c in audit_id):raise ValueError('Invalid audit ID')
                    record=json.loads((DATA/'patch-audit'/(audit_id+'.json')).read_text());patcher.rollback(record);reload_source(force=True)
                return self.json({'ok':True})
            if self.path!='/pay':return self.json({'error':'GATEWAY_ROUTE_NOT_FOUND'},404)
            trace=body.get('trace_id',uuid.uuid4().hex[:12]);start=now();spans=[];detail=None
            with condition:active+=1;fn=function;cfg=dict(configuration)
            try:
                def charge():
                    t=now()
                    try:result=request(f'http://127.0.0.1:{BANK}'+cfg['bank_path'],{'trace_id':trace},cfg['bank_timeout_ms']/1000)
                    except (TimeoutError,OSError):
                        spans.append({'service':'bank-api','ms':round((now()-t)*1000),'status':'timeout'});raise RuntimeError('BANK_TIMEOUT')
                    spans.append({'service':'bank-api','ms':round((now()-t)*1000),'status':'ok' if result.get('ok') else 'error'})
                    if not result.get('ok'):raise RuntimeError('BANK_ENDPOINT_NOT_FOUND' if result.get('_status')==404 else 'BANK_UNAVAILABLE')
                    return result
                def save(c,result):
                    t=now();c.execute('INSERT INTO payments VALUES(?,?,?)',(result['id'],3599,now()));c.commit()
                    spans.append({'service':'database','ms':round((now()-t)*1000),'status':'ok'})
                try:
                    if fn is None:raise RuntimeError('SOURCE_RELOAD_FAILED')
                    if cfg['processing_delay_ms']:
                        delay=now();time.sleep(cfg['processing_delay_ms']/1000);spans.append({'service':'payment-processing','ms':round((now()-delay)*1000),'status':'ok'})
                    result=fn(pool,charge,save)
                    if not isinstance(result,dict) or result.get('ok') is not True:raise RuntimeError('PAYMENT_RETURN_CONTRACT')
                    ok=True;error=None
                except Exception as e:
                    ok=False;error=str(e) if str(e) in ('DB_POOL_EXHAUSTED','DB_UNAVAILABLE','BANK_TIMEOUT','BANK_UNAVAILABLE','BANK_ENDPOINT_NOT_FOUND','SOURCE_RELOAD_FAILED','PAYMENT_RETURN_CONTRACT') else 'PAYMENT_INTERNAL_ERROR';result={}
                    frames=traceback.extract_tb(e.__traceback__)
                    detail={'exception':type(e).__name__,'message':str(e)[:250],'frames':[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in frames if Path(f.filename).name=='payment_logic.py']}
                    if error in ('DB_POOL_EXHAUSTED','DB_UNAVAILABLE'):spans.append({'service':'database-pool' if error=='DB_POOL_EXHAUSTED' else 'database','ms':round((now()-start)*1000),'status':'error'})
                elapsed=round((now()-start)*1000);spans.insert(0,{'service':'payment-service','ms':elapsed,'status':'ok' if ok else 'error'})
                with lock:logs.append({'timestamp':now(),'service':'payment-service','severity':'INFO' if ok else 'ERROR','trace_id':trace,'code':error or 'PAYMENT_COMPLETED','detail':detail})
            finally:
                with condition:active-=1;condition.notify_all()
            self.json({**result,'ok':ok,'error':error,'latency':elapsed,'trace_id':trace,'spans':spans},200 if ok else 503)
        except (ValueError,KeyError,TypeError) as e:self.json({'error':str(e)},409)

class GatewayHandler(Handler):
    def do_GET(self):
        if self.path=='/health':return self.json({'healthy':True,'service':'api-gateway'})
        if self.path=='/api/health':
            try:return self.json(request(f'http://127.0.0.1:{PAYMENT}/health'))
            except OSError:return self.json({'healthy':False},503)
        if self.path=='/api/transactions':
            with lock:rows=list(transactions)[-30:]
            return self.json({'transactions':rows})
        self.static('payflow.html' if self.path=='/' else self.path.lstrip('/'))
    def do_POST(self):
        try:
            body=self.body()
            if self.path!='/api/pay':return self.json({'error':'Not found'},404)
            trace=uuid.uuid4().hex[:12];start=now();spans=[];order={};result={};error=None
            try:
                order=request(f'http://127.0.0.1:{ORDER}/order',{'trace_id':trace})
                spans.append({'service':'order-service','ms':round((now()-start)*1000),'status':'ok' if order.get('ok') else 'error'})
                if not order.get('ok'):error='ORDER_UNAVAILABLE'
                else:
                    result=request(f'http://127.0.0.1:{PAYMENT}'+configuration['gateway_path'],{'trace_id':trace,'origin':body.get('origin','checkout')})
                    spans+=result.get('spans',[])
                    if not result.get('ok'):error='GATEWAY_ROUTE_NOT_FOUND' if result.get('_status')==404 else result.get('error','PAYMENT_UNAVAILABLE')
            except OSError:error='SERVICE_UNAVAILABLE'
            ok=bool(result.get('ok'));elapsed=round((now()-start)*1000)
            spans.insert(0,{'service':'api-gateway','ms':elapsed,'status':'ok' if ok else 'error'})
            with lock:
                events.append({'timestamp':now(),'trace_id':trace,'ok':ok,'error':error,'latency':elapsed,'spans':spans,'sha':deployments[-1]['sha'],'origin':body.get('origin','checkout')})
                logs.append({'timestamp':now(),'service':'order-service' if error=='ORDER_UNAVAILABLE' else 'api-gateway','severity':'INFO' if ok else 'ERROR','trace_id':trace,'code':error or 'PAYMENT_COMPLETED'})
                transactions.append({'timestamp':now(),'id':result.get('id'),'order_id':order.get('order_id') if ok else None,'ok':ok,'amount':3599,'trace_id':trace,'latency':elapsed})
            self.json({'ok':ok,'id':result.get('id'),'order_id':order.get('order_id') if ok else None,'latency':elapsed,'trace_id':trace,'amount':3599},200 if ok else 503)
        except (ValueError,OSError) as e:self.json({'ok':False,'error':'Payment could not be processed'},503)

if __name__=='__main__':
    initialize()
    for port,handler in [(PAYMENT,PaymentHandler),(BANK,BankHandler),(ORDER,OrderHandler)]:
        srv=server(port,handler); threading.Thread(target=srv.serve_forever,daemon=True).start()
    print(f'PayFlow ready: http://127.0.0.1:{GATEWAY}',flush=True)
    server(GATEWAY,GatewayHandler).serve_forever()
