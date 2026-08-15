# MTG Precon Upgrader

## Dryness Dial — This project: High

## Tooling

The Grimoire is a Vite + React + TypeScript app in [`web/`](web). DEC-149 cutover landed 2026-05-05; the previous vanilla-JS app is archived in [`legacy/`](legacy) for one release.

```bash
cd web
npm install
npm run dev      # http://localhost:5173 — vite serves /data/* via middleware
npm run build    # tsc -b && vite build → web/dist/
npm run preview  # http://127.0.0.1:4173 — serves dist/
npm run test     # vitest (unit + data layer)
npm run test:e2e # playwright smoke per artboard
npm run lint
npm run typecheck
```

Production deploy (`vercel.json`) runs `npm run build` in `web/`, copies `data/` into `dist/data/`, and serves `web/dist/` as the host root.

**Python scripts: run with `uv run python`** (e.g. `uv run python scripts/refresh_card_pool.py --deck {id}`). Bare `python` is not on PATH in all shells; the project uses `uv` for env + deps.

## Project Overview

A web application that provides recommended commander deck builds for Magic: The Gathering. The app displays card recommendations, synergies, and shopping lists for building commander decks up to Bracket 4.

## Architecture

- **Frontend**: React 18 + Vite + TypeScript SPA (`web/`), react-router with `?deck=...&view=...` URL state, 6 routes (Deck Guide, Codex, Compare, Shopping, Scrying, Dev). Every surface is fully responsive at phone widths; the iPhone-bezel `/m/:id` artboard retired per DEC-183 — `/m/:id` is now a redirect-only stub kept for one release.
- **Data**: JSON files in `data/commanders/{id}/{deck,simulation,metrics,candidates}.json`, fetched at runtime and normalized via `web/src/data/normalize.ts` (`DeckFull` shape)
- **Card metadata**: Scryfall via `useCard()` hook (`web/src/hooks/useCard.ts`) — 80ms throttle + dedupe + 24h localStorage cache
- **Styling**: CSS modules + global tokens in `web/src/styles/tokens.css` (3-layer: primitive → semantic → component). No Tailwind, no CSS-in-JS.
- **Hosting**: Static `web/dist/` (no backend)

## Key Files

| File | Purpose |
|------|---------|
| `web/src/App.tsx` | Routing root |
| `web/src/data/loader.ts` | Deck JSON loader (24h localStorage TTL) |
| `web/src/data/normalize.ts` | Raw deck.json → `DeckFull` normalization + types |
| `web/src/hooks/useCard.ts` | Scryfall card cache hook |
| `web/src/components/` | Atoms / molecules / organisms / global |
| `web/src/styles/tokens.css` | Design-token system (`--gv1-*`) |
| `data/index.json` | Deck catalog (commanders) |
| `data/commanders/{id}/deck.json` | Per-commander deck data (canonical) |
| `data/game-changers.json` | Official Game Changers card list |
| `legacy/` | Archived vanilla-JS app (one release; delete in follow-up) |

## Commander Deck Data Structure

Each deck JSON is a flat structure with no tier/upgrade wrappers:

```json
{
  "id": "titan-convergence",
  "type": "commander",
  "name": "Titan Convergence",
  "subtitle": "Cascading Inevitability",
  "commander": "Zhulodok, Void Gorger",
  "cost": "$200-350",
  "bracket": "4",
  "gameChangers": 2,
  "asymmetric_only": false,
  "sources": [...],
  "guideContent": {
    "strategyOverview": "...",
    "deckCategories": [{ "name": "Eldrazi Threats", "description": "...", "cards": [...] }]
  },
  "addCategories": [...],
  "adds": [...],
  "synergies": [...],
  "decklist": [{ "name": "Card Name", "type": "Creature" }, ...]
}
```

