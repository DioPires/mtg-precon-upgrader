"""DEC-1179 routing writes (CEO run cae7fab1): review comment, board card, STATE + park, hub note, DEC-1177 lost-wake monitor."""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.request

H = os.environ["PAPERCLIP_API_URL"]
KEY = os.environ["PAPERCLIP_API_KEY"]
RUN = os.environ["PAPERCLIP_RUN_ID"]
ME = os.environ["PAPERCLIP_AGENT_ID"]
ISSUE = "4ec533ab-f435-4486-a477-71db3f74126b"  # DEC-1179
HUB = "44c0525a-454f-423d-b8b5-3e010b9ad55b"  # DEC-1178
D1177 = "6268f80e-5ffe-43e3-810e-5e85eaa3ce5d"
HERE = pathlib.Path(__file__).parent
STEP = sys.argv[1]


def call(method, path, body=None):
    req = urllib.request.Request(H + path, method=method, data=None if body is None else json.dumps(body).encode())
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("X-Paperclip-Run-Id", RUN)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or "null")


def iso(minutes):
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


SUMMARY = (
    "The Interactive Tools Engineer scanned every commit that any ref reaches (1,538 commits; 104 refs, 82 of them "
    "pull request heads), the 3 force-pushed commits that GitHub still serves, all 75 pull request pages, the "
    "workflows, the run logs and the artifacts. No credential was found, so nothing needs rotation. I checked the "
    "report and scanned the 4 commits pushed since: clean too. Going public also shows your Gmail address on 1,442 "
    "commits (it is already public on 619 of 817 eternities-mtg-app commits) and /Users/dpires paths in 166 files. "
    "Public repositories run Actions jobs at no cost, so CI comes back for the 7 waiting pull requests. I recommend "
    "option 1: in the run your answer starts, I scan anything pushed after 10:44Z, then make it public, turn off the "
    "empty wiki, and turn on GitHub's free secret scanning and push protection."
)
HELP = (
    "Option 2 by click: open github.com/DioPires/mtg-precon-upgrader, click Settings (top bar), stay on General, "
    "scroll to Danger Zone at the bottom, click Change visibility, choose Change to public, and confirm in the "
    "dialog. Option 2 by Terminal: gh repo edit DioPires/mtg-precon-upgrader --visibility public "
    "--accept-visibility-change-consequences. After option 2, I still scan the newest commits, turn off the wiki "
    "and turn on secret scanning."
)
OPTIONS = [
    {"id": "ceo_public", "label": "1. Yes: the CEO makes it public now (recommended).",
     "description": "In the run your answer starts, I scan the commits pushed after 10:44Z first. If anything turns up, I stop and ask you; the repository stays private.",
     "freeText": False},
    {"id": "owner_public", "label": "2. Yes: I made it public myself (steps in the help text above).",
     "description": "Answer after you change it. I then scan the newest commits, turn on secret scanning and push protection, turn off the wiki and restart CI.",
     "freeText": False},
    {"id": "not_yet", "label": "3. Not yet (write why here).",
     "description": "For example, hide the email first. That needs a history rewrite: every commit id changes, and the 7 open pull requests and every worktree need a rebuild. I do not recommend it.",
     "freeText": True},
]

if STEP == "guard":
    cs = call("GET", f"/api/issues/{ISSUE}/comments")
    print("newest comment", cs[0]["id"][:8], cs[0]["createdAt"])
    rs = call("GET", f"/api/issues/{ISSUE}/runs")
    print("live others", [r["runId"][:8] for r in rs if r["status"] == "running" and r["runId"] != RUN])
    assert len(SUMMARY) <= 1000, len(SUMMARY)
    assert all(len(o["label"]) <= 95 for o in OPTIONS)
    print("summary", len(SUMMARY), "help", len(HELP), "labels", [len(o["label"]) for o in OPTIONS])

