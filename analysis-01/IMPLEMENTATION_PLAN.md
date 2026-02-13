# Implementation Plan: Codebase Review Fixes

**Date:** 2026-02-10
**Target:** `index.html` (6,375 lines — single-file vanilla JS app)
**Source:** `analysis-01/CODEBASE_REVIEW.md` (22 findings)

---

## Context

A multi-agent codebase review identified 22 issues across security, accessibility, performance, and UI/UX in the MTG Precon Upgrader app. This plan describes how to fix all 22 issues in 7 ordered phases, each independently deployable and testable.

**Constraints:**
- App must remain a single file (no splitting CSS/JS out)
- Zoom prevention code (viewport meta + JS gesture handlers) must NOT be changed
- All changes backward-compatible with existing precon JSON data
- Each phase leaves the app fully functional

**Excluded:** M3 (single-file 240KB architecture) — excluded per constraint.

---

## Dependency Graph

```
Phase 1 (Foundation utilities)
  ├── Phase 2 (CSS: contrast, transitions, will-change, reduced-motion, print)
  ├── Phase 3 (HTML: semantic landmarks, focus outlines, noscript, headings)
  ├── Phase 4 (Security: escapeHtml on all innerHTML sites)
  ├── Phase 5 (Accessibility: focus traps, ARIA menu, inline onclick)
  ├── Phase 6 (Performance: event delegation)
  └── Phase 7 (UI/UX: touch targets, mobile preview, localStorage, ARIA live, API dedup)
```

Phases 2–7 depend on Phase 1 but are independent of each other. Recommended order: 1 → 2+3 (parallel) → 4 → 5 → 6 → 7.

---

## Phase 1: Foundation Utilities

**Issues addressed:** Prerequisites for C1, H1, H3, L3
**Complexity:** ~60 new lines
**Insert location:** After `trackEvent()` function (line 3678), before `// === STATE ===` (line 3680)

### Change 1.1 — `escapeHtml()` utility

**Insert after line 3678:**

```javascript
// === SECURITY: HTML ESCAPING ===
function escapeHtml(str) {
  if (typeof str !== 'string') return str;
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
```

**Why this approach:** A simple string-replacement encoder is sufficient because all dynamic data in this app is plain text (card names, descriptions, prices). No intentional HTML is embedded in JSON data fields. The function handles the 5 HTML-significant characters per OWASP recommendations.

### Change 1.2 — `FocusTrap` class

**Insert after `escapeHtml()`:**

```javascript
// === ACCESSIBILITY: FOCUS TRAP ===
class FocusTrap {
  constructor(containerElement) {
    this.container = containerElement;
    this.previouslyFocused = null;
    this.onKeyDown = this.handleKeyDown.bind(this);
  }

  activate() {
    this.previouslyFocused = document.activeElement;
    this.container.addEventListener('keydown', this.onKeyDown);
    const first = this.getFocusableElements()[0];
    if (first) first.focus();
  }

  deactivate() {
    this.container.removeEventListener('keydown', this.onKeyDown);
    if (this.previouslyFocused && this.previouslyFocused.focus) {
      this.previouslyFocused.focus();
    }
  }

  getFocusableElements() {
    return Array.from(this.container.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    ));
  }

  handleKeyDown(e) {
    if (e.key !== 'Tab') return;
    const focusable = this.getFocusableElements();
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }
}
```

**Design rationale:** Follows the same class pattern as the existing `TiltEffect` class (lines 3765–3902) — constructor takes a DOM element, methods for activate/deactivate, event cleanup. The `getFocusableElements()` query runs on each Tab press rather than being cached, so it works with dynamically-added content (like search results inside the search modal).

### Change 1.3 — `announceStatus()` helper

**Insert after `FocusTrap`:**

```javascript
// === ACCESSIBILITY: STATUS ANNOUNCEMENTS ===
function announceStatus(message) {
  const el = document.getElementById('status-announcement');
  if (el) {
    el.textContent = '';
    setTimeout(() => { el.textContent = message; }, 100);
  }
}
```

**Why the setTimeout:** Screen readers may ignore live region updates that happen synchronously (same value → same value). Clearing first, then setting after a microtask, ensures the change is detected.

### Phase 1 — Verification

1. Load the app in browser. Open DevTools console.
2. Run `escapeHtml('<script>alert("xss")</script>')` → should return `&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;`
3. Run `new FocusTrap(document.body)` → should construct without error
4. App should function identically to before (no behavioral changes)

---

## Phase 2: CSS-Only Fixes

**Issues addressed:** C2, H2, M1, M2, M7, M8, L5
**Complexity:** ~45 line edits, all within `<style>` block (lines 12–3135)

### Change 2.1 — Fix text contrast (C2, M7)

**Line 18 — border visibility:**
```css
/* BEFORE */ --border-subtle: #2a2a4a;
/* AFTER  */ --border-subtle: #3a3a5a;
```

**Line 21 — secondary text:**
```css
/* BEFORE */ --text-secondary: #888;
/* AFTER  */ --text-secondary: #a0a0b0;
```
Contrast: `#a0a0b0` on `#1a1a2e` = ~4.7:1 (passes WCAG AA 4.5:1 for normal text).
Contrast: `#a0a0b0` on `#1e2746` = ~4.5:1 (passes WCAG AA).

**Line 22 — muted text:**
```css
/* BEFORE */ --text-muted: #555;
/* AFTER  */ --text-muted: #8a8a9a;
```
Contrast: `#8a8a9a` on `#1a1a2e` = ~3.5:1 (passes WCAG AA for large text 3:1). Used primarily for decorative text, timestamps, and placeholders where 3:1 is acceptable per WCAG 1.4.3.

### Change 2.2 — Replace `transition: all` with explicit properties (M1)

14 instances. Each replacement lists only the properties that actually change on hover/active states for that selector.

**Line 207** — `.bracket-info-icon`:
```css
/* BEFORE */ transition: all 0.2s;
/* AFTER  */ transition: border-color 0.2s, color 0.2s;
```

**Line 230** — `.bracket-segment`:
```css
/* BEFORE */ transition: all 0.3s ease;
/* AFTER  */ transition: opacity 0.3s ease;
```

**Line 475** — `.tab`:
```css
/* BEFORE */ transition: all 0.2s ease;
/* AFTER  */ transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
```

**Line 972** — `.synergy-card-tag` (or the selector at this line):
```css
/* BEFORE */ transition: all 0.15s;
/* AFTER  */ transition: border-color 0.15s, background 0.15s;
```

**Line 996** — `.synergy-explorer-btn`:
```css
/* BEFORE */ transition: all 0.2s;
/* AFTER  */ transition: border-color 0.2s, color 0.2s;
```