**Key fields:**
- `type: "commander"` (required)
- `bracket` — display field indicating deck power level
- `gameChangers` — count of Game Changer cards in the deck
- `asymmetric_only` — optional deck-side discovery modifier; set `true` only when symmetric punisher/resource-denial effects are strategic traps and the deck should prefer opponent-only templates
- `guideContent.deckCategories` — deck theme groupings
- `decklist` — full 99-card list as `{name, type}` objects with optional `quantity` field
- `adds` — notable/highlighted cards
- `synergies` — card synergy pairs/groups
- `sources` — attribution for the deck build

## Deck Rules

- **Display names should be strategic** (e.g., "Dark Dominion", not "Sauron Deck")
- Every card recommendation must be attributed via `sources`
- **Card pool**: All Commander-legal cards printed up to and including the current date of the analysis. There is no frozen cutoff — treat "the day this deck is being designed or reviewed" as the boundary. When in doubt about a recent printing, query Scryfall (`scryfall_search` with `released<=YYYY-MM-DD` if needed) rather than assuming a stale window.
- **Card text validation**: ALWAYS verify card names and oracle text via the `scryfall_card_by_name` MCP tool before recommending cards. Never assume card text or abilities from memory — validate every card considered. For bulk validation, use `scryfall_collection`.
- **Deck JSON validation**: After editing any `deck.json`, run `uv run python scripts/validate_deck_json.py --deck {id}`. The validator checks commander/decklist/highlight/category/win-condition/synergy card references against `priv_data/scryfall-oracle.json` and fails if reference blocks point to cards not in that deck. If the mirror is missing or stale, run `uv run python scripts/refresh_scryfall_mirror.py`.
- **Token data (DEC-403)**: `uv run python scripts/compute_tokens.py --deck {id}` regenerates a deck's `tokens[]` (tokens/emblems/game-state markers from Scryfall) and writes it into `deck.json`. Repeat `--deck` for multiple decks; **omitting `--deck` rewrites every deck** — only do that for an intentional fleet-wide token regen. Run it after decklist changes that add or cut token producers. Unknown ids exit 1 before writing anything.
- **Strategy-ceiling check (DEC-309)**: When validating a deck (or running `/phase-validate` on deck data), also run `uv run python scripts/validate_strategy_ceiling.py [--deck {id}]`. Detects shell/payoff mismatches (B4 shell + sub-B4 payoff, or fast combo + weak shell). Non-blocking — warnings only, exit code 0. Already invoked by `scripts/smoke_test.sh`. Thresholds + calibration documented in [`data/bracket-philosophy.md`](data/bracket-philosophy.md) "B4 Reality Check".
- **Bracket 4/5 deckbuilding principles**: See [`data/bracket-philosophy.md`](data/bracket-philosophy.md) for mana base, fast mana, free spells, interaction, and card quality standards. Apply when building or updating B4+ decks.
- **Deck modification workflow (board-approval required)**: When asked to review, rebalance, tune, or improve any existing deck, the deliverable is a **proposal comment** with adds/cuts and rationale — *not* edited `deck.json` files. Do not write to `deck.json`, `candidates.json`, or `metrics.json` (even as untracked draft files) before the board has explicitly accepted each individual swap. Acceptable pre-approval work: Scryfall lookups, `scripts/refresh_card_pool.py`, reading `candidates.json`, drafting proposal text. Present swaps as a checklist (`- [ ] CardName — reason`) so the board can accept/block line-by-line. Untracked ≠ approved.

## Source Attribution Schema

Every card add, synergy, and deck must have a `sources` array for traceability.

**Source object shape:**
```json
{
  "type": "edhrec" | "youtube" | "draftsim" | "article" | "scryfall" | "commanderspellbook" | "ai-inferred" | "other",
  "name": "Human-readable label",
  "url": "https://...",
  "detail": "Extra context (timestamp, section, etc.)"
}
```
- `type` (required): determines icon shown in UI
- `name` (required): human-readable label
- `url` (optional): link to source. Omit for `ai-inferred`
- `detail` (optional): extra context

**Where sources arrays go:**
- Per-deck: `sources` (root level)
- Per-card: `adds[].sources`
- Per-synergy: `synergies[].sources`

