"""Bounded local check: start wrangler dev (local D1) + a docs server, run the API test, the browser e2e
and the sprint regression, then stop everything. Usage: python cloud/api/run_local_checks.py"""
import os, subprocess, sys, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API = os.path.join(ROOT, 'cloud', 'api'); WPORT, DPORT = 8798, 8791
env = dict(os.environ, PYTHONIOENCODING='utf-8')
def up(url, t=90):
    for _ in range(t):
        try: urllib.request.urlopen(url, timeout=2); return True
        except Exception: time.sleep(1)
    return False
def kill(p):
    if p and p.poll() is None: subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True)
npx = 'npx.cmd' if os.name == 'nt' else 'npx'
subprocess.run([npx, '--yes', 'wrangler@4', 'd1', 'execute', 'chlopkow', '--local', '--command', 'DROP TABLE IF EXISTS runs'], cwd=API, capture_output=True, stdin=subprocess.DEVNULL)
subprocess.run([npx, '--yes', 'wrangler@4', 'd1', 'execute', 'chlopkow', '--local', '--file', 'schema.sql'], cwd=API, capture_output=True, stdin=subprocess.DEVNULL)
w = subprocess.Popen([npx, '--yes', 'wrangler@4', 'dev', '--local', '--port', str(WPORT), '--ip', '127.0.0.1'], cwd=API, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
d = subprocess.Popen([sys.executable, '-m', 'http.server', str(DPORT), '--bind', '127.0.0.1', '--directory', os.path.join(ROOT, 'docs')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
rc = {}
try:
    assert up(f'http://127.0.0.1:{WPORT}/health'), 'worker did not start'
    assert up(f'http://127.0.0.1:{DPORT}/index.html'), 'docs server did not start'
    W, G = f'http://127.0.0.1:{WPORT}', f'http://127.0.0.1:{DPORT}/index.html'
    rc['api'] = subprocess.run([sys.executable, os.path.join(API, 'test_api.py'), W], env=env).returncode
    # fresh DB for the e2e so the rate-limited spam rows from the API test do not block it
    kill(w); time.sleep(1)
    subprocess.run([npx, '--yes', 'wrangler@4', 'd1', 'execute', 'chlopkow', '--local', '--command', 'DELETE FROM runs'], cwd=API, capture_output=True, stdin=subprocess.DEVNULL)
    w = subprocess.Popen([npx, '--yes', 'wrangler@4', 'dev', '--local', '--port', str(WPORT), '--ip', '127.0.0.1'], cwd=API, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    assert up(f'{W}/health'), 'worker did not restart'
    runner = os.path.join(ROOT, 'test', 'isolated_browser_runner.py')
    rc['e2e'] = subprocess.run([sys.executable, runner, os.path.join(API, 'e2e_local.py'), G, W], env=env, cwd=ROOT).returncode
    rc['sprint'] = subprocess.run([sys.executable, runner, os.path.join('test', 'sprint_board_test.py')], env=dict(env, ARK_URL=G, ARK_SHOTS=os.environ.get('ARK_SHOTS', 'test')), cwd=ROOT).returncode
finally:
    kill(w); kill(d)
print('\nSUMMARY', rc)
sys.exit(0 if rc and all(v == 0 for v in rc.values()) else 1)
