import json, os, urllib.request, datetime
API = os.environ['PAPERCLIP_API_URL']; KEY = os.environ['PAPERCLIP_API_KEY']; RUN = os.environ['PAPERCLIP_RUN_ID']
C = 'a178baa8-538e-4172-88b9-c0b95e787e56'; I = '0d15c4a1-2d6b-4fd9-a9c0-28ecc6205ac5'
GOAL = '3b2ff26a-452f-447b-b09a-d5e11a5cfa86'; PROJ = '7f953c99-ffa7-44f4-8216-da5b91d8791a'
SIM = '6ba3ac88-12e8-41a7-834f-98e3d92dae78'
def req(method, path, body=None):
    r = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + KEY, 'X-Paperclip-Run-Id': RUN, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(r) as resp: return json.load(resp)
# guards
cm = sorted(req('GET', f'/api/issues/{I}/comments'), key=lambda c: c['createdAt'])
assert cm[-1]['id'].startswith('ed15d69c'), cm[-1]['id']
runs = req('GET', f'/api/issues/{I}/runs')
other = [r['runId'] for r in runs if r['status'] in ('running', 'queued') and r['runId'] != RUN]
assert not other, other
kids = req('GET', f'/api/companies/{C}/issues?parentId={I}')
kids = kids if isinstance(kids, list) else kids.get('issues', [])
assert not kids, [k['identifier'] for k in kids]
sim = req('GET', f'/api/companies/{C}/issues?assigneeAgentId={SIM}&status=todo,in_progress,in_review,blocked')
sim = sim if isinstance(sim, list) else sim.get('issues', [])
assert not sim, [k['identifier'] for k in sim]
cur = req('GET', f'/api/issues/{I}')
old = cur['description']
assert old.startswith('**Started: PR #81'), old[:80]
now = datetime.datetime.now(datetime.UTC)
NOW = now.strftime('%Y-%m-%d at %H:%MZ')
# 1. review (todo)
rdesc = open('review-desc.md').read().replace('TIME_Z', NOW)
assert 'TIME_Z' not in rdesc
r = req('POST', f'/api/companies/{C}/issues', {
    'title': 'Review PR #84 (DEC-1197): Saga chapter draws, net-zero draws, draws by you, "up to N target", and the pools',
    'description': rdesc, 'status': 'todo', 'priority': 'low', 'assigneeAgentId': SIM,
    'parentId': I, 'goalId': GOAL, 'projectId': PROJ})
RID, RN = r['id'], r['identifier']; print('review', RID, RN, r['status'], r.get('assigneeAgentId'))
# 2. ruling comment
body = open('ruling-comment.md').read().replace('DEC-REVIEW', RN).replace('TIME_Z', NOW)
assert 'DEC-REVIEW' not in body and 'TIME_Z' not in body
c = req('POST', f'/api/issues/{I}/comments', {'body': body})
CID = c['id']; print('comment', CID, c['createdAt'])
# 3. review description with the ruling id
rdesc2 = rdesc.replace('RULING_ID', CID[:8])
assert 'RULING_ID' not in rdesc2
r2 = req('PATCH', f'/api/issues/{RID}', {'description': rdesc2}); print('review patched', r2['status'])
# 4. state block on DEC-1197 + park with a fallback monitor
st = open('state-block.md').read().replace('DEC-REVIEW', RN).replace('TIME_Z', NOW).replace('RULING_ID', CID[:8])
assert 'DEC-REVIEW' not in st and 'RULING_ID' not in st and 'TIME_Z' not in st
nca = (now + datetime.timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%SZ')
notes = (f'Fallback for review {RN} of PR #84 (head 4985520). If no verdict: resume comment on {RN} if no live Sim Eng run. '
         f'If verdict: route by the STATE block (APPROVE: guard, pinned merge, sweep wt-dec1197, close this then {RN}; CHANGES: fix round to FE). Rulings {CID[:8]}.')
assert len(notes) < 500, len(notes)
p = req('PATCH', f'/api/issues/{I}', {'description': st + old, 'status': 'in_review',
    'executionPolicy': {'monitor': {'nextCheckAt': nca, 'scheduledBy': 'assignee', 'notes': notes}}})
print('dec1197', p['status'], (p.get('executionPolicy') or {}).get('monitor', {}).get('nextCheckAt'))
json.dump({'review': [RID, RN], 'comment': CID, 'time': NOW, 'monitor': nca}, open('posted.json', 'w'))
