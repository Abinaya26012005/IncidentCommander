"""Read-only, bounded local source/Git observations. No injector imports."""
import hashlib, subprocess, time
from pathlib import Path

FILES=('payment_logic.py','config.json')
def digest(text): return hashlib.sha256(text.encode()).hexdigest()

class LocalSourceChangeProvider:
    def __init__(self, repo, files=FILES): self.files=tuple(files); self.repo=Path(repo).resolve(); self.previous={}; self.observation=None; self.git_checked=0
    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],text=True,stderr=subprocess.STDOUT,timeout=5).strip()
    def read(self):
        result={}
        for name in self.files:
            p=self.repo/name
            if p.is_symlink() or p.resolve().parent!=self.repo: raise ValueError('Source path escaped repository')
            if p.stat().st_size>16000: raise ValueError('Demo source exceeds the 16 KB evidence limit')
            result[name]=p.read_text(encoding='utf-8')
        return result
    def scan(self, force=False):
        files=self.read(); hashes={k:digest(v) for k,v in files.items()}
        if not force and hashes==self.previous:
            if time.time()-self.git_checked<2:return None
            self.git_checked=time.time()
            if self.git('rev-parse','--short','HEAD')==(self.observation or {}).get('sha'):return None
        changed=[k for k in files if hashes[k]!=self.previous.get(k)]
        self.previous=hashes
        self.observation={'detected_at':time.time(),'changed_files':changed,'hashes':hashes,'files':files,
            'timestamps':{k:(self.repo/k).stat().st_mtime for k in files},
            'working_diff':self.git('diff','HEAD','--no-ext-diff','--',*self.files)[:24000],
            'status':self.git('status','--short','--',*self.files),
            'commit_diff':self.git('show','--format=fuller','--no-ext-diff','HEAD','--',*self.files)[:16000],
            'recent_commits':self.git('log','-5','--format=%h %ct %s')[:4000],
            'sha':self.git('rev-parse','--short','HEAD')}
        return self.observation

LocalGitProvider=LocalSourceChangeProvider
