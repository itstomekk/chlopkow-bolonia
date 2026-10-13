"""API test for chlopkow-api. Usage: python cloud/api/test_api.py [BASE_URL]
Default target: a local `wrangler dev --local` on 127.0.0.1:8799. It WRITES rows: never point it at production."""
import json, sys, urllib.request, urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8799'
assert 'workers.dev' not in BASE, 'this test writes rows; run it against a local wrangler dev only'
ORIGIN = 'http://127.0.0.1:8765'
fails = []


def check(cond, msg):
    print(('OK   ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)


def call(method, path, body=None, origin=ORIGIN):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'Origin': origin})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return r.status, json.loads(r.read() or b'{}'), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}'), dict(e.headers)


def splits(total, k=1.0):   # a plausible sprint trace ending at `total`
    base = [1.9, 3.1, 4.2, 5.3, 6.35, 7.4, 8.45, 9.5, 10.55, 11.6]
    return [round(v * total / 11.6, 2) for v in base]


def run(name, score, device='dev-aaaa-0001', strides=100, trace=None, penalty=0):
    return call('POST', '/v1/games/sprint/runs', {'device': device, 'name': name, 'char': 'arek', 'score': score,
                'trace': trace if trace is not None else splits(score - penalty), 'proof': {'strides': strides, 'falseStarts': 0}, 'mode': 'local2', 'client': 'test'})


st, b, h = call('GET', '/health'); check(st == 200 and b.get('service') == 'chlopkow-api', 'health')
check(h.get('Access-Control-Allow-Origin') == ORIGIN, 'CORS allows the local game')
st, b, h = call('GET', '/health', origin='https://evil.example'); check('Access-Control-Allow-Origin' not in h, 'CORS refuses other origins')
st, b, _ = call('GET', '/v1/games'); check(st == 200 and [g['id'] for g in b['games']] == ['sprint'], f'registry lists enabled games only {b}')
st, b, _ = call('GET', '/v1/games/sprint/board')
check(st == 200 and b['best'] == [] and b['recent'] == [] and b['average'] == {'score': None, 'count': 0} and b['cpu']['trace'] is None, f'empty board {b}')
check(call('GET', '/v1/games/pig/board')[0] == 404, 'disabled game is not open yet')

st, b, _ = run('Ala', 12.345); check(st == 200 and b['rank'] == 1 and b['score'] == 12.35 and b['players'] == 1, f'first run {b}')
st, b, _ = run('Ola', 11.2, device='dev-bbbb-0002'); check(st == 200 and b['rank'] == 1, f'faster run ranks 1 {b}')
st, b, _ = run('Ala', 14.0); check(st == 200 and b['rank'] == 2 and b['best'] == 12.35, f'slower run keeps best {b}')
st, b, _ = run('Ala', 13.0, device='dev-cccc-0003'); check(st == 200 and b['players'] == 3, f'same name on another device = another player {b}')
st, b, _ = run('Ola', 15.0, device='dev-bbbb-0002', penalty=2); check(st == 200, 'trace may be up to 2 s shorter than the score (false start)')
st, b, _ = run('Bot', 5.0); check(st == 422 and b['error'] == 'implausible score', 'too fast rejected')
st, b, _ = run('Bot', 12.0, strides=10); check(st == 422 and b['error'] == 'implausible run', 'too few strides rejected')
st, b, _ = run('Bot', 12.0, trace=[1] * 10); check(st == 422 and b['error'] == 'implausible trace', 'impossible splits rejected')
st, b, _ = run('Bot', 12.0, trace=splits(9.5)); check(st == 422 and b['error'] == 'trace does not match score', 'trace must match score')
st, b, _ = run('Bot', 12.0, trace=[1, 2]); check(st == 422 and b['error'] == 'bad trace', 'short trace rejected')
st, b, _ = run('', 12.0); check(st == 400, 'empty name rejected')
st, b, _ = run('X', 12.0, device='x'); check(st == 400 and b['error'] == 'device required', 'device id required')
check(call('POST', '/v1/games/pig/runs', {'device': 'dev-aaaa-0001', 'name': 'a', 'score': 9})[0] == 400, 'disabled game refuses runs')

st, b, _ = call('GET', '/v1/games/sprint/board')
best = [(r['name'], r['score']) for r in b['best']]
check(best == [('Ola', 11.2), ('Ala', 12.35), ('Ala', 13.0)], f'best = one row per player (device+name), ordered {best}')
check([r['score'] for r in b['recent']][:2] == [15.0, 13.0], f'recent = latest first {[r["score"] for r in b["recent"]]}')
scores = [12.35, 11.2, 14.0, 13.0, 15.0]
check(b['average']['count'] == 5 and abs(b['average']['score'] - round(sum(scores) / 5, 2)) < 1e-9, f'average of all results {b["average"]}')
tr = b['cpu']['trace']
check(tr is not None and len(tr) == 10 and all(tr[i] < tr[i + 1] for i in range(9)), f'cpu trace = averaged splits {tr}')
exp_last = round((12.35 + 11.2 + 14.0 + 13.0 + 13.0) / 5, 2)
check(abs(tr[-1] - exp_last) < .011 and b['cpu']['count'] == 5, f'cpu trace end = mean of trace ends ({tr[-1]} vs {exp_last})')
check(b['players'] == 3, 'players counted per device + name')
st, b, _ = call('GET', '/v1/games/sprint/board?period=day'); check(b['period'] == 'day' and b['average']['count'] == 5, 'day period includes today')

for i in range(80):
    st, b, _ = run(f'Spam{i}', 20 + i * .01, device='dev-spam-0009')
    if st == 429: break
check(st == 429, f'rate limit kicks in ({i + 1} more posts)')
print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
