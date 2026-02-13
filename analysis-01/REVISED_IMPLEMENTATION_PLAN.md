# Revised Implementation Plan: Codebase Review Fixes

**Date:** 2026-02-10
**Target:** `index.html` (6,375 lines — single-file vanilla JS app)
**Source:** `CODEBASE_REVIEW.md` (22 findings) + `REVIEW_FINDINGS.md` (24 review issues)

This plan supersedes the original `IMPLEMENTATION_PLAN.md`. It incorporates all corrections identified by the three-reviewer audit.

---

## Key Changes from Original Plan

| # | Original Problem | Revision |
|---|-----------------|----------|
| F1 | `highlightMatch()` XSS bypass not addressed | Added to Phase 4 — escape text before `<mark>` wrapping |
| F2 | `--text-muted` contrast insufficient for actual usage | Increased to `#a0a0b0` (≥4.5:1) |
| F3 | `javascript:` URL injection in `href` attributes | Added `sanitizeUrl()` utility to Phase 1 |
| F4 | `mouseout` delegation bug with child elements | Fixed all `mouseout` handlers to use `e.relatedTarget` |
| F5 | Broken `aria-labelledby` on existing modals | Added fixes to Phase 5 |
| F6 | Bracket info modal missing dialog role | Added ARIA attributes to Phase 5 |
| F7 | `aria-labelledby` IDs mismatched with actual headings | Corrected to use existing `*-header` IDs |
| F8 | TiltEffect memory leak on re-render | Added cleanup to Phase 6 |
| F10 | `<nav>` semantically wrong for view toggle | Changed to `role="tablist"` pattern |
| F11 | Heading hierarchy fix ineffective | Changed to actual `<h2>` fix |
| F12 | `aria-haspopup` contradicts menu role removal | Removed `aria-haspopup` from trigger |
| F13 | `prefers-reduced-motion` still incomplete | Added catch-all rule |
| F14 | FocusTrap doesn't trap with zero focusable elements | Added `preventDefault()` for empty case |
| F17/F24 | Ranking `onerror` handlers inconsistent | Added to Phase 5 |
| F19 | `escapeHtml()` returns raw `null`/`undefined` | Fixed non-string handling |
| F20 | `strategyOverview` should use `textContent` | Changed from `innerHTML` |

---

## Constraints (unchanged)

- App must remain a single file (no splitting CSS/JS out)
- Zoom prevention code must NOT be changed
- All changes backward-compatible with existing precon JSON data
- Each phase leaves the app fully functional
- M3 (single-file 240KB architecture) excluded per constraint

---

## Dependency Graph

```
Phase 1 (Foundation utilities: escapeHtml, sanitizeUrl, FocusTrap, announceStatus)
  ├── Phase 2 (CSS: contrast, transitions, will-change, reduced-motion, print)
  ├── Phase 3 (HTML: semantic landmarks, focus outlines, noscript, headings)
  ├── Phase 4 (Security: escapeHtml + sanitizeUrl on all innerHTML/href sites)
  ├── Phase 5 (Accessibility: focus traps, ARIA fixes, dialog roles, inline handlers)
  ├── Phase 6 (Performance: event delegation + TiltEffect cleanup)
  └── Phase 7 (UI/UX: touch targets, mobile preview, localStorage, ARIA live, API dedup)
```

Phases 2–7 depend on Phase 1 but are independent of each other.
Recommended order: 1 → 2+3 (parallel) → 4 → 5 → 6 → 7.

---

## Phase 1: Foundation Utilities

**Issues addressed:** Prerequisites for C1, H1, H3, L3, plus new F1, F3, F14, F19
**Complexity:** ~80 new lines
**Insert location:** After `trackEvent()` function (line 3678), before `// === STATE ===` (line 3680)

### Change 1.1 — `escapeHtml()` utility (REVISED)

**Insert after line 3678:**

```javascript
// === SECURITY: HTML ESCAPING ===
function escapeHtml(str) {
  if (typeof str !== 'string') return String(str ?? '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
```

**Change from original:** Non-string inputs now return `String(str ?? '')` instead of the raw value. This prevents "null" or "undefined" from appearing in the DOM if a JSON field is missing.

### Change 1.2 — `sanitizeUrl()` utility (NEW)

**Insert after `escapeHtml()`:**

