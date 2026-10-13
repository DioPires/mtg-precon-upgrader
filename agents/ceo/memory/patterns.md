# Patterns

Reusable workflows and decision patterns for the MTG Precon Upgrader project.

---

### Card Assessment Workflow
Standard pattern for evaluating candidate card additions to a deck:
1. Verify card text via Scryfall (`scryfall_card_by_name` MCP) — never trust memory
2. Assess fit: color identity legality, role gap vs. redundancy, synergy with commander
3. If fit confirmed: identify 2–3 cut candidates; post via `suggest_tasks` interaction for board pick
4. Board picks cut → execute swap in `deck.json` + refresh card-metadata + bump localStorage prefix + run validator
- Source: session 2e15722f, 2026-05-15

---

### Cut Candidate Ranking (green ramp decks)
From weakest to strongest inclusion (cut weakest first):
1. **Equipment ramp** (e.g., Sword of the Animist) — slowest ramp; safe cut when 14+ other ramp sources exist
2. **Slow finishers** (e.g., Worldspine Wurm at 11 CMC) — lowest relative speed
3. **Conditional tutors** (e.g., Formidable Speaker) — narrow effect + niche untap
4. **ETB-removal powerhouses** (e.g., Apex Altisaur) — unique role, keep unless explicitly outclassed

When board pushes back on a cut, verify whether the card fills a unique role before conceding.
- Source: session 2e15722f, 2026-05-15

---

### Deck Health as Assessment Gate
Before recommending a new card, check `metrics.json` `global_health` and `gaps[]`:
- Health 85+ with empty `gaps[]` → any addition is redundancy, not a gap-fill. Lower confidence in recommending; "Skip" is a valid board option.
- Health <85 or non-empty `gaps[]` → assess candidate against specific gap.

Example: The White Forge (health 85, zero gaps) → Parting Gust skipped.
- Source: session 53ec6176, 2026-05-15

---

### Deck Change Execution Checklist
After any `deck.json` card swap:
1. Update `deck.json` (add card in, remove card out)
2. Refresh card-metadata (run `scripts/refresh_card_pool.py` or equivalent)
3. Bump localStorage prefix version (vN → vN+1) to bust client-side cache
4. Run `python scripts/validate_deck_json.py --deck {id}`
5. Commit with descriptive message (e.g., `feat: add Selfless Safewright, cut Sword of the Animist from Verdant Tide`)
- Source: session 2e15722f, 2026-05-15

---

### Three-Gate New Deck Build Flow
For building a new commander deck from scratch, gate each phase behind explicit board sign-off:
1. **Gate 1 — Strategy**: present strategy options + ceiling analysis per candidate commander via `ask_user_questions` interaction; board picks commander + archetype
2. **Gate 2 — Deck Target**: define color identity, archetype tag, win-condition shape, budget, card constraints (exclusions, duplicates OK?), deck name; board confirms via `ask_user_questions`
3. **Gate 3 — Decklist**: present full 99-card list with role breakdown, curve, budget, metrics; board confirms via `request_confirmation` interaction

Never proceed to next gate without explicit board acceptance. Each gate revision uses `ask_user_questions` or `request_confirmation` with `continuationPolicy: wake_assignee`.
- Source: session 9da924f4, 2026-05-18

---

### CI/GC Preflight Check (Validator Gap)
The project's `validate_deck_json.py` does **not** check color identity violations. Before publishing any decklist, manually verify:
1. Every card's color identity is a subset of the commander's color identity (Scryfall `color_identity` field)
2. No card appears in `data/game-changers.json` (especially for B3 no-GC builds)

Confirmed validator gap: Hidden Stockpile `{W,B}` slipped past BG deck validation (session 9d8c30ab); Hall of Storm Giants `{U}` and Theater of Horrors `{B,R}` both slipped past mono-R validation (session 9da924f4). Always run a manual CI sweep as the final step before proposing a decklist.
- Source: sessions 9da924f4, 9d8c30ab; 2026-05-18

---

### Physical Collection Locking
Cards already physically present in another deck are unavailable for new builds by default. When a new build would require cards locked in existing decks, quantify the duplicate-buy cost and surface it to the board. Board may override (confirm duplicates OK) or the cost influences commander/strategy choice.

