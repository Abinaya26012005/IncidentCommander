"""Fixed test program invoked by PatchExecutor; never executes a caller command."""
import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from patch_safety import validate_python

def probe(source):
    validate_python(source)
    namespace={'__builtins__':{'RuntimeError':RuntimeError,'ValueError':ValueError,'TypeError':TypeError,'Exception':Exception}}
    exec(compile(source,'payment_logic.py','exec'),namespace)
    class Pool:
        def __init__(self):self.used=0
        def acquire(self):self.used+=1;return 'connection'
        def release(self,c):
            assert c=='connection';self.used-=1
    for failing in (False,True):
        pool=Pool();calls=[];saved=[]
        def charge():
            calls.append(1)
            if failing:raise RuntimeError('provider failure')
            return {'ok':True,'id':'test'}
        def save(c,r):saved.append((c,r))
        try:result=namespace['process'](pool,charge,save)
        except RuntimeError:
            if not failing:raise
        else:
            assert not failing,'Provider failure must propagate'
            assert result=={'ok':True,'id':'test'},'Return contract failed'
        assert len(calls)==1,'Charge must execute exactly once'
        assert pool.used==0,'Connections must be released on every path'
        assert len(saved)==(0 if failing else 1),'Persistence contract failed'
    return True
if __name__=='__main__':
    try:probe(json.load(sys.stdin)['source']);print('Success and exception path probes passed')
    except Exception as e:print(type(e).__name__+': '+str(e));raise SystemExit(1)
