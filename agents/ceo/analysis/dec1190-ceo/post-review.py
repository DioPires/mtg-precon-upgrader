import json, os, sys, time, urllib.request, datetime
API=os.environ['PAPERCLIP_API_URL']; KEY=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']
C='a178baa8-538e-4172-88b9-c0b95e787e56'; ISSUE='b090ef84-7c6c-4d1e-94d2-0018f340dd65'; FE='bc5c0753-6b0d-419c-9581-fa46ceb4a236'
def req(m,path,body=None):
    r=urllib.request.Request(API+path,method=m,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+KEY,'X-Paperclip-Run-Id':RUN,'Content-Type':'application/json'})
    with urllib.request.urlopen(r) as f: return json.load(f)
# guard 1: thread holds nothing newer than the hand-back
cs=req('GET',f'/api/issues/{ISSUE}/comments'); cs=cs if isinstance(cs,list) else cs.get('comments',[])
ids=[c['id'] for c in sorted(cs,key=lambda c:c['createdAt'])]
assert ids[-1].startswith('d79ab19a'), ids[-1]
# guard 2: reviewer has no live or queued run, and no open issue
runs=req('GET',f'/api/companies/{C}/heartbeat-runs?agentId={FE}&limit=3'); runs=runs if isinstance(runs,list) else runs.get('runs',[])
live=[r['id'] for r in runs if r['status'] in ('running','queued','scheduled')]
assert not live, live
op=req('GET',f'/api/companies/{C}/issues?assigneeAgentId={FE}&status=todo,in_progress,in_review,blocked,backlog&limit=20'); op=op if isinstance(op,list) else op.get('issues',[])
assert not op, [i['identifier'] for i in op]
iss=req('GET',f'/api/issues/{ISSUE}')
now=datetime.datetime.now(datetime.timezone.utc).strftime('%H:%MZ')
body=open('review-brief.md').read().replace('2026-10-16 16:2xZ','2026-10-16 '+now)
assert '16:2xZ' not in body
r=req('POST',f'/api/companies/{C}/issues',{'title':'Review PR #79: screen readers skip the decorative glyphs and hear words for the meaning glyphs (DEC-1190)','description':body,'status':'todo','priority':'low','assigneeAgentId':FE,'parentId':ISSUE,'goalId':iss['goalId'],'projectId':iss['projectId']})
print(r['identifier'], r['id'], r['status'], r['assigneeAgentId'], r['createdAt'])
json.dump({'identifier':r['identifier'],'id':r['id']},open('review-issue.json','w'))