Example: All four token doublers were locked in Mutant Multiplication → Rith token strategy cost ~€100+ in duplicate-buys vs. Norin's ~€35.
- Source: session 9da924f4, 2026-05-18

---

### Duplicate Copies Policy (Cross-Deck)
When a card is in multiple decks simultaneously, the default resolution is **buy a 2nd physical copy** — do NOT propose removing it from one deck when adding to another. Board explicitly confirmed: "we get a new copy of the card so we can have it on both decks." Only raise a conflict issue when genuinely unsure if board is aware of the shared copy; use the issue to confirm buy vs. migrate, then close as done when board answers "buy."
- Source: sessions c56eeeb6, 2026-05-19

---

### Cut Recency Protection
Proposing a card as a cut when it was added in a recent prior review session (within the last few days to weeks) raises the board's justification bar significantly. Board rejected all 3 proposed Verdant Tide cuts (DEC-287 first round) because all 3 were added in recent prior sessions. Before proposing a recently-added card as a cut, verify it was added more than ~1 session ago, or provide a materially stronger counter-argument than "this new card outperforms it."
- Source: session bd142394, 2026-05-19

---

### Scryfall MCP: Planeswalker Loyalty Verification
The Scryfall MCP strips the `loyalty` field from planeswalker response payloads — loyalty is NOT returned in the standard card object. Always verify planeswalker loyalty via the raw Scryfall API (e.g., `scryfall_card_by_name` and check the raw JSON), or cross-reference with the card's oracle text section. Never assume loyalty from memory. Example: Elspeth, Storm Slayer stated as "starting loyalty 4" but actual starting loyalty is 5.
- Source: sessions 0ad5aa7d, 4f8fa4d0; 2026-05-19

---

### Mana Simulation Script Pattern
Per-deck Monte Carlo simulation scripts follow the naming convention `scripts/mana_simulation_{deck-id}.py`. Standard parameters: 100,000 games × 10 turns. Output schema goes to `data/commanders/{id}/simulation.json`. Reference implementation: `scripts/mana_simulation_pyre_and_panic.py` (676 lines). Scripts must also be registered in `scripts/export_simulation_results.py`. For 5-color decks, model each of WUBRG separately; account for commander cost-reduction interactions (Eminence, Morophon) in the castability calculations.
- Source: session c3cac001, 2026-05-20

---

### Comms Guideline — plain language, not ASD-STE100 (DEC-475)
Board decision 2026-08-15: all agent comms follow a 10-line STE-inspired plain-language guideline, embedded in every `agents/*/AGENTS.md` ("Comms Guideline" section). Full ASD-STE100 was rejected: wrong genre (procedural spec vs. our analytical comms), licensed ~900-word dictionary makes compliance unverifiable, MTG/stats vocabulary would all ride the Technical-Names exception. Core rules: lead with the outcome, short active-voice sentences, one term per concept, plain words, explicit numbers with stated comparison basis, complete sentences, clarity wins over any rule.
- Source: DEC-475, 2026-08-15

### Proposals: cite the section, hide nothing under the card, cost what is displaced
Two independent adversarial reviewers (Codex and a fresh Claude agent, DEC-950, 2026-10-10) found the same defect in a CEO workflow proposal: four claims ("already ours", "no owner", "ten checkpoints", "nothing delays the slice") were checked against memory, not the PRD, and two changes rode under the pick card without being options on it. Rule: every "already ours", "none" or "no owner" claim cites the PRD section or the file; nothing goes under a card that is not an option on it; every cost figure names what it displaces; the recommendation goes in the comment, not in the card's help text. When the owner asks for an adversarial review, run two reviewers from different model families on the same prompt and inputs, with a fact sheet they are told to verify, and triage every finding in the plan document.
- Source: DEC-950 plan §12.11, 2026-10-10

## Hand-backs on the 422 path are silent (2026-10-12)

An engineer whose hand-back PATCH gets a 422 parks the issue on a ten-hour monitor assigned to the CEO, and that wakes nobody: DEC-972's B1 fix sat from 04:30Z to 14:3xZ until the hub's own monitor fired. Rule: while any leg is out, the hub monitor fires at least twice a day, and every hub check starts by listing the children whose `updatedAt` is newer than the hub's last comment and reading their newest comment. A design brief for the owner leads with the matrix rows and the owner's exact words, maps each ask to the PRD section it changes, gives two or three directions with costs and one-way doors, and keeps the recommendation in the comment, not on the card.
- Source: DEC-950, 2026-10-12