**Line 1125** — `.share-btn`:
```css
/* BEFORE */ transition: all 0.2s;
/* AFTER  */ transition: border-color 0.2s, color 0.2s;
```

**Line 1829** — `.export-btn`:
```css
/* BEFORE */ transition: all 0.2s;
/* AFTER  */ transition: border-color 0.2s, color 0.2s, background 0.2s;
```

**Line 1983** — `.filter-chip`:
```css
/* BEFORE */ transition: all 0.15s;
/* AFTER  */ transition: border-color 0.15s, background 0.15s, color 0.15s;
```

**Line 2006** — `.filter-clear`:
```css
/* BEFORE */ transition: all 0.15s;
/* AFTER  */ transition: border-color 0.15s, color 0.15s;
```

**Line 2167** — `.toggle-switch`:
```css
/* BEFORE */ transition: all 0.3s ease;
/* AFTER  */ transition: background 0.3s ease, border-color 0.3s ease;
```

**Line 2179** — `.toggle-switch::after`:
```css
/* BEFORE */ transition: all 0.3s ease;
/* AFTER  */ transition: left 0.3s ease, background 0.3s ease;
```

**Line 2307** — `.print-btn`:
```css
/* BEFORE */ transition: all 0.2s;
/* AFTER  */ transition: border-color 0.2s, color 0.2s;
```

**Line 2675** — `.view-toggle-btn`:
```css
/* BEFORE */ transition: all 0.2s ease;
/* AFTER  */ transition: color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
```

### Change 2.3 — Move `will-change` to interaction states (H2)

Currently `will-change` is on base selectors, permanently promoting elements to GPU layers.

**Line 1462** — `.commander-card-preview`:
```css
/* BEFORE */
.commander-card-preview {
  transform-style: preserve-3d;
  will-change: transform, box-shadow;       /* REMOVE THIS LINE */
  transition: transform var(--tilt-transition-out) cubic-bezier(0.23, 1, 0.32, 1),
              box-shadow var(--tilt-transition-out) cubic-bezier(0.23, 1, 0.32, 1);
}

/* AFTER */
.commander-card-preview {
  transform-style: preserve-3d;
  transition: transform var(--tilt-transition-out) cubic-bezier(0.23, 1, 0.32, 1),
              box-shadow var(--tilt-transition-out) cubic-bezier(0.23, 1, 0.32, 1);
}
```

**Line 1467** — `.commander-card-preview.tilting` — add `will-change`:
```css
/* BEFORE */
.commander-card-preview.tilting {
  transition: none;
}

/* AFTER */
.commander-card-preview.tilting {
  transition: none;
  will-change: transform, box-shadow;
}
```

**Line 1477** — `.preview-image-container img`:
```css
/* Remove will-change: transform, box-shadow; from base selector */
```

**Line 1482** — `.preview-image-container img.tilting`:
```css
/* AFTER */
.preview-image-container img.tilting {
  transition: none;
  will-change: transform, box-shadow;
}
```

**Line 1488** — `.guide-card-image`:
```css
/* Remove will-change: transform; from base selector */
```

**Line 1492** — `.guide-card-image.tilting`:
```css
/* AFTER */
.guide-card-image.tilting {
  transition: none;
  will-change: transform;
}
```

**Line 2815** — `.ranking-card-image`:
```css
/* Remove will-change: transform; from base selector */
/* Add to a new .tilting rule for this class: */
.ranking-card-image.tilting {
  will-change: transform;
}
```

**Line 2849** — `.ranking-hover-preview`:
```css
/* Remove will-change: transform, opacity; from base selector */
/* The .visible state already exists; add will-change there: */
.ranking-hover-preview.visible {
  will-change: transform, opacity;
}
```

### Change 2.4 — Complete `prefers-reduced-motion` coverage (M2)

Three CSS animations are NOT covered by the existing `@media (prefers-reduced-motion: reduce)` block (lines 1520–1536).

**Add inside the existing block, after line 1535:**

```css
.game-changer-star {
  animation: none !important;
}
.synergy-highlight {
  animation: none !important;
}
.skeleton {
  animation: none !important;
}
```

The missing animations are:
- `starPulse` (line 539) — 2s infinite pulse on Game Changer stars
- `synergyPulse` (line 1023) — 1.5s infinite pulse on synergy highlights
- `skeleton-loading` (line 1323) — 1.5s infinite shimmer on loading skeletons

### Change 2.5 — Print improvements (M8, L5)

**Add inside the existing `@media print` block (after line 2400):**

```css
/* Prevent content from breaking across pages */
.card-group,
.synergy-item,
.decklist-category,
.ranking-card {
  break-inside: avoid;
  page-break-inside: avoid;  /* fallback for older browsers */
}

/* Remove dark-theme visual effects in print */
.guide-card,
.ranking-card,
.synergy-card-tag {
  box-shadow: none !important;
  border: 1px solid #ccc !important;
}
```

### Phase 2 — Verification

1. **Contrast:** Open DevTools → computed styles on secondary text elements. Use WebAIM Contrast Checker to verify `#a0a0b0` on `#1a1a2e` = ≥4.5:1.
2. **Transitions:** Hover over buttons/cards in DevTools Performance panel. Verify no layout/paint events from `transition: all` (only color/opacity/transform changes).
3. **will-change:** Open DevTools Layers panel. Cards at rest should NOT show as promoted GPU layers. Hover → layer promoted. Leave → layer removed.
4. **Reduced motion:** In DevTools Rendering tab, check "Emulate CSS media feature prefers-reduced-motion: reduce". Verify: Game Changer stars stop pulsing, synergy highlights stop pulsing, skeleton shimmer freezes.
5. **Print:** File → Print Preview. Verify card groups don't split across pages and no dark box-shadows appear.

---

## Phase 3: HTML Semantics and Focus Outlines

**Issues addressed:** H4, H5, L2, L4
**Complexity:** ~25 line edits (HTML) + ~10 lines (CSS)

### Change 3.1 — Add semantic landmarks (H4)

**Line 3178** — Wrap view toggle in `<nav>`:
```html
<!-- BEFORE -->
<div class="view-toggle" id="view-toggle">

<!-- AFTER -->
<nav aria-label="View navigation">
  <div class="view-toggle" id="view-toggle">
```

And close the `</nav>` after the view toggle's closing `</div>` (around line 3195):
```html
  </div>
</nav>
```

**Line 3302** — Change main content wrapper from `<div>` to `<main>`:
```html
<!-- BEFORE -->
<div class="main-content" id="main-content" style="display: none;">

<!-- AFTER -->
<main class="main-content" id="main-content" style="display: none;">
```

