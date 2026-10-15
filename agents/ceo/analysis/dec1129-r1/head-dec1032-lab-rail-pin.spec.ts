// DEC-1032: the Combo Lab control rail pins from Contents down.
//
// The rail is 1329px tall with the fleet's decks, too tall to pin whole
// (DEC-1019). Its lower part (Contents, the tier legend, the exports and the
// small print, `.gv1-lab-rail-pin`) is 659px at its tallest and pins 20px
// from the top, where the lab has two columns and the screen is at least 700px
// tall. The mode switch and the deck picker scroll with the page.

import { expect, test, type Page } from './support/test';

const PIN = '.gv1-lab-rail-pin';
const PIN_TOP = 20;

// The scroll target is a whole pixel and the blocks' positions are not.
function expectWithin1px(received: number, expected: number, what: string): void {
  expect(Math.abs(received - expected), `${what}: expected ${expected}, read ${received}`).toBeLessThan(1);
}

async function openLab(page: Page): Promise<void> {
  await page.goto('/combos');
  await expect(page.locator('.gv1-lab-attrib')).toBeVisible();
  await expect(page.locator('.gv1-lab-combo').first()).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

// Scroll `past` px beyond the pinned part's own place in the page, and read
// the tops of the part and of the blocks above it. The places are read at the
// top of the page, where nothing pins yet.
async function railTopsScrolledPast(page: Page, past: number) {
  return page.evaluate(
    ({ selector, by }) => {
      window.scrollTo(0, 0);
      const pin = document.querySelector(selector)!;
      const above = [...pin.parentElement!.children].filter((el) => el !== pin);
      const placed = above.map((el) => el.getBoundingClientRect().top);
      const target = Math.round(pin.getBoundingClientRect().top + window.scrollY) + by;
      window.scrollTo(0, target);
      const r = pin.getBoundingClientRect();
      return {
        scrolled: window.scrollY,
        target,
        pinTop: r.top,
        pinBottom: r.bottom,
        above: above.map((el, i) => ({
          label: ['the mode switch', 'the deck picker'][i] ?? el.className,
          top: el.getBoundingClientRect().top,
          expected: placed[i] - window.scrollY,
        })),
      };
    },
    { selector: PIN, by: past },
  );
}

const PINNED = [
  { width: 1280, height: 800, fonts: 'live' },
  { width: 1440, height: 900, fonts: 'live' },
  { width: 1920, height: 1080, fonts: 'live' },
  { width: 1280, height: 800, fonts: 'blocked' },
] as const;

for (const { width, height, fonts } of PINNED) {
  test.describe(`DEC-1032 Combo Lab rail @ ${width}×${height}, fonts ${fonts}`, () => {
    test.use({ viewport: { width, height }, fonts });

    test('the rail pins from Contents down; the mode switch and the deck picker scroll', async ({ page }) => {
      await openLab(page);

      // The part keeps the rail's spacing: 20px between two blocks, as between
      // the deck picker and Contents.
      const gaps = await page.locator(PIN).evaluate((pin) => {
        const blocks = [pin.previousElementSibling!, ...pin.querySelectorAll(':scope > .gv1-lab-block')];
        return blocks.slice(1).map((b, i) => b.getBoundingClientRect().top - blocks[i].getBoundingClientRect().bottom);
      });
      expect(gaps, 'spaces from the deck picker to the exports').toHaveLength(3);
      for (const gap of gaps) expectWithin1px(gap, 20, 'space between two blocks of the rail');

      for (const past of [600, 1500]) {
        const m = await railTopsScrolledPast(page, past);
        expect(m.scrolled, 'the report is long enough to scroll that far').toBe(m.target);
        expectWithin1px(m.pinTop, PIN_TOP, `top of the pinned part, ${past}px past its place`);
        expect(m.pinBottom, 'the pinned part fits the screen whole').toBeLessThanOrEqual(height);
        expect(m.above, 'blocks of the rail above the pinned part').toHaveLength(2);
        for (const b of m.above) {
          expectWithin1px(b.top, b.expected, `top of ${b.label}, ${past}px past the pinned part's place`);
          expect(b.top, `${b.label} has scrolled off the top`).toBeLessThan(0);
        }
      }
    });
  });
}

// One column (the container query at 1080px), or a screen shorter than the
// part with 20px above and below it: the whole rail stays in the flow.
const IN_FLOW = [
  { width: 1080, height: 800 },
  { width: 1280, height: 690 },
];

for (const { width, height } of IN_FLOW) {
  test.describe(`DEC-1032 Combo Lab rail @ ${width}×${height}`, () => {
    test.use({ viewport: { width, height } });

    test('the whole rail scrolls with the page', async ({ page }) => {
      await openLab(page);
      const m = await railTopsScrolledPast(page, 600);
      expect(m.scrolled).toBe(m.target);
      expectWithin1px(m.pinTop, -600, 'top of the lower part, 600px past its place');
    });
  });
}

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`DEC-1032 Combo Lab rail, keyboard @ 1280×800, fonts ${fonts}`, () => {
    test.use({ viewport: { width: 1280, height: 800 }, fonts });

    // A control that sits on screen under a pinned block does not scroll when
    // it takes focus. Nothing in the rail follows the pinned part, and the
    // deck picker has left the screen before the part pins, so no control of
    // the rail can sit under it. Walk the page in 10px steps and check every
    // control of the rail that is on screen while the part pins. The report
    // column starts 44px to the right of the rail.
    test('no control of the rail sits on screen under the pinned part', async ({ page }) => {
      await openLab(page);

      const m = await page.evaluate(
        ({ selector, pinTop }) => {
          const pin = document.querySelector(selector)!;
          const rail = pin.parentElement!;
          const controls = [...rail.querySelectorAll<HTMLElement>('button, a, input, select, textarea, [tabindex]')];
          const others = controls.filter((el) => !pin.contains(el));
          const end = document.documentElement.scrollHeight - window.innerHeight;
          const under: string[] = [];
          let pinnedSteps = 0;
          for (let y = 0; y <= end; y += 10) {
            window.scrollTo(0, y);
            const p = pin.getBoundingClientRect();
            if (Math.abs(p.top - pinTop) >= 0.5) continue;
            pinnedSteps += 1;
            for (const el of others) {
              // A deck sits in its own scroller and shows only inside it.
              const r = el.getBoundingClientRect();
              const clip = el.closest('.gv1-lab-decks')?.getBoundingClientRect();
              const top = Math.max(r.top, clip?.top ?? -Infinity, 0);
              const bottom = Math.min(r.bottom, clip?.bottom ?? Infinity, window.innerHeight);
              if (bottom > top && top < p.bottom && bottom > p.top && r.left < p.right && r.right > p.left) {
                under.push(`${el.textContent?.trim().slice(0, 24)} at scroll ${y}`);
              }
            }
          }
          const report = document.querySelector('.gv1-lab-report')!.getBoundingClientRect();
          return { pinnedSteps, controls: others.length, under, gap: report.left - pin.getBoundingClientRect().right };
        },
        { selector: PIN, pinTop: PIN_TOP },
      );

      expect(m.pinnedSteps, 'scroll positions at which the part pins').toBeGreaterThan(100);
      expect(m.controls, 'controls of the rail outside the pinned part').toBeGreaterThan(2);
      expect(m.under, 'controls on screen under the pinned part').toEqual([]);
      expect(m.gap, 'space between the pinned part and the report column').toBeGreaterThanOrEqual(44);
    });

    // The one key that leaves the pinned part for a control above it. WebKit
    // on macOS moves focus to a button only with Option+Tab.
    test('Shift+Tab from the pinned Contents brings the last deck into view above the part', async ({
      page,
      browserName,
    }) => {
      await openLab(page);
      const pin = page.locator(PIN);
      const first = pin.getByRole('button', { name: /The Disclosure/ });
      const lastDeck = page.locator('.gv1-lab-deck').last();

      expectWithin1px((await railTopsScrolledPast(page, 600)).pinTop, PIN_TOP, 'top of the pinned part');
      await first.evaluate((el: HTMLElement) => el.focus({ preventScroll: true }));
      await page.keyboard.press(browserName === 'webkit' ? 'Shift+Alt+Tab' : 'Shift+Tab');
      await expect(lastDeck).toBeFocused();

      const deck = await lastDeck.evaluate((el) => el.getBoundingClientRect().toJSON() as DOMRect);
      const part = await pin.evaluate((el) => el.getBoundingClientRect().toJSON() as DOMRect);
      expect(deck.top, 'top of the focused deck').toBeGreaterThanOrEqual(0);
      expect(deck.bottom, `bottom of the focused deck (the part starts at ${part.top})`).toBeLessThanOrEqual(part.top);
    });
  });
}