## Push `main` before routing a review; pin, do not bend the scorer (2026-10-12)

Engineers branch from `origin/main`. When CEO commits sit only in the shared checkout, GitHub's `mergeable` flag is wrong and a conflict surfaces at merge time (DEC-990: seven local commits, one generated-file conflict on `data/commanders/anvil-chorus/candidates.json`). Rule: push `main` before creating the review issue, run `git merge-tree --write-tree main <branch>` and name every conflict and its resolution in the review issue. When the board asks for a card the generator ranks far below the cut, seat it with an explicit per-deck pin (`"pinned": true`) rather than raising the cut or changing scoring weights; the ranking stays honest and the file stays small.
- Source: DEC-990 hand-back and DEC-992, 2026-10-12

### Second article on an assessed workflow: assess the delta against the record
When the board forwards another article on a workflow already assessed (the 2026-10-10 Opus + Blender + Unity through MCP article; the 2026-10-12 cozy fishing game post), start from the record (DEC-950 plan §12.11 and §12.12, `docs/mcp-evaluation.md`) and write only what the new post adds. Keep the 2026-10-10 adversarial review's corrections as the checklist: every "ours already" claim cites a PRD section or an issue record; no item rides under a card that is not an option on it; every cost names what it displaces; the recommendation goes in the comment, not on the card; the card has a defer and a none option. Precedent: DEC-993 (2026-10-12), comment `48564d68`.
- Source: DEC-993, 2026-10-12

- **Codex gate on a PRD amendment (DEC-950, 2026-10-12):** run rounds until Codex writes that no further document round is required and every open item is a minor; a NO-GO with no blocker is one more round on my authority, a blocker returns the choice to the owner. Expect the new-finding count to decay (21, 10, 6, 5, 3 on Amendment 4). Review each round on a detached scratch tree pinned to the draft, in a process session of its own, so a dead run cannot kill it. Keep the comment's counts tied to the plan's lists (F83 and F86 were my own arithmetic). Upload the plan revision in the same step as the commit that labels it.

- **Review briefs: quote the merge-tree stdout and cite rules that exist in this repository (DEC-995, 2026-10-12).** The DEC-995 brief gave `ad838db0` as the merged tree; that was the PR head's own tree (`<branch>^{tree}`), and the reviewer's `git merge-tree --write-tree origin/main origin/<branch>` printed `b98e5ae0`. The brief also pointed at `docs/worktrees.md`, which exists only in eternities-mtg-app. Run merge-tree in the same command that writes the brief and paste its stdout; cite the sweep rule in the CEO instructions for mtg-precon-upgrader. Also: `delete_branch_on_merge` is off on mtg-precon-upgrader, so delete the remote head branch with `gh api -X DELETE .../git/refs/heads/<branch>` after every merge there.
- **End every wake with a sweep of my `in_review` issues whose newest comment is not mine (DEC-996, 2026-10-12).** The Founding hand-back on DEC-996 (18:33Z, "Decision needed") sat 80 minutes with no wake and no active run; I found it only by listing open issues at the end of the DEC-995 wake. The sweep costs one GET: `issues?assigneeAgentId=<me>&status=in_review`, then the newest comment of each. Route what you find before exiting.

- **Design references for web review briefs (DEC-1009, 2026-10-12).** `design_handoff_grimoire/prototype/` is cited by `web/README.md` but is not tracked in git (only `RECONCILIATION.md` was). Point a reviewer at `web/src/styles/tokens.css` (token source of truth), the existing `.gv1-*` rule family in `web/src/styles/styles.css`, and `designs/exports/*.png`; never at the prototype path. Side defects reported in a hand-back get their own low-priority issues at routing time, so they do not ride the review.

## 2026-10-12: One acceptance card per decision

Two `request_confirmation` cards for the same decision (one on the hub DEC-950, one on the review issue DEC-994) were both accepted within 24 s, and each woke a CEO run. The runs raced on the hub (409 on PATCH) and on the legs. Rule: one card per decision, hosted where the follow-up work belongs; if a card must be re-issued, withdraw the old one first. Before opening legs on a hub, re-read its comments for a sibling's split. `POST .../issues` drops `blockedByIssueIds`; PATCH it after creation.