```javascript
// === SECURITY: URL SANITIZATION ===
function sanitizeUrl(url) {
  if (typeof url !== 'string') return '#';
  const trimmed = url.trim();
  if (trimmed.startsWith('https://') || trimmed.startsWith('http://')) {
    return escapeHtml(trimmed);
  }
  return '#';
}
```

**Why this is needed:** `escapeHtml()` does not prevent `javascript:` protocol injection in `href` attributes. This function whitelists only `http(s)` protocols.

### Change 1.3 — `FocusTrap` class (REVISED)

**Insert after `sanitizeUrl()`:**

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
    if (focusable.length === 0) {
      e.preventDefault(); // Prevent focus from escaping empty container
      return;
    }
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

**Change from original:** Added `e.preventDefault()` when `focusable.length === 0` so the trap actually prevents focus from escaping when modal content hasn't loaded yet.

### Change 1.4 — `announceStatus()` helper (REVISED)

**Insert after `FocusTrap`:**

```javascript
// === ACCESSIBILITY: STATUS ANNOUNCEMENTS ===
function announceStatus(message) {
  const el = document.getElementById('status-announcement');
  if (el) {
    el.textContent = '';
    setTimeout(() => { el.textContent = message; }, 200);
  }
}
```

**Change from original:** Increased timeout from 100ms to 200ms for better JAWS compatibility.

### Phase 1 — Verification

1. `escapeHtml('<script>alert(1)</script>')` → `&lt;script&gt;alert(1)&lt;/script&gt;`
2. `escapeHtml(null)` → `""` (empty string, not "null")
3. `escapeHtml(42)` → `"42"` (string)
4. `sanitizeUrl('javascript:alert(1)')` → `"#"`
5. `sanitizeUrl('https://example.com')` → `"https://example.com"`
6. `new FocusTrap(document.body)` → constructs without error
7. App functions identically to before

---

## Phase 2: CSS-Only Fixes

**Issues addressed:** C2, H2, M1, M2, M7, M8, L5, plus F2, F13, F15
**Complexity:** ~55 line edits

### Change 2.1 — Fix text contrast (C2, M7) (REVISED)

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
Contrast: `#a0a0b0` on `#1a1a2e` = ~4.7:1 (passes WCAG AA).

**Line 22 — muted text (REVISED — increased from original):**
```css
/* BEFORE */ --text-muted: #555;
/* AFTER  */ --text-muted: #a0a0b0;
```

**Change from original:** The original plan proposed `#8a8a9a` (~3.5:1) which fails WCAG AA for normal text. Since `--text-muted` is used for card names, footer text, price data, and source attributions (all 0.75–0.85rem normal text), it must meet the 4.5:1 AA threshold. Setting it to the same value as `--text-secondary` ensures compliance. If the visual design requires differentiation between secondary and muted, use `#9a9ab0` (~4.2:1) as a minimum, but ~4.5:1 is safer.

### Change 2.2 — Replace `transition: all` with explicit properties (M1)

**No changes from original plan.** All 13 replacements verified correct. (Note: the count is 13, not 14 as originally stated.)

See original plan for full list of replacements at lines 207, 230, 475, 972, 996, 1125, 1829, 1983, 2006, 2167, 2179, 2307, 2675.

### Change 2.3 — Move `will-change` to interaction states (H2)

**No changes from original plan.** The timing consideration (F15) is acceptable — modern browsers handle `will-change` synchronously in practice, and the fallback (transform without GPU promotion) works with at most single-frame jank.

See original plan for full list: lines 1462, 1467, 1477, 1482, 1488, 1492, 2815, 2849.

### Change 2.4 — Complete `prefers-reduced-motion` coverage (M2) (REVISED)

**Add inside the existing `@media (prefers-reduced-motion: reduce)` block (after line 1535):**

```css
/* Catch-all: disable all non-essential transitions and animations */
*, *::before, *::after {
  transition-duration: 0.01ms !important;
  animation-duration: 0.01ms !important;
}
```

**Change from original:** Replaced the 3 individual animation overrides with a catch-all rule. This covers the 3 previously identified animations (starPulse, synergyPulse, skeleton-loading) PLUS all remaining transitions on buttons, tabs, chips, toggles, etc. that the original plan left uncovered. Using `0.01ms` instead of `0ms` avoids issues with some browsers that treat `0ms` as "no transition" differently from "instant transition."

### Change 2.5 — Print improvements (M8, L5)

**No changes from original plan.** See original for `break-inside: avoid` and print-specific overrides.

