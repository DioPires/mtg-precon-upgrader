// DEC-1171 (restart of DEC-1024): the shell's <main> pads 16px a side at 768px
// and below. Its 64px sides at every width left each Shopping and Compare
// section, which adds 16px a side on a phone, a 160px column at 320px.
//
// The floor at 320px is 256px: 320 less 16px a side for <main> and 16px a
// side for the section. Above 768px <main> keeps its 64px, and the deck guide
// keeps its own opt-out (0) at every width.

import { expect, test, type Page } from './support/test';

const FLOOR_320 = 256;

async function open(page: Page, width: number, path: string, ready: string) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto(path);
  await page.locator(ready).first().waitFor();
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
}

// The width of each element's content box: its border box less padding and border.
async function contentWidths(page: Page, selector: string): Promise<number[]> {
  return page.locator(selector).evaluateAll((els) =>
    els.map((el) => {
      const cs = getComputedStyle(el);
      const w = el.getBoundingClientRect().width
        - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)
        - parseFloat(cs.borderLeftWidth) - parseFloat(cs.borderRightWidth);
      return Math.round(w * 10) / 10;
    }),
  );
}

// <main>'s padding. The rule changes the sides only: the top and bottom stay 48px.
async function mainPadding(page: Page) {
  return page.locator('.gv1-app > main').evaluate((el) => {
    const cs = getComputedStyle(el);
    return { top: cs.paddingTop, right: cs.paddingRight, bottom: cs.paddingBottom, left: cs.paddingLeft };
  });
}

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`DEC-1171 shell gutter, web fonts ${fonts}`, () => {
    test.use({ fonts });

    for (const { surface, path, ready } of [
      // A deck is selected by default, so the summary section is in the page.
      { surface: 'Shopping', path: '/shopping', ready: '.gv1-shop-row' },
      { surface: 'Compare', path: '/compare', ready: 'main .gv1-section' },
    ]) {
      test(`at 320px every ${surface} section holds ${FLOOR_320}px or more`, async ({ page }) => {
        await open(page, 320, path, ready);
        const widths = await contentWidths(page, 'main .gv1-section');
        expect(widths.length, `the ${surface} sections`).toBeGreaterThan(1);
        expect(widths.filter((w) => w < FLOOR_320 - 0.5), `${surface} sections narrower than ${FLOOR_320}px: ${widths}`).toEqual([]);
      });
    }

    test('<main> pads 16px a side at 768px and 64px at 769px', async ({ page }) => {
      await open(page, 768, '/shopping', '.gv1-shop-row');
      expect(await mainPadding(page), 'at 768px').toEqual({ top: '48px', right: '16px', bottom: '48px', left: '16px' });
      await open(page, 769, '/shopping', '.gv1-shop-row');
      expect(await mainPadding(page), 'at 769px').toEqual({ top: '48px', right: '64px', bottom: '48px', left: '64px' });
    });

    test('at 320px the deck guide keeps its opt-out', async ({ page }) => {
      await open(page, 320, '/deck/anvil-chorus', '.gv1-perf-grid');
      expect(await mainPadding(page)).toEqual({ top: '48px', right: '0px', bottom: '48px', left: '0px' });
    });
  });
}
