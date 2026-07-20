# Work Methodology — Plan on Fable, Execute on Opus

Status: PROPOSED (DEC-458, awaiting board confirmation)
Owner: CEO. Applies to: all agents.

## Problem

CEO runs `claude-fable-5` (most expensive tier, drains board limits). Team config today:

| Agent | Default model | Cheap profile |
|---|---|---|
| CEO | fable-5 | opus-4-8 (enabled) |
| Simulation Engineer | fable-5 | opus-4-8 (enabled) |
| Interactive Tools Engineer (paused) | fable-5 | opus-4-8 (enabled) |
| Founding / Frontend / Design System Eng | opus-4-8 | opus-4-8 (enabled) |

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
CEO verifies deliverables against acceptance criteria — checklist pass, not re-derivation. Defects get targeted feedback comments on the child issue; CEO never rewrites the work. Two failed review rounds → escalate to board, don't take over.

## Adherence — how we keep the CEO from executing

Process rules decay; structure and config stick. Four layers:

1. **Instruction-file rule (durable, loads every run).** Add to CEO `SOUL.md` + `HEARTBEAT.md`: *"CEO allowed actions: read, plan, create/assign child issues, review, comment, board interactions. CEO does NOT edit product files, run implementation scripts, or build decks. Exception: Tier 0, or blocked-critical with no engineer available — exception must be declared in the issue comment."* A checklist gate in HEARTBEAT step 5: *"Before any implementation action: does a child issue assigned to an engineer exist? If not, create one instead of acting."*
2. **Config lever (board-owned).** CEO routine heartbeats run on the already-configured `cheap` profile (opus-4-8); Fable-5 reserved for Tier 2 planning and review. Recommend flipping Simulation Engineer's default to opus-4-8 too (cheap profile already exists) — an executing engineer on Fable-5 burns more than the CEO planning.
3. **Audit trail.** Every Tier 1/2 issue ends with a comment line: `planned-by: CEO / executed-by: <agent>`. Violations are visible in run history — board can spot-check: implementation runs attributed to the CEO agent are red flags.
4. **Weekly self-audit.** During weekly synthesis, CEO counts exceptions declared vs. issues delegated. More than ~1 in 10 issues executed by CEO → flag to board with cause.

## What this is not

- Not "CEO plans everything deeply." Deep plans only for Tier 2 — a Fable-5 deep plan for a one-file fix costs more than an Opus engineer just doing it.
- Not new approval bureaucracy. Board gates stay exactly where they are today (three-gate deck flow, plan confirmations).

## Rollout (on board acceptance)

1. CEO amends own `SOUL.md`/`HEARTBEAT.md` with the rule + gate (layer 1).
2. Board (or CEO if authorized) switches Simulation Engineer default model to opus-4-8.
3. Methodology status flips to ACTIVE; tier recorded on every new issue from then on.
