# Handoff: Combo Lab (§ XII) — production redesign of `/combos`

## Overview
A redesign of the Grimoire's **Combo Lab** page (the `/combos` route). Same feature set as the current production page — fleet/paste modes, Tier A/B/C findings, near-misses, completions, exports — restructured for hierarchy: a sticky **control rail** (mode, deck, contents, tier legend, export) beside a **report column** that opens with the bracket/Rule-0 **Disclosure** instead of burying it at the bottom, and gives each finding class its own visual form instead of identical gray boxes.

**Scope of this handoff: the Combo Lab page ONLY.** Everything else (Topbar, tokens, hover popover, data loaders, all other routes) is already implemented in the target codebase — reuse it, do not touch it.

## About the design files
The files in `design/` are **design references written in HTML/JSX for a browser-only prototype** — they show the intended look and behavior in pixel detail, but they are NOT production code to copy in. Your task is to **recreate this design inside the existing codebase** (`web/` — React + Vite + TypeScript) using its established patterns: typed data layer, existing hooks, react-router, CSS files on the `gv1-*` token layer.

Open **`design/Combo Lab.html`** in a browser to see it live: reference state 1 is the fleet report (Titan Convergence), state 2 is paste mode pre-analyzed. It is fully interactive — switch modes, pick decks, expand steps, hover any card name, click the export buttons.

## Fidelity
**High-fidelity.** `design/gv1-combolab.css` is the pixel source of truth — every color, size, spacing, and state in it is final. Port values verbatim (they reference semantic tokens from `gv1-tokens.css`, which the codebase already has). The JSX files define the exact DOM structure and copy.

## Target files in the codebase
- **Replace the render layer:** `web/src/routes/ComboLab.tsx` and `web/src/styles/combo-lab.css`.
- **Keep untouched (the redesign consumes their exact outputs):** `data/spellbook.ts`, `data/synergy.ts`, `data/tierB.ts`, `data/tierBIndex.ts`, `data/prices.ts`, `lib/spellbookMatch.ts`, `lib/spellbookReport.ts` (`bracketLabel`, `isTwoCardInfinite`, `isWinCombo`, `loopClassLabel`, `buildBracketDisclosure`, export builders), `lib/comboVerify.ts`, `lib/nearMissComplete.ts`, `lib/deckUrl.ts`, `deckLoader`.
- **Keep behavior:** `?deck=` / `?mode=` URL state, the Moxfield/Archidekt URL resolver, NF-3 parse+match timing log, all epistemic copy obligations (EI-1…EI-5).

## The page, screen by screen

### Layout shell
- Page header band (`.gv1-lab-hero`): grid `1fr / minmax(280px,420px)`, padding `44px 72px 30px`, bottom hairline. Left: eyebrow (`§ XII` in rune green mono 12px + dim mono annotation) over the 54px IM Fell title **The _Combo Lab_** (second words italic → gold via the global `em` rule). Right: italic serif lede, 15px/1.55, dim.
- Body (`.gv1-lab-layout`): grid `336px / minmax(0,1fr)`, gap 44px, padding `36px 72px 96px`. Rail is `position: sticky; top: 20px`.
- **Responsive:** container query (`container-name: gv1lab` on the page root, breakpoint 1080px) collapses to a single column, 2-col grids to 1-col, stats to 2-up. In production a viewport `@media` is equivalent — but keep the values.

### Control rail (top to bottom, each a `.gv1-lab-block`: bg-2 panel, 1px line border, dashed head divider)
1. **Mode toggle** — two equal cells, `aria-pressed`, active = 2px rune-green bottom border + focus-bg tint. Labels: "◈ mode i / Fleet deck", "◈ mode ii / Paste decklist". Equal emphasis by design.
2. **Fleet: deck picker** — one row per deck: `№NN` (mono 10px dimmer) · deck name (serif 16px, ellipsis) · combo count (mono, rune green) · mana pips. Active row = 2px rune left border + focus-bg. Decks without combo data: 55% opacity, count `—`, still selectable → "unscribed" empty state in the report.
3. **Paste: form** — commander input (optional), decklist textarea (mono 12px, bg-3, min-height 150px, quantities like `1x Name` accepted), `Analyze ⟶` primary chip + "Load example" ghost chip, then a timing note ("parse+match Nms · …").
4. **Contents** — one row per report section: folio (`XII·a`… mono 10px rune) · title (serif 15px) · count. Prototype pulses the target section on click; **production: smooth-scroll the page scroll container instead** (do not use window `scrollIntoView` if the rail stays fixed).
5. **The three tiers** — legend: A curated · human-verified (Spellbook) / B computed · verified under the model / C heuristic · speculative couplings.
6. **Scribe the findings** — corpus date in the head; 2×2 export buttons: Copy text / Copy markdown / ⇣ .txt / ⇣ .md. Copy feedback swaps the label to "Copied ◆" for 1.6s. Wire to the existing `buildPlainTextExport` / `buildMarkdownExport`.
7. Smallprint: Spellbook CC-BY-SA + Scryfall + WotC non-affiliation + "ownership flags read the § IX Shopping collection".

