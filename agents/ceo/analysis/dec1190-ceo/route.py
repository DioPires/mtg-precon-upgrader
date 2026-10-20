import json, os, datetime, urllib.request
API=os.environ['PAPERCLIP_API_URL']; KEY=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']
ISSUE='b090ef84-7c6c-4d1e-94d2-0018f340dd65'; REV=json.load(open('review-issue.json'))
def req(m,path,body=None):
    r=urllib.request.Request(API+path,method=m,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+KEY,'X-Paperclip-Run-Id':RUN,'Content-Type':'application/json'})
    with urllib.request.urlopen(r) as f: return json.load(f)
cs=req('GET',f'/api/issues/{ISSUE}/comments'); cs=cs if isinstance(cs,list) else cs.get('comments',[])
assert sorted(cs,key=lambda c:c['createdAt'])[-1]['id'].startswith('d79ab19a')
now=datetime.datetime.now(datetime.timezone.utc).strftime('%H:%MZ')
R=REV['identifier']
comment=f"""## Routed: the review goes to the Frontend Engineer on [{R}](/DEC/issues/{R}); rulings on the hand-back

**Outcome.** The Frontend Engineer reviews PR #79 on [{R}](/DEC/issues/{R}) (priority low, ports 14973 and 14974). It had no part in the pull request, no open issue and no live run at 16:22Z. The server skipped the assignment wake of your hand-back `d79ab19a`; your 30-minute monitor started this run at 16:17Z.

### Rulings
1. **Note 1, the minus sign: your rule stands.** A "−" directly before a digit is the sign of a number, and both checks pass it, as they pass "-1". A "−" in any other place stays a glyph. I do not put "−" in R0: R0 would then pass a decorative "−" in any place. I add no words: a screen reader says the sign of a number already. The distance chip keeps its words from the C3 table; spec line 322 checks them, and the reviewer runs a mutant on them.
2. **Pixels: I accept the sub-pixel cause if the reviewer's control shows it in all 15 states.** Your control covered 3 of the 15. I accept the 1 px growth of the "Copied" button: that state lasts 1.6 s.
3. **`lib/comboVerify.ts:517` ("mv ≤ N"): no change in this pull request.** It renders in no state that the spec reads. It is a named limit.
4. **Notes 2 to 10 stand as your decisions.** The reviewer checks each one against the code.

### Next
- On APPROVE, I merge PR #79 and remove `wt-dec1190`. Keep the tree until then.
- On CHANGES, a fix round comes back to you on this issue.
"""
c=req('POST',f'/api/issues/{ISSUE}/comments',{'body':comment}); cid=c['id']; print('comment',cid)
iss=req('GET',f'/api/issues/{ISSUE}'); old=iss['description']
assert not old.startswith('**STATE')
state=f"""**STATE (CEO run `9e4de761`, 2026-10-16 {now}). Read this section first. The build brief below is done; do not start it again.**

- **Done.** PR #79 is open, head `017060e`, base `main` `8f15c33`, `web-ci` run 38926608379 green. Hand-back `d79ab19a`. My rulings are in comment `{cid[:8]}`: the minus-sign rule stands; the pixel cause stands if the reviewer's control shows it in all 15 states; `lib/comboVerify.ts:517` is a named limit.
- **Where the leg is.** Review [{R}](/DEC/issues/{R}) (the Frontend Engineer, low). Its hand-back comes to me on {R}, with its own 30-minute monitor.
- **On APPROVE.**
  1. Run `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin`, then `git diff --stat 8f15c33 origin/main -- web data .github`.
  2. If step 1 prints files, run `HOME="$PAPERCLIP_GITHUB_HOST_HOME" gh pr update-branch 79` and wait for `web-ci` on the new head (about 10 minutes) with a bounded loop.
  3. Merge pinned: `gh pr merge 79 --merge --match-head-commit <head>`.
  4. Wait for the push run on `main` and the Vercel deploy. Quote the count lines.
  5. Remove `wt-dec1190`: `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, then `git worktree remove` (never `--force`), `git branch -D dec-1190-glyph-names`, `git worktree prune`, and delete the remote branch if GitHub kept it.
  6. Close {R}, then this issue. The A/B leg on DEC-1182 waits for the owner's card `345bc3b0`; see the DEC-1182 state block.
- **On CHANGES.** Write a fix round for the Design System Engineer at the top of this description ("FIX ROUND 1. Read this section first"). The re-read goes back to the Frontend Engineer on {R}.
- **Known limits.** R0 and the middle dot rest on the DEC-1182 reading (no VoiceOver pass). `lib/comboVerify.ts:517` keeps "≤". `Hero.tsx` is imported by no module.
- **Fallback monitor:** 20:50Z.

---

## Build brief (done)

"""
r=req('PATCH',f'/api/issues/{ISSUE}',{'description':state+old}); print('desc', len(r['description']))
mon={'status':'in_review','executionPolicy':{'monitor':{'nextCheckAt':'2026-10-16T20:50:00Z','scheduledBy':'assignee','notes':f'Fallback while review {R} (Frontend Engineer) reads PR #79 at 017060e. Rulings in comment {cid[:8]}. On wake: read {R} for a verdict; see the STATE block at the top of the description.'}}}
assert len(mon['executionPolicy']['monitor']['notes'])<500
r=req('PATCH',f'/api/issues/{ISSUE}',mon); print(r['status'], r['executionPolicy']['monitor']['nextCheckAt'])
