"""DEC-1179 close (run 11ded5e2): guard, record comment, done."""
import json, os, sys, urllib.request
API, KEY, RUN = os.environ["PAPERCLIP_API_URL"], os.environ["PAPERCLIP_API_KEY"], os.environ["PAPERCLIP_RUN_ID"]
ISSUE = "4ec533ab-f435-4486-a477-71db3f74126b"
HERE = os.path.dirname(os.path.abspath(__file__))
def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json", "X-Paperclip-Run-Id": RUN})
    with urllib.request.urlopen(req) as r:
        return json.load(r)
cs = call("GET", f"/api/issues/{ISSUE}/comments")
cs = cs if isinstance(cs, list) else cs.get("items", cs)
newest = max(cs, key=lambda c: c["createdAt"])
assert len(cs) == 2 and newest["id"].startswith("b8fec061"), (len(cs), newest["id"])
body = open(os.path.join(HERE, "record.md")).read()
c = call("POST", f"/api/issues/{ISSUE}/comments", {"body": body})
open(os.path.join(HERE, "record-id.txt"), "w").write(c["id"])
print("record comment", c["id"], c["createdAt"])
r = call("PATCH", f"/api/issues/{ISSUE}", {"status": "done"})
print("issue", r.get("identifier"), r.get("status"), r.get("completedAt"))
