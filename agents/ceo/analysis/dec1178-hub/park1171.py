import json, os, urllib.request
B=os.environ['PAPERCLIP_API_URL']; K=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']
U='3b9f78b4-42a5-43c3-b266-0e844758be95'; ME='f9427c33-d719-4fd5-a3c5-cd2f65dd01e8'; D1175='74248a98-98f9-4ad8-a4a9-69f75e439fb2'
def req(m,p,body=None):
    r=urllib.request.Request(B+p,method=m,data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+K,'Content-Type':'application/json','X-Paperclip-Run-Id':RUN})
    try:
        with urllib.request.urlopen(r) as f: return f.status, json.loads(f.read() or 'null')
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:500]
_,i=req('GET',f'/api/issues/{U}'); _,runs=req('GET',f'/api/issues/{U}/runs'); _,cm=req('GET',f'/api/issues/{U}/comments')
live=[r['runId'][:8] for r in runs if r['status'] in ('running','queued','scheduled') and r['runId']!=RUN]
print(i['status'], i['assigneeAgentId'][:8], 'live', live, 'newest', cm[0]['id'][:8])
assert i['status']=='in_review' and i['assigneeAgentId']==ME and not live and cm[0]['id'].startswith('c89533a3')
s,r=req('POST',f'/api/issues/{U}/comments',{'body':open('d1171-comment.md').read()}); print('comment',s, r['id'] if s in (200,201) else r)
notes='Parked on hub DEC-1178 (billing block). Fix round 1 done (c89533a3), PR #73 head 01f3395, no CI reading. When the repository is public, follow the state block at the top of this description: rerun or update-branch, then open the review. If still private, re-park.'
print('notes',len(notes))
s,r=req('PATCH',f'/api/issues/{U}',{'description':open('d1171-top.md').read()+i['description'],'status':'in_review','executionPolicy':{'monitor':{'nextCheckAt':'2026-10-16T16:10:00Z','scheduledBy':'assignee','notes':notes}}})
print('PATCH',s, r['executionPolicy']['monitor']['nextCheckAt'] if s==200 else r)
_,runs=req('GET',f'/api/issues/{D1175}/runs'); print('1175 runs',[(r['runId'][:8],r['status'],r['invocationSource'],r['startedAt'][11:19]) for r in runs[:2]])
