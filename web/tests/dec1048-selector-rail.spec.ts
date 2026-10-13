// DEC-1048: the deck selector rail shows the whole focus ring on the active
// pill, leaves the first Tab from load to the topbar, and drops its right-edge
// fade once the track is scrolled to its end.
//
// The track clipped the ring: its 2px padding was narrower than the ring,
// which sits 4px outside the pill. The selector's mount effect called
// `track.scrollIntoView`, and Chromium moves its sequential focus starting
// point to whatever it scrolls into view, so the first Tab landed on the
// active pill. The fade dimmed the last pill when nothing more lay to the
// right.
//
// Every deck is loaded for the ring because where the active pill sits in the
// track (first, centred, last) depends on the deck.

import { expect, test, type Page } from './support/test';

const WIDTHS = [390, 1280];

type Box = { left: number; top: number; right: number; bottom: number };
type RingCheck = {
  focusVisible: boolean;
  outline: string;
  ring: Box;
  visible: Box;
  scrollLeft: number;
  expectedScrollLeft: number;
};

async function deckIds(page: Page): Promise<string[]> {
  const r = await page.request.get('/data/index.json');
  return ((await r.json()) as { commanders: { id: string }[] }).commanders.map((c) => c.id);
}

// The selector's smooth scrolls are still running when the guide first
// paints. Resolve once neither the track nor the page has moved for 300ms
// and the web fonts are in.
async function openSettled(page: Page, deck: string): Promise<void> {
  await page.goto(`/deck/${deck}`);
  await page.locator('.gv1-selector-track .gv1-active').waitFor();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      const track = document.querySelector('.gv1-selector-track')!;
      const read = () => `${track.scrollLeft}|${window.scrollY}`;
      const started = Date.now();
      let last = read();
      let still = 0;
      const tick = () => {
        const now = read();
        still = now === last ? still + 1 : 0;
        last = now;
        if (still < 6 && Date.now() - started < 5000) {
          setTimeout(tick, 50);
          return;
        }
        resolve();
      };
      setTimeout(tick, 50);
    });
  });
}

// Focus the active pill without scrolling, then read the ring's box (the
// pill grown by the outline's width and offset) and the track's visible box
// (its padding box: the track clips everything past it).
async function ringCheck(page: Page): Promise<RingCheck> {
  return page.evaluate(() => {
    const track = document.querySelector<HTMLElement>('.gv1-selector-track')!;
    const pill = track.querySelector<HTMLElement>('.gv1-active')!;
    pill.focus({ preventScroll: true });
    const cs = getComputedStyle(pill);
    const grow = parseFloat(cs.outlineWidth) + parseFloat(cs.outlineOffset);
    const p = pill.getBoundingClientRect();
    const t = track.getBoundingClientRect();
    const left = t.left + track.clientLeft;
    const top = t.top + track.clientTop;
    // DEC-1008: the active pill is centred, or the track stops at an end.
    const max = track.scrollWidth - track.clientWidth;
    const centred = track.scrollLeft + (p.left + p.width / 2) - (left + track.clientWidth / 2);
    const result = {
      focusVisible: pill.matches(':focus-visible'),
      outline: `${cs.outlineStyle} ${cs.outlineWidth}`,
      ring: { left: p.left - grow, top: p.top - grow, right: p.right + grow, bottom: p.bottom + grow },
      visible: { left, top, right: left + track.clientWidth, bottom: top + track.clientHeight },
      scrollLeft: track.scrollLeft,
      expectedScrollLeft: Math.min(Math.max(centred, 0), max),
    };
    pill.blur();
    return result;
  });
}

const fadeOpacity = (page: Page) =>
  page.evaluate(() => getComputedStyle(document.querySelector('.gv1-selector')!, '::after').opacity);

const box = (b: Box) =>
  `x ${b.left.toFixed(1)}–${b.right.toFixed(1)}, y ${b.top.toFixed(1)}–${b.bottom.toFixed(1)}`;

