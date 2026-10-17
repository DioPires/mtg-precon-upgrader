"""Route the DEC-1198 CHANGES verdict (CEO run 15bb14f0, 2026-10-17). Writes in this order, after a guard:
1. the rulings comment on DEC-1191 (my own issue: wakes nobody);
2. DEC-1197's description (the board's start, item 3, item 7a);
3. DEC-1191's description (FIX ROUND 1 on top of the old text);
4. DEC-1191 to the Design System Engineer, `todo`, monitor null (the assignment wakes it).
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

API, KEY, RUN = os.environ["PAPERCLIP_API_URL"], os.environ["PAPERCLIP_API_KEY"], os.environ["PAPERCLIP_RUN_ID"]
HERE = Path(__file__).resolve().parent
D1191 = "1e1b2026-4bbb-4855-836b-948540e1713c"
D1197 = "0d15c4a1-2d6b-4fd9-a9c0-28ecc6205ac5"
D1198 = "fb88bde8-be13-49e5-8c9f-6537c588fb18"
DSE = "8ea33a50-69a7-4a75-bcc1-245bd1e7c73a"
C = "a178baa8-538e-4172-88b9-c0b95e787e56"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode())
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("X-Paperclip-Run-Id", RUN)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


# Guard: nothing newer than the verdict on DEC-1198, nothing newer than my routing comment on DEC-1191,
# no comment on DEC-1197, no live run but mine on DEC-1191, and the reviewer-free engineer idle.
assert call("GET", f"/api/issues/{D1198}/comments")[0]["id"].startswith("14a16973")
assert call("GET", f"/api/issues/{D1191}/comments")[0]["id"].startswith("1db737e6")
assert call("GET", f"/api/issues/{D1197}/comments") == []
live = [r for r in call("GET", f"/api/issues/{D1191}/runs") if r["status"] in ("running", "queued") and r["runId"] != RUN]
assert not live, live
p = call("GET", f"/api/issues/{D1191}")
assert p["assigneeAgentId"] == "f9427c33-d719-4fd5-a3c5-cd2f65dd01e8" and p["status"] == "in_review"
dse_runs = call("GET", f"/api/companies/{C}/heartbeat-runs?agentId={DSE}&limit=3")
dse_runs = dse_runs if isinstance(dse_runs, list) else dse_runs.get("runs", dse_runs)
assert all(r["status"] not in ("running", "queued") for r in dse_runs), dse_runs
assert call("GET", f"/api/companies/{C}/issues?assigneeAgentId={DSE}&status=todo,in_progress,blocked,in_review") == []
d1197 = call("GET", f"/api/issues/{D1197}")
assert d1197["status"] == "todo" and d1197["assigneeAgentId"].startswith("4e51e111")
print("guard ok")

now = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%MZ")
body = (HERE / "rulings.md").read_text().replace("{TIME}", now)
assert "{" + "TIME}" not in body
c = call("POST", f"/api/issues/{D1191}/comments", {"body": body})
rid = c["id"]
print("rulings", rid, now)

old97 = HERE / "d1197_old.md"
old97.write_text(d1197["description"])
subprocess.run([sys.executable, "-I", str(HERE / "d1197_edits.py"), str(old97), str(HERE / "d1197_new.md"), rid[:8]],
               check=True)
new97 = (HERE / "d1197_new.md").read_text()
r = call("PATCH", f"/api/issues/{D1197}", {"description": new97})
assert r["description"].rstrip("\n") == new97.rstrip("\n")
print("DEC-1197 description", len(new97))

fix = (HERE / "fix1.md").read_text().replace("{TIME}", now).replace("{RULINGS}", rid[:8])
assert "{" + "TIME}" not in fix and "{" + "RULINGS}" not in fix
(HERE / "d1191_old.md").write_text(p["description"])
new91 = fix + p["description"]
(HERE / "d1191_new.md").write_text(new91)
r = call("PATCH", f"/api/issues/{D1191}", {"description": new91})
assert r["description"].rstrip("\n") == new91.rstrip("\n")
print("DEC-1191 description", len(new91))

r = call("PATCH", f"/api/issues/{D1191}",
         {"assigneeAgentId": DSE, "status": "todo", "executionPolicy": {"monitor": None}})
print("DEC-1191 assigned", r["assigneeAgentId"][:8], r["status"], r.get("executionPolicy"))
print(datetime.datetime.now(datetime.timezone.utc).isoformat())
