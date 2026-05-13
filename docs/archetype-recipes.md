# Archetype Scryfall Recipes — Methodology

Status: **draft, pending board approval** (DEC-238). Until approved, this document is a proposal.

## Why this exists

The existing discovery system in `data/discovery-playbook.json` uses internal regex `oracle_patterns` to score a local Scryfall mirror and produce `candidates.json` (top-200 per deck). This is the **scoring** layer — it runs automatically and surfaces cards the deck might be missing, but its patterns aren't legible to the board and are easy to silently underfit.

Archetype recipes are a complementary **exploration** layer: human-vetted Scryfall native-syntax queries, co-authored with the board, that we run during deck research. Native syntax (`f:commander`, `id<=BRG`, `o:"text"`, `mv<=N`, `is:permanent`, `edhrec` ordering) is more expressive than our regex and — more importantly — legible enough that the board can review what the recipe is actually looking for.

Two layers, two purposes:

| Layer | Where | What | Reviewer |
|---|---|---|---|
| Scoring (existing) | `data/discovery-playbook.json` + `scripts/refresh_card_pool.py` | Automatic regex scoring → `candidates.json` | Agent-only |
| Exploration (new) | `data/archetype-recipes/{id}.json` | Hand-authored Scryfall queries, run during deck research | Board (explicit approval gate) |

Neither replaces the other. The board's "we miss good cards" concern is addressed by both: scoring catches things that score well by pattern; exploration catches things the board has explicitly told us to look for.

## Authoring workflow — three serial approval gates

A recipe is only valid after passing all three. Each gate produces a Paperclip `request_confirmation` interaction.

### Gate 1 — Taxonomy

Before any recipe is authored, the board approves the **archetype taxonomy** — the set of archetype IDs that warrant recipes. The taxonomy lives in `docs/archetype-taxonomy.md`.

### Gate 2 — Canon set

Per archetype, we propose a **canon set**: 10-20 cards that the archetype's recipe MUST surface. Drawn from existing decks tagged with this archetype, EDHREC top cards for the archetype, and known combo pieces from Commander Spellbook. Board approves the canon set before queries are authored — this prevents us from writing queries that retroactively justify a too-narrow card list.

### Gate 3 — Recipe

We author the recipe (a JSON file at `data/archetype-recipes/{id}.json`, see schema below), run it against the Scryfall API, and validate that it surfaces **≥90%** of the canon set. The board reviews:

- The query strings
- The recall percentage and which canon cards are missed (and why)
- A sample of high-scoring non-canon results — for noise assessment

On approval, the recipe is committed with an `approval` block recording the reviewer, date, and Paperclip interaction ID. The recipe's `version` is `1`.

### Re-approval on edits

Any change to a recipe's query strings bumps `version`. Re-approval is required before the new version is used. `last_reviewed` is informational; `version` is the binding identifier.

## Recipe file schema

```json
{
  "id": "aristocrats",
  "name": "Aristocrats / Sacrifice",
  "summary": "Sac outlets, death-trigger payoffs, and recursion that closes through incremental drains.",
  "version": 1,
  "last_reviewed": "YYYY-MM-DD",
  "approval": {
    "reviewer": "local-board",
    "date": "YYYY-MM-DD",
    "paperclip_interaction_id": "<uuid>"
  },
  "canon": [
    "Blood Artist", "Zulaport Cutthroat", "Bastion of Remembrance",
    "Viscera Seer", "Carrion Feeder", "..."
  ],
  "sub_recipes": {
    "sac_outlets": {
      "intent": "Free or 1-mana repeatable sac outlets",
      "queries": [
        "f:commander t:creature o:\"sacrifice a creature\" mv<=2",
        "f:commander t:creature o:\"sacrifice another creature\" mv<=2"
      ]
    },
    "death_payoffs": {
      "intent": "Triggered drains/draws/counters when creatures die",
      "queries": [
        "f:commander o:\"another creature dies\" o:\"loses\" o:\"life\"",
        "f:commander o:\"creature you control dies\" o:\"loses\" o:\"life\"",
        "f:commander o:\"another creature dies\" o:draw"
      ]
    },
    "recursion": { "intent": "...", "queries": ["..."] },
    "wildcard": {
      "intent": "Intentionally broad — surfaces oddities the precise queries miss",
      "queries": ["f:commander o:dies o:create"]
    }
  },
  "excludes": {
    "symmetric_punishers": "-o:\"each player loses\" -o:\"each player sacrifices\""
  },
  "shared_refs": ["_shared/recursion"]
}
```

Notes on the schema:

- **`canon`** is the ground truth for recall validation. Generated from a board-approved list before queries are written.
- **`sub_recipes`** are named query clusters; each may contain multiple queries (alternate oracle-text phrasings count as separate queries in one cluster).
- **`shared_refs`** allow archetypes to import sub-recipes from `data/archetype-recipes/_shared/`. Avoids duplication for idioms shared across archetypes (e.g., recursion appears in both aristocrats and reanimator).
- **`excludes`** are pasted into every query in the file (or applied post-fetch — see runtime semantics below).

## Runtime semantics

When a deck review begins:

1. Read `archetypes` from the deck's `deck.json`.
2. For each archetype, load `data/archetype-recipes/{id}.json` if it exists.
3. Compose runtime query: original query + `id<=<deck color identity>` + excludes + post-fetch filter for cards already in `decklist` + `candidates.json`.
4. Run via Scryfall API, `order=edhrec`, capped at top-50 per sub-recipe.
5. **Union** results across archetypes (de-duped). Decks with multiple archetypes get a broader pool, not a narrower one.
6. Surface results in the candidate-review step — each result is either added to the deck (with `sources: [{type: scryfall, detail: "archetype-recipe:aristocrats/death_payoffs"}]`), deferred, or rejected with a reason.

The recipe step is **no-op** if the deck has no archetype tag that maps to a recipe — we record a comment in `sources` noting the gap rather than blocking the review.

## Process integration

Insert into `AGENTS.md` "Research Workflow" as step **1b**, between candidate-pool refresh and per-card triage:

> **1b. Archetype recipes** — For each `archetypes` tag on the deck that has an approved recipe in `data/archetype-recipes/`, run the recipe. Diff results against `decklist` + `candidates.json` top-50. Triage each delta: include, defer (with note), or reject (with reason). If the deck has no recipe-covered archetype tag, record a comment in `sources` and skip.

## Maintenance

- **Versioning**: edits bump `version`. Re-approval required.
- **Audit cadence**: at minimum quarterly, or after any new MTG set release that touches a recipe's archetype. Audits re-run every recipe against current Scryfall data and surface new printings since `last_reviewed`. Board reviews adds.
- **Taxonomy expansion**: a new archetype warrants a recipe when at least one deck is tagged with it AND it's expected to recur. Adding to the taxonomy is a Gate-1 re-approval.

## Honest scope

This system addresses an estimated **~70%** of the "we miss good cards" problem the board raised in DEC-238. It does **not** address:

- **Cross-archetype staples** — cards that are strong across many archetypes but aren't owned by any single one (e.g., universal card draw, removal). These are caught by the candidates.json scoring layer, not recipes.
- **Format-shifting new printings** — a new mana rock or interaction piece that affects every deck. Caught by post-set sweep, not recipes.
- **Decks outside the taxonomy** — toolbox, niche tribal, oddball commanders that don't fit any defined archetype. Recipe step is no-op; we lean on candidates.json + manual research.

Recipes are not a silver bullet. They are a board-vetted lens that closes the largest single gap.