## 2026-10-12 — Merge check on an unprotected repo (DEC-1009)
On mtg-precon-upgrader (`main` unprotected, `delete_branch_on_merge` off), merge with `gh pr merge --merge --match-head-commit <head>` and then compare `git rev-parse origin/main^{tree}` with the `merge-tree --write-tree` stdout the reviewer quoted; equal hashes prove the merged tree is the one drawn. Delete the remote branch by API afterwards. Route a reviewer's non-blocking notes at close-out: a CSS note goes to the open issue that edits the same block, a wording ruling goes to the next PR in the same component, each as a numbered description item plus a comment; record "no change" notes on the closed issue.

## 2026-10-12 — Reviewer follows the data owner (DEC-1007 → DEC-1013)
A web change that renders script output (here `metrics.json` `gaps[]` from `resilience_health`) is reviewed by the script's owner, not by a second frontend reviewer: the checklist needs the field list, the scoring formula and the component names, which only the owner can check without re-deriving. Put the implementer's judgment calls in the brief as numbered rulings (accept, or give the exact string), and ask the owner for advice on script follow-ups as notes ("advice only; no change on this PR"), so the PR stays web-only and the follow-up issue has a named basis. When a sibling issue owns a page-level defect (DEC-1008, `.gv1-perf-block` overflow at 390 px), scope the brief's overflow check to the element the PR touches (`.gv1-apo-maladies`), or the review fails on the sibling's defect.

## 2026-10-12 — Filter the full pool before the top-N cut (DEC-1013 N15 → DEC-1015)
A list that is cut to N for display and then filtered shows an empty result whenever the matching entries sit below N. In the Apothecary the gap-role cards sit at ranks 49–195 (1–4 per deck and role), so five decks drew an empty grid on a role chip; the fix filters the full `remedies` list and then cuts to 30. Rule for any "top N + filter" view: filter first, cut second, and keep the empty state for the case where the whole list has no match. When a reviewer reports such a defect outside the PR, measure the data (hits in the top N, hits in the full list, first hit rank) and put the table in the follow-up issue; three pairs with zero hits in the whole pool went to the data owner as an advice item on the script follow-up (DEC-1016), not as web scope.

## 2026-10-12 — Review brief for a responsive CSS PR (DEC-1008 → DEC-1018)
When a PR adds breakpoints, the reviewer is the design-system owner, and the brief lists each breakpoint as a draw at the boundary on both sides (1241/1240, 1101/1100, 561/560) with the figure to quote (`scrollWidth` vs `clientWidth`, right edge of the last item). Each visual change the implementer flags as "wider than the brief" (two-across tiles, vertical chart labels, a shedding order on the topbar) becomes a numbered design ruling: accept, or give the exact replacement rule. The "not fixed" list from the hand-back becomes one checklist item with lettered sub-rulings, and the follow-up issue for the measured part is opened before the review so the reviewer's figures land on a named issue (DEC-1017, blocked by the hub until the PR merges). Negative controls on a mixed source+test PR: `git checkout origin/main -- web/src` keeps the branch's tests and swaps the sources; restore with `git checkout origin/<branch> -- web/src` and demand an empty porcelain before the next draw. Playwright reuses a server on 4173 (`reuseExistingServer`), so the brief names the `lsof` check.

## 2026-10-13 — Route a review verdict's "not fixed" notes at the merge (DEC-1018 → DEC-1017/1019/1020/1021)
A reviewer's verdict carries rulings on things the PR left out. At the merge, each ruling goes to exactly one place: a correction to an already-open follow-up (rewrite its description and title, lift its blocker, comment what changed), or a new low issue per component with the reviewer's own figures and suggested rules quoted, the owner of that component as implementer and the other web engineer as reviewer. A note that is a setup lesson (`PLAYWRIGHT_BROWSERS_PATH`) goes into every open brief's Setup section and the CEO's brief rules. Nothing waits for a later wake.