**Line ~3610** — Close with `</main>` instead of `</div>`:
```html
<!-- BEFORE -->
</div> <!-- end main-content -->

<!-- AFTER -->
</main> <!-- end main-content -->
```

**Guide sections** — Change 5 `.guide-section` divs to `<section>`:

| Line | Current | Change to |
|------|---------|-----------|
| ~3313 | `<div class="guide-section adds">` | `<section class="guide-section adds" aria-labelledby="adds-title">` |
| ~3382 | `<div class="guide-section cuts">` | `<section class="guide-section cuts" aria-labelledby="cuts-title">` |
| ~3401 | `<div class="guide-section synergies">` | `<section class="guide-section synergies" aria-labelledby="synergies-title">` |
| ~3431 | `<div class="guide-section deck-stats">` | `<section class="guide-section deck-stats" aria-labelledby="stats-title">` |
| ~3476 | `<div class="guide-section decklist">` | `<section class="guide-section decklist" aria-labelledby="decklist-title">` |

Each section's closing `</div>` becomes `</section>`.

Add `id` attributes to the corresponding `<h2>` elements if not present:
- "What We're Adding" → `id="adds-title"`
- "Why We're Cutting" → `id="cuts-title"`
- "Key Synergies" → `id="synergies-title"`
- "Deck Statistics" → `id="stats-title"`
- "Full Upgraded Deck List" → `id="decklist-title"`

**No CSS impact** — all selectors use class names (`.guide-section`, `.main-content`), not element types.

### Change 3.2 — Fix heading hierarchy (L4)

The `<h3 id="commander-name">` (line 3205) sits under `<h1>` without an `<h2>` in between. Wrap the selector section in a `<section>` with an accessible label:

```html
<!-- Around line 3197 -->
<section class="selector-section" aria-label="Precon selection">
```

This gives screen readers a landmark to navigate to, sidestepping the heading-level jump. The `<h3>` for commander name is acceptable within a labeled section.

### Change 3.3 — Fix incomplete focus outlines (H5)

Three elements remove outlines without `:focus-visible` recovery.

**After line 136** (after `select:hover, select:focus { outline: none; }`):
```css
select:focus-visible {
  outline: 2px solid var(--accent-purple);
  outline-offset: 2px;
}
```

**After line 1950** (after `.filter-select:hover, .filter-select:focus { outline: none; }`):
```css
.filter-select:focus-visible {
  outline: 2px solid var(--accent-purple);
  outline-offset: 2px;
}
```

**After line 2066** (after `.search-input { outline: none; }`):
```css
.search-input:focus-visible {
  outline: 2px solid var(--accent-purple);
  outline-offset: 2px;
}
```

This matches the existing pattern used at lines 2622–2639 for other interactive elements.

### Change 3.4 — Add `<noscript>` fallback (L2)

**After line 3137** (`<body>`), before the aria-live region:

```html
<noscript>
  <div style="padding: 40px; text-align: center; color: #e0e0e0; font-family: sans-serif;">
    <h1>MTG Precon Upgrade Guides</h1>
    <p>This application requires JavaScript to display upgrade guides. Please enable JavaScript in your browser settings.</p>
  </div>
</noscript>
```

### Phase 3 — Verification

1. **Landmarks:** Chrome DevTools → Accessibility tab (or axe DevTools extension). Verify `<nav>`, `<main>`, `<section>` landmarks appear in the accessibility tree.
2. **Focus outlines:** Tab to a `<select>` element and the search input. Verify 2px purple outline appears on `:focus-visible`.
3. **Noscript:** Disable JavaScript in browser settings (or DevTools). Verify the noscript message appears on a dark background.
4. **Headings:** Run Lighthouse accessibility audit. Verify no heading-level skip warnings (or if any remain, they are inside labeled sections).

---

## Phase 4: XSS Prevention via `escapeHtml()`

**Issues addressed:** C1
**Complexity:** ~60 line modifications across 20+ innerHTML call sites
**Depends on:** Phase 1 (Change 1.1)

### Strategy

Apply `escapeHtml()` to every `${variable}` in innerHTML template literals where the variable originates from JSON data. Do NOT escape:
- Intentional HTML structure (SVG icons, structural divs)
- `<mark>` tags from search highlighting
- URLs (these go through `encodeURIComponent()` separately)

### Important: `data-*` attribute safety

Card names appear in both `data-card-name` attributes and display text. `escapeHtml()` converts `"` to `&quot;`, which is correct for HTML attributes. When read back via `element.dataset.cardName`, the browser automatically decodes the HTML entities, returning the original string. So event delegation and `showCardPreview()` calls work unmodified.

### Call site modifications by function

#### 4a. `renderDeckList()` (lines 4650–4701)

**Line 4655** — Commander card:
```javascript
// BEFORE
html += `<div class="decklist-card commander" data-card-name="${currentPrecon.commander}"><a href="${getCardmarketUrl(currentPrecon.commander)}" target="_blank" rel="noopener noreferrer">${currentPrecon.commander}</a></div>`;

// AFTER
html += `<div class="decklist-card commander" data-card-name="${escapeHtml(currentPrecon.commander)}"><a href="${getCardmarketUrl(currentPrecon.commander)}" target="_blank" rel="noopener noreferrer">${escapeHtml(currentPrecon.commander)}</a></div>`;
```

**Line 4657** — Alternate commander (same pattern):
```javascript
// Escape both data-card-name and link text for currentPrecon.alternateCommander
```

**Line 4677** — Deck cards in loop:
```javascript
// BEFORE
html += `<div class="decklist-card${addedClass}" data-card-name="${card.name}">${quantity}<a href="${cardmarketUrl}" target="_blank" rel="noopener noreferrer">${card.name}</a></div>`;

// AFTER
html += `<div class="decklist-card${addedClass}" data-card-name="${escapeHtml(card.name)}">${quantity}<a href="${cardmarketUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(card.name)}</a></div>`;
```

**Lines 4688–4690** — "Other" cards: same pattern as line 4677.

#### 4b. `createGuideCardHtml()` (lines 4865–4903)

This function renders cut and add cards. Multiple variables need escaping:

**Line 4876** — Card name in link/text:
```javascript
// BEFORE
? `<a href="${getCardmarketUrl(cardName)}" target="_blank" rel="noopener noreferrer">${cardName}</a>`
: cardName;

// AFTER
? `<a href="${getCardmarketUrl(cardName)}" target="_blank" rel="noopener noreferrer">${escapeHtml(cardName)}</a>`
: escapeHtml(cardName);
```

**Line 4884** — Substitute tradeoff in `title` attribute:
```javascript
// BEFORE
<div class="card-substitute" title="${sub.tradeoff}">

