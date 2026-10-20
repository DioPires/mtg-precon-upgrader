import json, os, urllib.request, hashlib
B=os.environ['PAPERCLIP_API_URL']; K=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']
HUB='44c0525a-454f-423d-b8b5-3e010b9ad55b'
def req(m,p,body=None):
    r=urllib.request.Request(B+p,method=m,data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+K,'Content-Type':'application/json','X-Paperclip-Run-Id':RUN})
    try:
        with urllib.request.urlopen(r) as f: return f.status, json.loads(f.read() or 'null')
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:500]
_,h=req('GET',f'/api/issues/{HUB}'); t=h['description']
print('sha', hashlib.sha256(t.encode()).hexdigest()[:8], h['updatedAt'])
_,cm=req('GET',f'/api/issues/{HUB}/comments'); print('newest comment', cm[0]['id'][:8])
assert cm[0]['id'].startswith('37b6f24a'), 'new comment on hub; stop'
reps=[
("The board question is the card on [DEC-1155](/DEC/issues/DEC-1155).",
 "The board answered the card on [DEC-1155](/DEC/issues/DEC-1155) at 10:13:03Z with B: make the repository public after an engineer scans its history for secrets ([DEC-1179](/DEC/issues/DEC-1179))."),
("- Precedent: [DEC-880]",
 "- The board card was `c6017844` on DEC-1155. Options: A raise the budget (about $180 a month at $0.008 a minute), B public after a secrets scan of the history, C wait for 1 November, D other. The board chose B at 10:13:03Z (`37b6f24a`).\n"
 "- Minutes from 1 to 16 October (every job that got a runner, each rounded up to a whole minute; `agents/ceo/analysis/dec1155-billing/minutes.py`): 333 runs, 550 jobs, **2,928 runner-minutes**, against the Pro quota of 3,000. By job: `web-ci / e2e` 2,397 (82%), `lint-typecheck-unit` 415, `pytest` 82, `deploy-branch` 34. By day: 13 October 447, 14 October 646, 15 October 1,488, 16 October to 10:01Z 226. At about 860 a day, a month uses about 25,800 minutes.\n"
 "- Refused also: `lint-typecheck-unit` of run 38885447372 (PR #70, head `4d11b47`) at 10:10:23Z.\n"
 "- Precedent: [DEC-880]"),
("## What it blocks (at 10:15Z)", "## What it blocks (at 10:17Z)"),
("| #70 | [DEC-1153](/DEC/issues/DEC-1153) | `a75bcc2` | green, but its basis is before `e886907` |",
 "| #70 | [DEC-1153](/DEC/issues/DEC-1153) | `4d11b47` | refused (run 38885447372, update-branch at 10:10:14Z); APPROVE `21b0938a` on DEC-1170 at `a75bcc2` |"),
("| #71 | [DEC-1161](/DEC/issues/DEC-1161) | `5874fd4` | green on a merge with `e886907`; review DEC-1176 open |",
 "| #71 | [DEC-1161](/DEC/issues/DEC-1161) | `5874fd4` | green on a merge with `e886907`; review DEC-1176 yielded at 10:11Z (`ee74b63d`), no B item so far |"),
("| #74 | [DEC-1160](/DEC/issues/DEC-1160) | `7cba124` | green on a merge with `e886907`; review DEC-1175 |",
 "| #74 | [DEC-1160](/DEC/issues/DEC-1160) | `7cba124` | green on a merge with `e886907` (`e2e` success, run 38882262578); APPROVE `6b8cc3cb` on DEC-1175; merge run from DEC-1175's monitor at 10:19Z |"),
("Use `gh run rerun 38884232804 --failed` (PR #66's `e2e`, a reading we need anyway).",
 "Use `gh run rerun 38884232804 --failed` (PR #66's `e2e`, a reading we need anyway). Since the board's answer only a monitor's check reruns: the quota is used up, so a rerun only tests the block."),
("6. When the block ends, rerun the refused runs, then route each pull request by its own state block. Close this hub when every refused run has a reading.",
 "6. The block ends when the repository is public. Then rerun each refused run once: 38884232804 (PR #66), 38885108440 (PR #73) and 38885447372 (PR #70). For a pull request whose guard diff (rule 1) lists files at that time, run update-branch with `expected_head_sha` instead: a rerun tests the old merge commit. Then route each pull request by its own state block. Close this hub when each pull request of the table has a reading on its current head.\n"
 "7. Rule 1 allows one merge while the block lasts. A merge that changes `web/` or `data/` puts its files into every other open pull request's guard diff, and no new reading can come. PR #74 takes that merge: DEC-1175's APPROVE hand-back lost its wake, and run `6b0169a3` routed it. The steps are at the top of DEC-1175's description. After that merge, PR #70 also needs update-branch at the block's end."),
("The board's answer on the DEC-1155 card wakes the CEO on DEC-1155, and that run updates this hub.",
 "The scan's hand-back wakes the CEO on DEC-1179. That run passes the report on and writes the visibility card on DEC-1179. When the repository is public, the next CEO run does rule 6."),
]
for a,b in reps:
    assert t.count(a)==1, ('anchor', a[:60], t.count(a)); t=t.replace(a,b)
mon={'nextCheckAt':'2026-10-16T16:00:00Z','scheduledBy':'assignee','notes':'Billing block hub. On fire: rerun 38884232804 --failed once. If it starts, rule 6. If refused, re-park 6 h ahead. Check the merge of PR #74 (DEC-1175), deploy (rule 3) and DEC-1179.'}
print('notes', len(mon['notes']))
s,r=req('PATCH',f'/api/issues/{HUB}',{'description':t,'status':'in_review','executionPolicy':{'monitor':mon}})
print('PATCH', s, r['status'] if s==200 else r, r['executionPolicy']['monitor']['nextCheckAt'] if s==200 else '')
body=("**Parked (CEO run `6b0169a3`, 10:19Z): `in_review`, monitor at 16:00Z. I folded `45b1e947` and `37b6f24a` into the description, so run `a9b35256` need not add them.**\n\n"
"- **The block holds.** The newest refusal is run 38885447372 at 10:10:23Z, on PR #70's head `4d11b47`. I ran no rerun.\n"
"- **Lost wake routed: PR #74.** [DEC-1175](/DEC/issues/DEC-1175) read APPROVE at `7cba124` at 09:58:57Z (`6b8cc3cb`), and no CEO run took the hand-back. PR #74 passes rule 1: `e2e` success on run 38882262578, and the guard diff from merge base `e886907` to `cffaa03` prints nothing. A monitor at 10:19:04Z starts a CEO run on DEC-1175. That run merges it, fast-forwards `deploy` by hand, and closes DEC-1175 and DEC-1160.\n"
"- **Why merge now.** Whichever pull request merges first, each other one needs update-branch and a new run afterward. PR #74 needs no new run, so the merge now ships the fix sooner at no extra CI cost.\n"
"- **New rule 7, and rule 6 changed.** Rule 1 allows one merge while the block lasts. At the block's end, a pull request whose guard diff lists files gets update-branch, not a rerun: a rerun tests the old merge commit.\n"
"- I posted the block's rules on [DEC-1170](/DEC/issues/DEC-1170) (`d569e253`) before I read `e79d755f`; run `33287686` had already read them.")
s,r=req('POST',f'/api/issues/{HUB}/comments',{'body':body}); print('comment', s, r['id'] if s in (200,201) else r)
