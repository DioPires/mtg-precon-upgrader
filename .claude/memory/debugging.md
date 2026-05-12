# Debugging

### `getEffectiveCommander is not defined` — ReferenceError on Deck Load
**Symptom:** Red error banner on every deck selection. App shows gallery but won't load deck detail.
**Root cause:** `getEffectiveCommander()` called 7 times in `app.js` but never defined. Was a legacy helper from the old tier-based deck structure.
**Fix:** Add at top of `app.js` utility section:
```js
function getEffectiveCommander() {
  return currentDeck.commander;
}
```
**Commit:** `6614bf9`
- Source: session 9a365107, 2026-03-20

### Browser Cache Hides JS Fixes
After editing `app.js`, headless browser (and regular Chrome) may serve the old cached version. Kill and restart the local dev server to bust cache.
- Source: session 9a365107, 2026-03-20

### Paper MCP — `get_computed_styles` Parameter Format
`get_computed_styles` expects a `nodeIds` **array**, not a single string. Similarly, `get_font_family_info` expects a `familyNames` **array**. Passing a string causes a parameter error.
- Source: session a8e6cc42, 2026-03-20

### Paper MCP — `display: grid` Not Supported
Paper artboard elements don't support CSS Grid (`display: grid`). Use `display: flex; flex-wrap: wrap` for multi-column layouts. `margin` is also unsupported — use `padding` + `gap` only.
- Source: session 01f7504e, 2026-03-20

### Paper MCP — `backdrop-filter` Not Supported
`backdrop-filter: blur(...)` has no effect in Paper artboards. Use solid `rgba(r,g,b,a)` backgrounds instead.
- Source: session 01f7504e, 2026-03-20

### Scryfall Images — Three Pre-Fix Bugs
1. **Unthrottled bulk loads**: 12+ scattered Scryfall URL constructions bypassed the rate limiter entirely, causing 429s when loading deck gallery (11 images) or decklist gallery (99 images) at once. Fix: centralize via `scryfallImageUrl()` + IntersectionObserver queue capped at 10 req/s.
2. **Ephemeral imageCache**: `imageCache` Map was in-memory only — lost on page reload. Fix: persist to localStorage under `grimoire-image-urls` key (2000-entry cap).
3. **`showMobilePreview()` cache bypass**: This function constructed Scryfall URLs directly, ignoring `imageCache`. Fix: route through the centralized cache before fetching.
- Source: session a074338b, 2026-03-20

### Pencil MCP — `alignItems: "baseline"` Invalid
Pencil `.pen` schema does not accept `"baseline"` as an `alignItems` value. Valid values are `"start"`, `"center"`, `"end"` only. Using `"baseline"` causes a silent schema rejection.
- Source: session d3c6539f, 2026-03-20

### Paperclip — Stale executionRunId Blocks All Issue Mutations
When a heartbeat exits without completing its Paperclip API updates, the issue remains locked to the previous run's `executionRunId`. Subsequent runs cannot PATCH status, POST comments, or release the issue — all return 409 or 403. Checkout with `expectedStatuses: ["in_progress"]` from the new run resolves the lock. Work is still safely committed to git; only the Paperclip status lags behind.
- Source: session a074338b, 2026-03-20; session ee35b340, 2026-03-20

### Pencil MCP — `Move` Doesn't Trigger Layout Recalculation
Moving a child node within a frame via `mcp__pencil__batch_design` (Move operation) changes the tree order but the layout engine may not visually reposition children — `snapshot_layout` shows the node at its old y-coordinate despite the new index.
**Fix:** Toggle the parent frame's layout off then back on (e.g., `batch_design` with `layout: null`, then restore original layout type) immediately after the Move. This forces a full relayout.
- Source: session de8ea6f9, 2026-03-21

