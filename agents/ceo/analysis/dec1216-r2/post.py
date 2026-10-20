"""Posts the DEC-1216 result comment, then closes the issue. Run once, after the push and the sync."""
import json
import os
import pathlib
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
status, issue = call("PATCH", f"/api/issues/{ISSUE}", {"status": "done"})
print("issue", status, issue.get("status"))