for (const width of WIDTHS) {
  test.describe(`DEC-1048 @ ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    test('the track shows the whole focus ring on every active pill', async ({ page }) => {
      test.setTimeout(180_000);
      const offenders: string[] = [];

      for (const deck of await deckIds(page)) {
        await openSettled(page, deck);
        const m = await ringCheck(page);

        if (!m.focusVisible || m.outline.startsWith('none')) {
          offenders.push(`${deck}: the focused pill shows no ring (${m.outline})`);
          continue;
        }
        const { ring: r, visible: v } = m;
        if (r.left < v.left || r.top < v.top || r.right > v.right || r.bottom > v.bottom) {
          offenders.push(`${deck}: the ring (${box(r)}) runs past the track (${box(v)})`);
        }
        if (Math.abs(m.scrollLeft - m.expectedScrollLeft) > 1) {
          offenders.push(
            `${deck}: the track is at ${m.scrollLeft}, not ${m.expectedScrollLeft.toFixed(1)} (pill centred or track at an end)`,
          );
        }
      }

      expect(offenders, `Active pills at ${width}px (viewport coordinates)`).toEqual([]);
    });

    for (const deck of ['titan-convergence', 'anvil-chorus']) {
      test(`the first Tab from load on ${deck} focuses the first topbar control`, async ({
        page,
      }) => {
        await openSettled(page, deck);
        const first = await page.evaluate(() => {
          const controls = document.querySelectorAll<HTMLElement>(
            '.gv1-topbar a[href], .gv1-topbar button, .gv1-topbar [tabindex]:not([tabindex="-1"])',
          );
          const el = Array.from(controls).find((c) => c.getClientRects().length > 0);
          el?.setAttribute('data-dec1048-first', '');
          return el?.outerHTML.slice(0, 80) ?? null;
        });
        expect(first, 'the topbar has a visible control').not.toBeNull();

        await page.keyboard.press('Tab');

        const focused = await page.evaluate(() => {
          const a = document.activeElement as HTMLElement | null;
          return {
            isFirst: !!a?.hasAttribute('data-dec1048-first'),
            what: a ? `${a.tagName.toLowerCase()}.${a.className}` : 'nothing',
          };
        });
        expect(focused.isFirst, `the first Tab focused ${focused.what}, not ${first}`).toBe(true);
      });
    }

    test('the right-edge fade shows on the first deck and is gone at the end of the track', async ({
      page,
    }) => {
      // The first pill: the track is at its start, and more pills lie right.
      await openSettled(page, 'titan-convergence');
      expect(await fadeOpacity(page)).toBe('1');

      // The last pill: the selector scrolls the track to its end.
      await openSettled(page, 'anvil-chorus');
      await expect.poll(() => fadeOpacity(page)).toBe('0');

      // Scrolled back from the end, the fade returns.
      await page.evaluate(() => document.querySelector('.gv1-selector-track')!.scrollTo({ left: 0 }));
      await expect.poll(() => fadeOpacity(page)).toBe('1');
    });

    test('opening a deck from a scrolled page brings the rail into view', async ({ page }) => {
      await openSettled(page, 'titan-convergence');
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await expect
        .poll(() =>
          page.evaluate(() => document.querySelector('.gv1-selector-track')!.getBoundingClientRect().bottom),
        )
        .toBeLessThan(0);

      // A client-side route change: the selector stays mounted.
      await page.evaluate(() => {
        history.pushState({}, '', '/deck/anvil-chorus');
        dispatchEvent(new PopStateEvent('popstate'));
      });
      await page.locator('.gv1-selector-track .gv1-active', { hasText: 'Anvil Chorus' }).waitFor();

      await expect
        .poll(() =>
          page.evaluate(() => {
            const r = document.querySelector('.gv1-selector-track')!.getBoundingClientRect();
            return r.top >= 0 && r.bottom <= document.documentElement.clientHeight;
          }),
        )
        .toBe(true);
    });
  });
}

test.describe('DEC-1048 @ 6400px', () => {
  test.use({ viewport: { width: 6400, height: 900 } });

  test('a rail that does not overflow shows no fade', async ({ page }) => {
    await openSettled(page, 'titan-convergence');
    const overflow = await page.evaluate(() => {
      const t = document.querySelector('.gv1-selector-track')!;
      return t.scrollWidth - t.clientWidth;
    });
    test.skip(overflow > 0, `the rail still overflows by ${overflow}px at 6400px`);
    await expect.poll(() => fadeOpacity(page)).toBe('0');
  });
});
