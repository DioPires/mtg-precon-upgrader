# DEC-90 — Deck Building Process Overview

**Status:** Proposal — awaiting board approval before any implementation.

## The Problem

When analysing a new deck or reviewing an existing one we routinely overlook printed cards. Symptoms:

- Recommendations skew to staples/recent prints we already remember.
- The recommendation engine (`scripts/generate_recommendations.py`) **scores cards we already have in scope** — it does not enumerate the full commander-legal universe matching deck criteria.
- No archetype → query mapping forces a broad sweep before review.
- Owned-cards CSV (`priv_data/owned_formatted.csv`, 4,206 rows) is referenced as an overlay but not as a *discovery* source for adds.

## Root cause

Discovery is *recall-led* (we query for cards we think of) instead of *retrieval-led* (we enumerate every commander-legal card matching deck criteria, then filter).

Agreed standard from `agents-files/global/AGENTS.md`: *"Retrieval over recall — verify domain facts against specs, docs, or APIs before relying on training knowledge."* We're violating this for card discovery.

## Options

### A — Process only (lightweight)
**What:** Author an archetype → Scryfall query playbook (`docs/discovery-playbook.md`). Mandate running it before any deck build/review. Each archetype lists required Scryfall queries (e.g. graveyard reanimator: `o:"return target creature card from your graveyard to the battlefield" f:commander id<={colors} cmc<=6`).

**Pros:** Zero infrastructure, immediate, no maintenance.
**Cons:** Per-query API round trips. Still depends on agent discipline. Can't easily multi-criterion score the universe.
**Effort:** ~1 day of playbook authoring.

### B — Local Scryfall mirror (infrastructure only)
**What:** Daily fetch of Scryfall `oracle-cards` bulk (~150 MB, ~33k cards). Store as `priv_data/scryfall-oracle.json` (gitignored) or SQLite. Refresh script + jq/SQL helpers.

**Pros:** Full search space queryable instantly. Complex multi-criteria filters. Owned-cards joins are trivial.
**Cons:** Storage + freshness discipline. By itself doesn't change *behaviour* — still needs a process layer.
**Effort:** ~0.5 day for fetch script; ~1 day for query helpers.

### C — Hybrid: mirror + playbook + candidate-pool generator (recommended)
**What:**
1. Local Scryfall mirror (B).
2. Archetype playbook with named queries (A).
3. New script `scripts/generate_candidate_pool.py` that, for each deck, emits `data/commanders/{id}/candidates.json` — every commander-legal card matching the deck's color identity + archetype tags + CMC envelope, ranked by a coarse fitness score (oracle-text matches against archetype keywords + owned flag + game-changer flag).
4. Deck-review checklist gains a "diff decklist vs candidates.json" step. Anything in the top N of candidates not in the decklist must be explicitly considered (and rejected with a reason if cut).

**Pros:** Forces breadth at review time. Persists per-deck. Bridges into existing `recommendations.json` pipeline. Owned-cards integration native.
**Cons:** Most build effort. Candidate files add ~50–500 KB per deck (gitignored or committed — open question).
**Effort:** ~1 day mirror + ~1 day playbook + ~1.5 days candidate generator + integration with review workflow.

### D — Per-deck candidate snapshots only (no playbook, no mirror)
**What:** Use existing Scryfall MCP (`scryfall_search`) at deck-review time to dynamically build candidate pools. No persisted local mirror.

**Pros:** No mirror maintenance. Existing tooling.
**Cons:** API rate limits during enumeration. Slower iteration. Discovery still depends on the reviewer choosing the right queries — the recall-bias problem is unsolved.
**Effort:** ~1 day for review helper script.

## Recommendation

**Option C.** The mirror is the only thing that makes "score every commander-legal card against this deck" tractable, and it pays back every time we review a deck. The playbook keeps the *process* honest — without it, infra alone doesn't change behaviour. The candidate pool file is the durable artifact that makes overlooks visible.

If we want to ship something today and iterate: **start with A (playbook) + B (mirror)**, then layer C's candidate generator next heartbeat once we see what queries actually find.

## Open questions for the board

1. **Scope:** Pure process (A), pure infra (B), or hybrid (C)? *— pending*
2. **Cadence:** Daily Scryfall bulk refresh — manual, on-demand, or scheduled? *— pending*
3. **Storage:** Commit `candidates.json` per deck, or gitignore? *— recommended: **commit, trimmed payload, top-200**.* Reasoning: aligns with existing `recommendations.json` / `simulation.json` precedent; auditability is the whole point of the artifact (gitignore erases the "did we consider it?" trail); reviewer reproducibility without forcing mirror setup; ≈900 KB total across all current decks at top-200 trimmed; diffs against new sets become a reviewable signal. Mirror itself stays gitignored (~150 MB).
4. **Threshold:** What size candidate pool is useful — top 50 per deck? Top 200? All matches? *— pending; recommendation defaults to top-200 alongside Q3 above.*
5. **Trigger:** Should the candidate pool be regenerated on every deck change, or only on demand? *— pending*

## Out of scope (for this issue)

- Auto-applying candidate-pool suggestions to decklists (would still need board approval).
- UI changes to surface candidates in the Grimoire app.
- Changing the existing `recommendations.json` scoring methodology.

## Next action

Board chooses A / B / C / D (or another direction). Until then, no code changes.