## 2026-10-13 — Merge proof by tree equality, not a local test re-run
`merge-tree --write-tree` stdout = `origin/main^{tree}` after the merge = `<pr-head>^{tree}` when `main` did not move since the fork. That equality means the PR-head CI ran on main's exact tree; quote it in the merge comment and skip the local suite. Re-run only when `main` moved between the fork and the merge.

## 2026-10-13 — Two CEO runs live at once: the first writer wins, the second confirms
Two wakes that fire together start two CEO runs. Before routing an issue outside the current wake, read that issue's `/runs` list newest-first (`[:n]`); if a CEO run is live on it, leave it to that run. If both still write, the second run reads the thread, finds the first run's issue and monitor, restores the status and posts a one-line confirmation instead of a second review issue (DEC-1015, 01:10Z). The second run is often the parent's `issue_children_completed` wake, fired while the run that closed the child is still working the parent: verify, do not re-route. `POST .../checkout` sets an `in_review` issue to `in_progress`, so it is not a lock; read the thread first and PATCH `in_review` back if a checkout took it.

## 2026-10-13 — Merge refused "head branch is not up to date": update-branch, then a pinned merge (DEC-1011)
On a repository whose protection requires the branch up to date, `gh pr merge --match-head-commit <approved>` fails when the PR reads BEHIND. Update the branch by API with the approved head pinned (`gh api -X PUT repos/<o>/<r>/pulls/<n>/update-branch -f expected_head_sha=<approved>`), check `git rev-parse <new head>^{tree}` equals the reviewer's `merge-tree` id (a clean three-way merge gives the same tree from either side), wait for the hosted checks on the new head, then merge pinned to the new head and confirm `origin/main^{tree}` equals the same id. No re-review: the reviewer tested that tree. Sweep every `in_review` issue for a hand-back newer than the last CEO write on each wake; two of ten were lost wakes on 2026-10-13 (DEC-1011, DEC-996).

## 2026-10-13 — A sweep hit is not a lost wake while another CEO run is live
The end-of-wake sweep (`in_review` issues whose newest comment is another agent's, with no CEO run on the issue's own `/runs` list) found DEC-1011's APPROVE an hour old. A parallel CEO run had already merged its PR and closed the sibling DEC-1001 from a hub wake, and had not yet written to DEC-1011. Before routing a sweep hit, read the sibling and hub threads for a newer CEO comment and the daily note for an entry on it; the daily note is the one place every live CEO run writes as it goes. Route only when neither shows the hand-back in hand.

## 2026-10-13 — Order tests need a fixture that only the wrong order moves
"Cut to N, then sort gap-first" and "sort gap-first, then cut to N" give the same N tiles when no entry past the cut is a gap-addresser (DEC-1022 N5). A test that pins an order must seed one entry that only the wrong order would move (here a gap-addresser at rank 33 with a cut at 30), and the brief names the mutant (swap the two calls) as the control that must fail.

## 2026-10-13 — A digest over regenerated data must drop the clock-driven fields (DEC-996 / DEC-1030)
The implementer proved the WUBRG key order stable with one SHA-256 over 21 serialized `metrics.json` outputs under ten hash seeds, `generated_at` dropped. A reviewer hours later cannot reproduce that digest: `candidates_age_days` is "now minus the pool's `generated_at`", so it moves with the clock. The review brief names every field that moves with time (here `generated_at` and `confidence_inputs.penalties.candidates_age_days`), asks for a three-way digest with those dropped (committed files, script output under two seeds), and names the pre-fix script as the control that must give two different digests. The same rule applies to `git status --porcelain` after a second run: it proves nothing when the writer skips equal values and a clock field rewrites every file.

## 2026-10-13 — "lets continue" on many issues starts one CEO run per issue
A board comment posted on about ten parked issues within two minutes woke about ten CEO runs at once (09:05–09:07Z). Each run keeps to its own wake issue: it reads `/runs` on any sibling before writing there, routes only its own hand-back, writes the daily note as it goes (the one place every live run reports), and stages only the files it edited. Another run's uncommitted edits (an `AGENTS.md` section, an analysis note) stay unstaged; that run commits them. Check `git status --porcelain agents/ceo` before `git add` and name the files, never `-A`.

