# Patterns

### Paperclip Heartbeat — Blocked Task Dedup
Before working a `blocked` task: fetch comment thread. If your most recent comment was a blocked-status update AND no new comments from other agents/users have arrived since — skip entirely. Don't checkout, don't post. Only re-engage when new context exists (new comment, status change, or mention-triggered wake).
- Source: session a2964006, 2026-03-20

### Paperclip — Always Checkout Before PATCH/Comment
Must call `POST /api/issues/{id}/checkout` before any status PATCH or comment POST. Skipping causes "Issue run ownership conflict" 403 error.
- Source: session a8e6cc42, 2026-03-20

### Paperclip — Plan Documents via API
Plans go in issue documents (key: `plan`), not inline descriptions. Always fetch current document revision first and pass `baseRevisionId` on PUT — omitting it when the document already exists will error.
```
GET /api/issues/{id}/documents/plan  → get baseRevisionId
PUT /api/issues/{id}/documents/plan  → update with baseRevisionId
```
- Source: session a8e6cc42, 2026-03-20

### Paperclip — Stale executionRunId Conflict on Checkout
When checkout returns a conflict due to a queued run with stale `executionRunId`, the workaround is to do the work under the parent task context and update subtask status after completing.
- Source: session a8e6cc42, 2026-03-20

### Paper MCP — Efficient Artboard Building
Use `duplicate_nodes` for repeated elements (card rows, grid cells) to reduce tool call count. Cloning an existing artboard and restyling is faster than rebuilding Direction B from scratch (~65 calls vs 120+). Download card images locally before building artboards — external URLs may not load reliably.
- Source: session 01f7504e, 2026-03-20

### CSS Section Header with Horizontal Rule (B Design)
B design section headers use green color + flex `::after` pseudo-element as a horizontal rule:
```css
.guide-section-title {
  color: var(--accent-green);
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  gap: 12px;
}
.guide-section-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-subtle);
}
```
- Source: session a8e6cc42, 2026-03-20

### Paperclip — `instructionsFilePath` Must Be Absolute Path
For `claude_local` adapter agents, `instructionsFilePath` must be an absolute path. A relative path (e.g. `agents/design-eng/AGENTS.md`) causes ENOENT at startup — the adapter doesn't resolve it against `cwd`. Use the dedicated `PATCH /api/agents/{agentId}/instructions-path` endpoint to set or update the path after creation.
- Source: session 23c72808, 2026-03-20

### Paperclip — Release Endpoint Requires Being Current Assignee
`POST /api/issues/{issueId}/release` fails with "Only assignee can release issue" if the caller is no longer the assignee (e.g. you already reassigned via PATCH first). This is not a real error when reassignment already succeeded — the task is correctly assigned to the new owner.
- Source: session 23c72808, 2026-03-20

### Scryfall Lazy Loading — `data-scryfall-src` Pattern
For any bulk image render (gallery grids, card lists), set `data-scryfall-src="<url>"` on `<img>` elements instead of `src`. Then call `observeScryfallImages(containerEl)` after setting innerHTML. IntersectionObserver watches each image and moves the URL to `src` only when it enters the viewport. Cache hit → set `src` directly, no queue. Miss → enqueue for throttled fetch. This prevents 429 rate-limit errors from Scryfall.
- Source: session a074338b, 2026-03-20

### Pencil MCP — `.pen` Files Are App-Managed
Pencil `.pen` files are managed internally by the Pencil editor application and do not appear as readable/writable files on the filesystem. All design operations must go through `mcp__pencil__*` tools (`batch_design`, `get_editor_state`, `export_nodes`, etc.). To persist design work for git: use `mcp__pencil__export_nodes` to export artboards as PNGs, then commit those exports to `designs/exports/`.
- Source: session d3c6539f, 2026-03-20

### Pencil MCP — Placeholder Workflow for Artboards
When building a complex artboard incrementally, set `placeholder: true` on the frame node during construction. This prevents layout calculation issues while children are being added. Remove the placeholder flag (`placeholder: false`) only when the artboard is complete and ready for review/export.
- Source: session d3c6539f, 2026-03-20

### Shopping List UX Conventions
Established design decisions for the shopping list view:
- CTA label: **"Import owned cards"** (not "Upload")
- Layout: flat styles (no rounded card containers for sections), full-width dashed-border upload bar, rounded-pill sort buttons
- No redundant "Shopping List" header — tab label already names the view
- Moxfield/Archidekt export buttons removed — only "Copy Buy List" (plain text format)
- Summary bar uses `border-top` with `--deck-accent` theme color
- Source: session a2964006, 2026-03-20; session a07e6b41, 2026-03-20

