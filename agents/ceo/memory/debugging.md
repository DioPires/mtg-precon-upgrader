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

## 2026-10-13 — `/api/issues/{id}/runs` is newest-first
The runs list puts the latest run first. Slicing `[-4:]` shows the oldest runs and hides a live one; slice `[:4]`. This misread made a parallel-handled hand-back look like a lost wake (DEC-1015).