### Report column (52px gaps between sections; every section head: `§ XII·x` folio 72px col · 30px serif title · right-aligned mono annotation, hairline under)
1. **The Disclosure** (summary band, strong border): head row = deck name serif 32px + mana pips + commander + right label "bracket / rule-0 disclosure". Five stat cells (serif 44px numbers, mono 10px uppercase labels, hairline separators): curated combos · **two-card infinites (gold when > 0)** · win the game · verified loops (fleet) / cards analyzed (paste) · near-misses in corpus. Foot row: goldfish caveat ("A goldfish is assumed — no opposing interaction. Absence is not proof…") + Spellbook tag tally (`Ruthless ×3 · …`) + corpus stamp.
2. **§ XII·a Combos Present** — Tier A framing box (rune-green 2px left border, tier chip + italic serif sentence). Findings in a **2-col grid** of cards: head chips (Tier A · Win gold flag · 2-card infinite flag · bracket word · popularity right), the **card-name chain** in serif 20px joined by dim `+`, each name `[data-card-name]` (dotted underline, `cursor: help`) — **no inline art thumbnails; card previews come from the existing global hover popover** (explicit decision, keeps combo-dense decks short). Then produces chips (`∞` prefix, rune green for infinite), a `<details>` "Steps & prerequisites" (numbered 01/02/… mono + serif lines, curated text verbatim, attributed), and the "Why? — Commander Spellbook ↗" permalink footer. `(cmdr)` superscript in gold when `mustBeCommander`. Zero combos → the `.gv1-empty` state ("No curated combos found… corpus is not exhaustive").
3. **§ XII·b Verified Loops** — Tier B framing (amber). Same card anatomy; corroborated loops wear **Tier A + "Also curated"**, novel/engines wear Tier B; loop-class label right (`infinite loop (k=0)` / `per-turn value engine (k=n)` / `candidate loop · not strictly closed`); engines get a **Leaks** line (amber mono, e.g. "Leaks 1 mana/iteration" + italic note); `<details>` holds the numbered trace, prerequisites (min mana, guards), and the provenance line. Provenance-gate holdbacks → the warn strip. Empty → "No loops verified under the model — not an exhaustiveness claim…".
4. **§ XII·c One–Two Cards Away** — a **denser ledger**, not cards. Row grid `40px / minmax(200px,.85fr) / minmax(0,1.15fr) / auto`: distance chip (`−1` gold / `−2` dim) · **missing piece in gold serif 17px** (templates as dashed chips: "a Sacrifice Outlet") · "completes …" chain + produces line · popularity + `spellbook ↗`. Intro note explains the gold = missing convention. Collapse at 8, "Show all N" ghost chip. Annotation: "top 16 of 120 stored · N qualifying".
5. **§ XII·d Synergy Candidates** — Tier C framing (blue). Rows: Tier C chip + band chip (**strong = gold outline**, speculative = dim) + serif card pair + shape label right; under it the matched coupling edges as mono lines (`A ⟶ B · label`) — every candidate is justified, never a numeric score. Collapse at 6; "Deep couplings — triples & 4-cycles (N)" toggle reveals two side-by-side groups.
6. **§ XII·e Complete a Near-Miss** — Tier B framing ("A report only: it never edits your deck"). Filters row: Max price input · **Owned only** chip (disabled + tooltip when no collection; reads the same store as Shopping — `localStorage['grimoire-owned-cards']` in the prototype, whatever Shopping ships with in production) · status note linking to § IX Shopping when empty. Rows: 58px card thumb (the one place inline art stays) · name serif 19px + "· owned" rune tag · italic sample sentence ("with X + Y → Infinite card draw — and 2 more") · right rail `+N` (serif 28px rune) over "combos unlocked" + price.
7. **Attribution footer** — Spellbook (CC-BY-SA), Scryfall, WotC non-affiliation.

### Paste mode specifics
Same report shell. Summary swaps "verified loops" for "cards analyzed". **In production, Tier B/C and completions run for paste too** (client-side verifier + KB — that code already exists); the prototype shows framed "production only" placeholders in those two sections purely because the KB isn't bundled. Keep the unresolved-lines warning from the current build (prototype cut it; production must not).

