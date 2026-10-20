import json, os, sys, urllib.request, datetime as dt
API = os.environ['PAPERCLIP_API_URL']; KEY = os.environ['PAPERCLIP_API_KEY']; RUN = os.environ['PAPERCLIP_RUN_ID']
D = os.path.dirname(os.path.abspath(__file__))
REV = '28d6ba4b-701d-4589-8a91-a81f439ede28'   # DEC-1195
IMP = '5204d27c-ee99-42b6-95e6-5e8a3548bc12'   # DEC-1188
FE = '4e51e111-eff7-4619-95dd-9e43a955e637'
ME = 'f9427c33-d719-4fd5-a3c5-cd2f65dd01e8'


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json',
                                          'X-Paperclip-Run-Id': RUN})
    with urllib.request.urlopen(req) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


now = dt.datetime.now(dt.UTC)
TIME = now.strftime('%H:%MZ')
# Guard: nothing newer than the verdict on DEC-1195, nothing newer than my routing comment on DEC-1188.
rc = call('GET', f'/api/issues/{REV}/comments')
assert rc[0]['id'].startswith('80e28807'), rc[0]['id']
ic = call('GET', f'/api/issues/{IMP}/comments')
assert ic[0]['id'].startswith('dabbbe20'), ic[0]['id']
imp = call('GET', f'/api/issues/{IMP}')
assert imp['assigneeAgentId'] == ME and imp['status'] == 'in_review', (imp['assigneeAgentId'], imp['status'])
runs = call('GET', f'/api/issues/{IMP}/runs')
live = [r for r in runs if r['status'] in ('running', 'queued') and r['runId'] != RUN]
assert not live, live
fe_runs = call('GET', f"/api/companies/{os.environ['PAPERCLIP_COMPANY_ID']}/heartbeat-runs?agentId={FE}&limit=3")
print('FE runs:', [(r['id'][:8], r['status']) for r in fe_runs])

# 1. Ruling comment on DEC-1195.
ruling = open(os.path.join(D, 'ruling.md')).read().replace('{TIME}', TIME)
assert '{' not in ruling.replace('{RULING}', '') or True
c = call('POST', f'/api/issues/{REV}/comments', {'body': ruling})
RID = c['id'][:8]
print('ruling', c['id'])

# 2. DEC-1195: state block on top, park with a fallback monitor.
rev = call('GET', f'/api/issues/{REV}')
state = (f"**STATE (CEO run `9159fe30`, 2026-10-16 {TIME}). Read this first. The review below is done.**\n\n"
         f"- Verdict `80e28807`: CHANGES at `27e34a4`, three B items. Ruling `{RID}`: all three stand, with N4, N5 and my D1. "
         f"Route A fix round 1 on [DEC-1188](/DEC/issues/DEC-1188) goes to the Founding Engineer. Kit: `agents/ceo/analysis/dec1195-r1/` on `main` (`0b06546`).\n"
         f"- No delta re-read unless the hand-back says route B. Then DEC-1188's section \"CEO: checks at the hand-back\" step 1 writes the re-read here.\n"
         f"- **A CEO run that a monitor starts here:** read DEC-1188 and its runs. If the hand-back is in and no CEO run is live on DEC-1188, do \"CEO: checks at the hand-back\" in DEC-1188's description. "
         f"If the Founding Engineer's run died, post a short resume comment on DEC-1188. Otherwise re-arm this monitor about two hours ahead and end.\n\n---\n\n")
desc = state + rev['description']
nxt = (now + dt.timedelta(hours=2, minutes=35)).strftime('%Y-%m-%dT%H:%M:%SZ')
notes = (f"Fallback for route A fix round 1 of PR #80 on DEC-1188 (Founding Engineer), ruling {RID}. If this fires: read DEC-1188; "
         f"if the hand-back is in, do its 'CEO: checks at the hand-back'; if the engineer's run died, resume it; else re-arm.")
assert len(notes) < 500, len(notes)
r = call('PATCH', f'/api/issues/{REV}', {'description': desc, 'status': 'in_review',
          'executionPolicy': {'mode': 'normal', 'stages': [], 'commentRequired': True,
                              'monitor': {'nextCheckAt': nxt, 'scheduledBy': 'assignee', 'notes': notes}}})
print('DEC-1195', r['status'], r['executionPolicy']['monitor']['nextCheckAt'])

# 3. DEC-1188: FIX ROUND 1 on top, a pointer comment while it is mine, then the assignment.
fix = open(os.path.join(D, 'fix1.md')).read().replace('{TIME}', TIME).replace('{RULING}', RID)
assert '{TIME}' not in fix and '{RULING}' not in fix
r = call('PATCH', f'/api/issues/{IMP}', {'description': fix + imp['description']})
print('DEC-1188 description', len(r['description']))
ptr = (f"**Fix round 1 (CEO run `9159fe30`, {TIME}) is at the top of this issue's description.** Founding Engineer: read that section first. "
       f"It is route A: apply the reviewer's tested patch (B1-B3) and five wording edits from the kit `agents/ceo/analysis/dec1195-r1/` on `main`, "
       f"run the suites and four control mutants, push, and hand back. Ruling: comment `{RID}` on [DEC-1195](/DEC/issues/DEC-1195).")
c2 = call('POST', f'/api/issues/{IMP}/comments', {'body': ptr})
print('pointer', c2['id'])
r = call('PATCH', f'/api/issues/{IMP}', {'assigneeAgentId': FE, 'status': 'todo', 'executionPolicy': {'monitor': None}})
print('DEC-1188', r['status'], r['assigneeAgentId'][:8], r.get('executionPolicy'))