// AFTER
<div class="card-substitute" title="${escapeHtml(sub.tradeoff)}">
```

**Line 4886** — Substitute name:
```javascript
// BEFORE
<span class="card-substitute-name" data-card-name="${sub.name}">${sub.name}</span>

// AFTER
<span class="card-substitute-name" data-card-name="${escapeHtml(sub.name)}">${escapeHtml(sub.name)}</span>
```

**Line 4887** — Substitute price:
```javascript
// BEFORE
<span class="card-substitute-price">${sub.price}</span>

// AFTER
<span class="card-substitute-price">${escapeHtml(sub.price)}</span>
```

**Line 4893** — Guide card wrapper:
```javascript
// BEFORE
<div class="guide-card" data-card-name="${cardName}" tabindex="0" role="button" aria-label="View ${cardName}">

// AFTER
<div class="guide-card" data-card-name="${escapeHtml(cardName)}" tabindex="0" role="button" aria-label="View ${escapeHtml(cardName)}">
```

**Line 4894** — Image alt text:
```javascript
// BEFORE
<img class="guide-card-image" src="${imageUrl}" alt="${cardName}" loading="lazy" />

// AFTER
<img class="guide-card-image" src="${imageUrl}" alt="${escapeHtml(cardName)}" loading="lazy" />
```

**Line 4897** — Reason text:
```javascript
// BEFORE
<div class="guide-card-reason">${reason}</div>

// AFTER
<div class="guide-card-reason">${escapeHtml(reason)}</div>
```

#### 4c. `renderCutGroups()` / `renderAddGroups()` (lines 4799–4857)

These pass `category.name` and `category.description` into template literals:

```javascript
// Escape in the category header template:
<div class="card-group-name">${escapeHtml(category.name)}</div>
<div class="card-group-description">${escapeHtml(category.description)}</div>
```

#### 4d. `renderSynergies()` (lines 4960–4977)

**Line 4967** — Card tags:
```javascript
// BEFORE
`<span class="synergy-card-tag" data-card-name="${cardName}" tabindex="0" role="button">${cardName}</span>`

// AFTER
`<span class="synergy-card-tag" data-card-name="${escapeHtml(cardName)}" tabindex="0" role="button">${escapeHtml(cardName)}</span>`
```

**Line 4972** — Synergy title:
```javascript
// BEFORE
<div class="synergy-title">${synergy.title}</div>

// AFTER
<div class="synergy-title">${escapeHtml(synergy.title)}</div>
```

**Line 4974** — Synergy description:
```javascript
// BEFORE
<div class="synergy-description">${synergy.description}</div>

// AFTER
<div class="synergy-description">${escapeHtml(synergy.description)}</div>
```

#### 4e. Strategy overview (line 4775)

```javascript
// BEFORE
document.getElementById('strategy-content').innerHTML = guideContent.strategyOverview;