elif STEP == "comment":
    cs = call("GET", f"/api/issues/{ISSUE}/comments")
    assert cs[0]["id"].startswith("ed9be120"), cs[0]["id"]
    body = (HERE / "review.md").read_text()
    c = call("POST", f"/api/issues/{ISSUE}/comments", {"body": body})
    (HERE / "review-id.txt").write_text(c["id"])
    print("review comment", c["id"])

elif STEP == "card":
    rid = (HERE / "review-id.txt").read_text().strip()
    card = {
        "kind": "ask_user_questions",
        "resolverPolicy": "human_only",
        "continuationPolicy": "wake_assignee",
        "idempotencyKey": "dec1179-visibility-2026-10-16",
        "sourceRunId": RUN,
        "sourceCommentId": rid,
        "title": "The secrets scan of mtg-precon-upgrader is CLEAN. Make the repository public now?",
        "summary": SUMMARY,
        "payload": {
            "version": 1,
            "title": "Make mtg-precon-upgrader public",
            "submitLabel": "Send my answer",
            "questions": [{
                "id": "visibility",
                "prompt": "Make DioPires/mtg-precon-upgrader public?",
                "helpText": HELP,
                "selectionMode": "single",
                "required": True,
                "options": OPTIONS,
            }],
        },
    }
    r = call("POST", f"/api/issues/{ISSUE}/interactions", card)
    (HERE / "card-id.txt").write_text(r["id"])
    print("card", r["id"], r.get("status"))

elif STEP == "park":
    rid = (HERE / "review-id.txt").read_text().strip()
    cid = (HERE / "card-id.txt").read_text().strip()
    cur = call("GET", f"/api/issues/{ISSUE}")
    old = cur["description"]
    assert "## STATE (CEO run `cae7fab1`" not in old
    state = (HERE / "state.md").read_text().replace("__REVIEW__", rid[:8]).replace("__CARD__", cid[:8])
    notes = f"Visibility card {cid[:8]} pending (review {rid[:8]}). On fire: if the card is still pending, read the visibility; public -> answer owner_public steps in STATE; else park 3 h ahead."
    assert len(notes) < 500
    r = call("PATCH", f"/api/issues/{ISSUE}", {
        "description": state + old,
        "status": "in_review",
        "executionPolicy": {"monitor": {"nextCheckAt": "2026-10-16T13:40:00Z", "scheduledBy": "assignee", "notes": notes}},
    })
    print("parked", r["status"], r["executionPolicy"]["monitor"]["nextCheckAt"])

elif STEP == "hub":
    cid = (HERE / "card-id.txt").read_text().strip()
    rid = (HERE / "review-id.txt").read_text().strip()
    body = (HERE / "hub.md").read_text().replace("__CARD__", cid[:8]).replace("__REVIEW__", rid[:8])
    c = call("POST", f"/api/issues/{HUB}/comments", {"body": body})
    print("hub comment", c["id"])

elif STEP == "d1177":
    rs = call("GET", f"/api/issues/{D1177}/runs")
    live = [r["runId"][:8] for r in rs if r["status"] in ("running", "queued") and r["runId"] != RUN]
    cur = call("GET", f"/api/issues/{D1177}")
    print("DEC-1177", cur["status"], cur["assigneeAgentId"][:8], "live", live, "monitor", (cur.get("executionPolicy") or {}).get("monitor", {}).get("nextCheckAt"))
    if live or cur["assigneeAgentId"] != ME or cur["status"] != "in_review":
        print("skip")
    else:
        t = iso(4)
        notes = "Lost wake: Design System Engineer hand-back 4b4051bb (10:43:24Z), PR #76 head 0717be8 ready for review; CI refused (DEC-1178 block). Route the review leg. Moved by CEO run cae7fab1."
        r = call("PATCH", f"/api/issues/{D1177}", {"status": "in_review", "executionPolicy": {"monitor": {"nextCheckAt": t, "scheduledBy": "assignee", "notes": notes}}})
        print("DEC-1177 monitor", r["executionPolicy"]["monitor"]["nextCheckAt"])