### Phase 2 — Verification

1. **Contrast:** Verify `#a0a0b0` on `#1a1a2e` = ≥4.5:1 using WebAIM Contrast Checker
2. **Muted text:** Verify footer text, ranking sources, cut card names, price data are all readable
3. **Transitions:** Hover over elements in DevTools Performance panel — no layout events from transitions
4. **will-change:** DevTools Layers panel — cards at rest not promoted, promoted on hover
5. **Reduced motion:** Emulate `prefers-reduced-motion: reduce` — ALL animations and transitions should be instant (not just the 3 originally listed)
6. **Print:** File → Print Preview — card groups don't split, no dark shadows

---

## Phase 3: HTML Semantics and Focus Outlines

**Issues addressed:** H4, H5, L2, L4, plus F7, F10, F11
**Complexity:** ~35 line edits

### Change 3.1 — Add semantic landmarks (H4) (REVISED)

**View toggle — use `role="tablist"` instead of `<nav>` (REVISED):**

```html
<!-- BEFORE -->
<div class="view-toggle" id="view-toggle">
  <button class="view-toggle-btn active" data-view="guides">Upgrade Guides</button>
  <button class="view-toggle-btn" data-view="rankings">Creator Rankings</button>
</div>

<!-- AFTER -->
<div class="view-toggle" id="view-toggle" role="tablist" aria-label="View selection">
  <button class="view-toggle-btn active" data-view="guides" role="tab" aria-selected="true">Upgrade Guides</button>
  <button class="view-toggle-btn" data-view="rankings" role="tab" aria-selected="false">Creator Rankings</button>
</div>
```

**Change from original:** Replaced `<nav>` wrapper with `role="tablist"` + `role="tab"` + `aria-selected` directly on the existing elements. The view toggle is a tab pattern (switching between two views), not navigation. `<nav>` would mislead screen reader users.

**JS addition** — In the view toggle click handler, update `aria-selected`:
```javascript
// When switching views, update aria-selected on both buttons
document.querySelectorAll('.view-toggle-btn').forEach(btn => {
  btn.setAttribute('aria-selected', btn.dataset.view === view ? 'true' : 'false');
});
```

**`<main>` element** — Same as original plan. Change `<div class="main-content">` to `<main class="main-content">`.

**Guide sections with correct `aria-labelledby` IDs (REVISED):**

| Line | Change to | `aria-labelledby` |
|------|-----------|-------------------|
| ~3313 | `<section class="guide-section adds" aria-labelledby="adds-header">` | Uses existing `id="adds-header"` |
| ~3382 | `<section class="guide-section cuts" aria-labelledby="cuts-header">` | Uses existing `id="cuts-header"` |
| ~3401 | `<section class="guide-section synergies" aria-labelledby="synergies-header">` | **Add** `id="synergies-header"` to heading |
| ~3431 | `<section class="guide-section deck-stats" aria-labelledby="stats-header">` | **Add** `id="stats-header"` to heading |
| ~3476 | `<section class="guide-section decklist" aria-labelledby="decklist-header">` | **Add** `id="decklist-header"` to heading |

**Change from original:** Uses existing `*-header` IDs where they exist. Only adds new IDs where missing. All use consistent `-header` suffix.

### Change 3.2 — Fix heading hierarchy (L4) (REVISED)

**BEFORE (line 3205):**
```html
<h3 id="commander-name"></h3>
```

**AFTER:**
```html
<h2 id="commander-name"></h2>
```

**Change from original:** The original plan wrapped in a `<section aria-label>` to "sidestep" the heading jump. This doesn't work — browsers/assistive technology don't implement the HTML5 outline algorithm. The correct fix is to change the `<h3>` to `<h2>`, which is the natural level after the `<h1>` page title.

**CSS impact:** Check if any selectors target `h3#commander-name` specifically. If so, update them to `h2#commander-name` (or better, just `#commander-name`).

### Change 3.3 — Fix incomplete focus outlines (H5)

**No changes from original plan.** Add `:focus-visible` for `select`, `.filter-select`, and `.search-input`.

### Change 3.4 — Add `<noscript>` fallback (L2)

**No changes from original plan.**

### Phase 3 — Verification

