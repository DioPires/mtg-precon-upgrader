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
