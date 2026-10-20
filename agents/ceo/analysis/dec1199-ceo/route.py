import json, os, sys, subprocess, urllib.request, datetime
API=os.environ['PAPERCLIP_API_URL']; KEY=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']; CO=os.environ['PAPERCLIP_COMPANY_ID']
FE='bc5c0753-6b0d-419c-9581-fa46ceb4a236'; CEO='f9427c33-d719-4fd5-a3c5-cd2f65dd01e8'
I1199='e9907775-d24f-42bf-8a33-40d2e7700b0e'; I1182='2320e373-3837-4579-8edf-e9058196365a'; GOAL='3b2ff26a-452f-447b-b09a-d5e11a5cfa86'
def req(method, path, body=None):
    data=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request(API+path, data=data, method=method, headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json','X-Paperclip-Run-Id':RUN})
    try:
        with urllib.request.urlopen(r) as f:
            raw=f.read(); return f.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]
T=datetime.datetime.now(datetime.timezone.utc).strftime('%H:%MZ')
# guards
s,c=req('GET',f'/api/issues/{I1199}/comments'); assert s==200 and c[0]['id'].startswith('81ea90b7'), ('thread moved', c[0]['id'])
s,r=req('GET',f'/api/companies/{CO}/heartbeat-runs?agentId={FE}&limit=3'); live=[x for x in r if x['status'] in ('queued','running','scheduled')]; assert not live, live
s,r=req('GET',f'/api/companies/{CO}/issues?assigneeAgentId={FE}&status=todo,in_progress,blocked,in_review'); assert s==200 and not r, [x['identifier'] for x in r]
s,r=req('GET',f'/api/companies/{CO}/issues?parentId={I1199}'); assert s==200 and not [x for x in r if x['status']!='cancelled'], [x['identifier'] for x in r]
head=subprocess.run(['gh','pr','view','82','-R','DioPires/mtg-precon-upgrader','--json','headRefOid','--jq','.headRefOid'],capture_output=True,text=True,env={**os.environ,'HOME':os.environ['PAPERCLIP_GITHUB_HOST_HOME']}).stdout.strip()
assert head.startswith('014984a'), head
print('guards ok', T)
brief=open('/tmp/dec1199-ceo/brief.md').read().replace('{T}',T)
assert '{T}' not in brief
s,iss=req('POST',f'/api/companies/{CO}/issues',{'title':'Review PR #82 (DEC-1199): one mark in each two-mark box on /shopping, Compare and the Combo Lab loading line','description':brief,'status':'todo','priority':'low','assigneeAgentId':FE,'parentId':I1199,'goalId':GOAL})
print('POST',s, iss.get('identifier') if isinstance(iss,dict) else iss)
assert s in (200,201)
N=iss['identifier']; NID=iss['id']; assert N.startswith('DEC-')
open('/tmp/dec1199-ceo/review-id.txt','w').write(N+' '+NID+'\n')
# DEC-1199: state block + park
s,d=req('GET',f'/api/issues/{I1199}'); old=d['description']
state=open('/tmp/dec1199-ceo/state.md').read().replace('{T}',T).replace('{N}',N).rstrip('\n')
newdesc=state+'\n\n---\n\n'+old
mon={'nextCheckAt':'2026-10-17T15:20:00Z','scheduledBy':'assignee','notes':f'Fallback only. PR #82 (head 014984a) is in review on {N} (Frontend Engineer). Its hand-back comes to {N} with its own monitor. On wake: read {N} runs and thread; route a lost verdict there by the STATE block here. Routed by run 8d1902ed.'}
assert len(mon['notes'])<500
s,r=req('PATCH',f'/api/issues/{I1199}',{'description':newdesc,'status':'in_review','executionPolicy':{'monitor':mon}})
print('PATCH 1199',s, r if s!=200 else (r['status'], (r.get('executionPolicy') or {}).get('monitor',{}).get('nextCheckAt')))
cm=open('/tmp/dec1199-ceo/comment.md').read().replace('{T}',T).replace('{N}',N)
s,r=req('POST',f'/api/issues/{I1199}/comments',{'body':cm}); print('comment',s, r['id'] if s in (200,201) else r)
# DEC-1182: state line + monitor
s,d=req('GET',f'/api/issues/{I1182}'); old=d['description']; pol=d.get('executionPolicy') or {}
line=open('/tmp/dec1199-ceo/dec1182-state.md').read().replace('{T}',T).replace('{N}',N)
mon2={'nextCheckAt':'2026-10-17T16:30:00Z','scheduledBy':'assignee','notes':f'Fallback only. DEC-1199 PR #82 is in review on {N} (Frontend Engineer); route its verdict on {N}, not here. DEC-1182 closes in the PR #82 merge run, first in the close order of the DEC-1199 STATE block. Moved from 12:30Z by run 8d1902ed.'}
assert len(mon2['notes'])<500
s,r=req('PATCH',f'/api/issues/{I1182}',{'description':line+old,'status':'in_review','executionPolicy':{'monitor':mon2}})
print('PATCH 1182',s, r if s!=200 else (r['status'], (r.get('executionPolicy') or {}).get('monitor',{}).get('nextCheckAt')))
