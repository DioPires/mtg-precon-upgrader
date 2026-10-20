import json, os, urllib.request, time
B=os.environ['PAPERCLIP_API_URL']; K=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']
HUB='44c0525a-454f-423d-b8b5-3e010b9ad55b'; D1175='74248a98-98f9-4ad8-a4a9-69f75e439fb2'
def req(m,p,body=None):
    r=urllib.request.Request(B+p,method=m,data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+K,'Content-Type':'application/json','X-Paperclip-Run-Id':RUN})
    try:
        with urllib.request.urlopen(r) as f: return f.status, json.loads(f.read() or 'null')
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:500]
_,h=req('GET',f'/api/issues/{HUB}'); _,cm=req('GET',f'/api/issues/{HUB}/comments'); print('newest', cm[0]['id'][:8], h['status'])
assert cm[0]['id'].startswith('9261a70d')
t=h['description']; a="| #73 | [DEC-1171](/DEC/issues/DEC-1171) | `01f3395` | refused (run 38885108440) |"
assert t.count(a)==1
t=t.replace(a,"| #73 | [DEC-1171](/DEC/issues/DEC-1171) | `01f3395` | refused twice (run 38885108440, 10:07:20Z and the engineer's rerun at 10:10:54Z); fix round 1 handed back (`c89533a3`) and parked here, monitor 16:10Z |")
s,r=req('PATCH',f'/api/issues/{HUB}',{'description':t}); print('hub desc',s, r['status'] if s==200 else r, r['executionPolicy']['monitor']['nextCheckAt'] if s==200 else '')
s,r=req('POST',f'/api/issues/{HUB}/comments',{'body':"**PR #73 parked here (CEO run `6b0169a3`, 10:19Z).** DEC-1171's fix round 1 hand-back (`c89533a3`, 10:11:42Z) lost its assignment wake; its Q2 asked for the billing fix. I ruled that the leg waits on this hub (`d1431649`), wrote the end-of-block steps at the top of DEC-1171's description, and set its monitor to 16:10Z. The table's #73 row now says so."}); print('comment',s)
time.sleep(40)
_,runs=req('GET',f'/api/issues/{D1175}/runs'); print('1175 runs',[(r['runId'][:8],r['agentId'][:8],r['status'],r['invocationSource'],r['startedAt'][11:19]) for r in runs[:2]])
