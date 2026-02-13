# MTG Precon Upgrader — Codebase Review

**Date:** 2026-02-10
**Scope:** Performance, UI/UX Design, Accessibility & Web Standards
**File reviewed:** `index.html` (6,375 lines — all CSS, HTML, and JS in a single file)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Findings Summary](#findings-summary)
3. [Critical Issues](#critical-issues)
4. [High Priority Issues](#high-priority-issues)
5. [Medium Priority Issues](#medium-priority-issues)
6. [Low Priority Issues](#low-priority-issues)
7. [Things Done Well](#things-done-well)

---

## Architecture Overview

The entire application lives in a single `index.html` file containing:
- **CSS** (~3,135 lines): Inline styles including dark theme, responsive breakpoints, animations, print styles
- **HTML** (~490 lines): Body structure with modals, selector, bracket visualization, guide sections, rankings view
- **JavaScript** (~2,750 lines): Vanilla JS SPA with Scryfall API integration, state management, DOM rendering

No build tools, frameworks, bundlers, or minification. Static hosting with JSON data files.

---

## Findings Summary

| Severity | Count | Category Breakdown |
|----------|-------|--------------------|
| Critical | 2 | Security (1), Accessibility (1) |
| High | 7 | Performance (2), Accessibility (3), UI/UX (2) |
| Medium | 8 | Performance (3), Accessibility (3), UI/UX (2) |
| Low | 5 | Accessibility (2), Performance (1), UI/UX (2) |
| **Total** | **22** | |

---

## Critical Issues

### C1. innerHTML XSS Vectors
**Category:** Security
**Lines:** 4176, 4213, 4695, 4775, 4800, 4824, 4965, 5342, 5410, 5422, 5612, 5626, 5788, 6200 (and more)

There are **20+ innerHTML assignments** where card names, commander names, synergy descriptions, and price data from external JSON files are inserted directly into the DOM without any HTML encoding or sanitization.

**Example pattern:**
```javascript
// Line 4695 — card names from currentPrecon.baseDeck injected via innerHTML
decklistContent.innerHTML = html;

// Line 4800 — cut card data from JSON
cutGroups.innerHTML = categories.map(...)

// Line 6200 — rankings data including precon names, commanders
content.innerHTML = `...`
```

**Risk:** If any JSON data source is compromised or contains HTML/script content, arbitrary code execution is possible. The app currently relies entirely on data being clean.

**Fix:** Create a text-encoding utility (e.g., `escapeHtml()`) and apply it to all dynamic string values before insertion, or switch to `textContent` / DOM creation APIs for user-facing text.

---

### C2. Text Contrast Failures (WCAG AA)
**Category:** Accessibility
**Lines:** 21–22 (CSS variable definitions)

The secondary and muted text colors fail WCAG AA contrast requirements against all dark backgrounds used in the app.

| Variable | Value | Background | Contrast Ratio | WCAG AA (4.5:1) |
|----------|-------|-----------|----------------|-----------------|
| `--text-secondary` | `#888` | `--bg-primary` (#1a1a2e) | ~3.2:1 | FAIL |
| `--text-muted` | `#555` | `--bg-primary` (#1a1a2e) | ~1.9:1 | FAIL |
| `--text-secondary` | `#888` | `--bg-surface` (#1e2746) | ~3.1:1 | FAIL |
| `--text-muted` | `#555` | `--bg-surface` (#1e2746) | ~1.8:1 | FAIL |

These colors are used extensively for subtitles, metadata, timestamps, helper text, and placeholders throughout the UI.

**Fix:** Increase `--text-secondary` to at least `#a0a0a0` (~4.6:1 on #1a1a2e) and `--text-muted` to at least `#8a8a8a` (~3.3:1 minimum, or higher for AA compliance on body text).

---

## High Priority Issues

### H1. No Event Delegation for Card Elements
**Category:** Performance
**Lines:** 4698–4700, 4980–4989, 5003–5013, 5435–5436, 5634–5636, 3813–3815

Approximately **40–50 individual event listeners** are attached per-element inside rendering loops. Each card in the deck list gets 2–3 listeners (mouseenter, click, sometimes keydown). The TiltEffect class adds 3 listeners per card element (mousemove, mouseleave, mouseenter).

For a 100-card deck, this means 200–500+ listeners created and destroyed on each re-render.

**Fix:** Use event delegation — attach a single listener on the parent container and use `event.target.closest('.decklist-card')` to identify which card was interacted with. For TiltEffect, consider a single `mousemove` listener on the container with hit-testing.

---

### H2. `will-change` Permanently Applied
**Category:** Performance
**Lines:** 1462, 1477, 1488, 2815, 2849

Five `will-change` declarations are on **base selectors** (not `:hover`), permanently promoting elements to GPU compositor layers:

```css
/* Line 1462 — always active, not just on hover */
.commander-card-preview {
  will-change: transform, box-shadow;
}

/* Line 1488 */
.guide-card-image {
  will-change: transform;
}
```

Each promoted layer consumes GPU memory. With multiple card images visible, this can add up.

**Fix:** Move `will-change` to the `:hover` or `.tilting` state so layers are only promoted during interaction, or toggle via JavaScript just before animation starts.

---

### H3. Missing Modal Focus Traps
**Category:** Accessibility
**Lines:** 3142–3156 (search modal), 3159–3165 (mobile preview modal)

Both modals declare `role="dialog"` and `aria-modal="true"` but have **no JavaScript focus trap logic**. Users navigating with keyboard can Tab out of the modal into background content.

No `trapFocus`, `focusableElements`, or similar functions exist in the JavaScript.

**Fix:** Implement a focus trap that:
1. On modal open, saves the previously focused element
2. Constrains Tab/Shift+Tab to focusable elements within the modal
3. On modal close, restores focus to the saved element

---

### H4. Missing Semantic HTML Landmarks
**Category:** Accessibility
**Lines:** 3137–3630 (HTML body)

The HTML body uses only `<div>` elements for structural sections. Present semantic elements:
- `<header>` (line 3173) — present
- `<footer>` (line 3626) — present

Missing semantic elements:
- `<main>` — no main landmark wrapping primary content
- `<nav>` — no navigation landmark for precon selector / view toggle
- `<section>` — no section elements for guide sections, deck list, etc.
- `<article>` — no article elements for individual card groups or guide content

Screen readers rely on landmarks to provide page navigation shortcuts. Without `<main>`, users cannot quickly jump to the primary content.

**Fix:** Wrap the primary content area in `<main>`, use `<nav>` for the view toggle / precon selector, and use `<section>` with appropriate headings for each guide panel.

---

### H5. Incomplete Focus Outline Recovery
**Category:** Accessibility
**Lines:** 135, 1949, 2065, 2630

The code applies `outline: none` on interactive elements, then restores outlines via `:focus-visible` (lines 2633–2639). This is the correct modern pattern for the 7 elements covered at line 2630.

However, **two elements are not recovered**:
- `select:hover, select:focus` (line 135) — removes outline without `:focus-visible` fallback
- `.search-input` (line 2065) — removes outline without `:focus-visible` fallback

**Fix:** Add `:focus-visible` rules for `select` and `.search-input` that restore a visible outline, or remove the `outline: none` on those elements.

---

### H6. Fixed Preview Panel on Small Viewports
**Category:** UI/UX
**Lines:** 518–528 (CSS media query for max-width: 600px)

On mobile viewports, the card preview panel switches to `position: fixed` anchored at bottom-right:
```css
.preview-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
  width: 200px;
}
```

This permanently occupies screen real estate and can overlap interactive content (buttons, card lists) on smaller devices. There is no way for the user to dismiss or minimize it.

**Fix:** Consider making the preview a tap-to-show overlay, or add a collapse/dismiss control. The existing mobile preview modal (line 3159) is a better pattern — consider using it exclusively on mobile and removing the fixed panel.

---

### H7. Filter Chip Touch Targets Below Minimum
**Category:** UI/UX
**Lines:** 1975–1983

Filter chips have very small padding:
```css
.filter-chip {
  padding: 4px 10px;
  font-size: 0.75rem;
}
```

This produces touch targets of approximately 20–24px in height — well below the WCAG 2.5.8 recommended minimum of 44x44px for mobile touch targets.

**Fix:** Increase vertical padding to at least `10px 14px` and ensure a minimum `height: 44px` on touch devices via a media query or by default.

---

## Medium Priority Issues

### M1. `transition: all` Anti-Pattern
**Category:** Performance
**Lines:** 207, 230, 475, 972, 996, 1125, 1829, 1983, 2006, 2167, 2179, 2307, 2675

There are **14 instances** of `transition: all` across the CSS. This forces the browser to check and animate ALL property changes (including layout-triggering ones like `width`, `height`, `padding`) instead of only visual properties.

**Example:**
```css
/* Line 972 */
.guide-card { transition: all 0.15s; }

/* Line 207 */
button { transition: all 0.2s; }
```

**Fix:** Replace each `transition: all` with explicit properties. For example:
```css
.guide-card { transition: background 0.15s, box-shadow 0.15s, border-color 0.15s; }
```

---

### M2. Incomplete `prefers-reduced-motion` Coverage
**Category:** Accessibility
**Lines:** 1520–1536 (media query), 539, 1023, 1323 (uncovered animations)

The `prefers-reduced-motion` media query (lines 1520–1536) disables transitions on card previews, guide card images, tilt glare, and ranking hover previews. The TiltEffect class (line 3780) also checks the preference.

However, **three CSS animations are NOT covered**:
- `starPulse` (line 539) — infinite 2s pulse on Game Changer stars
- `synergyPulse` (line 1023) — infinite 1.5s pulse on synergy highlights
- `skeleton-loading` (line 1323) — infinite 1.5s shimmer on skeleton placeholders

**Fix:** Add these to the `prefers-reduced-motion: reduce` media query:
```css
.game-changer-star { animation: none !important; }
.synergy-highlight { animation: none !important; }
.skeleton { animation: none !important; }
```

---

### M3. Single-File Architecture (240KB Unminified)
**Category:** Performance
**Lines:** Entire file

The entire application is a single 240KB unminified HTML file containing all CSS, HTML, and JavaScript. No code splitting, minification, lazy loading of JS modules, or CSS extraction.

**Impact:**
- Full 240KB must be downloaded and parsed before any rendering
- No ability to cache CSS/JS independently
- Browser must parse ~3,135 lines of CSS and ~2,750 lines of JS upfront
- No tree-shaking of unused code

**Consideration:** For a project of this scope (single-page app with limited views), this may be an acceptable trade-off for simplicity. The file compresses well with gzip (~40–50KB). However, if the app grows further, splitting is recommended.

**Fix (if needed):** Extract CSS to a separate `styles.css`, JavaScript to `app.js`, and add minification. Use `defer` on the script tag.

---

### M4. Scryfall API Request Patterns
**Category:** Performance
**Lines:** 4251–4394

The Scryfall API integration has two caching layers (`imageCache` and `cardMetadataCache`) which is good. However:
- Individual card fetches (`fetchCardMetadata`) are called per-card when batch would be more efficient
- No request deduplication — if the same card name is requested twice before the first resolves, two API calls fire
- No retry logic with exponential backoff for rate-limited responses

**Fix:** Implement a request deduplication map (in-flight promises) and batch card requests where possible using Scryfall's `/cards/collection` endpoint.

---

### M5. ARIA Menu Pattern Incomplete
**Category:** Accessibility
**Lines:** 3499–3503

The export dropdown uses `role="menu"` with `role="menuitem"` children, but lacks the expected keyboard interaction pattern:
- No arrow key navigation between menu items
- No `aria-expanded` on the trigger button
- No `aria-haspopup="menu"` on the trigger
- Focus doesn't move to the first menuitem on open

**Fix:** Either implement full ARIA menu keyboard handling (arrow keys, Home/End, Escape) or switch to a simpler pattern using a list of buttons without the menu role.

---

### M6. Export Dropdown Inline Event Handler
**Category:** Accessibility / Maintainability
**Line:** 6101

The rankings error retry button is created with an inline `onclick`:
```javascript
content.innerHTML = `<button onclick="loadAndRenderRankings()">Retry</button>`;
```

This is the only inline event handler in the codebase and is inconsistent with the `addEventListener` pattern used everywhere else.

**Fix:** Use the same DOM creation + addEventListener pattern as the rest of the app.

---

### M7. Dark Theme Specific Contrast Issues
**Category:** UI/UX
**Lines:** 13–46 (CSS variables)

Beyond the primary contrast failures (C2), several interactive element states have insufficient contrast in the dark theme:

- Disabled/inactive tab text blends into the dark background
- Border colors (`--border-subtle: #2a2a4a`) are nearly invisible against `--bg-primary` (#1a1a2e)
- Placeholder text in search input inherits `--text-muted` (#555) which is unreadable

**Fix:** Audit all interactive states (hover, focus, disabled, active, placeholder) against their specific backgrounds using a contrast checker.

---

### M8. No Page-Break Rules in Print Styles
**Category:** UI/UX
**Lines:** 2315–2432

Print styles exist and properly hide interactive elements, but there are no `page-break-inside: avoid` or `break-inside: avoid` rules. Long card lists or shopping lists can break mid-item across pages.

**Fix:** Add `break-inside: avoid` to card group containers and shopping list rows.

---

## Low Priority Issues

### L1. localStorage `setItem` Not Protected
**Category:** Performance / Resilience
**Line:** 5667

`localStorage.setItem()` is called without try/catch:
```javascript
function savePreferences() {
  const prefs = { lastPrecon: currentPreconId, lastTier: currentUpgrade, filters: filterState };
  localStorage.setItem('mtg-upgrade-prefs', JSON.stringify(prefs)); // Can throw
}
```

The corresponding `getItem` + `JSON.parse` is wrapped in try/catch (lines 5674–5678), but `setItem` can throw if storage is full, disabled, or in private browsing mode on some browsers.

**Fix:** Wrap the `setItem` call in try/catch with a silent fallback.

---

### L2. No `<noscript>` Fallback
**Category:** Accessibility
**Line:** N/A (absent)

The page provides no feedback to users with JavaScript disabled. The entire page renders blank.

**Fix:** Add a `<noscript>` element with a message explaining that JavaScript is required:
```html
<noscript><p>This application requires JavaScript to run.</p></noscript>
```

---

### L3. Missing ARIA Live Announcements for Dynamic Updates
**Category:** Accessibility
**Lines:** 3139 (existing live region), various rendering functions

A `#preview-announcement` live region exists (line 3139) for card preview changes, but other dynamic content changes are not announced:
- Switching precons (entire page content changes)
- Filtering deck lists (card count changes)
- Loading states (skeleton → content)
- Tab switches (guide → deck list → comparison)

**Fix:** Use the existing live region or add new ones to announce significant content changes (e.g., "Showing 42 cards" after filter, "Loaded Eldrazi Unbound guide" after selection).

---

### L4. Heading Hierarchy Gaps
**Category:** Accessibility
**Lines:** Throughout HTML

The heading structure has jumps (e.g., `<h1>` to `<h3>` without `<h2>`). Screen reader users who navigate by headings may find the hierarchy confusing.

**Fix:** Ensure headings follow a logical nesting order (h1 → h2 → h3) throughout the document.

---

### L5. Print Styles Show Some Interactive-Only Elements
**Category:** UI/UX
**Lines:** 2315–2402

While most interactive elements are hidden in print, some styling artifacts remain:
- Hover states and box-shadows defined in non-print CSS still resolve
- Card border-glow effects could render as dark borders in print

**Fix:** Add explicit print overrides for remaining visual effects (box-shadow: none, border-color adjustments for B&W printing).

---

## Things Done Well

These patterns are solid and should be maintained:

1. **Google Fonts loading** — `display=swap` is present in the font URL (line 11), and `preconnect` hints are set for both `fonts.googleapis.com` and `fonts.gstatic.com` (lines 9–10). This prevents invisible text during font loading.

2. **`:focus-visible` usage** — The global `:focus-visible` rule (line 2622–2625) and per-element recovery rules (lines 2633–2639) follow the modern best practice of removing default outlines only when replaced with custom visible focus indicators.

3. **Image lazy loading** — Dynamically generated `<img>` tags for commander cards, guide cards, and ranking images include `loading="lazy"` (lines 4561, 4565, 4894, 6116, 6143).

4. **Modal ARIA attributes** — Both modals have `role="dialog"`, `aria-modal="true"`, and `aria-labelledby` pointing to appropriate labels (lines 3142, 3159).

5. **Scryfall API caching** — Both `imageCache` and `cardMetadataCache` (lines 4251+) prevent redundant API calls for previously fetched cards.

6. **Debounce and throttle utilities** — Custom `debounce` and `throttle` functions (lines 3649–3666) are used for search input and scroll handling.

7. **TiltEffect respects reduced motion** — The TiltEffect class checks `prefers-reduced-motion` via `matchMedia` (line 3780) and returns early if the user prefers reduced motion.

8. **Live region for card preview** — `#preview-announcement` (line 3139) with `aria-live="polite"` announces card preview changes to screen readers.

9. **Dark theme coherence** — The CSS custom properties system provides consistent theming across the entire app with a well-organized variable structure.

10. **Responsive breakpoints** — Multiple media queries handle viewport sizes down to 600px and 480px, adapting layout, font sizes, and padding appropriately.