## Interactions & behavior
- All hover/active/disabled states are in the CSS (`--gv1-transition-quick`, 140ms ease-out). Chips lift borders on hover; card-name hovers trigger the existing global popover.
- `<details>` disclosure for steps/traces (rotating ▸ marker).
- Collapse thresholds: near-misses 8, synergy pairs 6, deep couplings behind a toggle, completions max 10.
- Export buttons: real clipboard + file download, 1.6s "Copied ◆" feedback.
- TOC: smooth-scroll (see above), `aria-current` on the active section if you track scroll position (nice-to-have).
- Keyboard: everything is a real `<button>`/`<a>`/`<input>`; focus rings come from the global `:focus-visible` rule. Mode toggle uses `aria-pressed`; deck picker is `role="listbox"`/`option`.
- Reduced motion: pulse/transition durations already zero out via the token layer.

## State
Route-level: `mode` + `deck` in URL params (existing). Local: paste text + commander, `showAllNear`, `showAllSyn`, `showDeep`, `maxPrice`, `ownedOnly`, copy feedback. Data via existing `deckLoader` / matcher / verifier / synergy / completion modules — the design maps 1:1 to `ComboReport`, `TierBReport`, `SynergyReport`, `CompletionReport` fields already produced.

## Design tokens
All from the existing `gv1-tokens.css` (already in the codebase): bg `#0b1220` / panels `#0f1828` / `#141f33`; ink `#e8e1cf` (bright `#f5efd8`, dim `#8a8674`); rune green `#7cc892`; gold `#c8a654` (light `#e8d090`); tier colors — A rune green, B `--gv1-mana-r` amber `#e8a898`, C `--gv1-mana-u` blue `#a8c8e8`; hairlines `rgba(232,225,207,.12/.22)`; fonts IM Fell English (serif) + JetBrains Mono; radius 0 (sharp corners everywhere); 4px spacing scale. The ~40 `gv1-lab-*` component rules in `design/gv1-combolab.css` are new — port them as the new `combo-lab.css`.

## Assets
None. Card imagery and prices are live Scryfall via the existing card cache/hook; sigils are text glyphs (◈ ◇ ∞ ⟶).

## Files in this bundle
- `design/Combo Lab.html` — standalone interactive reference (open in a browser)
- `design/gv1-combolab.jsx` + `design/gv1-combolab-parts.jsx` — DOM structure, copy, and behavior reference
- `design/gv1-combolab.css` — pixel source of truth for the new styles
- `design/gv1-combo-data.js` — trimmed fleet data the reference renders (header documents the trim; production reads the full per-deck JSON it already loads)
- `design/gv1-tokens.css`, `gv1-states.css`, `gv1-styles.css`, `gv1-chrome.jsx`, `gv1-engine.jsx`, `gv1-cardhover.jsx`, `gv1-cards.js`, `gv1-data.js`, `gv1-real-decks.js`, `gv1-game-changers.js` — supporting prototype context so the reference runs; these already exist in production form. **Do not port these.**

## Acceptance checklist
1. `/combos?deck=…` and `?mode=paste` still work; deck picker and mode toggle write to the URL.
2. Disclosure band renders first with the five stats; two-card infinites turn gold when > 0.
3. Each tier keeps its framing box, color, and exact epistemic copy; corroborated loops present as Tier A.
4. Near-miss ledger shows the missing piece in gold; collapse/expand at 8.
5. Paste mode runs the full existing pipeline (matcher, unresolved warning, Tier B/C, completions) inside the new layout.
6. Exports produce the existing report builders' output; owned flags read the Shopping collection.
7. No regressions to the global card-hover popover, Topbar, or any other route.

---

## What to tell Claude Code (copy-paste prompt)

> Implement the redesigned Combo Lab page. Read `design_handoff_combo_lab/README.md` in full, then open `design_handoff_combo_lab/design/Combo Lab.html` in a browser as the visual reference (its JSX/CSS siblings are the structure and pixel source of truth).
>
> Work ONLY on the Combo Lab page: replace the render layer in `web/src/routes/ComboLab.tsx` and `web/src/styles/combo-lab.css` to match the design pixel-for-pixel. Everything else is already implemented — reuse the existing data layer, matcher, Tier-B verifier, synergy engine, completion engine, export builders, URL state, deck-URL resolver, card-hover popover, and design tokens exactly as they are; do not modify any file outside the ComboLab route and its stylesheet unless the README's keep-list says otherwise.
>
> The prototype stubs a few things production must keep real (paste-mode Tier B/C + completions, the full matcher index, the unresolved-lines warning, EUR prices) — the README's "Paste mode specifics" and acceptance checklist cover these. Verify against the checklist before finishing.

