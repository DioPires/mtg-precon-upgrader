# Debugging

Known bugs, tool quirks, and root-cause fixes discovered during development sessions.

---

### Commander Spellbook MCP: Transient Null Error
The Commander Spellbook MCP (`commanderspellbook_find_combos`) occasionally returns a transient null/empty response even when the API is reachable. This is a backend transience issue, not a decklist problem. Workaround: document known combos manually when the MCP fails, then retry in a later heartbeat. The combo was still valid — the error is from the MCP layer, not from the decklist being wrong.

Confirmed example: Hidden Legion deck (DEC-290/DEC-291) — Kiki-Jiki + Cloudstone Curio + Dragon Tempest combo documented manually after MCP null error.
- Source: session c3cac001, 2026-05-20

---

### Scryfall MCP: Planeswalker Loyalty Field Missing
The Scryfall MCP response object for planeswalkers does not include the `loyalty` field. This causes incorrect loyalty values to be stated when relying on the MCP response. Always verify planeswalker loyalty via raw Scryfall API JSON or manual lookup. See also the corresponding entry in `patterns.md` (Scryfall MCP: Planeswalker Loyalty Verification).
- Source: sessions 0ad5aa7d, 4f8fa4d0; 2026-05-19

---

### Paperclip interactions API payload schema
`POST /api/issues/{uuid}/interactions` requires `payload: {version: 1, prompt: "<string>"}`. Keys like `title`/`message`/`documentPath` fail validation (`invalid_literal` on version, `prompt` required). Top-level: `kind`, `continuationPolicy`, `idempotencyKey`.
- Source: run 533db3a5, 2026-07-20 (DEC-458)

---

### gh CLI needs HOME set in agent runs
In Paperclip runs `gh` returns `HTTP 401: Requires authentication` because the run's HOME is not the owner's home, so the keychain token is not found. Prefix with `HOME=/Users/dpires gh ...`. Plain `git fetch` works without it.
- Source: run on DEC-950, 2026-10-10

### codex CLI needs HOME=/Users/dpires in Paperclip runs

Same cause as `gh`: the run's HOME is not the owner's home, so `codex exec` cannot find `~/.codex/auth.json` and dies after five reconnects with `401 Unauthorized: Missing bearer or basic authentication in header`. Prefix with `HOME=/Users/dpires CODEX_HOME=/Users/dpires/.codex codex exec ...`. Also close stdin (`< /dev/null`) or a run can hang waiting on it (seen on the DEC-950 round-4 pass), and pass `--skip-git-repo-check` when the working directory is a scratch folder.
- Source: run on DEC-950, 2026-10-10 20:5xZ (adversarial review of the article proposal)

- **Agent instruction files can silently vanish (2026-10-10, DEC-950).** `GET /api/agents/{id}` → `adapterConfig.instructionsFilePath`; the Interactive Tools Engineer pointed at `agents/interactive-eng/AGENTS.md`, deleted in `b938316` five months earlier, and ran without it. Restored in `6b4f869`. When an agent behaves as if it never read the handoff or comms rules, check the path resolves before blaming the model.

## Paperclip `executionPolicy.monitor.notes` is capped at 500 characters (2026-10-11)

`PATCH /api/issues/{id}` returns 400 `too_big` on `executionPolicy.monitor.notes` above 500 characters, and the whole PATCH (status, `blockedByIssueIds`) is dropped with it. Keep the note short and put the routing detail in the issue comment. Seen on DEC-966, 2026-10-11 07:46Z.

## Codex exec: capture the review with `-o` (2026-10-12)

`codex exec ... -o <file>` writes the final message to the file; stdout carries the transcript (tool calls, reasoning summaries), which is noise for the record. Full form used for the DEC-950 round-5 gate: `HOME=/Users/dpires CODEX_HOME=/Users/dpires/.codex codex exec --sandbox read-only -m gpt-6-astra -c model_reasoning_effort=high --skip-git-repo-check -o <review.md> "$(cat prompt.md)" < /dev/null`, run from the worktree so the read-only sandbox roots there. Background it with start/end marker files and wait on the end file; a round takes 3 to 7 minutes.

### Keeping a Paperclip run alive while an external process runs (2026-10-12)
Ending the turn with only a background waiter pending ended the run twice (16:10Z, 16:39Z) and the second time the Codex child died with it. Launch the child in its own session (`python3 -I` + `subprocess.Popen(..., start_new_session=True)`, stdin DEVNULL, HOME and CODEX_HOME set; macOS has no `setsid`) and hold in the foreground with `while kill -0 $PID; do sleep 10; done` under a `timeout` up to 590000 ms, re-issued on expiry. A sleep inside a loop is not blocked.

## Daily notes under `agents/ceo/memory/` are gitignored (2026-10-12)

`.gitignore:59` (`memory/`) ignores the whole directory; only `MEMORY.md`, `debugging.md`, `mtg-cards.md` and `patterns.md` are tracked (added before or around the rule). A plain `git add` of the daily note fails with "paths are ignored", and `git add -f` tracks a file the repository means to keep local. Commit the four topic files only; the daily notes stay on disk. The DEC-995 run force-added `2026-10-12.md` in `df8a6c2` and untracked it again in the next commit.
- **Paperclip checkout body (2026-10-12).** `POST /api/issues/{id}/checkout` with `{}` returns 400 "Validation error": the body needs `{"agentId": "<my agent id>", "expectedStatuses": ["todo", "in_review", ...]}`. The harness checks out the wake's own issue; send the full body only when switching to a sibling issue.