// AFTER
document.getElementById('strategy-content').innerHTML = escapeHtml(guideContent.strategyOverview);
```

This is safe because `strategyOverview` is plain text in all existing JSON files (verified: `data/precons/*/deck.json`).

#### 4f. `updateSearchResults()` (lines 5301–5342)

The `result.name` goes into a `data-card` attribute. The `highlightMatch()` function wraps matches in `<mark>` tags, which must NOT be escaped. Solution: escape the name for the attribute, but pass the original name to `highlightMatch()` (which handles its own regex escaping):

**Lines 5308, 5321, 5334** — all three groups follow this pattern:
```javascript
// BEFORE
html += `<div class="search-result" data-index="${searchResults.indexOf(result)}" data-card="${result.name}">
  <span class="search-result-name">${highlighted}</span>

// AFTER
html += `<div class="search-result" data-index="${searchResults.indexOf(result)}" data-card="${escapeHtml(result.name)}">
  <span class="search-result-name">${highlighted}</span>
```

The `highlighted` variable (from `highlightMatch()`) intentionally contains `<mark>` tags and should NOT be escaped. The `highlightMatch()` function (line 5354) already regex-escapes the query string for safety.

#### 4g. `renderComparisonView()` (lines 5400–5431)

**Lines 5405, 5408, 5417, 5420** — all comparison cards:
```javascript
// BEFORE
fullHtml += `<div class="comparison-card unique-full" data-card-name="${name}">${name}</div>`;

// AFTER
fullHtml += `<div class="comparison-card unique-full" data-card-name="${escapeHtml(name)}">${escapeHtml(name)}</div>`;
```

Apply to all 4 loops (onlyInFull, shared-for-full, onlyInMidrange, shared-for-midrange).

**Line 5430** — Price diff:
```javascript
// BEFORE
`Full Upgrade: ${fullUpgrade.cost} | Mid-Range: ${midrangeUpgrade.cost} | ...`

// AFTER
`Full Upgrade: ${escapeHtml(fullUpgrade.cost)} | Mid-Range: ${escapeHtml(midrangeUpgrade.cost)} | ...`
```

#### 4h. `renderFilteredDeckList()` (lines 5534–5643)

Same pattern as `renderDeckList()`. Escape `currentPrecon.commander`, `currentPrecon.alternateCommander`, and `card.name` in all template literals:

- **Line 5573** — Commander: escape `data-card-name` and link text
- **Line 5575** — Alternate commander: same
- **Line 5595** — Cards in type-grouped loop: escape `data-card-name` and link text
- **Line 5607** — "Other" cards: same
- **Line 5623** — Cards in flat list: escape `data-card-name` and link text

#### 4i. `generateShoppingList()` (lines 5788–5812)

**Line 5807:**
```javascript
// BEFORE
<td class="card-col">${card.name}</td>

// AFTER
<td class="card-col">${escapeHtml(card.name)}</td>
```

#### 4j. `renderRankings()` (lines 6095–6238)

**Line 6111** — Reasons list:
```javascript
// BEFORE
const reasonsHtml = precon.reasons.map(r => `<li>${r}</li>`).join('');

// AFTER
const reasonsHtml = precon.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('');
```

**Lines 6116, 6143** — Image alt text:
```javascript
alt="${escapeHtml(precon.commander)}"
```

**Line 6119** — Precon name:
```javascript
<h3 class="ranking-card-name">${escapeHtml(precon.name)}</h3>
```

**Line 6120** — Price:
```javascript
<span class="ranking-card-price">${escapeHtml(precon.price)}</span>
```

**Line 6123** — Set:
```javascript
<span class="ranking-card-set">${escapeHtml(precon.set)}</span>
```

**Line 6124** — Commander:
```javascript
<span class="ranking-card-commander">${escapeHtml(precon.commander)}</span>
```

**Line 6129** — Source link text:
```javascript
<a href="${escapeHtml(precon.sourceUrl)}" ...>${escapeHtml(precon.source)}</a>
```

**Lines 6136–6165** — Best Value cards: same pattern. Escape `precon.name`, `precon.price`, `precon.valueRatio`, `precon.singleValue`, `precon.set`, `precon.commander`, `highlights` items, `precon.source`, `precon.sourceUrl`.

**Lines 6139:**
```javascript
// BEFORE
const highlightsHtml = precon.highlights.map(h => `<li>${h}</li>`).join('');

// AFTER
const highlightsHtml = precon.highlights.map(h => `<li>${escapeHtml(h)}</li>`).join('');
```

**Lines 6171–6182** — Set recommendations:
```javascript
${escapeHtml(data.setRecommendations.best2024.name)}
${escapeHtml(data.setRecommendations.best2024.reason)}
${escapeHtml(data.setRecommendations.bestQuality.name)}
${escapeHtml(data.setRecommendations.bestQuality.caveat)}
${escapeHtml(data.setRecommendations.sleeper2025.name)}
${escapeHtml(data.setRecommendations.sleeper2025.reason)}
```

**Lines 6193–6196** — Sources:
```javascript
<div class="source-channel">${escapeHtml(source.channel)}</div>
<div class="source-video">${escapeHtml(source.video)}</div>
<div class="source-views">${escapeHtml(source.views)} views</div>
```

**Line 6236** — Last updated:
```javascript
Last updated: ${escapeHtml(data.lastUpdated)}
```

### Phase 4 — Verification

1. **XSS test:** Temporarily edit `data/precons/eldrazi-unbound/deck.json` — change a card name to `Test <img onerror=alert(1) src=x>`. Load the precon. Verify the name renders as literal text, no alert fires. Revert the JSON.
2. **Normal rendering:** Load all 3 precons. Verify all card names, reasons, synergies, prices display correctly with no double-escaping (no `&amp;` visible in normal text).
3. **Search highlighting:** Open search (Ctrl+K), type a partial card name. Verify matches are highlighted with `<mark>` tags (not escaped).
4. **Cardmarket links:** Click a card's Cardmarket link. Verify the URL works correctly (escapeHtml does not affect `href` values passed through `getCardmarketUrl()`).
5. **Rankings view:** Switch to Creator Rankings. Verify all precon names, prices, reasons, sources render correctly.

---

## Phase 5: Modal Focus Traps and ARIA Fixes

**Issues addressed:** H3, M5, M6
**Complexity:** ~55 lines of JS changes + 4 HTML attribute changes
**Depends on:** Phase 1 (Change 1.2 — `FocusTrap` class)

### Change 5.1 — Wire focus traps into modals (H3)

**Add near line 3692** (state variables section):
```javascript
let searchModalTrap = null;
let mobilePreviewTrap = null;
let bracketInfoTrap = null;
```

**Modify `openSearch()` at line 5240:**
```javascript
// BEFORE
function openSearch() {
  const modal = document.getElementById('search-modal');
  const input = document.getElementById('search-input');
  modal.classList.add('open');
  input.value = '';
  input.focus();
  updateSearchResults('');
}

// AFTER
function openSearch() {
  const modal = document.getElementById('search-modal');
  const input = document.getElementById('search-input');
  modal.classList.add('open');
  input.value = '';
  updateSearchResults('');
  if (!searchModalTrap) {
    searchModalTrap = new FocusTrap(modal.querySelector('.search-container'));
  }
  searchModalTrap.activate();
  input.focus(); // Focus input after trap activates
}
```

**Modify `closeSearch()` at line 5249:**
```javascript
// BEFORE
function closeSearch() {
  document.getElementById('search-modal').classList.remove('open');
  selectedResultIndex = -1;
}

// AFTER
function closeSearch() {
  document.getElementById('search-modal').classList.remove('open');
  selectedResultIndex = -1;
  if (searchModalTrap) searchModalTrap.deactivate();
}
```

**Modify `showMobilePreview()` at line 5682:**
```javascript
// Add at the end of the function, after modal.classList.add('open'):
if (!mobilePreviewTrap) {
  mobilePreviewTrap = new FocusTrap(modal.querySelector('.mobile-preview-content'));
}
mobilePreviewTrap.activate();
```

**Modify `closeMobilePreview()` at line 5697:**
```javascript
// BEFORE
function closeMobilePreview() {
  document.getElementById('mobile-preview-modal').classList.remove('open');
}

// AFTER
function closeMobilePreview() {
  document.getElementById('mobile-preview-modal').classList.remove('open');
  if (mobilePreviewTrap) mobilePreviewTrap.deactivate();
}
```

**Modify bracket info modal handlers at lines 5100–5112:**
```javascript
// BEFORE
document.querySelector('.bracket-info-icon').addEventListener('click', () => {
  document.getElementById('bracket-info-modal').classList.add('visible');
});

document.getElementById('bracket-info-modal-close').addEventListener('click', () => {
  document.getElementById('bracket-info-modal').classList.remove('visible');
});

document.getElementById('bracket-info-modal').addEventListener('click', (e) => {
  if (e.target.id === 'bracket-info-modal') {
    e.target.classList.remove('visible');
  }
});

// AFTER
document.querySelector('.bracket-info-icon').addEventListener('click', () => {
  const modal = document.getElementById('bracket-info-modal');
  modal.classList.add('visible');
  if (!bracketInfoTrap) {
    bracketInfoTrap = new FocusTrap(modal.querySelector('.bracket-info-modal-content'));
  }
  bracketInfoTrap.activate();
});

document.getElementById('bracket-info-modal-close').addEventListener('click', () => {
  document.getElementById('bracket-info-modal').classList.remove('visible');
  if (bracketInfoTrap) bracketInfoTrap.deactivate();
});

document.getElementById('bracket-info-modal').addEventListener('click', (e) => {
  if (e.target.id === 'bracket-info-modal') {
    e.target.classList.remove('visible');
    if (bracketInfoTrap) bracketInfoTrap.deactivate();
  }
});
```

### Change 5.2 — Fix ARIA menu pattern (M5)

The export dropdown uses `role="menu"` and `role="menuitem"` but lacks the required keyboard interaction pattern (arrow keys, Home/End, focus management). The simplest fix is to remove the menu roles and use a simpler disclosed-list pattern.

**Line 3499** — Change export dropdown menu:
```html
<!-- BEFORE -->
<div class="export-dropdown-menu" id="copy-deck-menu" role="menu">
  <button class="export-dropdown-item" data-format="plain" role="menuitem">Plain Text</button>
  <button class="export-dropdown-item" data-format="arena" role="menuitem">Arena/MTGO</button>
  <button class="export-dropdown-item" data-format="moxfield" role="menuitem">Moxfield Import</button>
  <button class="export-dropdown-item" data-format="archidekt" role="menuitem">Archidekt Import</button>
</div>

<!-- AFTER -->
<div class="export-dropdown-menu" id="copy-deck-menu" role="group" aria-label="Export format options">
  <button class="export-dropdown-item" data-format="plain">Plain Text</button>
  <button class="export-dropdown-item" data-format="arena">Arena/MTGO</button>
  <button class="export-dropdown-item" data-format="moxfield">Moxfield Import</button>
  <button class="export-dropdown-item" data-format="archidekt">Archidekt Import</button>
</div>
```

The trigger button (around line 3489) already has `aria-haspopup="true"` and `aria-expanded="false"`, which remain valid for a generic disclosed container.

### Change 5.3 — Remove inline onclick handler (M6)

**Line 6098–6103** — In `renderRankings()` error state:
```javascript
// BEFORE
content.innerHTML = `
  <div class="rankings-error">
    <p>Failed to load rankings data.</p>
    <button onclick="loadAndRenderRankings()">Retry</button>
  </div>
`;

// AFTER
content.innerHTML = `
  <div class="rankings-error">
    <p>Failed to load rankings data.</p>
    <button id="rankings-retry-btn">Retry</button>
  </div>
`;
content.querySelector('#rankings-retry-btn')?.addEventListener('click', loadAndRenderRankings);
```

### Phase 5 — Verification

1. **Search modal focus trap:** Press Ctrl+K to open search. Press Tab repeatedly — focus should cycle between the search input and the ESC shortcut text. Tab should NOT escape to background elements. Press ESC — focus should return to whatever was focused before opening.
2. **Mobile preview focus trap:** On a mobile-width viewport (≤768px), tap a card. The preview modal should trap focus. Close button should return focus.
3. **Bracket info focus trap:** Click the "i" icon next to the bracket bar. Tab should stay within the modal. Click the X or backdrop to close — focus returns.
4. **Export dropdown:** Inspect with DevTools. Verify no `role="menu"` or `role="menuitem"` attributes exist. Verify the group has `aria-label`.
5. **Rankings retry:** Temporarily rename `data/creator-rankings.json` to force an error. Verify the Retry button works without inline `onclick`. Rename the file back.

---

## Phase 6: Event Delegation

**Issues addressed:** H1
**Complexity:** ~120 lines (new delegation setup function + removal of ~80 lines of per-element loops)

### Strategy

Create a `setupDelegatedListeners()` function called once from `initializeApp()`. Use `mouseover` (which bubbles) instead of `mouseenter` (which doesn't) with a `lastHovered` guard to prevent redundant `showCardPreview()` calls.

Key insight: since all rendering uses innerHTML replacement, per-element listeners are destroyed on every re-render and must be re-attached. Delegated listeners on parent containers survive innerHTML replacement.

### Change 6.0 — Create `setupDelegatedListeners()` function

**Insert before `initializeApp()` (around line 6320):**

```javascript
// === DELEGATED EVENT LISTENERS ===
function setupDelegatedListeners() {
  const decklistContent = document.getElementById('decklist-content');
  const addGroups = document.getElementById('add-groups');
  const cutGroups = document.getElementById('cut-groups');
  const synergiesList = document.getElementById('synergies-list');
  const comparisonView = document.getElementById('comparison-view');
  const searchResults = document.getElementById('search-results');
  const manaCurveChart = document.getElementById('mana-curve-chart');
  const categoryBars = document.getElementById('category-bars');
  const tooltip = document.getElementById('category-tooltip');

  // --- 6.1: Decklist cards ---
  let lastHoveredDeckCard = null;
  decklistContent.addEventListener('mouseover', (e) => {
    const card = e.target.closest('.decklist-card');
    if (card && card !== lastHoveredDeckCard) {
      lastHoveredDeckCard = card;
      showCardPreview(card.dataset.cardName);
    }
  });
  decklistContent.addEventListener('mouseout', (e) => {
    if (e.target.closest('.decklist-card') === lastHoveredDeckCard) {
      lastHoveredDeckCard = null;
    }
  });
  decklistContent.addEventListener('click', (e) => {
    if (e.target.closest('a')) return; // Preserve Cardmarket link clicks
    const card = e.target.closest('.decklist-card');
    if (card) showCardPreview(card.dataset.cardName);
  });
  decklistContent.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const card = e.target.closest('.decklist-card');
      if (card) {
        e.preventDefault();
        showCardPreview(card.dataset.cardName);
      }
    }
  });

  // --- 6.2: Guide cards (adds + cuts) ---
  [addGroups, cutGroups].forEach(container => {
    let lastHoveredGuide = null;
    container.addEventListener('mouseover', (e) => {
      const sub = e.target.closest('.card-substitute-name');
      if (sub) {
        showCardPreview(sub.dataset.cardName);
        return;
      }
      const card = e.target.closest('.guide-card');
      if (card && card !== lastHoveredGuide) {
        lastHoveredGuide = card;
        showCardPreview(card.dataset.cardName);
      }
    });
    container.addEventListener('mouseout', (e) => {
      if (e.target.closest('.guide-card') === lastHoveredGuide) {
        lastHoveredGuide = null;
      }
    });
    container.addEventListener('click', (e) => {
      const sub = e.target.closest('.card-substitute-name');
      if (sub) {
        e.stopPropagation();
        showCardPreview(sub.dataset.cardName);
        return;
      }
      if (e.target.closest('a')) return; // Preserve Cardmarket links
      const card = e.target.closest('.guide-card');
      if (card) {
        showCardPreview(card.dataset.cardName);
        if (exploreModeActive && synergyGraph.has(card.dataset.cardName)) {
          highlightSynergyCards(card.dataset.cardName);
        }
      }
    });
    container.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        const card = e.target.closest('.guide-card');
        if (card) {
          e.preventDefault();
          showCardPreview(card.dataset.cardName);
          if (exploreModeActive && synergyGraph.has(card.dataset.cardName)) {
            highlightSynergyCards(card.dataset.cardName);
          }
        }
      }
    });
  });

  // --- 6.3: Synergy card tags ---
  synergiesList.addEventListener('mouseover', (e) => {
    const tag = e.target.closest('.synergy-card-tag');
    if (tag) showCardPreview(tag.dataset.cardName);
  });
  synergiesList.addEventListener('click', (e) => {
    const tag = e.target.closest('.synergy-card-tag');
    if (tag) {
      showCardPreview(tag.dataset.cardName);
      if (exploreModeActive) {
        e.stopPropagation();
        highlightSynergyCards(tag.dataset.cardName);
      }
    }
  });
  synergiesList.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const tag = e.target.closest('.synergy-card-tag');
      if (tag) {
        e.preventDefault();
        showCardPreview(tag.dataset.cardName);
        if (exploreModeActive) {
          highlightSynergyCards(tag.dataset.cardName);
        }
      }
    }
  });

  // --- 6.4: Comparison cards ---
  comparisonView.addEventListener('mouseover', (e) => {
    const card = e.target.closest('.comparison-card');
    if (card) showCardPreview(card.dataset.cardName);
  });
  comparisonView.addEventListener('click', (e) => {
    const card = e.target.closest('.comparison-card');
    if (card) showCardPreview(card.dataset.cardName);
  });

  // --- 6.5: Search results ---
  searchResults.addEventListener('click', (e) => {
    const result = e.target.closest('.search-result');
    if (result) selectSearchResult(result.dataset.card);
  });

  // --- 6.6: Mana curve bars ---
  manaCurveChart.addEventListener('click', (e) => {
    const bar = e.target.closest('.mana-bar');
    if (bar) {
      const cards = bar.dataset.cards.split(', ').filter(c => c);
      if (cards.length > 0) showCardPreview(cards[0]);
    }
  });

  // --- 6.7: Category bars ---
  categoryBars.addEventListener('mouseover', (e) => {
    const item = e.target.closest('.category-bar-item');
    if (item && tooltip) {
      const category = item.dataset.category;
      const cards = item.dataset.cards.split('|').filter(c => c);
      const config = CATEGORY_CONFIG.find(c => c.id === category);
      if (cards.length > 0) {
        tooltip.querySelector('.category-tooltip-title').textContent = `${config.name} (${cards.length})`;
        tooltip.querySelector('.category-tooltip-cards').textContent = cards.slice(0, 10).join(', ') +
          (cards.length > 10 ? `, +${cards.length - 10} more` : '');
        const rect = item.getBoundingClientRect();
        tooltip.style.left = `${rect.right + 10}px`;
        tooltip.style.top = `${rect.top}px`;
        tooltip.classList.add('visible');
      }
    }
  });
  categoryBars.addEventListener('mouseout', (e) => {
    const item = e.target.closest('.category-bar-item');
    if (item && tooltip) {
      tooltip.classList.remove('visible');
    }
  });
  categoryBars.addEventListener('click', (e) => {
    const item = e.target.closest('.category-bar-item');
    if (item) {
      const cards = item.dataset.cards.split('|').filter(c => c);
      if (cards.length > 0) showCardPreview(cards[0]);
    }
  });
}
```

### Removals — delete per-element listener loops

After adding the delegated function, **remove** these code blocks:

| Lines | Function | What to remove |
|-------|----------|---------------|
| 4698–4701 | `renderDeckList()` | `document.querySelectorAll('.decklist-card').forEach(card => { ... });` |
| 4980–4998 | `renderSynergies()` | `document.querySelectorAll('.synergy-card-tag').forEach(tag => { ... });` |
| 5002–5031 | `addGuideCardHoverEvents()` | The `.guide-card` and `.card-substitute-name` forEach loops. Keep only `initializeGuideThumbnailTilt()` call. |
| 5345–5349 | `updateSearchResults()` | `resultsContainer.querySelectorAll('.search-result').forEach(...)` |
| 5434–5439 | `renderComparisonView()` | `document.querySelectorAll('.comparison-card').forEach(...)` |
| 5633–5642 | `renderFilteredDeckList()` | `document.querySelectorAll('.decklist-card').forEach(...)` |
| 4179–4186 | `renderManaCurve()` | `chart.querySelectorAll('.mana-bar').forEach(...)` |
| 4217–4248 | `renderCategoryBars()` | `container.querySelectorAll('.category-bar-item').forEach(...)` |

### Simplified `addGuideCardHoverEvents()`

```javascript
// BEFORE (lines 5001-5035): Full forEach with 3 event types per card
function addGuideCardHoverEvents() {
  document.querySelectorAll('.guide-card').forEach(card => { ... });
  document.querySelectorAll('.card-substitute-name').forEach(sub => { ... });
  initializeGuideThumbnailTilt();
}

// AFTER: Only tilt initialization remains
function addGuideCardHoverEvents() {
  initializeGuideThumbnailTilt();
}
```

### Call `setupDelegatedListeners()` from `initializeApp()`

**Add at line ~6325** (early in `initializeApp()`, before any content renders):
```javascript
setupDelegatedListeners();
```

### Phase 6 — Verification

1. **Listener count:** Open DevTools → Elements → select `#decklist-content` → Event Listeners panel. Should show 3–4 listeners on the container, NOT hundreds on child `.decklist-card` elements.
2. **Card hover:** Hover over cards in deck list, guide sections, synergy tags, comparison view. Card preview should update correctly.
3. **Card click:** Click cards. Preview should update. Cardmarket links should still open in new tab.
4. **Keyboard:** Tab to guide cards, press Enter/Space. Preview should update. Explore mode synergy highlighting should work.
5. **Re-render survival:** Switch upgrade tiers (Full ↔ Mid-Range). After re-render, hover/click on new cards. Should work without re-attaching listeners.
6. **Filtered deck list:** Apply a filter (e.g., "Creature" type). Hover over filtered cards. Should work.
7. **Search results:** Open search, type a query, click a result. Should navigate to the card.
8. **Mana curve:** Click a mana bar. Should show first card at that CMC.
9. **Category bars:** Hover over a category bar. Tooltip should appear with card names. Click should show preview.

---

## Phase 7: UI/UX Polish and Resilience

**Issues addressed:** H6, H7, L1, L3, M4
**Complexity:** ~45 lines across CSS, HTML, and JS

### Change 7.1 — Fix filter chip touch targets (H7)

**Lines 1975–1984** — Replace filter chip styles:

```css
/* BEFORE */
.filter-chip {
  padding: 4px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  font-size: 0.75rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;  /* Note: already replaced in Phase 2 */
}

