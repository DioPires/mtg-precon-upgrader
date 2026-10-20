import json
import os
import pathlib
import sys
import urllib.request

API = os.environ["PAPERCLIP_API_URL"]
HEADERS = {
    "Authorization": "Bearer " + os.environ["PAPERCLIP_API_KEY"],
    "X-Paperclip-Run-Id": os.environ["PAPERCLIP_RUN_ID"],
    "Content-Type": "application/json",
}
ISSUE = os.environ["PAPERCLIP_TASK_ID"]
HERE = pathlib.Path(__file__).parent


def call(method, path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers=HEADERS, method=method)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read() or b"{}")


status, comment = call("POST", f"/api/issues/{ISSUE}/comments", {"body": (HERE / "comment.md").read_text()})
print("comment", status, comment.get("id"))

card = {
    "kind": "ask_user_questions",
    "resolverPolicy": "human_only",
    "continuationPolicy": "wake_assignee",
    "idempotencyKey": "dec1216-steps-card-1",
    "sourceRunId": os.environ["PAPERCLIP_RUN_ID"],
    "sourceCommentId": comment["id"],
    "title": "Uncommitted files: which steps shall I take?",
    "summary": (
        "Most files are already on GitHub; the shared checkout's branch is 554 commits old. "
        "About 300 CEO note files and 5 engineer rule lines are not on GitHub. "
        "The repository is public, so a push publishes them (gitleaks found no secret)."
    ),
    "payload": {
        "version": 1,
        "title": "Uncommitted files: which steps shall I take?",
        "submitLabel": "Send",
        "questions": [
            {
                "id": "sync",
                "prompt": "Shall I push the missing notes to GitHub and bring the checkout up to date?",
                "helpText": "Steps 1, 2 and 4 of the comment above. Step 2 changes no file; it moves the local branch to origin/main.",
                "selectionMode": "single",
                "required": True,
                "options": [
                    {"id": "all", "label": "Yes: steps 1, 2 and 4", "description": "Merge both TOOLS.md copies, push the notes after a second gitleaks scan, move the local branch, add the rule."},
                    {"id": "push-only", "label": "Push only: steps 1 and 4", "description": "The local branch stays old, so git status keeps listing the files."},
                    {"id": "none", "label": "No: leave everything as it is", "description": "The CEO's loaded TOOLS.md keeps missing 40 lessons, and GitHub keeps missing 24."},
                ],
            },
            {
                "id": "cleanup",
                "prompt": "Shall I also do the cleanup (step 3)?",
                "helpText": "Delete 2 .pid files and the engineer scratch folder (441 files; DEC-1072, DEC-1102 and DEC-1131 are done), restore RECONCILIATION.md, ignore .codex/, priv_data/.claude/ and *.pid, and stop tracking .claude/settings.local.json (your copy on this Mac stays).",
                "selectionMode": "single",
                "required": True,
                "options": [
                    {"id": "all", "label": "Yes: all of step 3", "description": "Everything in the help text."},
                    {"id": "keep-scratch", "label": "Yes, but keep the engineer scratch folder", "description": "I add the folder to .gitignore and delete nothing in it."},
                    {"id": "none", "label": "No cleanup", "description": "git status keeps listing these files."},
                ],
            },
        ],
    },
}
status, made = call("POST", f"/api/issues/{ISSUE}/interactions", card)
print("card", status, made.get("id"), made.get("status"))
sys.exit(0)
