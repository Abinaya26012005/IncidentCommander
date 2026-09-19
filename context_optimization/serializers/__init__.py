"""Reference TOON 4.1.1; deterministic reversible HYBRID framing v1."""
import json,subprocess,shutil
from pathlib import Path
from ..integrity_guard import canonical
from ..profiler import uniform

VERSION='JSON/1; @toon-format/toon/4.1.1; HYBRID/1'

def codec(values,op='encode'):
    node=shutil.which('node')
    if not node:raise ValueError('Node reference codec unavailable')
    result=subprocess.run([node,str(Path(__file__).with_name('codec.mjs'))],input=canonical({'op':op,'values':values}),text=True,encoding='utf-8',capture_output=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('TOON codec unavailable or rejected input')
    return json.loads(result.stdout)

def json_candidate(payload):return canonical(payload),json.loads(canonical(payload))
def toon_candidate(payload):
    result=codec([payload])[0];return result['text'],result['decoded']

def hybrid_candidate(payload):
    tables=[];paths=[]
    def split(x,path=()):
        if uniform(x) and len(x)>=4:
            paths.append(list(path));tables.append(x);return None
        if isinstance(x,dict):return {k:split(v,path+(k,)) for k,v in sorted(x.items())}
        if isinstance(x,list):return [split(v,path+(i,)) for i,v in enumerate(x)]
        return x
    tree=split(payload);parts=codec(tables) if tables else []
    # Each section uses an explicit character length: embedded newlines cannot break framing.
    text='HYBRID/1\n'+canonical(tree)+'\n'
    for path,part in zip(paths,parts):
        text+=canonical({'path':path,'characters':len(part['text'])})+'\n'+part['text']+'\n'
    return text,decode_hybrid(text)

def decode_hybrid(text):
    if not text.startswith('HYBRID/1\n'):raise ValueError('Invalid hybrid version')
    line,tail=text[len('HYBRID/1\n'):].split('\n',1);tree=json.loads(line);sections=[];paths=[]
    while tail:
        header,tail=tail.split('\n',1);header=json.loads(header);n=header['characters']
        if type(n) is not int or n<0 or len(tail)<=n or tail[n]!='\n':raise ValueError('Invalid hybrid frame')
        paths.append(header['path']);sections.append(tail[:n]);tail=tail[n+1:]
    values=codec(sections,'decode') if sections else []
    for path,value in zip(paths,values):
        if not path:tree=value;continue
        target=tree
        for key in path[:-1]:target=target[key]
        if target[path[-1]] is not None:raise ValueError('Invalid hybrid replacement')
        target[path[-1]]=value
    return tree