/* AFTER */
.filter-chip {
  padding: 8px 14px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;  /* From Phase 2 */
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}
```

Changes: `padding` 4px→8px vertical, 10px→14px horizontal; `font-size` 0.75rem→0.8rem; added `min-height: 44px`, `display: inline-flex`, `align-items: center` for WCAG touch target compliance.

### Change 7.2 — Fix mobile preview panel (H6)

**Verify line ~1209 (max-width: 768px breakpoint):**

The preview panel should be hidden on mobile viewports. If a `display: none` rule already exists at `@media (max-width: 768px)`, keep it. If not, add:

```css
@media (max-width: 768px) {
  .preview-panel {
    display: none;
  }
}
```

The mobile preview modal (line 3159, triggered by `showMobilePreview()` at line 5682) already handles card preview on tap for viewports ≤768px, so hiding the fixed panel is a clean handoff.

### Change 7.3 — Protect `localStorage.setItem` (L1)

**Line 5661–5668** — Wrap in try/catch:

```javascript
// BEFORE
function savePreferences() {
  const prefs = {
    lastPrecon: currentPreconId,
    lastTier: currentUpgrade,
    filters: filterState
  };
  localStorage.setItem('mtg-upgrade-prefs', JSON.stringify(prefs));
}

// AFTER
function savePreferences() {
  const prefs = {
    lastPrecon: currentPreconId,
    lastTier: currentUpgrade,
    filters: filterState
  };
  try {
    localStorage.setItem('mtg-upgrade-prefs', JSON.stringify(prefs));
  } catch (e) {
    // Storage may be full, disabled, or unavailable in private browsing
  }
}
```

### Change 7.4 — Add ARIA live announcements for dynamic updates (L3)

**HTML — After line 3139** (after the existing `#preview-announcement`):
```html
<div id="status-announcement" aria-live="polite" aria-atomic="true" style="position: absolute; left: -9999px;"></div>
```

