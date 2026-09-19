"""Restricted patch policy and reproducible validation. Never accepts shell commands."""
import ast, difflib, hashlib, json, os, subprocess, sys, time, uuid, tempfile
from pathlib import Path
from source_provider import digest, FILES

def validate_python(source):
    tree=ast.parse(source)
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef):raise ValueError('Only one process function is allowed')
    f=tree.body[0]
    if f.returns or any(a.annotation for a in f.args.args):raise ValueError('Function annotations are not allowed')
    if f.name!='process' or [a.arg for a in f.args.args]!=['pool','charge','save'] or f.decorator_list or f.args.defaults or f.args.kwonlyargs or f.args.vararg or f.args.kwarg or f.args.posonlyargs:raise ValueError('Process signature must remain process(pool, charge, save)')
    allowed=(ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Assign,ast.Name,ast.Load,ast.Store,ast.Call,ast.Attribute,ast.Return,ast.Try,ast.ExceptHandler,ast.Raise,ast.If,ast.Compare,ast.Eq,ast.NotEq,ast.Is,ast.IsNot,ast.Gt,ast.GtE,ast.Lt,ast.LtE,ast.Constant,ast.Expr,ast.Pass,ast.UnaryOp,ast.Not,ast.BoolOp,ast.And,ast.Or,ast.Subscript,ast.Dict,ast.List,ast.Tuple,ast.keyword)
    if sum(isinstance(n,ast.FunctionDef) for n in ast.walk(tree))!=1:raise ValueError('Nested functions are not allowed')
    for node in ast.walk(tree):
        if not isinstance(node,allowed):raise ValueError('Unsupported code construct: '+type(node).__name__)
        if isinstance(node,ast.Name) and (node.id.startswith('_') or node.id in ('eval','exec','open','compile','globals','locals','getattr','setattr','__import__')):raise ValueError('Unsafe identifier')
        if isinstance(node,ast.Assign) and any(not isinstance(t,ast.Name) or t.id in ('pool','charge','save','RuntimeError','ValueError','Exception') for t in node.targets):raise ValueError('Cannot replace capabilities or mutate attributes')
        if isinstance(node,ast.Attribute) and (node.attr.startswith('_') or node.attr not in ('acquire','release','get')):raise ValueError('Unsafe attribute')
        if isinstance(node,ast.Call):
            if isinstance(node.func,ast.Name):
                if node.func.id not in ('charge','save','RuntimeError','ValueError','TypeError','Exception'):raise ValueError('Call is not allowlisted')
            elif isinstance(node.func,ast.Attribute):
                if node.func.attr in ('acquire','release') and (not isinstance(node.func.value,ast.Name) or node.func.value.id!='pool'):raise ValueError('Invalid pool capability')
                if node.func.attr not in ('acquire','release','get'):raise ValueError('Call is not allowlisted')
            else:raise ValueError('Indirect call not allowed')
        if isinstance(node,ast.Constant) and isinstance(node.value,str) and len(node.value)>2000:raise ValueError('String too large')
    return tree

def validate_config(content):
    value=json.loads(content)
    expected={'bank_timeout_ms':int,'bank_available':bool,'bank_latency_ms':int,'database_available':bool,'order_available':bool,'bank_path':str,'gateway_path':str,'pool_size':int,'processing_delay_ms':int}
    if not isinstance(value,dict) or set(value)!=set(expected):raise ValueError('Configuration keys are restricted')
    for k,t in expected.items():
        if type(value[k]) is not t:raise ValueError('Invalid type: '+k)
    for k,lo,hi in [('bank_timeout_ms',10,6000),('bank_latency_ms',0,2500),('pool_size',1,20),('processing_delay_ms',0,2000)]:
        if not lo<=value[k]<=hi:raise ValueError('Out-of-range configuration: '+k)
    for k in ('bank_path','gateway_path'):
        if value[k] not in ('/charge','/pay','/missing'):raise ValueError('Only local allowlisted endpoint paths are supported')
    return value

