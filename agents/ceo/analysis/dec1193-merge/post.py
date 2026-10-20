import json, os, sys, urllib.request
U=os.environ["PAPERCLIP_API_URL"]; H={"Authorization":"Bearer "+os.environ["PAPERCLIP_API_KEY"],"X-Paperclip-Run-Id":os.environ["PAPERCLIP_RUN_ID"],"Content-Type":"application/json"}
ME=os.environ["PAPERCLIP_RUN_ID"]
I93="d0a5f1e5-5f31-4f1e-bbe7-23bbacdab233"; I90="b090ef84-7c6c-4d1e-94d2-0018f340dd65"; I82="2320e373-3837-4579-8edf-e9058196365a"
def req(m,p,b=None):
    r=urllib.request.Request(U+p,method=m,headers=H,data=None if b is None else json.dumps(b).encode())
    try:
        with urllib.request.urlopen(r) as x: return x.status, json.loads(x.read() or b"null")
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:300]
def comments(i):
    s,d=req("GET",f"/api/issues/{i}/comments"); d=d if isinstance(d,list) else d.get("items",d)
    return sorted(d,key=lambda c:c["createdAt"])
# guard
for i,last in ((I93,"f867c368"),(I90,"68559943"),(I82,None)):
    s,runs=req("GET",f"/api/issues/{i}/runs")
    live=[r["runId"][:8] for r in runs if r["status"] in("running","queued") and r["runId"]!=ME]
    c=comments(i); newest=c[-1]["id"][:8] if c else None
    print(i[:8],"live:",live,"newest:",newest, c[-1]["createdAt"] if c else "")
    if live: sys.exit("live run, stop")
    if last and newest!=last: sys.exit("thread moved, stop")
s,ix=req("GET",f"/api/issues/{I82}/interactions"); ix=ix if isinstance(ix,list) else ix.get("items",ix)
card=[x for x in ix if x["id"].startswith("345bc3b0")][0]; print("card",card["status"])
if card["status"]!="pending": sys.exit("card answered, stop")
rd=lambda f: open(f).read()
print("c93",req("POST",f"/api/issues/{I93}/comments",{"body":rd("c-dec1193.md")})[1].get("id"))
s,d90=req("GET",f"/api/issues/{I90}")
print("d90",req("PATCH",f"/api/issues/{I90}",{"description":rd("state-dec1190.md")+d90["description"]})[0])
print("c90",req("POST",f"/api/issues/{I90}/comments",{"body":rd("c-dec1190.md")})[1].get("id"))
s,d82=req("GET",f"/api/issues/{I82}")
print("d82",req("PATCH",f"/api/issues/{I82}",{"description":rd("state-dec1182.md")+d82["description"]})[0])
print("c82",req("POST",f"/api/issues/{I82}/comments",{"body":rd("c-dec1182.md")})[1].get("id"))
s,r=req("PATCH",f"/api/issues/{I90}",{"status":"done","executionPolicy":{"monitor":None}}); print("done90",s, r.get("status") if isinstance(r,dict) else r)
s,r=req("PATCH",f"/api/issues/{I93}",{"status":"done","executionPolicy":{"monitor":None}}); print("done93",s, r.get("status") if isinstance(r,dict) else r)
