# Work Methodology — Plan on Fable, Execute on Opus

Status: PROPOSED r2 (DEC-458, awaiting board confirmation; revised 2026-07-20 after board flipped engineer models)
Owner: CEO. Applies to: all agents.

## Problem

CEO runs `claude-fable-5` (most expensive tier, drains board limits). Team config as of 2026-07-20 (verified via agents API):

| Agent | Default model | Cheap profile |
|---|---|---|
| CEO | fable-5 | opus-4-8 (enabled) |
| All engineers (Sim, Founding, Frontend, Design System, Interactive Tools*) | opus-4-8 | opus-4-8 (enabled) |

*Interactive Tools Engineer is paused. Board flipped Simulation Engineer (and Interactive Tools) to opus-4-8 on 2026-07-20 — the CEO is now the **only** Fable-5 consumer, so the single remaining cost leak is the CEO executing instead of delegating. That is exactly what the adherence layers below gate.

Fable-5 tokens should buy judgment (planning, review, trade-offs), not execution (file edits, script runs, deck swaps). Today nothing stops the CEO from doing both.

## Methodology: tiered plan-and-delegate

Route work by tier. Tier decided at triage, recorded in first issue comment.

### Tier 0 — Trivial. CEO handles inline.
Comment replies, status updates, one-line data fixes. A delegation round-trip costs more than the work. No plan doc.

### Tier 1 — Standard. CEO specs, engineer executes.
Single-deck changes, single-script work, routine fixes. CEO writes a **short spec** (not a deep plan) into a child issue, assigns an Opus engineer, reviews result against acceptance criteria.

### Tier 2 — Complex/critical. CEO plans deeply, then delegates.
New deck builds, cross-cutting features, architecture, anything `priority: critical` or multi-agent. CEO produces a full plan on Fable-5: design decisions, task breakdown, per-task acceptance criteria, risks, review gates. Board-visible scope gets `request_confirmation` before implementation subtasks (existing three-gate flow stays). Then child issues to engineers; CEO reviews only.

### Child-issue spec template (Tier 1/2)
- **Objective** — one sentence.
- **Context** — links to files, decks, prior issues.
- **Constraints** — CI legality, budget, patterns to follow, out-of-scope list.
- **Steps** — outline, not prescription.
- **Acceptance criteria** — verifiable checklist. This is the contract; review checks only this.

### Review protocol
CEO verifies deliverables against acceptance criteria — checklist pass, not re-derivation. A checklist review does not need Fable-5 depth; it is eligible for the cheap profile (see layer 2). Defects get targeted feedback comments on the child issue; CEO never rewrites the work. Two failed review rounds → escalate to board, don't take over.

### Mis-tiered work
Tiers are a triage guess, not a contract. Anyone can re-tier with a one-line comment stating why. If a Tier 1 task outgrows its spec mid-execution, the engineer stops and hands back; CEO re-plans it as Tier 2 rather than the engineer improvising scope.

## Adherence — how we keep the CEO from executing

Process rules decay; structure and config stick. Four layers:

1. **Instruction-file rule (durable, loads every run).** Add to CEO `SOUL.md` + `HEARTBEAT.md`: *"CEO allowed actions: read, plan, create/assign child issues, review, comment, board interactions. CEO does NOT edit product files, run implementation scripts, or build decks. Exception: Tier 0, or blocked-critical with no engineer available — exception must be declared in the issue comment."* A checklist gate in HEARTBEAT step 5: *"Before any implementation action: does a child issue assigned to an engineer exist? If not, create one instead of acting."*
2. **Config lever (board-owned).** The engineer half is done: board flipped all engineers to opus-4-8 (2026-07-20). The CEO half needs an honest caveat the r1 draft glossed over: an agent cannot switch its own model mid-run, and profile selection (default vs `cheap`) is harness/board-owned. So: **Fable-5 stays reserved for Tier 2 planning; everything else the CEO does (triage, Tier 0, specs, checklist reviews, heartbeats) is eligible for the cheap profile.** If/when the harness supports routing CEO runs to `cheap` (per-run or per-issue), the board should enable it for non-Tier-2 work. Until then this layer saves nothing by itself — the enforced savings lever is layer 1: delegation makes CEO runs fewer and shorter regardless of which model they land on.
3. **Audit trail.** Every Tier 1/2 issue ends with a comment line: `planned-by: CEO / executed-by: <agent>`. Violations are visible in run history — board can spot-check: implementation runs attributed to the CEO agent are red flags.
4. **Weekly self-audit.** During weekly synthesis, CEO counts exceptions declared vs. issues delegated. More than ~1 in 10 issues executed by CEO → flag to board with cause.

## What this is not

- Not "CEO plans everything deeply." Deep plans only for Tier 2 — a Fable-5 deep plan for a one-file fix costs more than an Opus engineer just doing it.
- Not new approval bureaucracy. Board gates stay exactly where they are today (three-gate deck flow, plan confirmations).

## Rollout (on board acceptance)

1. ~~Board switches Simulation Engineer default model to opus-4-8.~~ **Done 2026-07-20** (board flipped all engineers; verified via agents API).
2. CEO amends own `SOUL.md`/`HEARTBEAT.md` with the rule + gate (layer 1).
3. Optional, board call: enable cheap-profile routing for non-Tier-2 CEO runs when harness support allows (layer 2 caveat).
4. Methodology status flips to ACTIVE; tier recorded on every new issue from then on.
