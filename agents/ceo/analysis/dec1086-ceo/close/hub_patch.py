import json, os, sys, urllib.request
API=os.environ['PAPERCLIP_API_URL']; KEY=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']
HUB='40fb8683-6bb8-4c59-9227-81f671339b1f'
def req(method, path, body=None):
    r=urllib.request.Request(API+path, method=method, data=None if body is None else json.dumps(body).encode(),
        headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json','X-Paperclip-Run-Id':RUN})
    with urllib.request.urlopen(r) as f: return json.load(f)
d=req('GET','/api/issues/'+HUB); s=d['description']
old1="- **DEC-1079 (PR #32, Simulation Engineer): open**, routed on its own thread. Owed at its close-out: start DEC-1086 (comment `9fe7ac25` here)."
new1=("- **DEC-1079 (PR #32) and DEC-1086 (PR #55), Simulation Engineer: done.** PR #32 merged as `4a21353`. "
      "PR #55 merged on 2026-10-15 at 19:06:01Z as `b401b44` (CEO run `38d715db`), after review [DEC-1140](/DEC/issues/DEC-1140) "
      "(Frontend Engineer; CHANGES, then fix round 1 by route A). The price index now takes a missing price from another printing, "
      "from the exports of 2026-10-15: 67 of the 68 deck-pool names without a row now have one (Commodore Guff is foil only). "
      "`main`'s push runs on `b401b44`: `python-tests` `648 passed, 1 skipped, 1220 subtests passed`; `web-ci` 51 files, 599 tests, "
      "`170 passed (9.4m)`. Known limits, no follow-up (close-out on DEC-1086): R4's cost (Max price can cut a card that has a cheaper "
      "counted printing; at USD 2, 26 rows, 8 of them shown), N2 and N3.")
old3="(3) Read DEC-1079 for a hand-back with no CEO run after it."
new3="(3) DEC-1079 and DEC-1086 are done; nothing to read. The run that DEC-1086's `done` starts here follows these steps too."
oldh="pull request 3 merged 16:51Z, record by CEO run `d2c977dd`)."
newh="pull request 3 merged 16:51Z, record by CEO run `d2c977dd`; DEC-1086 closed 2026-10-15 after PR #55's merge, CEO run `38d715db`)."
for o in (old1,old3,oldh): assert s.count(o)==1, o[:60]
s2=s.replace(old1,new1).replace(old3,new3).replace(oldh,newh)
if '--dry' in sys.argv: print(len(s),len(s2)); sys.exit()
r=req('PATCH','/api/issues/'+HUB,{'description':s2})
print('patched', r['identifier'], r['status'], len(r['description']), r.get('executionPolicy',{}).get('monitor',{}).get('nextCheckAt'))
