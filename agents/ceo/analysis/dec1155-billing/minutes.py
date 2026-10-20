# Runner minutes of DioPires/mtg-precon-upgrader since 2026-10-01: every job that
# got a runner, each job rounded up to a whole minute (GitHub bills that way).
import json, math, subprocess, sys
from collections import defaultdict
from datetime import datetime

REPO = "DioPires/mtg-precon-upgrader"
SINCE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-01"

def api(path):
    out = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True, check=True).stdout
    # --paginate concatenates JSON objects; split them
    dec, i, objs = json.JSONDecoder(), 0, []
    while i < len(out):
        while i < len(out) and out[i].isspace():
            i += 1
        if i >= len(out):
            break
        o, i = dec.raw_decode(out, i)
        objs.append(o)
    return objs

def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")

runs = []
for page in api(f"repos/{REPO}/actions/runs?per_page=100&created=>={SINCE}"):
    runs.extend(page["workflow_runs"])
by_job = defaultdict(lambda: [0, 0])
by_day = defaultdict(int)
total = jobs_n = refused = 0
for r in runs:
    for page in api(f"repos/{REPO}/actions/runs/{r['id']}/jobs?filter=all&per_page=100"):
        for j in page["jobs"]:
            if not j.get("started_at") or not j.get("completed_at") or not j.get("runner_name"):
                refused += 1
                continue
            secs = (ts(j["completed_at"]) - ts(j["started_at"])).total_seconds()
            if secs <= 0:
                refused += 1
                continue
            m = math.ceil(secs / 60)
            key = f"{r['name']} / {j['name']}"
            by_job[key][0] += m
            by_job[key][1] += 1
            by_day[j["started_at"][:10]] += m
            total += m
            jobs_n += 1
print(f"since {SINCE}: {len(runs)} runs, {jobs_n} jobs with a runner, {refused} jobs without one, {total} runner-minutes")
for k, (m, n) in sorted(by_job.items(), key=lambda kv: -kv[1][0]):
    print(f"  {k}: {m} min over {n} jobs")
for d in sorted(by_day):
    print(f"  {d}: {by_day[d]}")