## 2026-10-12 — Paperclip issue list omits monitors
`GET /api/companies/{cid}/issues?status=…` returns `executionPolicy.monitor` with `nextCheckAt` null and no notes even when `GET /api/issues/{id}` shows a live monitor. Use the single-issue GET before concluding a monitor is missing or before rewriting one.

## 2026-10-12 — A hidden-overflow root hides page overflow and still scrolls (DEC-1008)
`.gv1-root { overflow: hidden }` keeps wide blocks off `documentElement`, so a page-overflow check on `documentElement.scrollWidth` reads equal widths and passes. Script can still scroll a hidden-overflow box: `scrollIntoView({ inline: 'center' })` on a pill inside it slid the whole guide 34 px left at 390 px with no way back. Measure overflow on the clipping ancestor (`scrollWidth`, `clientWidth`, `scrollLeft`), load every deck (the first deck's pill never needs the scroll), and check the mobile grid track: a bare `1fr` grows to the widest child's min-content, `minmax(0, 1fr)` does not.

## 2026-10-13 — Playwright in agent runs: browsers live under the host home (DEC-1018 N2)
The sandbox `HOME` of an agent run has no `~/Library/Caches/ms-playwright`, so `npm run test:e2e` fails every case at browser launch. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` beside `HOME="$PAPERCLIP_GITHUB_HOST_HOME"`.

## 2026-10-13 — `overflow: hidden` on the app root kills `position: sticky` inside it (DEC-1018 N15d)
Under `overflow: hidden` the root becomes the scroll container for its descendants, so a sticky rail's top reads −600 after a 600 px page scroll; under `overflow: clip` it reads 0 and the rail sticks. Changing the root to `clip` switches on every sticky rule that never worked: check each one visually at the merge.

## 2026-10-13 — `/api/issues/{id}/runs` is newest-first and lists writers, not wakes
The runs list puts the latest run first (slice `[:n]`, not `[-n:]`) and holds every run that wrote to the issue: a run woken on another issue appears after its first write, and so does the current run. On DEC-1015 the DEC-1018 run (`c3257939`) saw itself in the list and took it for a parallel run; the hand-back was a real lost wake, because the assignee's 422 fallback PATCH (assignee + `executionPolicy.monitor`) woke no CEO run. Judge liveness by `runId` ≠ own run and `status: running`, then read the thread.

## 2026-10-13 — `executionPolicy.monitor.scheduledBy` is an enum (DEC-1019)
`PATCH /api/issues/{id}` with `executionPolicy.monitor.scheduledBy: "ceo"` returns 400 `invalid_value`, expected `"assignee"` or `"board"`, and drops the whole PATCH (the status change too). The CEO parking an issue it is assigned to writes `assignee`. Working shape: `{"status":"in_review","executionPolicy":{"monitor":{"nextCheckAt":"<ISO>","scheduledBy":"assignee","notes":"<500 chars"}}}`. `blockedByIssueIds` PATCH echoes the list in the response but GET by UUID can still show `[]`; the PATCH echo is the evidence.

## 2026-10-13 — `git add` exits 1 on an ignored untracked path and stops the `&&` chain
`agents/ceo/memory/` is gitignored; only `MEMORY.md`, `debugging.md`, `patterns.md`, `mtg-cards.md` are tracked (force-added once). `git add <tracked> <ignored-untracked>` stages the tracked files but exits 1 with the "paths are ignored" hint, so `git add … && git commit …` never commits. Stage tracked files in their own command; daily notes stay untracked. Found twice on the DEC-1019 run (`9b60ffb`, `85cb20b` needed a second attempt each).

## 2026-10-13 — zsh eats `$B:path` in `git show $B:scripts/x.py`
In zsh, `$B:scripts/compute_deck_metrics.py` applies the `:s/…/…/` history modifier to `$B` and git sees `origin/dec-pool-hygienek_metrics.py`. Write `"${B}:scripts/x.py"`. Also quote `--include='*.ts'`: unquoted, zsh fails the command with "no matches found" instead of passing the pattern to grep.

## 2026-10-13 — A model-limit failure on a wake is a lost wake (DEC-1021, DEC-1026, DEC-1028)
When a CEO run dies on the provider limit (`errorCode: claude_transient_upstream`; the issue's only new comment reads "You've reached your Fable limit"), Paperclip schedules no retry for that wake. The hand-back it carried sits `in_review` with me until its ten-hour monitor fires or the board comments ("lets continue", 09:06Z, six hours later). An `issue_assigned` wake can also leave no run on the issue at all (DEC-1028: hand-back 02:55Z, next run 09:06Z). On the first wake after such a failure, sweep every `in_review` issue for a hand-back newer than my last write and route each one from the current run, scoped by the wake-at-once rule in `patterns.md`.

## 2026-10-13 — Paperclip `/runs` rows carry `runId`, and `/runs` and `/comments` are newest-first (DEC-1026 routed twice)
`GET /api/issues/{uuid}/runs` rows have `runId`, `agentId`, `status`, `startedAt`, `errorCode`; there is no `id`. A `KeyError: 'id'` is a crashed read, not an empty list: retry it, never route on it. `GET /api/issues/{uuid}/comments` is newest-first, so `rows[0]` is the latest comment and `rows[-1]` the first; a "newer CEO comment" guard on `rows[-1]` always passes. Both failed in one run on 2026-10-13: I never saw the live run `f44a9ae8` on DEC-1026, routed its D1 verdict 42 s after that run did, and opened DEC-1036 as a duplicate of DEC-1032. Cancelled and corrected in the same run.
