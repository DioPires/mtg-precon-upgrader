# Builds and posts the board card on DEC-1155. Args: total minutes, days, minutes per 30 days.
import json, os, sys, urllib.request
summary = (
 "Since 10:01Z today GitHub refuses every test job in the private repository mtg-precon-upgrader. "
 "GitHub's message: \"recent account payments have failed or your spending limit needs to be increased\". "
 "From 1 to 16 October the repository used 2,928 test minutes. GitHub includes 3,000 a month on the Pro plan (2,000 on Free), "
 "so the quota is most likely used up. The count resets on 1 November. "
 "The rate grows: 13 to 15 October alone used 2,581 minutes (about 860 a day), and the browser tests take 80% of it. "
 "Seven pull requests wait for test results, and a merge no longer reaches the live site by itself. "
 "No agent can change billing. eternities-mtg-app is public and still runs; in September (DEC-880) you made it public to end the same block. "
 "I recommend B: it costs nothing a month. Details: DEC-1178."
)
assert len(summary) <= 1000, len(summary)
q = {
 "id": "path",
 "prompt": "How do we get the tests of mtg-precon-upgrader running again?",
 "helpText": "Only you can change GitHub billing or the repository's visibility. Pick one; I route the work from your answer.",
 "selectionMode": "single",
 "required": True,
 "options": [
  {"id": "budget", "label": "A. I raised the GitHub Actions budget (or fixed the payment). Re-run the tests.",
   "description": (f"Browser: github.com, your picture (top right), Settings, Billing and licensing, Budgets and alerts "
     "(github.com/settings/billing/budgets). Raise the Actions budget, or turn off 'Stop usage when budget limit is reached', then save. "
     "A failed payment: Billing and licensing, Payment information. There is no Terminal command for this. "
     "Cost: if the last three days' rate holds, about 22,800 minutes a month above the quota. At $0.008 a minute (GitHub's Linux price before 2026; "
     "check github.com/pricing) that is about $180 a month. I also open a leg to cut the minute rate."), "freeText": False},
  {"id": "public", "label": "B. Make mtg-precon-upgrader public, after an engineer scans its history for secrets.",
   "description": ("Hosted tests cost nothing on a public repository. Everything becomes public: the code, the whole history, "
     "and 1,054 agent note files. The tracked files hold .mcp.json and .claude/settings.local.json. A quick scan of the newest commit found no key, "
     "but nobody has scanned the history. Pick this and I open the scan now (about an hour); you change the visibility only after my report. "
     "Then: repository Settings, General, Danger Zone, Change visibility; or in Terminal: gh repo edit DioPires/mtg-precon-upgrader --visibility public --accept-visibility-change-consequences. "
     "To keep tests running during the scan, raise the budget a little too and say so under D."), "freeText": False},
  {"id": "wait", "label": "C. Wait for the free minutes to come back on 1 November.",
   "description": ("The tests stay off for 15 days. Engineers then run the browser tests on the Mac before each merge, which is weaker: "
     "on 16 October CI found a fault that only Linux shows. I move the live site by hand after each merge. "
     "At this rate the quota runs out again in November."), "freeText": False},
  {"id": "other", "label": "D. Something else (write it here).", "description": "", "freeText": True},
 ],
}
payload = {
 "kind": "ask_user_questions",
 "resolverPolicy": "human_only",
 "continuationPolicy": "wake_assignee",
 "idempotencyKey": "dec1178-billing-block-2026-10-16",
 "sourceRunId": os.environ["PAPERCLIP_RUN_ID"],
 "sourceCommentId": "5527f57c-a2a5-4a1a-bdd4-22e171b6548c",
 "title": "GitHub stopped running the tests of mtg-precon-upgrader (billing). How do we get them back?",
 "summary": summary,
 "payload": {"version": 1, "title": "GitHub Actions billing block on mtg-precon-upgrader", "submitLabel": "Send my answer", "questions": [q]},
}
if "--dry" in sys.argv:
    print(json.dumps(payload, indent=1)[:3000]); print(len(summary)); sys.exit()
req = urllib.request.Request(f"{os.environ['PAPERCLIP_API_URL']}/api/issues/{os.environ['PAPERCLIP_TASK_ID']}/interactions",
  data=json.dumps(payload).encode(), method="POST",
  headers={"Authorization": f"Bearer {os.environ['PAPERCLIP_API_KEY']}", "X-Paperclip-Run-Id": os.environ["PAPERCLIP_RUN_ID"], "Content-Type": "application/json"})
try:
    d = json.load(urllib.request.urlopen(req)); print(d.get("id"), d.get("status"))
except urllib.error.HTTPError as e:
    print(e.code, e.read()[:600])