class PatchExecutor:
    def __init__(self,repo,audit,files=FILES,config_validator=validate_config):
        self.files=tuple(files);self.config_validator=config_validator
        self.repo=Path(repo).resolve(); self.audit=Path(audit);self.audit.mkdir(parents=True,exist_ok=True)
    def path(self,name):
        if name not in self.files:raise ValueError('Restricted path: only '+', '.join(self.files)+' may change')
        p=self.repo/name
        if p.is_symlink() or p.resolve().parent!=self.repo:raise ValueError('Path traversal or symlink rejected')
        return p
    def validate(self,edits):
        if not isinstance(edits,list) or not 1<=len(edits)<=2:raise ValueError('One or two structured file edits required')
        names=[];diffs=[]; originals={};checks=[]
        for edit in edits:
            if not isinstance(edit,dict) or set(edit)!= {'path','original_hash','content'}:raise ValueError('Invalid edit; commands and extra fields are forbidden')
            p=self.path(edit['path']);names.append(edit['path']);current=p.read_text(encoding='utf-8')
            if digest(current)!=edit['original_hash']:raise ValueError('Source changed since proposal')
            content=edit['content']
            if not isinstance(content,str) or len(content.encode())>16000:raise ValueError('Patch content too large')
            if content==current:raise ValueError('No-op patch')
            originals[edit['path']]=current
            if p.suffix=='.py':
                validate_python(content)
                probe=subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('patch_probe.py'))],input=json.dumps({'source':content}),text=True,capture_output=True,timeout=5,env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','TEMP','TMP','PATH')})
                if probe.returncode:raise ValueError('Patch validation failed: '+probe.stdout[:300])
                checks.extend(['Syntax valid','Restricted AST: no imports, shell, filesystem, loops or indirect calls','Success + exception cleanup tests passed'])
            else:self.config_validator(content);checks.extend(['JSON schema and type checks passed','Local endpoint allowlist passed'])
            diffs.append(''.join(difflib.unified_diff(current.splitlines(True),content.splitlines(True),fromfile='a/'+edit['path'],tofile='b/'+edit['path'])))
        if len(set(names))!=len(names):raise ValueError('Duplicate path')
        return {'checks':list(dict.fromkeys(['Restricted paths; no secret files']+checks)),'diff':'\n'.join(diffs),'originals':originals,'passed':True}
    def record(self,record):
        (self.audit/(record['id']+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
    def apply(self,edits,approved=False):
        if approved is not True:raise ValueError('Human approval required')
        validation=self.validate(edits)
        for edit in edits:
            if digest(self.path(edit['path']).read_text(encoding='utf-8'))!=edit['original_hash']:raise ValueError('Source changed during validation')
        record={'id':uuid.uuid4().hex,'timestamp':time.time(),'originals':validation['originals'],'proposed':edits,'approved':True,'result':'applying'};self.record(record)
        try:
            for edit in edits:
                p=self.path(edit['path'])
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.repo,prefix='.ic-patch-',delete=False) as stream:
                    stream.write(edit['content']);tmp=Path(stream.name)
                try:tmp.replace(p)
                finally:tmp.unlink(missing_ok=True)
            record['result']='applied';record['applied_hashes']={e['path']:digest(e['content']) for e in edits};self.record(record)
            return record
        except Exception:
            for name,content in record['originals'].items():self.path(name).write_text(content,encoding='utf-8')
            record['result']='reverted_after_error';self.record(record);raise
    def rollback(self,record):
        for name,value in record['applied_hashes'].items():
            if digest(self.path(name).read_text(encoding='utf-8'))!=value:raise ValueError('Rollback blocked: newer source change')
        for name,content in record['originals'].items():self.path(name).write_text(content,encoding='utf-8')
        record['result']='rolled_back';self.record(record)
        return record
