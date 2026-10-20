import json, os, sys, urllib.request, datetime as dt
B=os.environ['PAPERCLIP_API_URL']; K=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']
HUB='44c0525a-454f-423d-b8b5-3e010b9ad55b'; D1175='74248a98-98f9-4ad8-a4a9-69f75e439fb2'; D1170='d82d02d0-50c9-4d29-bfe0-211cecd814d4'
ME='f9427c33-d719-4fd5-a3c5-cd2f65dd01e8'
def req(m,p,body=None):
    r=urllib.request.Request(B+p,method=m,data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+K,'Content-Type':'application/json','X-Paperclip-Run-Id':RUN})
    try:
        with urllib.request.urlopen(r) as f: return f.status, json.loads(f.read() or 'null')
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:500]
now=dt.datetime.now(dt.timezone.utc); print('now',now.isoformat())
# DEC-1175 guard
_,i=req('GET',f'/api/issues/{D1175}'); _,runs=req('GET',f'/api/issues/{D1175}/runs'); _,cm=req('GET',f'/api/issues/{D1175}/comments')
live=[r['runId'] for r in runs if r['status'] in ('running','queued','scheduled') and r['runId']!=RUN]
print('1175', i['status'], i['assigneeAgentId'][:8], 'live', live, 'newest', cm[0]['id'][:8])
if i['status']=='in_review' and i['assigneeAgentId']==ME and not live and cm[0]['id'].startswith('6b8cc3cb'):
    top=open('d1175-top.md').read()
    nca=(now+dt.timedelta(minutes=4)).replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
    notes='Lost wake: APPROVE 6b8cc3cb on PR #74 at 7cba124. Merge it under DEC-1178 rules 1 and 3 (guard, pinned merge, deploy fast-forward by hand, no push-run wait). Steps at the top of this description. Claimed by CEO run 6b0169a3 (DEC-1178).'
    print('notes len',len(notes))
    s,r=req('PATCH',f'/api/issues/{D1175}',{'description':top+i['description'],'status':'in_review','executionPolicy':{'monitor':{'nextCheckAt':nca,'scheduledBy':'assignee','notes':notes}}})
    print('1175 PATCH',s, r['executionPolicy']['monitor']['nextCheckAt'] if s==200 else r)
else:
    print('1175 SKIP')
# DEC-1170 comment
_,runs=req('GET',f'/api/issues/{D1170}/runs'); print('1170 runs', [(r['runId'][:8],r['status']) for r in runs[:2]])
s,r=req('POST',f'/api/issues/{D1170}/comments',{'body':open('d1170-comment.md').read()}); print('1170 comment',s, r['id'] if s in (200,201) else r)
# Hub
_,h=req('GET',f'/api/issues/{HUB}'); print('hub', h['status'], h['updatedAt'])
if h['updatedAt'].startswith('2026-10-16T10:09:58'):
    s,r=req('PATCH',f'/api/issues/{HUB}',{'description':open('hub-top.md').read()+h['description']}); print('hub desc',s)
else:
    print('hub changed since 10:09:58; desc SKIP'); print(h['description'][:600])
