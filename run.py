"""Run both apps. No pip install is necessary (Python 3.10+ and Git)."""
import os, subprocess, sys, time, urllib.request, secrets
from pathlib import Path

root=Path(__file__).resolve().parent
base=int(os.environ.get('IC_BASE_PORT','8787'))
os.environ['IC_CONTROL_TOKEN']=secrets.token_hex(32)
children=[]
try:
    children.append(subprocess.Popen([sys.executable,str(root/'payflow.py')],cwd=root))
    for _ in range(60):
        if children[0].poll() is not None: raise RuntimeError('PayFlow could not start. Check port availability and Git installation.')
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{base+1}/health',timeout=.5).close(); break
        except OSError: time.sleep(.25)
    else: raise RuntimeError('PayFlow startup timed out')
    children.append(subprocess.Popen([sys.executable,str(root/'converselab'/'server.py')],cwd=root))
    children.append(subprocess.Popen([sys.executable,str(root/'commander.py')],cwd=root))
    print(f'\nOpen IncidentCommander: http://127.0.0.1:{base}\nOpen PayFlow: http://127.0.0.1:{base+1}\nOpen ConverseLab: http://127.0.0.1:{int(os.environ.get("CL_BASE_PORT",base+10))}\nCtrl+C stops all applications.\n',flush=True)
    while all(p.poll() is None for p in children): time.sleep(.5)
finally:
    for child in children:
        if child.poll() is None: child.terminate()
    for child in children:
        try: child.wait(timeout=5)
        except subprocess.TimeoutExpired: child.kill()
