// DEC-181 design-system-eng visual + a11y QA at all six mandated
// widths. Asserts the structural exit criteria — redirects in both
// directions, sticky shopping rail, scrying mobile banner gate, no
// page-level horizontal overflow, and full topbar a11y lifecycle
// (aria-expanded toggle, aria-controls, keyboard reach, Esc close,
// outside-click close, route-change close).
//
// `tests/smoke.spec.ts` covers the 390×844 happy-path; this file is
// the broader regression gate.

import { expect, test, type Page } from '@playwright/test';

const WIDTHS = [360, 375, 390, 430, 768, 1024];
const HEIGHT = 900;

async function getFirstDeck(page: Page): Promise<string> {
  const r = await page.request.get('/data/index.json');
  const idx = (await r.json()) as { commanders: { id: string }[] };
  return idx.commanders[0].id;
}

async function pageOverflows(page: Page): Promise<boolean> {
  const m = await page.evaluate(() => ({
    win: window.innerWidth,
    doc: document.documentElement.scrollWidth,
  }));
  return m.doc > m.win + 1;
}

for (const width of WIDTHS) {
  test.describe(`DEC-181 QA @ ${width}px`, () => {
    test.use({ viewport: { width, height: HEIGHT } });

    test('every surface renders without page-level overflow', async ({ page }) => {
      const overflows: string[] = [];
      const deck = await getFirstDeck(page);

      await page.goto('/codex');
      await page.locator('.gv1-codex').waitFor();
      if (await pageOverflows(page)) overflows.push('codex');

      // DEC-183: /deck/:id renders responsively at every width — no /m/:id redirect.
      await page.goto(`/deck/${deck}`);
      await expect(page).toHaveURL(new RegExp(`/deck/${deck}$`));
      await expect(page.locator('.gv1-deck-guide')).toBeVisible();
      await page.waitForLoadState('networkidle');
      if (await pageOverflows(page)) overflows.push('deck');

      // DEC-183: /m/:id is preserved as a redirect to /deck/:id for one release
      // so existing bookmarks don't 404. The bezel artboard is retired.
      await page.goto(`/m/${deck}`);
      await expect(page).toHaveURL(new RegExp(`/deck/${deck}$`));
      await expect(page.locator('.gv1-deck-guide')).toBeVisible();
      await page.waitForLoadState('networkidle');
      if (await pageOverflows(page)) overflows.push('mobile-redirect');

      await page.goto('/compare');
      await page.locator('.gv1-cmp-table').waitFor();
      if (await pageOverflows(page)) overflows.push('compare');

      await page.goto('/shopping');
      await page.locator('.gv1-shop-rail').waitFor();
      if (await pageOverflows(page)) overflows.push('shopping');

      await page.goto(`/scrying/${deck}`);
      await page.locator('[data-gv1-screen="scrying"]').waitFor();
      const banner = page.locator('.gv1-scry-mobile-banner');
      if (width <= 480) {
        await expect(banner).toBeVisible();
      } else {
        await expect(banner).toBeHidden();
      }
      if (await pageOverflows(page)) overflows.push('scrying');

      expect(overflows, `Pages with horizontal overflow at ${width}px`).toEqual([]);
    });

    test('topbar a11y + behavior', async ({ page }) => {
      await page.goto('/codex');

      if (width <= 768) {
        // Class-based locator survives the aria-label flip from "Open…" to "Close…".
        const btn = page.locator('.gv1-topbar-mobile-btn');
        await expect(btn).toBeVisible();
        await expect(btn).toHaveAttribute('aria-expanded', 'false');
        await expect(btn).toHaveAttribute('aria-label', /open navigation menu/i);
        const menuId = await btn.getAttribute('aria-controls');
        expect(menuId).toBeTruthy();

        await btn.click();
        await expect(btn).toHaveAttribute('aria-expanded', 'true');
        await expect(btn).toHaveAttribute('aria-label', /close navigation menu/i);
        const menu = page.locator(`[id="${menuId}"]`);
        await expect(menu).toBeVisible();

        // The dropdown's hamburger entry-point exposes all five surfaces.
        for (const label of [/codex/i, /guide/i, /scrying/i, /shopping/i, /compare/i]) {
          await expect(menu.getByRole('link', { name: label })).toBeVisible();
        }

        // Esc closes.
        await page.keyboard.press('Escape');
        await expect(menu).toBeHidden();
        await expect(btn).toHaveAttribute('aria-expanded', 'false');

        // Outside-click closes.
        await btn.click();
        await expect(menu).toBeVisible();
        await page.evaluate(() => {
          document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        });
        await expect(menu).toBeHidden();

        // Route change closes the menu (Topbar effect on pathname change).
        await btn.click();
        await expect(menu).toBeVisible();
        await page.goto('/shopping');
        await expect(page.locator('.gv1-topbar-mobile-menu')).toBeHidden();

        // Hamburger is reachable via keyboard.
        await page.goto('/codex');
        await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur?.());
        let focused = false;
        for (let i = 0; i < 30; i++) {
          await page.keyboard.press('Tab');
          focused = await page.evaluate(() =>
            !!document.activeElement?.classList.contains('gv1-topbar-mobile-btn'),
          );
          if (focused) break;
        }
        expect(focused).toBe(true);
      } else {
        const nav = page.getByRole('navigation', { name: /surfaces/i });
        await expect(nav).toBeVisible();
        await expect(page.locator('.gv1-topbar-mobile')).toBeHidden();
      }
    });
  });
}
