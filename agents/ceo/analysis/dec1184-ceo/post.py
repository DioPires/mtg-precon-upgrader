import json, os, re, sys, datetime, urllib.request
API = os.environ["PAPERCLIP_API_URL"]; KEY = os.environ["PAPERCLIP_API_KEY"]; RUN = os.environ["PAPERCLIP_RUN_ID"]
C = "a178baa8-538e-4172-88b9-c0b95e787e56"; I = "afc7fa7d-24a8-4135-a89d-3b826f5c9224"
FE = "4e51e111-eff7-4619-95dd-9e43a955e637"; SIM = "6ba3ac88-12e8-41a7-834f-98e3d92dae78"
GOAL = "3b2ff26a-452f-447b-b09a-d5e11a5cfa86"; PROJ = "7f953c99-ffa7-44f4-8216-da5b91d8791a"
def req(method, path, body=None):
    r = urllib.request.Request(API + path, method=method, headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json", "X-Paperclip-Run-Id": RUN})
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(r, data) as f:
        raw = f.read()
        return json.loads(raw) if raw else None
log = open("post.log", "a")
def note(*a):
    s = " ".join(map(str, a)); print(s); log.write(s + "\n"); log.flush()
# guard: newest comment is the hand-back; no other live CEO run on the issue
cm = req("GET", f"/api/issues/{I}/comments")
assert cm[0]["id"][:8] in ("ab7eec12", "097754fa"), cm[0]["id"]
runs = req("GET", f"/api/issues/{I}/runs")
live = [x for x in runs if x["status"] == "running" and x["runId"] != RUN]
assert not live, live
for t in ("followup-brief.md", "review-brief.md", "ruling.md", "state-block.md"):
    assert not re.search(r"\\[nr]", open(t).read()), t
step = sys.argv[1]
if step == "followup":
    body = open("followup-brief.md").read()
    iss = req("POST", f"/api/companies/{C}/issues", {
        "title": "Classifier follow-ups of PR #78: a cantrip is not card draw, a power cut is not removal, a qualified toughness cut and \"up to N target\" are removal, and a census of net-zero draws (DEC-1184 rulings R1 to R5)",
        "description": body, "status": "backlog", "priority": "low", "assigneeAgentId": FE,
        "parentId": I, "goalId": GOAL, "projectId": PROJ})
    note("followup", iss["id"], iss["identifier"], iss["status"])
    json.dump(iss, open("followup.json", "w"))
elif step == "ruling":
    fu = json.load(open("followup.json"))["identifier"]
    body = open("ruling.md").read().replace("<FOLLOWUP>", fu)
    assert "<" + "FOLLOWUP>" not in body
    c = req("POST", f"/api/issues/{I}/comments", {"body": body})
    note("ruling", c["id"], c["createdAt"])
    json.dump(c, open("ruling.json", "w"))
elif step == "review":
    rid = json.load(open("ruling.json"))["id"][:8]
    body = open("review-brief.md").read().replace("<RULING>", rid)
    assert not re.search(r"<[A-MO-Z][A-Z]*>|<N[A-Z]+>", body), re.findall(r"<[A-Z]+>", body)
    sruns = req("GET", f"/api/companies/{C}/heartbeat-runs?agentId={SIM}&limit=3")
    sruns = sruns if isinstance(sruns, list) else sruns.get("runs", sruns)
    note("sim runs", [(x["id"][:8], x["status"]) for x in sruns[:3]])
    iss = req("POST", f"/api/companies/{C}/issues", {
        "title": "Review PR #78: classifier follow-ups of PR #71 (a steal is not a blink, the guard stops at \"then\", +N/-M is removal, a land target is not) (DEC-1184)",
        "description": body, "status": "todo", "priority": "low", "assigneeAgentId": SIM,
        "parentId": I, "goalId": GOAL, "projectId": PROJ})
    note("review", iss["id"], iss["identifier"], iss["status"], iss.get("createdAt"))
    json.dump(iss, open("review.json", "w"))
elif step == "fill":
    rid = json.load(open("ruling.json"))["id"][:8]
    fu = json.load(open("followup.json")); rv = json.load(open("review.json"))
    body = open("followup-brief.md").read().replace("<RULING>", rid)
    assert not re.search(r"<[A-MO-Z][A-Z]*>|<N[A-Z]+>", body)
    r = req("PATCH", f"/api/issues/{fu['id']}", {"description": body})
    note("followup filled", r["identifier"], r["status"])
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%MZ")
    sb = open("state-block.md").read().replace("15:4xZ", now).replace("15:3xZ", "15:28Z")
    sb = sb.replace("<RULING>", rid).replace("<REVIEW>", rv["identifier"]).replace("<FOLLOWUP>", fu["identifier"])
    assert not re.search(r"<[A-Z]+>", sb.replace("<head>", "")), re.findall(r"<[A-Z]+>", sb)
    cur = req("GET", f"/api/issues/{I}")["description"]
    assert cur.startswith("**Started: PR #71"), cur[:80]
    r = req("PATCH", f"/api/issues/{I}", {"description": sb + cur})
    note("state block", r["identifier"], r["status"], (r.get("executionPolicy") or {}).get("monitor", {}).get("nextCheckAt"))
    open("state-block-posted.md", "w").write(sb)
