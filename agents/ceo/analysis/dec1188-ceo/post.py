"""DEC-1188 routing (CEO run ce405b94): guard, review issue, STATE block, park, comment."""
import json
import os
import sys
import urllib.request

U = os.environ['PAPERCLIP_API_URL']
H = {
    'Authorization': 'Bearer ' + os.environ['PAPERCLIP_API_KEY'],
    'X-Paperclip-Run-Id': os.environ['PAPERCLIP_RUN_ID'],
    'Content-Type': 'application/json',
}
C = os.environ['PAPERCLIP_COMPANY_ID']
ISSUE = '5204d27c-ee99-42b6-95e6-5e8a3548bc12'
DSE = '8ea33a50-69a7-4a75-bcc1-245bd1e7c73a'
LAST_COMMENT = '1f7f32ba-006b-4842-860a-0d81877778c1'
HERE = os.path.dirname(os.path.abspath(__file__))
DRY = '--dry' in sys.argv


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(U + path, data=data, method=method, headers=H)
    with urllib.request.urlopen(req) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


def rows(d, key):
    return d if isinstance(d, list) else d.get(key, d)


# Guard 1: nothing newer than the dead run's error comment on DEC-1188.
comments = rows(call('GET', f'/api/issues/{ISSUE}/comments'), 'comments')
assert comments[0]['id'] == LAST_COMMENT, ('newer comment', comments[0]['id'], comments[0]['body'][:200])
# Guard 2: the reviewer has no live or queued run and no open issue.
runs = rows(call('GET', f'/api/companies/{C}/heartbeat-runs?agentId={DSE}&limit=5'), 'runs')
live = [r['id'] for r in runs if r['status'] in ('queued', 'running', 'scheduled_retry')]
assert not live, ('reviewer busy', live)
open_issues = rows(call('GET', f'/api/companies/{C}/issues?assigneeAgentId={DSE}&status=todo,in_progress,in_review,blocked'), 'issues')
assert not open_issues, ('reviewer has open issues', [i['identifier'] for i in open_issues])
# Guard 3: DEC-1188 is still mine and in_review.
issue = call('GET', f'/api/issues/{ISSUE}')
assert issue['assigneeAgentId'] == os.environ['PAPERCLIP_AGENT_ID'] and issue['status'] == 'in_review', (issue['assigneeAgentId'], issue['status'])
old_desc = issue['description']
assert not old_desc.startswith('**STATE'), 'state block already there'
print('guards pass')

brief = open(os.path.join(HERE, 'review-brief.md')).read().rstrip('\n')
state_t = open(os.path.join(HERE, 'state.md')).read().rstrip('\n')
comment_t = open(os.path.join(HERE, 'comment.md')).read().rstrip('\n')
notes = ('Fallback for DEC-1188 (CEO run ce405b94). Review {R} (Design System Engineer) of PR #80 at 27e34a4 '
         'is out. If this fires: read {R} for a verdict; route it by the STATE block. If no verdict, read '
         "the reviewer's runs and resume or re-arm.")
if DRY:
    print(brief[:300]); print(state_t[:300]); print(comment_t[:300]); print(len(notes)); sys.exit(0)

review = call('POST', f'/api/companies/{C}/issues', {
    'title': 'Review PR #80 at `27e34a4` (DEC-1188: an answer whose body never ends no longer hangs the tab; the H2 row; the README for a price refresh)',
    'description': brief,
    'status': 'todo',
    'priority': 'low',
    'assigneeAgentId': DSE,
    'parentId': ISSUE,
    'goalId': issue['goalId'],
    'projectId': issue['projectId'],
})
R = review['identifier']
print('review', R, review['id'], review['status'])
open(os.path.join(HERE, 'review-id.txt'), 'w').write(f"{R} {review['id']}\n")

import datetime
T = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%MZ')
state = state_t.replace('{R}', R).replace('{T}', T)
assert '{R}' not in state and '{T}' not in state
d = call('PATCH', f'/api/issues/{ISSUE}', {'description': state + '\n\n---\n\n' + old_desc})
assert d['description'].startswith('**STATE'), 'state block missing'
print('state block written')

n = notes.replace('{R}', R)
assert len(n) < 500, len(n)
d = call('PATCH', f'/api/issues/{ISSUE}', {'status': 'in_review', 'executionPolicy': {'monitor': {
    'nextCheckAt': '2026-10-16T23:00:00Z', 'scheduledBy': 'assignee', 'notes': n}}})
print('park', d['status'], d['executionPolicy']['monitor']['nextCheckAt'])

body = comment_t.replace('{R}', R)
assert '{R}' not in body
c = call('POST', f'/api/issues/{ISSUE}/comments', {'body': body})
print('comment', c['id'])