**When to use `ai-inferred`:** For synergy identification, strategic analysis, or card recommendations that came from Claude's analysis rather than a specific external source.

## Research Workflow

When building or updating deck guides, use all available sources and cross-reference findings:

1. **Candidate Pool (mandatory first step — DEC-90)** — Run `uv run python scripts/refresh_card_pool.py --deck {id}` before any review. This refreshes the local Scryfall mirror and regenerates `data/commanders/{id}/candidates.json`: the top-200 commander-legal cards scored against the deck's archetype tags + color identity + curve + ownership. Diff the `decklist` against the top of `candidates.json`. Any high-scoring candidate that is *not* in the decklist must be explicitly considered. Cuts require a reason captured in deck `sources` or review notes. See [`docs/discovery-playbook.md`](docs/discovery-playbook.md) for the archetype tagging contract.
   - **Re-run whenever it keeps `candidates.json` in sync**, not only before a review: **after any change to a deck's `decklist`** (scoring is decklist-dependent — keeps candidates + `gaps[]` current), when the **Scryfall mirror was just refreshed**, or when a deck's `candidates.json` is **stale** (≳7 days per `candidates_age_days`). Regenerating `candidates.json` *after* a committed/approved deck change is expected hygiene, not a pre-approval edit. (`metrics.json` is regenerated by its own metrics step, separate from card-pool.)
1b. **Archetype recipes (DEC-238)** — For each `archetypes` tag on the deck that has an approved recipe in `data/archetype-recipes/{id}.json` (status `live`), run the recipe's sub-recipe queries. Splice the deck's color identity (`id<=<colors>`) into each query at runtime; order by `edhrec`; cap at top-50 per sub-recipe. Post-filter results against `decklist` + `candidates.json` top-50 to surface only genuine deltas. For each delta, triage: include (with `sources: [{type: scryfall, detail: "archetype-recipe:<archetype>/<sub_recipe>"}]`), defer (with note), or reject (with reason). If the deck has no archetype tag with a `live` recipe, record a comment in `sources` and skip — do not block on missing recipes. See [`docs/archetype-recipes.md`](docs/archetype-recipes.md) for the methodology.
2. **YouTube** — Search for commander deck tech videos, fetch transcripts, extract card recommendations
3. **EDHREC** — Check commander pages for top cards, new additions from recent sets
   - **EDHREC closing diff (mandatory before handing off any new or changed decklist — DEC-402)**: after the 99 is drafted, fetch the commander's EDHREC page again and diff the final `decklist` against the top ~30 overall cards and top ~10 of each deck-relevant category (e.g. Equipment for a Voltron deck). Every high-inclusion card (≳40%) not in the list gets an explicit include/defer/reject line in the review notes. Research-stage EDHREC data does NOT satisfy this — Buster Sword (43% inclusion) was collected during DEC-402 research and still missed at build time because no closing diff existed. Inclusion rates are auto-fetched into `priv_data/edhrec/{deck-id}.json` by `refresh_card_pool.py` (via `scripts/fetch_edhrec_rates.py`, 7-day cache; board informed-override of the DEC-312 ToS bar, DEC-410 — keep it low-volume, see `docs/discovery-playbook.md`) and feed the candidate scorer as a 0–20 boost. The closing diff itself remains a mandatory human review gate — the scorer only surfaces candidates; include/defer/reject calls still happen here.
4. **Commander Spellbook** — Use `commanderspellbook_find_combos` MCP tool with the full decklist.
   - Record `included` combos as synergies with `"type": "commanderspellbook"` source
   - **Review `almost_included` combos** (1-2 cards away) — triage each near-miss to one of four outcomes (DEC-474 L7): **complete**, **defer** (with note), **reject** (with reason), or **retain-as-soft-combo**
   - Complete: when the missing card(s) fit deck strategy, budget, and bracket target, recommend the add with `commanderspellbook` source and note it was discovered via near-miss analysis
   - Retain-as-soft-combo: keep the incomplete loop deliberately as a value engine — the inverse of completing a combo. This is the right call for B3 decks at Game Changer caps, where completing a combo could force a bracket relabel (worked example: tidal-legion at the 3-GC B3+ cap). Record the choice with a reason in review notes or `sources`
   - Combo URLs: `https://commanderspellbook.com/combo/{id}/`
