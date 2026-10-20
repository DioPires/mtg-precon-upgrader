import datetime as dt
import json
import os
import sys
import urllib.request

API = os.environ["PAPERCLIP_API_URL"]
KEY = os.environ["PAPERCLIP_API_KEY"]
RUN = os.environ["PAPERCLIP_RUN_ID"]
CO = os.environ["PAPERCLIP_COMPANY_ID"]
HERE = os.path.dirname(os.path.abspath(__file__))
ISSUE = "74dac66b-ccfd-4bdb-835c-04e92ab09fd8"
REVIEWER = "4e51e111-eff7-4619-95dd-9e43a955e637"
LAST_COMMENT = "bf105fbe-e677-4596-9450-55fae1d6b98c"


def call(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + KEY,
            "Content-Type": "application/json",
            "X-Paperclip-Run-Id": RUN,
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:800]


def read(name):
    with open(os.path.join(HERE, name)) as f:
        return f.read()


# Guard: nothing newer than the hand-back, and no live run but mine.
s, comments = call("GET", f"/api/issues/{ISSUE}/comments")
assert s == 200, (s, comments)
items = comments if isinstance(comments, list) else comments.get("comments", [])
newest = max(items, key=lambda c: c["createdAt"])
assert newest["id"] == LAST_COMMENT, ("newer comment", newest["id"], newest["body"][:200])
s, runs = call("GET", f"/api/issues/{ISSUE}/runs")
live = [r for r in runs if r.get("status") in ("running", "queued") and r.get("runId") != RUN]
assert not live, ("live run", live)
s, issue = call("GET", f"/api/issues/{ISSUE}")
assert issue["assigneeAgentId"] == "f9427c33-d719-4fd5-a3c5-cd2f65dd01e8", issue["assigneeAgentId"]
old_desc = issue["description"]
assert not old_desc.startswith("**STATE"), "state block already written"
print("guard ok")

# 1. The review issue, backlog first so that no run starts before the rulings exist.
brief = read("review-brief.md")
s, rev = call(
    "POST",
    f"/api/companies/{CO}/issues",
    {
        "title": "Review of PR #48 at `7d38c7b` (DEC-1032: the Combo Lab rail pins from Contents down)",
        "description": brief,
        "status": "backlog",
        "priority": "low",
        "assigneeAgentId": REVIEWER,
        "parentId": ISSUE,
        "goalId": issue["goalId"],
        "projectId": issue["projectId"],
    },
)
assert s in (200, 201), (s, rev)
rev_id, rev_ident = rev["id"], rev["identifier"]
print("review issue", rev_ident, rev_id)

# 2. The ruling comment on DEC-1032.
s, com = call("POST", f"/api/issues/{ISSUE}/comments", {"body": read("ruling.md").replace("REVIEW_ISSUE", rev_ident)})
assert s in (200, 201), (s, com)
ruling_id = com["id"]
print("ruling comment", ruling_id)

# 3. The review issue gets the ruling id and starts.
s, r = call("PATCH", f"/api/issues/{rev_id}", {"description": brief.replace("RULING_ID", ruling_id[:8]), "status": "todo"})
assert s == 200, (s, r)
print("review issue todo", r["status"], r["assigneeAgentId"])

# 4. DEC-1032: state block on top, parked in_review with a fallback monitor.
now = dt.datetime.now(dt.timezone.utc)
block = (
    read("state-block.md")
    .replace("08:3xZ", now.strftime("%H:%MZ"))
    .replace("RULING_ID", ruling_id[:8])
    .replace("REVIEW_ISSUE", rev_ident)
)
nxt = (now + dt.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
notes = (
    f"Review {rev_ident} (Founding Engineer) of PR #48 at 7d38c7b. Rulings {ruling_id[:8]}. "
    f"If the review run is live or queued, re-park 3 h. If a verdict is unrouted, follow the state block's APPROVE or CHANGES steps."
)
assert len(notes) < 500, len(notes)
s, r = call(
    "PATCH",
    f"/api/issues/{ISSUE}",
    {
        "description": block + old_desc,
        "status": "in_review",
        "executionPolicy": {"monitor": {"nextCheckAt": nxt, "scheduledBy": "assignee", "notes": notes}},
    },
)
assert s == 200, (s, r)
print("DEC-1032", r["status"], json.dumps(r.get("executionPolicy", {}).get("monitor", {}).get("nextCheckAt")))
