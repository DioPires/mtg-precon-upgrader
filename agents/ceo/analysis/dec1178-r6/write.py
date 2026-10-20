import json, os, sys, urllib.request, datetime
API=os.environ["PAPERCLIP_API_URL"]; KEY=os.environ["PAPERCLIP_API_KEY"]; RUN=os.environ["PAPERCLIP_RUN_ID"]
ME="f9427c33-d719-4fd5-a3c5-cd2f65dd01e8"; START="2026-10-16T13:39:47"
def req(m,p,b=None):
    r=urllib.request.Request(API+p,method=m,data=None if b is None else json.dumps(b).encode(),headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json","X-Paperclip-Run-Id":RUN})
    try:
        with urllib.request.urlopen(r) as f: return f.status, json.loads(f.read() or b"null")
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:400]
ISS={"DEC-1170":"d82d02d0-50c9-4d29-bfe0-211cecd814d4","DEC-1177":"6268f80e-5ffe-43e3-810e-5e85eaa3ce5d","DEC-1155":"861f9175-f728-43f4-8c36-b223c762d763","DEC-1167":"1a558dc7-f357-447e-b0d3-5749463877ae","DEC-1161":"a8d9ae87-b428-492d-b980-15cad94018b4","DEC-1172":"7b8ab1c7-8c9d-4610-a58c-fba2f0ce6e41","DEC-1171":"3b9f78b4-42a5-43c3-b266-0e844758be95"}
def guard(u):
    s,runs=req("GET",f"/api/issues/{u}/runs")
    live=[r["runId"] for r in runs if r["status"] in ("running","queued","scheduled") and r["runId"]!=RUN]
    s,cs=req("GET",f"/api/issues/{u}/comments")
    newer=[c["id"][:8] for c in cs[:3] if c["createdAt"]>START and c.get("createdByRunId")!=RUN]
    s,iss=req("GET",f"/api/issues/{u}")
    return live,newer,iss
mode=sys.argv[1]
if mode=="headers":
    for ident,u in ISS.items():
        live,newer,iss=guard(u)
        if live or newer or iss["assigneeAgentId"]!=ME:
            print(ident,"SKIP live",live,"newer",newer,"assignee",iss["assigneeAgentId"]); continue
        head=open(f"{ident}.md").read().rstrip()
        d=iss["description"]
        if d.startswith("**QUEUE"): print(ident,"already has a QUEUE header; skip"); continue
        s,r=req("PATCH",f"/api/issues/{u}",{"description":head+"\n\n---\n\n"+d})
        print(ident,"PATCH",s, (r.get("updatedAt") if isinstance(r,dict) else r))
elif mode=="arm":
    ident=sys.argv[2]; mins=int(sys.argv[3]); notes=sys.argv[4]
    u=ISS[ident]; live,newer,iss=guard(u)
    if live or newer: print(ident,"SKIP",live,newer); sys.exit(1)
    t=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=mins)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert len(notes)<500
    s,r=req("PATCH",f"/api/issues/{u}",{"status":"in_review","executionPolicy":{"monitor":{"nextCheckAt":t,"scheduledBy":"assignee","notes":notes}}})
    print(ident,"ARM",s,t, r.get("executionPolicy",{}).get("monitor") if isinstance(r,dict) else r)