5. **Moxfield** — Search popular decklists for the commander
6. **Scryfall** — Use `scryfall_card_by_name`, `scryfall_search`, and `scryfall_collection` MCP tools to verify card names, check oracle text, and look up card data
7. **Web Search** — Articles, Reddit discussions, deck tech write-ups

Attribute every recommendation to its source(s). Multiple sources for the same card strengthens the recommendation.

**Trigger frequency per turn cycle (DEC-477, from DEC-474 lesson L1)**: before citing a triggered ability in a rationale, state how often it fires per turn cycle under the vanilla 4-player model. Opponent-turn triggers fire ×3. Symmetric "each player" triggers fire ×2 versus the 1v1 read. Own-attack-gated triggers fire ×1. This keeps multiplayer value claims explicit instead of imported from 1v1 intuition. (The candidate scorer applies a matching +5 boost for opponent-scaled trigger templates — see [`docs/discovery-playbook.md`](docs/discovery-playbook.md).)

### Deck Review Checklist (DEC-90)

Before recommending changes to any deck:

1. Confirm `archetypes` is set on `data/commanders/{id}/deck.json`. If missing, tag with one or more IDs from [`data/discovery-playbook.json`](data/discovery-playbook.json).
2. Run `uv run python scripts/refresh_card_pool.py --deck {id}`.
3. Open `data/commanders/{id}/candidates.json`. Scan the top 50 — each entry not already in the decklist is a potential overlook.
4. For each top candidate not in the deck, decide: include, defer (with note), or reject (with reason).
5. Verify any candidate you plan to add via `scryfall_card_by_name` MCP — never trust the playbook's pattern match without confirming the card text.
6. Update `decklist`, `highlights`, `synergies` as needed. Always attribute via `sources`.
7. **Hoser-coverage check (DEC-474 L6)** — Name the deck's top 1–2 hate classes: the hoser effects opponents will point at its strategy (e.g., graveyard hate for a reanimator deck, artifact hate for a treasure deck). Hosers ride on permanents — identify which permanent types carry each hate class (artifact / enchantment / land) and verify the interaction suite answers every one of those types. Example: Rest in Peace needs enchantment removal; Grafdigger's Cage needs artifact removal — a suite of only creature removal and counterspells fails a resolved hoser. In decks that treat the graveyard as a resource, prefer recurable, permanent-based interaction over one-shot spells, since those decks can re-buy permanent answers but lose spells to their own engine's exile/hate exposure. Why this step exists: bracket-philosophy's interaction section is speed/quality-only, and interaction counts live in deck-metrics (`interaction_density`) — neither covers hoser classes or permanent-type coverage.
8. **Manabase audit (DEC-426)** — Run `uv run python scripts/manabase_check.py --deck {id}`. The candidate pipeline never surfaces lands (`score_card` disqualifies cards with no archetype match), so this is the only automated land-discovery step. Review the Karsten deficits, the weak-current-lands list, and the top owned fixing candidates; give each land you skip an explicit defer/reject reason, same as step 4. Ranking caveats: `RESTRICTED` marks "spend this mana only" producers; cost-gated or conditionally-gated any-color lands (extra `{1}`, devotion, graveyard gates) still rank optimistically — judge those against the deck by hand; colorless-CI decks are out of scope for the discovery ranking (no colored credit/pip census — use the audit half only and pick utility lands by hand). Unowned new land cycles still enter via the EDHREC closing diff (DEC-402).
9. **Commander-dependency check (DEC-474 L8)** — Ask whether the deck still executes its plan when the commander is neutralized rather than killed. Darksteel Mutation-class locks (Darksteel Mutation, Imprisoned in the Moon, Song of the Dryads) leave the commander on the battlefield as an inert permanent, so the command-zone return never applies — that replacement only fires on a zone change. Remember CR 903.3d: "controlling a commander" means the battlefield only. If the plan collapses under such a lock, require a backup line in the 99 or targeted protection, and name the covering cards in the review notes. This is a review heuristic only — `resilience_health` (DEC-308) keeps its current components.
10. **Permanent-type durability (DEC-474 L8)** — At equal function, prefer engine pieces on harder-to-answer permanent types: enchantment or artifact over creature. Creatures face the widest removal range plus combat and board wipes; enchantments and artifacts dodge most of it. Apply this as a tiebreaker between functionally equivalent candidates, not a veto on creature engines. Same scope note as step 9: no metric change.
11. **Win-from-this-board goldfish (DEC-474 L3)** — Run this step when `gaps[]` reports a wincon gap or `uv run python scripts/validate_strategy_ceiling.py --deck {id}` flags shell-exceeds-payoff. First, characterize the deck's typical turn 6–7 goldfish board from `data/commanders/{id}/simulation.json`: board size, counters, tokens, available mana, and damage output. Then run targeted Scryfall searches keyed on that board profile to surface single-card converters — cards that turn that exact end-state into a win. Triage each hit like any candidate: include, defer, or reject with a reason (step 4), and verify oracle text before adding (step 5). This step is a generative complement to `gaps[]`: `gaps[]` names the missing role; this search finds the card that converts the board this deck actually builds. Worked example (source V1, DEC-474): the creator's stated T7 board supported a 36-counter transfer; searching on that profile surfaced Marionette Master and Faerie Bladecrafter as clean single-card converters — for example, Faerie Bladecrafter dies with those counters and each opponent loses 36 (both cards oracle-verified).