1. **Tablist:** Use screen reader — view toggle should announce as "tab, 1 of 2" etc.
2. **aria-selected:** Switch views — verify `aria-selected` toggles correctly on both buttons
3. **Landmarks:** axe DevTools — verify `<main>`, `<section>` landmarks appear
4. **aria-labelledby:** Inspect each section — verify IDs match actual heading elements
5. **Headings:** Run Lighthouse — no heading-level skip warnings
6. **Focus outlines:** Tab to selects and search input — purple outline appears
7. **Noscript:** Disable JS — message appears

---

## Phase 4: XSS Prevention

**Issues addressed:** C1, plus F1, F3, F20, F21
**Complexity:** ~70 line modifications
**Depends on:** Phase 1 (Changes 1.1, 1.2)

### Strategy (REVISED)

Apply `escapeHtml()` to every `${variable}` in innerHTML template literals where the variable originates from JSON data. Apply `sanitizeUrl()` to every JSON-sourced value used in `href` attributes. Do NOT escape:
- Intentional HTML structure (SVG icons, structural divs)
- `<mark>` tags from search highlighting (but escape the text BEFORE marking — see 4f)
- Internal URLs generated by `getCardmarketUrl()` (these are constructed from known-safe base URLs)

### Changes 4a–4d, 4g–4i

**No changes from original plan** for these sections, EXCEPT:

**4e — `strategyOverview` (REVISED):**
```javascript
// BEFORE
document.getElementById('strategy-content').innerHTML = guideContent.strategyOverview;

// AFTER
document.getElementById('strategy-content').textContent = guideContent.strategyOverview;
```

**Change from original:** Uses `textContent` instead of `innerHTML = escapeHtml()`. Since `strategyOverview` is plain text, `textContent` is semantically correct and inherently safe without needing escaping.

**4f — `highlightMatch()` fix (NEW — addresses F1):**

