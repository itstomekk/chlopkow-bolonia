"""Review-store test for chlopkow-api (local only). Usage: python cloud/api/test_review.py [BASE_URL]
Seeds its own review row in the LOCAL D1 (wrangler d1 execute --local) with a throwaway key, then exercises GET/PUT/history/CORS.
It writes rows: refuses a workers.dev URL."""
import hashlib, json, os, subprocess, sys, urllib.request, urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8799'
assert 'workers.dev' not in BASE, 'this test writes rows; run it against a local wrangler dev only'
API = os.path.dirname(os.path.abspath(__file__))
ORIGIN = 'https://itstomekk.pages.dev'
RID, KEY = 'test-review', 'k' * 8 + 'localtestkey0123456789'
fails = []


def check(cond, msg):
    print(('OK   ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)


def call(method, path, body=None, key=KEY, origin=ORIGIN, raw=None, headers=None):
    h = {'Origin': origin} if origin else {}
    if key is not None: h['X-Review-Key'] = key
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    if data is not None: h['Content-Type'] = 'application/json'
    h.update(headers or {})
    req = urllib.request.Request(BASE + path, method=method, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, json.loads(r.read() or b'{}'), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}'), dict(e.headers)


def d1(sql):
    npx = 'npx.cmd' if os.name == 'nt' else 'npx'
    r = subprocess.run([npx, '--yes', 'wrangler@4', 'd1', 'execute', 'chlopkow', '--local', '--command', sql], cwd=API, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stdout + r.stderr


d1(f"DELETE FROM review_history; DELETE FROM reviews; INSERT INTO reviews (id, key_hash, created_at) VALUES ('{RID}', '{hashlib.sha256(KEY.encode()).hexdigest()}', 1)")

P = f'/review/{RID}'
check(call('GET', P, key=None)[0] == 401, 'GET without key -> 401')
check(call('GET', P, key='wrong-key')[0] == 401, 'GET with wrong key -> 401')
check(call('PUT', P, {'a': 1}, key=None)[0] == 401, 'PUT without key -> 401')
check(call('PUT', P, {'a': 1}, key='wrong-key')[0] == 401, 'PUT with wrong key -> 401')
check(call('GET', '/review/nope', key=KEY)[0] == 401, 'unknown review id -> 401 (no enumeration)')
check(call('GET', '/review/BAD_ID!', key=KEY)[0] == 404, 'malformed id -> 404')
st, b, h = call('GET', P); check(st == 200 and b['doc'] == {} and b['rev'] == 0, f'fresh doc {b}')
check(h.get('Access-Control-Allow-Origin') == ORIGIN and h.get('Cache-Control') == 'no-store', 'CORS allows only the Pages origin, no-store')
check('Access-Control-Allow-Origin' not in call('GET', P, origin='https://evil.example')[2], 'CORS refuses other origins')
check('Access-Control-Allow-Origin' not in call('GET', P, origin='http://127.0.0.1:8765')[2], 'CORS refuses localhost for the review')
st, b, h = call('OPTIONS', P, key=None)
check(st == 204 and 'X-Review-Key' in h.get('Access-Control-Allow-Headers', '') and 'PUT' in h.get('Access-Control-Allow-Methods', '') and h.get('Access-Control-Allow-Origin') == ORIGIN, 'preflight allows PUT + X-Review-Key from the Pages origin')

doc = {'review': 'x', 'state': {'houses': {'19': {'option': '2', 'note': 'zażółć gęślą jaźń'}}}}
st, b, _ = call('PUT', P, doc); check(st == 200 and b['rev'] == 1 and b['updated_at'] > 0, f'PUT stores {b}')
st, b, _ = call('GET', P); check(b['doc'] == doc and b['rev'] == 1, 'GET returns what was stored (unicode intact)')
st, b, _ = call('PUT', P, {'n': 2}, headers={'X-Base-Rev': '0'}); check(st == 409 and b['rev'] == 1, f'stale X-Base-Rev -> 409 {b}')
st, b, _ = call('PUT', P, {'n': 2}, headers={'X-Base-Rev': '1'}); check(st == 200 and b['rev'] == 2, 'matching X-Base-Rev -> saved')
check(call('GET', P)[1]['doc'] == {'n': 2}, 'conflict did not overwrite')
check(call('PUT', P, raw=b'{not json')[0] == 400, 'invalid JSON -> 400')
check(call('PUT', P, raw=b'[1,2]')[0] == 400, 'array document -> 400')
check(call('PUT', P, raw=b'null')[0] == 400, 'null document -> 400')
big = json.dumps({'pad': 'x' * (300 * 1024)}).encode()
check(call('PUT', P, raw=big)[0] == 413, 'body over 256 KB -> 413')
check(call('GET', P)[1]['doc'] == {'n': 2}, 'rejected writes changed nothing')
ok_big = json.dumps({'pad': 'y' * (200 * 1024)}).encode()
check(call('PUT', P, raw=ok_big)[0] == 200, '200 KB document accepted')
check(call('DELETE', P)[0] == 405, 'DELETE not allowed')

for i in range(25): call('PUT', P, {'i': i})
st, b, _ = call('GET', P + '/history')
revs = [x['rev'] for x in b['history']]
check(st == 200 and len(revs) == 20 and revs == sorted(revs, reverse=True), f'history keeps the newest 20, newest first ({revs[:3]}..{revs[-1]})')
cur = call('GET', P)[1]
check(revs[0] == cur['rev'], 'newest history entry = current rev')
st, b, _ = call('GET', P + f'/history?rev={cur["rev"] - 3}'); check(st == 200 and b['doc'] == {'i': 21}, f'history?rev returns that save {b}')
check(call('GET', P + '/history?rev=1')[0] == 404, 'old saves are pruned')
check(call('GET', P + '/history', key='bad')[0] == 401, 'history needs the key too')

# game endpoints untouched
st, b, h = call('GET', '/v1/games', key=None, origin='http://127.0.0.1:8765')
check(st == 200 and [g['id'] for g in b['games']] == ['sprint'] and h.get('Access-Control-Allow-Origin') == 'http://127.0.0.1:8765', 'score registry + its CORS unchanged')
check('Access-Control-Allow-Origin' not in call('GET', '/v1/games', key=None, origin=ORIGIN)[2], 'Pages origin gets no CORS on the score endpoints')
check(call('GET', '/v1/games/sprint/board', key=None)[0] == 200, 'board still answers')
check(call('GET', '/nothing', key=None)[0] == 404, 'unknown path -> 404')
print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