### Card Hover Preview — Dedup Pattern (lastHoveredXxx)
To prevent flicker when hovering child elements of a card container, use a `lastHoveredXxx` variable. Only call `showCardPreview(cardName)` when the card name differs from the last call. Example (guide cards handler uses `lastHoveredGuideCard`). The upgrade paths section omitted this dedup initially, causing the preview image to rebuild on every child-element mouseover.
- Source: session 92527ddd, 2026-03-23

### Local-First Image Loading Helpers
Three helper functions wrap the local-first + Scryfall fallback pattern in `app.js`:
- `cardImgAttr(name, version)` — returns `src` attr string (local path or Scryfall URL)
- `setImgWithFallback(imgEl, name, version)` — sets src + adds onerror fallback to Scryfall
- `loadBgImageWithFallback(el, name, version)` — sets CSS background-image with same fallback logic
A global `window.onerror` handler catches 404s from missing local images and swaps in Scryfall URLs automatically.
- Source: session 90f9b134, 2026-03-22

### Upgrade Paths — Interactive Card References
Synergy card names mentioned in the rationale text and the swap-for card in `.upgrade-swap-cut` should be rendered as `<span data-card-name="Card Name" class="card-name">` elements rather than plain text. The `mouseover` event on `.upgrade-paths-content` delegates to `closest('[data-card-name]')`, prioritizing the innermost element. This enables hover preview of synergy/swap targets distinct from the main recommended card.
- Source: session 92527ddd, 2026-03-23

### Card Swap Checklist — All Files to Update
When swapping one card for another in a deck, update ALL of the following:
1. `deck.json` — decklist array (remove/add card object)
2. `deck.json` — categories array (remove from old category, add to new)
3. `deck.json` — tokens array (if the removed card produced unique tokens)
4. `deck.json` — highlights/adds (update or add entry for new card)
5. `deck.json` — synergies (remove old synergies, add new card's synergies)
6. `deck.json` — win conditions (if applicable)
7. `data/card-metadata.json` — add entry for new card if absent
8. Re-run simulation script and export results
9. Verify total card count is exactly 99 after edits
- Source: session d7bac209, 2026-04-07; session 8b5634a5, 2026-04-07

### Deck Swap — Partial Board Approval
Board may approve some proposed swaps and decline others in the same batch (e.g., approve Inspiring Statuary, decline Academy Manufactor for ownership). Declined-for-ownership cards move to **defer** status (not reject), with a note naming which deck holds the copy. The approved swap(s) land in a single commit with sources attribution; declined cards remain in the defer list for a future review when a second copy is acquired.
- Source: session 556a72ac, 2026-05-04

### Deck Swap — Ownership Constraint Rule
When the board declines a proposed include because the physical card is already in another deck (no second copy owned), classify it as **defer** (not reject) with annotation: "owned copy in {deck-name}, no second copy purchased." This preserves the card as a future candidate without counting it as a bad recommendation. The defer list is revisited if a second copy is acquired.
- Source: session 556a72ac, 2026-05-04

### `prefers-reduced-motion` Coverage — Scrying Pool CSS
The base `prefers-reduced-motion` block in `web/src/styles/styles.css` (initially at line 1175) covered only `.gv1-cardhover`. Must also suppress: hover `transform: translateY()` on `.gv1-scry-card-selectable` hand cards, and `height` transition on histogram bars. Failing to cover these caused a11y gaps found in DEC-156 QA pass (commit `cf2d822`).
- Source: session a4d0d123, 2026-05-05

### One-Shot `useEffect` with `useRef` Guard
For effects that should fire only once on first data arrival (and not re-fire when state later changes), use a ref guard instead of a size/length dep:
```ts
const didInitRef = useRef(false);
useEffect(() => {
  if (didInitRef.current) return;
  if (!data.length) return;
  didInitRef.current = true;
  // initialize once
}, [data]);
```
Adding `selected.size` to the dep array instead re-triggers the effect on clear — root cause of DEC-172 Shopping "clear all" regression.
- Source: session 097ce61d, 2026-05-06

### `cardCount()` Helper — Quantity-Aware Card Counting
Any time you need a deck card count, use a quantity-aware sum — never `.length`:
```ts
const cardCount = (cs: DeckCard[]) => cs.reduce((n, c) => n + (c.quantity ?? 1), 0);
```
`.length` undercounts when entries have `quantity > 1` (e.g., basics). Always sum `.quantity ?? 1` for deck size; `.length` is wrong whenever the deck includes multi-copy entries.
- Source: session 01f8b283, 2026-05-06