### Role taxonomy & deck metrics (DEC-90 P7)

When tagging cards, building decks, or reading metrics output:

- **Roles**: every `decklist[]` card has `primary_role` (required) and optional `secondary_role` from the closed 15-role set in [`docs/role-taxonomy.md`](docs/role-taxonomy.md). Commander has `commanderRoles` at deck root. `wincon` cards carry `wincon_style`; MDFCs are flagged `is_mdfc_land: true`.
- **Metrics**: `data/commanders/{id}/metrics.json` carries 5 deterministic scores (manabase health, role coverage, curve, interaction density, gameplan cohesion) + `global_health` + `gaps[]`. Formulas in [`docs/deck-metrics.md`](docs/deck-metrics.md).
- **Use gaps[] to drive review** — top-50 candidate review (step 3 above) should explicitly check whether each candidate addresses a `gaps[]` entry. The candidate-pool generator (P7.7) boosts gap-addressing cards in the score.

## Fleet Re-Audit Policy (DEC-396)

Board-approved via the DEC-369 next-steps interaction. Fleet assessments are **event-triggered**, not ad-hoc. Three triggers:

### Trigger 1 — Official Game Changers list update

- **Event**: WotC/Commander Format Panel publishes a Game Changers update (current baseline: 2026-02-09, 53 cards).
- **Detection (automated)**: `uv run python scripts/check_game_changers.py` — diffs `data/game-changers.json` against live Scryfall `format:commander is:gamechanger` (User-Agent header required, per DEC-370), verifies the `web/src/data/gameChangers.ts` mirror is in sync, recounts every deck's `gameChangers` field against its decklist, and checks caps. Exit 1 on any drift or violation. `--offline` skips the network diff. Run it at the start of any fleet-touching heartbeat; it is cheap (one paginated Scryfall query).
- **Response on drift**: (1) update `data/game-changers.json` **and** `web/src/data/gameChangers.ts` together — they must stay in sync; (2) re-run the script for the corrected fleet recount and fix stale `gameChangers` fields; (3) cap-compliance check — brackets ≤ 3 (incl. 3+) allow at most 3 GCs; verdant-tide and pyre-and-panic are hard-capped at 1 (board decision, DEC-369); 4-/4/4+/5 are uncapped. Any violation becomes a board proposal: swap-outs or a bracket relabel (relabel floor is GC-gated — a 4+-GC deck can only drop to 4-, see DEC-374).
- **Why it matters**: the Feb-2026 refresh alone moved 7 decks' counts and created Quill's 4/3 cap violation (DEC-382).
- **Who runs what**: whichever agent detects the drift runs the recount and files the proposal; deck changes still require per-swap board approval per the standard workflow.

