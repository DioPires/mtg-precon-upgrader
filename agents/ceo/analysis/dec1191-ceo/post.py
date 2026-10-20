import json, os, urllib.request, datetime, sys
API = os.environ['PAPERCLIP_API_URL']; KEY = os.environ['PAPERCLIP_API_KEY']; RUN = os.environ['PAPERCLIP_RUN_ID']
C = 'a178baa8-538e-4172-88b9-c0b95e787e56'; I = '1e1b2026-4bbb-4855-836b-948540e1713c'
GOAL = '3b2ff26a-452f-447b-b09a-d5e11a5cfa86'; PROJ = '7f953c99-ffa7-44f4-8216-da5b91d8791a'
FE = '4e51e111-eff7-4619-95dd-9e43a955e637'; SIM = '6ba3ac88-12e8-41a7-834f-98e3d92dae78'
def req(method, path, body=None):
    r = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + KEY, 'X-Paperclip-Run-Id': RUN, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(r) as resp: return json.load(resp)
log = {}
# guard: thread holds nothing newer than the hand-back; Sim Eng has no live run
cm = req('GET', f'/api/issues/{I}/comments')
assert cm[0]['id'] == '6934a8d5-743b-4ba3-8227-47a3a515c4c0', cm[0]['id']
runs = req('GET', f'/api/companies/{C}/heartbeat-runs?agentId={SIM}&limit=3')
live = [r for r in runs if r['status'] in ('running', 'queued')]
assert not live, live
sim_issues = req('GET', f'/api/companies/{C}/issues?assigneeAgentId={SIM}&status=todo,in_progress')
assert not sim_issues, [i['identifier'] for i in sim_issues]
# 1. follow-up (backlog)
fdesc = open('followup-desc.md').read()
f = req('POST', f'/api/companies/{C}/issues', {
    'title': 'Classifier follow-ups of PR #81: Saga chapter draws, "an additional card", a cost that spends the card, net-zero draws (R-1, R-2, R-4, repeatable loots) and "up to N target" (DEC-1191 rulings)',
    'description': fdesc, 'status': 'backlog', 'priority': 'low', 'assigneeAgentId': FE,
    'parentId': I, 'goalId': GOAL, 'projectId': PROJ})
FID, FN = f['id'], f['identifier']; log['follow'] = (FID, FN, f['status']); print('follow', FID, FN, f['status'])
# 2. review (todo)
rdesc = open('review-desc.md').read().replace('DEC-FOLLOW', FN)
assert 'DEC-FOLLOW' not in rdesc
r = req('POST', f'/api/companies/{C}/issues', {
    'title': 'Review PR #81 (DEC-1191): a cantrip is not card draw, a power cut is not removal, a qualified toughness cut is, and the pools',
    'description': rdesc, 'status': 'todo', 'priority': 'low', 'assigneeAgentId': SIM,
    'parentId': I, 'goalId': GOAL, 'projectId': PROJ})
RID, RN = r['id'], r['identifier']; log['review'] = (RID, RN, r['status']); print('review', RID, RN, r['status'])
# 3. ruling comment
now = datetime.datetime.now(datetime.UTC).strftime('2026-10-16 at %H:%MZ')
body = open('ruling-comment.md').read().replace('DEC-REVIEW', RN).replace('DEC-FOLLOW', FN).replace('TIME_Z', now)
assert 'DEC-REVIEW' not in body and 'DEC-FOLLOW' not in body and 'TIME_Z' not in body
c = req('POST', f'/api/issues/{I}/comments', {'body': body})
CID = c['id']; print('comment', CID, c['createdAt'])
# 4. follow-up description with the ruling id
fdesc2 = fdesc.replace('RULING_ID', '`' + CID[:8] + '`'.strip('`')) if False else fdesc.replace('`RULING_ID`', '`' + CID[:8] + '`').replace('RULING_ID', '`' + CID[:8] + '`')
assert 'RULING_ID' not in fdesc2
f2 = req('PATCH', f'/api/issues/{FID}', {'description': fdesc2}); print('follow patched', f2['status'])
# 5. state block on DEC-1191 + park
old = open('/tmp/dec1191-ceo/dec1191-desc-old.md').read()
cur = req('GET', f'/api/issues/{I}')['description']
assert cur == old, 'description moved'
st = open('state-block.md').read().replace('DEC-REVIEW', RN).replace('DEC-FOLLOW', FN).replace('TIME_Z', now).replace('`RULING_ID`', '`' + CID[:8] + '`')
assert 'DEC-REVIEW' not in st and 'RULING_ID' not in st
notes = f'Fallback for review {RN} of PR #81 (head a857950). If no verdict: resume comment on {RN}. If verdict: route by the STATE block (APPROVE: guard, merge pinned, sweep wt-dec1191, start {FN}; CHANGES: fix round). Rulings {CID[:8]}.'
assert len(notes) < 500, len(notes)
p = req('PATCH', f'/api/issues/{I}', {'description': st + old, 'status': 'in_review',
    'executionPolicy': {'monitor': {'nextCheckAt': '2026-10-17T00:30:00Z', 'scheduledBy': 'assignee', 'notes': notes}}})
print('dec1191', p['status'], p['executionPolicy']['monitor']['nextCheckAt'])
json.dump({'follow': [FID, FN], 'review': [RID, RN], 'comment': CID, 'time': now}, open('posted.json', 'w'))
