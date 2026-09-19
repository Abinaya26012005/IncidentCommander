"""Optional container supervisor. The existing run.py local workflow is unchanged."""
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy.gateway import DemoServer, DemoState


def child_environment(base, cl):
    environment = {k: v for k, v in os.environ.items() if k in {
        'PATH', 'SystemRoot', 'SYSTEMROOT', 'TEMP', 'TMP', 'LANG', 'LC_ALL',
        'APPDATA', 'LOCALAPPDATA', 'TIKTOKEN_CACHE_DIR', 'SSL_CERT_FILE', 'PYTHONUNBUFFERED'}}
    environment.update(IC_BASE_PORT=str(base), CL_BASE_PORT=str(cl),
                       IC_DATA_DIR=os.environ.get('IC_DATA_DIR', str(ROOT / 'runtime')),
                       IC_CONTROL_TOKEN=secrets.token_hex(32), OPENAI_API_KEY='', OPENAI_MODEL='')
    return environment


def main():
    if os.environ.get('DEMO_AUTH_ENABLED') != 'true':
        raise RuntimeError('Set DEMO_AUTH_ENABLED=true before starting public deployment')
    base = int(os.environ.get('IC_BASE_PORT', '8787'))
    cl = int(os.environ.get('CL_BASE_PORT', str(base + 10)))
    state = DemoState(os.environ.get('PUBLIC_ORIGIN') or os.environ.get('RENDER_EXTERNAL_URL', ''),
                      os.environ.get('DEMO_USERNAME', ''), os.environ.get('DEMO_PASSWORD', ''), base, cl)
    # Do not pass platform credentials or demo password into remediation processes.
    environment = child_environment(base, cl)
    children = []
    stopped = threading.Event()
    server = None
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stopped.set())
    try:
        for entry in ('payflow.py', 'converselab/server.py', 'commander.py'):
            children.append(subprocess.Popen([sys.executable, str(ROOT / entry)], cwd=ROOT, env=environment))
        deadline = time.monotonic() + 60
        while not stopped.is_set():
            if any(p.poll() is not None for p in children):
                raise RuntimeError('An application exited during startup')
            try:
                for port in state.ports.values():
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1) as response:
                        if response.status != 200: raise OSError('Not ready')
                break
            except OSError:
                if time.monotonic() >= deadline: raise RuntimeError('Application startup timed out')
                stopped.wait(.25)
        if stopped.is_set(): return
        server = DemoServer(('0.0.0.0', int(os.environ.get('PORT', '10000'))), state)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print('Authenticated demo gateway ready. Credentials are not logged.', flush=True)
        while not stopped.wait(.5):
            if any(p.poll() is not None for p in children):
                raise RuntimeError('An application exited; supervisor stopping for platform restart')
    finally:
        if server:
            server.shutdown()
            server.server_close()
        for child in children:
            if child.poll() is None: child.terminate()
        for child in children:
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)


if __name__ == '__main__': main()