### Trigger 2 — Deck reaches 3+ swap rounds since its last assessment

- **Event**: a deck accumulates 3 or more board-approved swap rounds (committed batches touching its `decklist`) since its last full assessment.
- **Detection**: after applying an approved swap round, count rounds since the last assessment: `git log --oneline <last-assessment-commit>.. -- data/commanders/{id}/deck.json`. Assessment baselines are the per-deck review issues (e.g., the DEC-369 cycle).
- **Response**: file a single-deck re-assessment issue — same rubric as a full review: card-pool refresh, metrics, re-sim, bar check (≥ B3+/4-, `data/bracket-philosophy.md`), **plus a stale-reference sweep of prose**: `guideContent`, category descriptions, and win-condition text can reference cut cards that the validator misses (it only checks card arrays). 3+ rounds is the stale-ref breeding regime — DEC-299 accumulated 5+ stale refs over 6 rounds.
- **Who runs what**: the agent applying the triggering (3rd) swap round files the issue; the board prioritizes it.

### Trigger 3 — Quarterly backstop

- **Event**: a calendar quarter ends. Skip only if a fleet-wide pass (trigger 1 response or a full assessment cycle) already ran that quarter.
- **Response**: slim verification pass (template: DEC-395 checklist):
  1. Before/after table for all decks vs the previous baseline — `global_health` (+ normalized), sim components, comboLethal/lethalProxy @T6–T8, `gaps[]` count.
  2. Bar check: every deck ≥ B3+/4-; flag misses with evidence.
  3. GC-cap compliance (run `scripts/check_game_changers.py`).
  4. Stale-reference sweep: `validate_deck_json` across all decks + prose grep for cut-card references.
- **Who runs what**: board schedules it; CEO executes or delegates via child issues.

## Common Tasks

### Add a New Commander Deck
1. Create `data/commanders/{new-id}/deck.json` with flat structure (see data structure above)
2. Add entry to `data/index.json` `commanders` array (with `theme` and `colors`)
3. Include full 99-card `decklist` array
4. Use `deckCategories` in `guideContent` for deck theme groupings
5. Run `uv run python scripts/compute_tokens.py --deck {new-id}` to populate `tokens[]`
6. Run `uv run python scripts/validate_deck_json.py --deck {new-id}` before handing off the change

### Research Deck Updates (with YouTube MCP)
1. Search YouTube for relevant videos
2. Fetch transcripts from top results
3. Extract card recommendations
4. Compare with existing deck data
5. Update deck.json with new findings
6. Run `uv run python scripts/validate_deck_json.py --deck {id}`

## Engineering Principles (board decision DEC-475, 2026-08-15)

1. Choose the simplest implementation that fully meets the current requirement. Avoid speculative abstractions, configuration, and indirection.
2. Grow the system in layers. Start from the smallest version that works end to end, and add each capability on top of a working product. Never trade a working product for unfinished complexity.
3. Keep components modular and concerns separated.
4. Lean on dependencies already in the project before you write new code or add a package. Do not assume a library lacks a capability — check its documentation and types first.
5. Add a new dependency only when an established, well-maintained library reduces overall complexity, and only within the locked architecture decisions (no Tailwind, no CSS-in-JS, no backend; see DEC-149-plan.md).
6. Do not preserve backward compatibility by default. Remove obsolete paths instead of adding compatibility layers or fallbacks. Exception: board-approved deprecation windows (for example, `legacy/` for one release).
7. Make design decisions for the long term. A temporary path is acceptable only with a named removal trigger.