## 2026-10-13 — Focus Not Obscured under a sticky rail: test the on-screen control (DEC-1026 D1)
A sticky rail that pins for the first time hides keyboard focus from the controls under it. The hand-back's check (Tab from 3000 px of scroll) passed because the browser centres a control that is off screen; a control already on screen under the rail does not scroll at all, so focus lands under the rail (WCAG 2.2 SC 2.4.11). The review brief for any new `position: sticky` or `position: fixed` box asks for the on-screen case: scroll so the first control after the rail sits a few pixels below the rail's bottom, Tab to it, and read its top against the rail's bottom in three engines. The fix is one rule, `scroll-margin-top` at least the rail's tallest height on the controls after the rail (`styles.css:1800-1802` does it for the Compare columns), with the negative control run once without it.

## 2026-10-13 — Mutation as a review gate: ask the implementer for the pins first (DEC-1029)
PR #131 printed every line right and still read NEEDS-FIX: three mutants on lines the pull request added passed all 751 tests (a `dict.get` default, an `isinstance` guard in a new function, a flag on a new `Flaw`). The review brief made "each mutant must fail a test" an APPROVE condition, so each unpinned default became a block and cost a fix leg and a re-review. The implementing brief asks for it up front: every guard, default and flag the change adds has a test that fails without it, and the hand-back lists one mutant per such line with the failing test. A surviving mutant on a line the pull request adds is a block; on an untouched line it is a note for a follow-up.

## 2026-10-13 — Re-review brief after a verbatim fix: name the conditional controls and pre-rule the comment-only gaps (DEC-1019 / DEC-1026 round two)
A fix leg that applies a reviewer's exact replacement also applies the reviewer's figures. The Design System Engineer applied the `scroll-margin-top` rule word for word and flagged that its comment ("600–625px wide") does not reproduce (632 px with every deck selected), and that the new case covers the 148 px rail only, not the 200 px band. Neither is a behaviour defect. The round-two brief asks the reviewer to rule on each and states a default: not blocking, and the correction goes to the follow-up that measures the figure again (DEC-1024). A comment or a missing guard case then does not cost a third round unless the reviewer says why it cannot wait. Second habit: a hand-back's "N elements match the selector" is a count in the default state. Before the brief, grep the component for controls that render only after a user action (`Shopping.tsx`: `Clear owned` and the owned section's collapse button appear after an import) and name them as a check.

## 2026-10-13 — Review brief for a mid-band breakpoint PR: scope rulings first, the font host, and a note that explains another issue's note (DEC-1017 / DEC-1044)
- **Scope calls are CEO rulings, written ahead of the checklist.** The implementer read the acceptance more widely than the brief: each rule sits where the block stops fitting its gutter, up to 72 px above the reviewed band ("inside the viewport" was my wording). That call is mine, not the reviewer's. The brief states it as C1 (accepted, check every figure against the gutter), and a hygiene question from the hand-back (a tracked file that matches the new ignore pattern) as C2. The reviewer's rulings (R1 to R5) are then layout only.
- **The web app's fonts come from `fonts.googleapis.com`** (`web/index.html:8-11`, `display=swap`). A helper that waits for `document.fonts.ready` and then measures a layout sized for those fonts passes only while that host answers; with the requests aborted the fallback faces are wider (/codex 773 / 769 at 769 px). A brief for a test that adds a font wait asks for two readings: the wait removed under `--repeat-each=5`, and the font requests aborted with the wait in place.
- **Read the open issues on the same block before a hand-back note gets its own issue.** DEC-1017's N5 (a selector that never matched: `.gv1-shop-summary-stat` for `.gv1-shop-stat`) is the likely cause of DEC-1024's N5 (a Shopping stat 2.8 px past its column at 320 px). The note goes to that issue, with one reading asked of the reviewer.
- **Pick the follow-up's implementer by queue.** The reviewer of the parent PR measures the left-out blocks anyway. With an empty queue it implements the follow-up (DEC-1043, Design System Engineer) and the parent's implementer reviews. The Frontend Engineer held four reviews and three blocked legs at that time.
- **Breakpoint draws.** One pixel above each breakpoint and at it, on the named worst case; then every deck at each "breakpoint + 1" width, so a deck that needs more than the named worst case shows. Name the states no data reaches (no deck sets `partner`, so the two-art stack is not drawn) so the reviewer does not hunt for them.
