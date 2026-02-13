# Implementation Plan — Consolidated Review Findings

**Date:** 2026-02-10
**Reviewers:** Security/Correctness, Accessibility/HTML Standards, Performance/Architecture
**Target:** `analysis-01/IMPLEMENTATION_PLAN.md`

---

## Summary

Three independent reviewers analyzed the implementation plan against the actual source code (`index.html`, 6,375 lines). They found **24 distinct issues** (after deduplication), broken down as:

| Severity | Count |
|----------|-------|
| CRITICAL | 2 |
| HIGH | 6 |
| MEDIUM | 10 |
| LOW | 6 |

Line number accuracy was verified: **15/15 spot-checks matched** the actual source.

---

## CRITICAL Issues

### F1. `highlightMatch()` XSS bypass in search results
**Source:** Security reviewer (#2)
**Affects:** Phase 4f

The plan explicitly says NOT to escape the output of `highlightMatch()`. However, `highlightMatch()` receives raw card names from JSON data and wraps matched substrings in `<mark>` tags — but the **unmatched portions** pass through unescaped. If a card name contained `<img onerror=alert(1)>`, the unmatched portion would be injected as raw HTML, bypassing all Phase 4 protections in search results.

**Required fix:** `highlightMatch()` must HTML-escape the text BEFORE applying the `<mark>` regex:
```javascript
function highlightMatch(text, query) {
  const escaped = escapeHtml(text);
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return escaped.replace(regex, '<mark>$1</mark>');
}
```

**Note:** After escaping, the regex match operates on escaped text, so the query should also be escaped for display purposes. Verify that searching for `&` still highlights correctly.

---

### F2. `--text-muted` contrast claim is incorrect — fails WCAG AA for normal text
**Source:** Accessibility reviewer (#1)
**Affects:** Phase 2, Change 2.1

The plan proposes `--text-muted: #8a8a9a` at ~3.5:1 and claims this is acceptable because it's used for "decorative text, timestamps, and placeholders." This is **factually wrong**. `--text-muted` is used for:

- Footer content text (line 750) — readable sentences
- `.decklist-card.cut` (line 1252) — card names users must read
- `.ranking-source` at 0.8rem (line 2940)
- `.single-value` at 0.75rem (line 2968) — price data
- `.set-card-label` at 0.75rem (line 2987)
- `.source-views` at 0.8rem (line 3061)
- `.rankings-last-updated` at 0.8rem (line 3078)

All of these are 0.75–0.85rem (12–14px), which is **normal text** under WCAG (large text requires 18pt/24px or 14pt/18.67px bold). At 3.5:1 they fail AA for normal text (4.5:1 required).

**Required fix:** Increase `--text-muted` to at least `#9a9aaa` (~4.0:1) or preferably `#a0a0b0` (~4.5:1+), OR split the variable so that text users must read gets a higher-contrast color.

---

## HIGH Issues

### F3. `javascript:` protocol injection in `href` attributes not prevented
**Source:** Security reviewer (#3)
**Affects:** Phase 4j

`escapeHtml()` does NOT prevent `javascript:` protocol URLs. The plan proposes `escapeHtml(precon.sourceUrl)` for `href` attributes, but `javascript:alert(1)` contains none of the 5 escaped characters and would pass through unchanged. Applies to lines 6129, 6160, 6188.

**Required fix:** Add URL protocol validation for any value used in `href`. Either whitelist `https:`/`http:` only, or add a `sanitizeUrl()` helper.

---

### F4. `mouseout` delegation clears `lastHovered` prematurely — redundant preview calls
**Source:** Security reviewer (#6) + Performance reviewer (#2) — independently discovered
**Affects:** Phase 6, Change 6.0

When the mouse moves from a `.decklist-card` to a child `<a>` element, `mouseout` fires with `e.target` being the card div. The `closest()` check matches, so `lastHoveredDeckCard` is set to `null`. Then `mouseover` immediately fires on the child, finding the same card again, triggering a redundant `showCardPreview()` call. This defeats the purpose of the `lastHovered` guard.

**Required fix:** Use `e.relatedTarget` to verify the mouse actually left the card:
```javascript
decklistContent.addEventListener('mouseout', (e) => {
  const card = e.target.closest('.decklist-card');
  if (card === lastHoveredDeckCard && (!e.relatedTarget || !card.contains(e.relatedTarget))) {
    lastHoveredDeckCard = null;
  }
});
```
Apply the same pattern to all `mouseout` handlers in `setupDelegatedListeners()`.

---

### F5. Existing modal `aria-labelledby` references are broken
**Source:** Accessibility reviewer (#3)
**Affects:** Phase 5, Change 5.1

The search modal references `aria-labelledby="search-title"` (line 3142) and the mobile preview modal references `aria-labelledby="mobile-preview-title"` (line 3159), but **neither ID exists in the HTML**. The codebase review praised these as "solid" and the plan doesn't fix them. These are dangling ARIA references.

**Required fix:** Either add matching `id` attributes to headings inside each modal, or switch to `aria-label` with descriptive text.

---

### F6. Bracket info modal missing `role="dialog"` and `aria-modal="true"`
**Source:** Accessibility reviewer (#2)
**Affects:** Phase 5, Change 5.1

The plan adds a focus trap to the bracket info modal but doesn't add `role="dialog"` and `aria-modal="true"` to `<div class="bracket-info-modal" id="bracket-info-modal">` (line 3230). Without these, screen readers won't announce it as a dialog.

**Required fix:** Add `role="dialog" aria-modal="true" aria-label="Commander Bracket System"` to the bracket info modal element.

---

### F7. `aria-labelledby` IDs for guide sections don't match actual heading IDs
**Source:** Accessibility reviewer (#4)
**Affects:** Phase 3, Change 3.1

The plan proposes `aria-labelledby="adds-title"`, `"cuts-title"`, etc. But the actual headings already have `id="adds-header"` (line 3315) and `id="cuts-header"` (line 3383). The synergies/stats/decklist headings have **no ID at all**. The plan would create mismatched or duplicated IDs.

**Required fix:** Use existing `*-header` IDs where they exist. Only add new IDs for headings that lack them. Update `aria-labelledby` values to match.

---

### F8. TiltEffect instances leak on innerHTML re-renders
**Source:** Performance reviewer (#3)
**Affects:** Phase 6

`initializeGuideThumbnailTilt()` creates `new TiltEffect(img)` per card image. When innerHTML replacement occurs (tier switch, filter), the DOM elements are destroyed but TiltEffect instances (with bound listeners, glare elements, rAF references) are never cleaned up via `destroy()`. This is a memory leak proportional to re-render count.

**Required fix:** Before innerHTML replacement in render functions, call `destroy()` on existing TiltEffect instances. Store them in an array for cleanup, or add cleanup to the beginning of `initializeGuideThumbnailTilt()`.

---

## MEDIUM Issues

### F9. `renderAddGroups()` does not output `category.description` — plan is misleading
**Source:** Security reviewer (#4)
**Affects:** Phase 4c

The plan groups `renderCutGroups()` and `renderAddGroups()` under "4c" and says to escape both `category.name` and `category.description`. But `renderAddGroups()` does NOT output `category.description`. Only `renderCutGroups()` does. This will confuse implementers.

**Required fix:** Clarify in the plan that `category.description` escaping applies only to `renderCutGroups()`.

---

### F10. `<nav>` around view toggle is semantically wrong
**Source:** Accessibility reviewer (#6)
**Affects:** Phase 3, Change 3.1

The view toggle is a 2-button switcher between "Upgrade Guides" and "Creator Rankings" — this is a tab pattern, not navigation. `<nav>` is for page/section navigation links. WAI-ARIA practices recommend `role="tablist"` with `role="tab"` and `aria-selected` for this pattern.

**Required fix:** Use `<div role="tablist">` instead of `<nav>`, and add `role="tab"` + `aria-selected` to the view toggle buttons.

---

### F11. Heading hierarchy fix doesn't resolve WCAG violation
**Source:** Accessibility reviewer (#7)
**Affects:** Phase 3, Change 3.2

The plan wraps the selector section in `<section aria-label="...">` to sidestep the h1→h3 heading jump. But WCAG heading hierarchy rules apply to the document's heading outline globally — the HTML5 sectioning algorithm was never implemented by browsers or assistive technology. A labeled section does NOT reset heading levels.

**Required fix:** Change `<h3 id="commander-name">` to `<h2>`, or add a visually-hidden `<h2>` before it.

---

### F12. `aria-haspopup="true"` contradicts removal of `role="menu"`
**Source:** Accessibility reviewer (#10)
**Affects:** Phase 5, Change 5.2

The plan removes `role="menu"` and uses `role="group"`. But the trigger button's `aria-haspopup="true"` is equivalent to `aria-haspopup="menu"` per ARIA spec. Keeping it while removing `role="menu"` is contradictory. Also, `role="group"` is intended for form controls, not disclosure widgets.

**Required fix:** Remove both `role="menu"` and `role="group"`. Remove `aria-haspopup` from the trigger button (keep `aria-expanded`). The buttons inside are self-describing.

---

### F13. `prefers-reduced-motion` is still incomplete after the plan's additions
**Source:** Accessibility reviewer (#11)
**Affects:** Phase 2, Change 2.4

The plan adds 3 missing animations but doesn't address the remaining CSS transitions on tabs, buttons, filter chips, toggles, etc. For WCAG 2.3.3 compliance, all non-essential motion should be reduced.

**Required fix:** Add a catch-all inside the reduced-motion block:
```css
*, *::before, *::after {
  transition-duration: 0.01ms !important;
  animation-duration: 0.01ms !important;
}
```

---

### F14. FocusTrap doesn't actually trap when container has zero focusable elements
**Source:** Accessibility reviewer (#5)
**Affects:** Phase 1, Change 1.2

If `getFocusableElements()` returns empty (possible during async content load), `handleKeyDown` returns early without calling `preventDefault()`, so Tab escapes the modal. The trap doesn't actually trap.

**Required fix:** Call `e.preventDefault()` when `focusable.length === 0` to prevent focus from leaving the container.

---

### F15. `will-change` on `.tilting` class has a timing consideration
**Source:** Performance reviewer (#4)
**Affects:** Phase 2, Change 2.3

The `.tilting` class and first transform can happen in the same frame. The browser needs time to promote the layer after `will-change` is set. In practice, modern browsers handle this synchronously, and the fallback (transform without GPU promotion) still works with at most single-frame jank.

**Recommendation:** Acceptable trade-off. Note in the plan that this is a pragmatic choice, not spec-guaranteed behavior.

---

### F16. Scryfall API dedup value is overstated
**Source:** Performance reviewer (#6)
**Affects:** Phase 7, Change 7.5

The existing `processQueue` while-loop already has a cache re-check. If two requests for the same card are in the queue, the second resolves from cache without a duplicate API call. The `inFlightRequests` dedup only saves the cost of queue entry and cache lookup — not actual duplicate API calls.

**Recommendation:** Keep the dedup (it's still a minor improvement) but downgrade its description from "prevents duplicate API calls" to "prevents redundant queue entries."

---

### F17. Ranking card inline `onerror` handlers and per-element listeners not addressed
**Source:** Performance reviewer (#7)
**Affects:** Phase 5 (M6) and Phase 6 (event delegation)

Lines 6116 and 6143 have inline `onerror="handleRankingImageError(this)"` — identical in pattern to the `onclick` being removed in Phase 5. Also, `initializeRankingCardTilt()` attaches per-element listeners to ranking cards but is not covered by Phase 6's event delegation.

**Required fix:** Convert inline `onerror` to `addEventListener` pattern for consistency. Either add ranking card events to the delegation setup, or document why they're excluded.

---

### F18. `announceStatus()` with `setTimeout(100ms)` is fragile
**Source:** Accessibility reviewer (#9)
**Affects:** Phase 1, Change 1.3

100ms may not be enough for all screen readers (JAWS sometimes needs 200–500ms). If two announcements fire within 100ms, the first gets swallowed.

**Recommendation:** Increase to 200ms, or use two alternating live region elements for robustness. Note this is pragmatic — the technique works in most cases.

---

## LOW Issues

### F19. `escapeHtml()` returns non-string inputs as-is — cosmetic bug
**Source:** Security reviewer (#1)
**Affects:** Phase 1, Change 1.1

If a JSON field is `null`, `escapeHtml(null)` returns `null` the value, and `${null}` renders as the string "null" in the DOM.

**Fix:** Change to `if (typeof str !== 'string') return String(str ?? '');`

---

### F20. `strategyOverview` would be better as `textContent` than `innerHTML = escapeHtml()`
**Source:** Security reviewer (#10)
**Affects:** Phase 4e

Since `strategyOverview` is plain text, using `textContent` is semantically clearer and doesn't require escaping at all. With `innerHTML = escapeHtml()`, newlines in the text won't render as line breaks.

**Fix:** Use `document.getElementById('strategy-content').textContent = guideContent.strategyOverview;`

---

### F21. Missing `escapeHtml()` on `priceDisplay` in shopping list
**Source:** Security reviewer (#12)
**Affects:** Phase 4i

Line 5809 outputs `${priceDisplay}` without escaping. Unlikely attack vector but inconsistent with the thoroughness elsewhere.

**Fix:** Add `escapeHtml(priceDisplay)`.

---

### F22. Phase 6 removal line range is slightly imprecise
**Source:** Security reviewer (#11)
**Affects:** Phase 6, Removals table

The plan says lines "5002-5031" for `addGuideCardHoverEvents()` but the function extends to ~5035. Could cause incomplete deletion.

**Fix:** Correct the line range.

---

### F23. Mobile preview panel gap at 601–768px viewports
**Source:** Accessibility reviewer (#14)
**Affects:** Phase 7, Change 7.2

The plan hides `.preview-panel` at `max-width: 768px`, but the existing code only changes behavior at `max-width: 600px`. Between 601–768px the preview is in its default state. Verify behavior in this range.

**Fix:** Test and confirm the 768px breakpoint works for both the panel hide and the mobile modal activation.

---

### F24. Inline `onerror` on ranking images inconsistent with M6 fix
**Source:** Security reviewer (#8), Performance reviewer (#7)
**Affects:** Phase 5

Ranking card images at lines 6116 and 6143 use inline `onerror="handleRankingImageError(this)"`. This is the same pattern Phase 5 removes for the retry button. Inconsistent.

**Fix:** Convert to `addEventListener` after rendering, or use event delegation.

---

## Pre-existing Issues Noted (Not Caused by Plan)

### P1. `querySelector` CSS-injection with card names containing quotes
**Source:** Performance reviewer (#1)

Lines 4936, 4944, and 5364 use `querySelector(`[data-card-name="${cardName}"]`)` where `cardName` may contain quotes. This is a pre-existing bug that the plan doesn't worsen, but should be addressed with `CSS.escape()`.

---

## Issues Confirmed Correct (No Action Needed)

- **`data-*` attribute auto-decode**: Browser correctly decodes HTML entities in dataset properties. Verified.
- **Line number accuracy**: 15/15 spot-checks passed.
- **`transition: all` replacements**: 5/5 cross-checks confirmed correct property lists.
- **`escapeHtml` performance**: ~0.8ms worst case for 400 calls. Adequate.
- **Scryfall dedup correctness**: No race conditions. Works correctly with queue system.