```javascript
// BEFORE
function highlightMatch(text, query) {
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
}

// AFTER
function highlightMatch(text, query) {
  const escaped = escapeHtml(text);
  const escapedQuery = escapeHtml(query);
  const regex = new RegExp(`(${escapedQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return escaped.replace(regex, '<mark>$1</mark>');
}
```

**Why:** The original plan said not to escape `highlightMatch` output (correct — it contains intentional `<mark>` tags). But the input `text` was never escaped, so a malicious card name could inject HTML through the unmatched portions. Escaping the text first, then applying the regex, ensures safety.

**Note:** The query is also escaped so the regex matches against the escaped text correctly. E.g., searching for `&` matches `&amp;` in the escaped text, producing `<mark>&amp;</mark>` which renders as highlighted `&`.

**4i — Shopping list `priceDisplay` (REVISED — addresses F21):**

```javascript
// BEFORE
<td class="price-col">${priceDisplay}</td>

// AFTER
<td class="price-col">${escapeHtml(priceDisplay)}</td>
```

**4j — Rankings `href` attributes (REVISED — addresses F3):**

All `href` attributes that use JSON-sourced URLs must use `sanitizeUrl()` instead of `escapeHtml()`:

```javascript
// BEFORE
<a href="${escapeHtml(precon.sourceUrl)}" ...>

// AFTER
<a href="${sanitizeUrl(precon.sourceUrl)}" ...>
```

Apply `sanitizeUrl()` at lines 6129, 6160, 6188 (and any other `href` using JSON data). Continue using `escapeHtml()` for display text.

### Phase 4 — Verification

1. **XSS test:** Edit a card name in JSON to `Test <img onerror=alert(1) src=x>`. Load precon. Verify literal text, no alert.
2. **Search XSS test:** With the malicious card name, open search (Ctrl+K), type "Test". Verify the match is highlighted but no HTML injection occurs.
3. **URL injection test:** Edit a `sourceUrl` in rankings JSON to `javascript:alert(1)`. Load rankings. Verify the link `href` is `#`, not the javascript URL.
4. **Normal rendering:** Load all precons. No double-escaping (no visible `&amp;`).
5. **Search highlighting:** Search for `&` if any card name contains it. Verify highlighting works.
6. **Cardmarket links:** Click a card — URL works correctly.
7. **Rankings:** All names, prices, reasons, sources render correctly.

---

## Phase 5: Modal Focus Traps and ARIA Fixes

**Issues addressed:** H3, M5, M6, plus F5, F6, F12, F17/F24
**Complexity:** ~70 lines of changes
**Depends on:** Phase 1 (Change 1.3 — `FocusTrap` class)

### Change 5.1 — Wire focus traps into modals (H3)

**Same as original plan** for search modal, mobile preview modal, and bracket info modal. See original plan for `openSearch()`, `closeSearch()`, `showMobilePreview()`, `closeMobilePreview()`, and bracket info modal handlers.

### Change 5.2 — Fix broken `aria-labelledby` on existing modals (NEW — addresses F5)

**Line 3142 — Search modal:**
The search modal has `aria-labelledby="search-title"` but no element with `id="search-title"` exists. Fix:
```html
<!-- Option A: Add id to an existing element inside the modal -->
<!-- If there's a heading or label, add id="search-title" to it -->

<!-- Option B: Switch to aria-label -->
<div class="search-overlay" id="search-modal" role="dialog" aria-modal="true" aria-label="Search cards">
```

**Line 3159 — Mobile preview modal:**
Same issue with `aria-labelledby="mobile-preview-title"`. Fix:
```html
<div class="mobile-preview-modal" id="mobile-preview-modal" role="dialog" aria-modal="true" aria-label="Card preview">
```

### Change 5.3 — Add dialog role to bracket info modal (NEW — addresses F6)

**Line 3230:**
```html
<!-- BEFORE -->
<div class="bracket-info-modal" id="bracket-info-modal">

<!-- AFTER -->
<div class="bracket-info-modal" id="bracket-info-modal" role="dialog" aria-modal="true" aria-label="Commander Bracket System">
```

### Change 5.4 — Fix ARIA pattern for export dropdown (M5) (REVISED — addresses F12)

```html
<!-- BEFORE -->
<button class="export-btn" aria-haspopup="true" aria-expanded="false">Copy Deck List</button>
<div class="export-dropdown-menu" id="copy-deck-menu" role="menu">
  <button class="export-dropdown-item" data-format="plain" role="menuitem">Plain Text</button>
  ...
</div>

<!-- AFTER -->
<button class="export-btn" aria-expanded="false">Copy Deck List</button>
<div class="export-dropdown-menu" id="copy-deck-menu">
  <button class="export-dropdown-item" data-format="plain">Plain Text</button>
  ...
</div>
```

**Change from original:** Removed `role="group"` (which was semantically wrong for a disclosure widget) and removed `aria-haspopup` from the trigger (which is equivalent to `aria-haspopup="menu"` and contradicts removing `role="menu"`). The `aria-expanded` on the trigger is sufficient for a disclosure pattern. The buttons inside are self-describing.

### Change 5.5 — Remove inline onclick handler (M6)

**Same as original plan.** Convert rankings retry button from inline `onclick` to `addEventListener`.

### Change 5.6 — Convert ranking image inline `onerror` handlers (NEW — addresses F17/F24)

**Lines 6116 and 6143** — Replace inline `onerror`:

```javascript
// BEFORE (in renderRankings template)
<img ... onerror="handleRankingImageError(this)" />

// AFTER
<img ... />
```

After the innerHTML assignment for rankings, add:
```javascript
content.querySelectorAll('.ranking-card-image, .value-card-image').forEach(img => {
  img.addEventListener('error', function() { handleRankingImageError(this); });
});
```

### Phase 5 — Verification

1. **Focus traps:** Test all 3 modals — Tab should cycle within modal, Escape should close
2. **Screen reader:** Open each modal — should announce as "dialog" with label
3. **Broken ARIA:** Inspect modals — no dangling `aria-labelledby` references
4. **Export dropdown:** No `role="menu"`, no `aria-haspopup`. `aria-expanded` toggles on click
5. **Rankings retry:** Force error — Retry button works without inline handler
6. **Ranking images:** Load rankings — broken images call `handleRankingImageError` correctly

---

## Phase 6: Event Delegation

**Issues addressed:** H1, plus F4, F8
**Complexity:** ~140 lines (delegation setup + TiltEffect cleanup + removal of per-element loops)

### Change 6.0 — Create `setupDelegatedListeners()` function

**Same structure as original plan**, with the following REVISIONS:

**All `mouseout` handlers REVISED (addresses F4):**

Every `mouseout` handler must use `e.relatedTarget` to verify the mouse actually left the card:

```javascript
// PATTERN — apply to all mouseout handlers
container.addEventListener('mouseout', (e) => {
  const card = e.target.closest('.decklist-card');
  if (card === lastHoveredDeckCard && (!e.relatedTarget || !card.contains(e.relatedTarget))) {
    lastHoveredDeckCard = null;
  }
});
```

Apply this pattern to:
- Decklist cards (section 6.1)
- Guide cards in addGroups/cutGroups (section 6.2)
- Category bars (section 6.7)

### Change 6.1 — TiltEffect cleanup before re-render (NEW — addresses F8)

**Add a tracking array near the state variables (around line 3692):**
```javascript
let activeTiltEffects = [];
```

**Add a cleanup function:**
```javascript
function cleanupTiltEffects() {
  activeTiltEffects.forEach(effect => effect.destroy());
  activeTiltEffects = [];
}
```

**Modify `initializeGuideThumbnailTilt()` to track effects:**
```javascript
function initializeGuideThumbnailTilt() {
  cleanupTiltEffects(); // Destroy previous instances first
  document.querySelectorAll('.guide-card-image').forEach(img => {
    if (!img._tiltInitialized) {
      const effect = new TiltEffect(img, { ... });
      activeTiltEffects.push(effect);
    }
  });
}
```

**Similarly for `initializeRankingCardTilt()`:**
```javascript
function initializeRankingCardTilt() {
  // Clean up previous ranking tilt effects
  activeTiltEffects.forEach(effect => {
    if (effect.element && effect.element.classList.contains('ranking-card-image')) {
      effect.destroy();
    }
  });
  activeTiltEffects = activeTiltEffects.filter(effect =>
    !effect.element || !effect.element.classList.contains('ranking-card-image')
  );

  document.querySelectorAll('.ranking-card-image').forEach(img => {
    if (!img._tiltInitialized) {
      const effect = new TiltEffect(img, { ... });
      activeTiltEffects.push(effect);
    }
  });
}
```

### Removals and simplified `addGuideCardHoverEvents()`

**Same as original plan**, correcting the line range for `addGuideCardHoverEvents()` to extend to line ~5035 (not 5031).

### Phase 6 — Verification

1. **Listener count:** DevTools Elements → `#decklist-content` Event Listeners. Should show 3–4 on container, not hundreds on children.
2. **Card hover:** Hover cards — preview updates. Move mouse within card (over child `<a>` tag) — no flickering or redundant calls.
3. **Card click:** Preview updates. Cardmarket links still open in new tab.
4. **Keyboard:** Tab to cards, Enter/Space — preview updates. Explore mode highlighting works.
5. **Re-render survival:** Switch tiers — hover/click works on new cards without re-attaching.
6. **Memory leak:** Switch tiers 10 times. DevTools Memory → take heap snapshot. Verify no accumulating TiltEffect instances.
7. **All other interactions:** Filter, search, mana curve, category bars — all still functional.

---

## Phase 7: UI/UX Polish and Resilience

**Issues addressed:** H6, H7, L1, L3, M4, plus F16, F18, F23
**Complexity:** ~50 lines

### Change 7.1 — Fix filter chip touch targets (H7)

**Same as original plan.** Increase padding, min-height 44px, `display: inline-flex`.

### Change 7.2 — Fix mobile preview panel (H6) (REVISED — addresses F23)

**Add at the `@media (max-width: 768px)` breakpoint:**

```css
@media (max-width: 768px) {
  .preview-panel {
    display: none;
  }
}
```

**Verification note:** Test at 601px, 700px, and 768px viewports to confirm the fixed panel is hidden and the mobile preview modal activates correctly at these widths. The existing mobile preview modal triggers at ≤768px viewport width, so hiding the fixed panel at the same breakpoint provides a clean handoff.

### Change 7.3 — Protect `localStorage.setItem` (L1)

**Same as original plan.** Wrap in try/catch.

### Change 7.4 — Add ARIA live announcements (L3) (REVISED — addresses F18)

**HTML — After line 3139:**
```html
<div id="status-announcement" aria-live="polite" aria-atomic="true" style="position: absolute; left: -9999px;"></div>
```

**JS calls — Same locations as original plan**, using the revised `announceStatus()` (200ms timeout from Phase 1).

### Change 7.5 — Scryfall API request deduplication (M4) (REVISED — addresses F16)

**Same code as original plan.** The dedup is correct and doesn't introduce race conditions. Note: the existing queue-level cache check already prevents duplicate API calls, so this is a minor optimization (prevents redundant queue entries), not a critical fix.

### Phase 7 — Verification

Same as original plan.

---

## Pre-existing Issue to Address (Bonus)

### Change B1 — `querySelector` CSS-injection safety (P1 from review)

Lines 4936, 4944, and 5364 use `querySelector(`[data-card-name="${cardName}"]`)` where `cardName` could contain quotes. Add `CSS.escape()`:

```javascript
// BEFORE
document.querySelector(`[data-card-name="${cardName}"]`);

// AFTER
document.querySelector(`[data-card-name="${CSS.escape(cardName)}"]`);
```

This can be done in any phase. It's a pre-existing bug not caused by the plan.

---

## Issue-to-Phase Cross-Reference

| ID | Issue | Severity | Phase | Change |
|----|-------|----------|-------|--------|
| C1 | innerHTML XSS vectors | Critical | 4 | 4a–4j |
| C2 | Text contrast WCAG AA | Critical | 2 | 2.1 |
| H1 | No event delegation | High | 6 | 6.0 |
| H2 | will-change permanent | High | 2 | 2.3 |
| H3 | Missing modal focus traps | High | 5 | 5.1 |
| H4 | Missing semantic landmarks | High | 3 | 3.1 |
| H5 | Incomplete focus outlines | High | 3 | 3.3 |
| H6 | Fixed preview on mobile | High | 7 | 7.2 |
| H7 | Filter chip touch targets | High | 7 | 7.1 |
| M1 | transition: all | Medium | 2 | 2.2 |
| M2 | Incomplete reduced-motion | Medium | 2 | 2.4 |
| M3 | Single-file 240KB | Medium | — | Excluded |
| M4 | Scryfall API dedup | Medium | 7 | 7.5 |
| M5 | ARIA menu pattern | Medium | 5 | 5.4 |
| M6 | Inline onclick handler | Medium | 5 | 5.5 |
| M7 | Dark theme contrast | Medium | 2 | 2.1 |
| M8 | Print page-breaks | Medium | 2 | 2.5 |
| L1 | localStorage unprotected | Low | 7 | 7.3 |
| L2 | No noscript fallback | Low | 3 | 3.4 |
| L3 | ARIA live announcements | Low | 7 | 7.4 |
| L4 | Heading hierarchy | Low | 3 | 3.2 |
| L5 | Print visual artifacts | Low | 2 | 2.5 |
| **F1** | **highlightMatch XSS** | **Critical** | **4** | **4f** |
| **F2** | **--text-muted contrast** | **Critical** | **2** | **2.1** |
| **F3** | **javascript: URL injection** | **High** | **1+4** | **1.2, 4j** |
| **F4** | **mouseout delegation bug** | **High** | **6** | **6.0** |
| **F5** | **Broken aria-labelledby** | **High** | **5** | **5.2** |
| **F6** | **Missing dialog role** | **High** | **5** | **5.3** |
| **F7** | **Mismatched section IDs** | **High** | **3** | **3.1** |
| **F8** | **TiltEffect memory leak** | **High** | **6** | **6.1** |
| **F10** | **nav → tablist** | **Medium** | **3** | **3.1** |
| **F11** | **Heading fix ineffective** | **Medium** | **3** | **3.2** |
| **F12** | **aria-haspopup contradiction** | **Medium** | **5** | **5.4** |
| **F13** | **Reduced-motion incomplete** | **Medium** | **2** | **2.4** |
| **F14** | **FocusTrap empty container** | **Medium** | **1** | **1.3** |
| **F17/F24** | **Ranking onerror handlers** | **Medium** | **5** | **5.6** |
| **P1** | **querySelector CSS-injection** | **Low** | **Bonus** | **B1** |

---

## Recommended Execution Order

| Order | Phase | Effort | Can parallelize with |
|-------|-------|--------|---------------------|
| 1st | Phase 1 — Foundation Utilities | ~80 lines | — |
| 2nd | Phase 2 — CSS Fixes | ~55 edits | Phase 3 |
| 2nd | Phase 3 — HTML Semantics | ~35 edits | Phase 2 |
| 3rd | Phase 4 — XSS Prevention | ~70 edits | — |
| 4th | Phase 5 — Focus Traps & ARIA | ~70 lines | — |
| 5th | Phase 6 — Event Delegation | ~140 lines | — |
| 6th | Phase 7 — UI/UX Polish | ~50 lines | — |

**Total estimated changes:** ~500 lines modified/added (up from ~350 in original plan)
**Commits:** 7 (one per phase) + optional bonus commit