Uses the same visually-hidden pattern as the existing `#preview-announcement` (line 2642–2645).

**JS — Add `announceStatus()` calls in 3 places:**

In `selectPrecon()` — after content loads successfully (around line 4584):
```javascript
announceStatus(`Loaded ${currentPrecon.name} upgrade guide`);
```

In `applyFilters()` — at the end (around line 5531):
```javascript
const filtered = /* the filtered cards array */;
announceStatus(`Showing ${filtered.length} cards`);
```

In `switchView()` — after view switch (around line 6260):
```javascript
announceStatus(view === 'rankings' ? 'Showing Creator Rankings' : 'Showing Upgrade Guides');
```

### Change 7.5 — Add Scryfall API request deduplication (M4)

**After line 4253** (after `const cardMetadataCache = new Map();`):
```javascript
const inFlightRequests = new Map();
```

**Modify `fetchCardMetadata()` (lines 4283–4294):**
```javascript
// BEFORE
async function fetchCardMetadata(cardName) {
  if (cardMetadataCache.has(cardName)) {
    return cardMetadataCache.get(cardName);
  }
  return new Promise((resolve) => {
    requestQueue.push({ cardName, resolve });
    processQueue();
  });
}

// AFTER
async function fetchCardMetadata(cardName) {
  if (cardMetadataCache.has(cardName)) {
    return cardMetadataCache.get(cardName);
  }
  if (inFlightRequests.has(cardName)) {
    return inFlightRequests.get(cardName);
  }
  const promise = new Promise((resolve) => {
    requestQueue.push({ cardName, resolve });
    processQueue();
  });
  inFlightRequests.set(cardName, promise);
  promise.finally(() => inFlightRequests.delete(cardName));
  return promise;
}
```