### Upgrade Paths Hover Flicker — Missing Dedup
**Symptom:** Card preview image rebuilds (flickers) every time the mouse moves over child elements within an upgrade card row.
**Root cause:** `mouseover` fires on every child element; `closest('.upgrade-card')` always resolves to the same parent, but `showCardPreview()` was called without checking if the card already matches `currentHoveredCard`. `showCardPreview` does `previewContainer.innerHTML = ''` on every call, rebuilding the image element.
**Fix:** Add `lastHoveredUpgradeCard` dedup variable; skip `showCardPreview` call when card name is unchanged.
- Source: session 92527ddd, 2026-03-23

### deck.json Category Edit — Duplicate Match Failure
`deck.json` files often have identical card-list strings in both `guideContent.deckCategories` and `categories` arrays. Editing a string that appears in both fails with "2 matches found" error.
**Fix:** Use `replace_all=true` on the Edit call to update both occurrences simultaneously.
- Source: session 4d43917b, 2026-03-27

### Commander Spellbook MCP — Key Name Mismatch (API vs Recommendations Script)
`commanderspellbook_find_combos` MCP tool returns `almost_included` (snake_case). `scripts/generate_recommendations.py` expects `almostIncluded` (camelCase). When saving combos to `/tmp/combos-{id}.json` for the recommendations script, normalize the top-level key: `almost_included` → `almostIncluded`.
- Source: session 4d43917b, 2026-03-27

### Pre-Existing Test Gaps — card-metadata.json Missing Entries
Some cards in deck.json files are absent from `data/card-metadata.json`, causing test failures. Known gap: `High-Society Hunter` in eternal-harvest. These failures are pre-existing and unrelated to deck swap work — simulation tests should still pass even when per-deck metadata tests fail for those cards. Check whether a test failure existed before your change before treating it as a regression.
- Source: session 8b5634a5, 2026-04-07

### Playwright + Vite Preview Host Binding
**Symptom:** Playwright E2E tests time out against `http://127.0.0.1:4173` even though `npm run preview` appears to start.
**Root cause:** Vite preview binds to `localhost` / IPv6 `::1` by default, not `127.0.0.1`. `playwright.config.ts` targets `http://127.0.0.1:4173` — a different interface.
**Fix:** Add `--host 127.0.0.1` to the preview npm script in `web/package.json`: `"preview": "vite preview --host 127.0.0.1"`. Commit `5de51ca`.
- Source: session a4d0d123, 2026-05-05

### Scryfall CORS in Headless Browser
Scryfall image/card fuzzy fetches throw CORS errors in headless Playwright environments. Cannot verify live Scryfall image loading in E2E tests. Do build-level checks (tsc, vitest) to confirm card cache logic; skip headless Scryfall image assertions.
- Source: session a5bf6822, 2026-05-05

### Shopping "Clear All" Reverts to First Deck (DEC-172)
**Symptom**: Clicking "None" or clearing selection always re-selects the first deck.
**Root cause**: `Shopping.tsx` useEffect depended on `[decks, selected.size]`. When the user clears (`selected.size → 0`), the effect re-fires and re-initializes with `decks[0]`.
**Fix**: Replace size-dependent dep with a `useRef(false)` one-shot guard. See patterns.md → "One-Shot useEffect with useRef Guard".
- Source: session 097ce61d, 2026-05-06

### Manifest Section Undercounts Cards (DEC-174)
**Symptom**: Manifest section shows fewer than 100 cards even though deck.json sums to 99 (+ commander = 100).
**Root cause**: `Decklist.tsx` used `g.cards.length` — counts unique entries, not copies. Multi-copy entries (`{name:'Plains', quantity:7}`) counted as 1.
**Fix**: Use `cardCount(cs) = cs.reduce((n, c) => n + (c.quantity ?? 1), 0)` for all card-count display sites (deck total, per-group badges). Same fix also needed in `normalize.ts` role grouping and curve/func aggregation.
- Source: session 01f8b283, 2026-05-06
