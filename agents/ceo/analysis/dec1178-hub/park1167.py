import json, os, urllib.request
B=os.environ['PAPERCLIP_API_URL']; K=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']
U='1a558dc7-f357-447e-b0d3-5749463877ae'; ME='f9427c33-d719-4fd5-a3c5-cd2f65dd01e8'; HUB='44c0525a-454f-423d-b8b5-3e010b9ad55b'
def req(m,p,body=None):
    r=urllib.request.Request(B+p,method=m,data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+K,'Content-Type':'application/json','X-Paperclip-Run-Id':RUN})
    try:
        with urllib.request.urlopen(r) as f: return f.status, json.loads(f.read() or 'null')
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:500]
_,i=req('GET',f'/api/issues/{U}'); _,runs=req('GET',f'/api/issues/{U}/runs'); _,cm=req('GET',f'/api/issues/{U}/comments')
live=[r['runId'][:8] for r in runs if r['status'] in ('running','queued','scheduled') and r['runId']!=RUN]
print(i['status'], i['assigneeAgentId'][:8], 'live', live, 'newest', cm[0]['id'][:8])
assert i['status']=='in_review' and i['assigneeAgentId']==ME and not live and cm[0]['id'].startswith('3542ac99')
s,r=req('POST',f'/api/issues/{U}/comments',{'body':open('d1167-comment.md').read()}); print('comment',s, r['id'] if s in (200,201) else r)
notes='Parked on hub DEC-1178 (billing block). Fix round 1 done (3542ac99), PR #72 head 47d2db3. Checks 1, 2, 4 hold; check 3 (CI) waits. When the repository is public, follow the state block at the top: update-branch (PR #74 merged), wait, then merge. If still private, re-park.'
print('notes',len(notes))
s,r=req('PATCH',f'/api/issues/{U}',{'description':open('d1167-top.md').read()+i['description'],'status':'in_review','executionPolicy':{'monitor':{'nextCheckAt':'2026-10-16T16:30:00Z','scheduledBy':'assignee','notes':notes}}})
print('PATCH',s, r['executionPolicy']['monitor']['nextCheckAt'] if s==200 else r)
# hub row 72
_,h=req('GET',f'/api/issues/{HUB}'); _,hc=req('GET',f'/api/issues/{HUB}/comments'); print('hub newest', hc[0]['id'][:8], (hc[0].get('authorAgentId') or '')[:8], hc[0]['createdAt'][11:19])
t=h['description']; a="| #72 | [DEC-1167](/DEC/issues/DEC-1167) | `0cfe1f3` | green; fix round 1 open |"
if t.count(a)==1:
    t=t.replace(a,"| #72 | [DEC-1167](/DEC/issues/DEC-1167) | `47d2db3` | refused (run 38885774801); fix round 1 handed back (`3542ac99`), checks 1, 2 and 4 hold; parked here, monitor 16:30Z |")
    s,r=req('PATCH',f'/api/issues/{HUB}',{'description':t}); print('hub desc',s, r['executionPolicy']['monitor']['nextCheckAt'] if s==200 else r)
else: print('row 72 anchor missing; skip')