**Why `.finally()` instead of `.then()`:** Ensures the in-flight entry is cleaned up whether the promise resolves or rejects.

### Phase 7 — Verification

1. **Touch targets:** Inspect filter chips with DevTools. Each should be at least 44px tall. Test on a phone or mobile emulator — tapping should feel natural.
2. **Mobile preview:** Set viewport to 375px width. The fixed preview panel should be hidden. Tap a card name — full-screen modal should open.
3. **localStorage:** In DevTools Application tab, clear storage and use a private/incognito window. Switch precons and tiers. Verify no console errors.
4. **ARIA announcements:** Enable VoiceOver (macOS) or NVDA (Windows). Switch precons — hear "Loaded [name] upgrade guide". Apply a filter — hear "Showing N cards". Switch to rankings view — hear "Showing Creator Rankings".
5. **API dedup:** Open DevTools Network tab. Rapidly hover the same card name 5 times quickly. Verify only 1 Scryfall request fires (not 5).

---

## Issue-to-Phase Cross-Reference

| ID | Issue | Severity | Phase | Change |
|----|-------|----------|-------|--------|
| C1 | innerHTML XSS vectors | Critical | 4 | 4a–4j |
| C2 | Text contrast WCAG AA | Critical | 2 | 2.1 |
| H1 | No event delegation | High | 6 | 6.0–6.7 |
| H2 | will-change permanent | High | 2 | 2.3 |
| H3 | Missing modal focus traps | High | 5 | 5.1 |
| H4 | Missing semantic landmarks | High | 3 | 3.1 |
| H5 | Incomplete focus outlines | High | 3 | 3.3 |
| H6 | Fixed preview on mobile | High | 7 | 7.2 |
| H7 | Filter chip touch targets | High | 7 | 7.1 |
| M1 | transition: all | Medium | 2 | 2.2 |
| M2 | Incomplete reduced-motion | Medium | 2 | 2.4 |
| M3 | Single-file 240KB | Medium | — | Excluded (constraint) |
| M4 | Scryfall API dedup | Medium | 7 | 7.5 |
| M5 | ARIA menu pattern | Medium | 5 | 5.2 |
| M6 | Inline onclick handler | Medium | 5 | 5.3 |
| M7 | Dark theme contrast | Medium | 2 | 2.1 |
| M8 | Print page-breaks | Medium | 2 | 2.5 |
| L1 | localStorage unprotected | Low | 7 | 7.3 |
| L2 | No noscript fallback | Low | 3 | 3.4 |
| L3 | ARIA live announcements | Low | 7 | 7.4 |
| L4 | Heading hierarchy | Low | 3 | 3.2 |
| L5 | Print visual artifacts | Low | 2 | 2.5 |

---

## Recommended Execution Order

| Order | Phase | Effort | Can parallelize with |
|-------|-------|--------|---------------------|
| 1st | Phase 1 — Foundation Utilities | ~60 lines | — |
| 2nd | Phase 2 — CSS Fixes | ~45 edits | Phase 3 |
| 2nd | Phase 3 — HTML Semantics | ~35 edits | Phase 2 |
| 3rd | Phase 4 — XSS Prevention | ~60 edits | — |
| 4th | Phase 5 — Focus Traps & ARIA | ~55 lines | — |
| 5th | Phase 6 — Event Delegation | ~120 lines | — |
| 6th | Phase 7 — UI/UX Polish | ~45 lines | — |

**Total estimated changes:** ~350 lines modified/added
**Commits:** 7 (one per phase)
