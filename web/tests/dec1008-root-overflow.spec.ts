// DEC-1008: the deck guide sits inside the viewport and stays unscrolled.
//
// `.gv1-root` is `overflow: hidden`, so a block wider than the viewport never
// shows up on `documentElement` — the root swallows it, and script can still
// scroll the root sideways. The deck selector did exactly that for decks at
// the far end of the rail, sliding the whole page left with no way back.
//
// Every deck is loaded because both halves of the bug depend on the deck:
// which block is widest, and whether its pill needs the scroll.

import { expect, test, type Page } from '@playwright/test';

// 769 is the first width above the phone layout. Seven blocks kept their
// desktop tracks there and ran past the viewport on every deck (DEC-1017).
const WIDTHS = [390, 769, 1100];

type RootBox = {
  docScrollWidth: number;
  rootScrollWidth: number;
  rootClientWidth: number;
  rootScrollLeft: number;
  pillInTrack: boolean;
};

async function deckIds(page: Page): Promise<string[]> {
  const r = await page.request.get('/data/index.json');
  const idx = (await r.json()) as { commanders: { id: string }[] };
  return idx.commanders.map((c) => c.id);
}

// The selector's smooth scroll is still running when the guide first paints.
// Resolve once neither the root nor the track has moved for 300ms. The web
// fonts come first: the fallback faces are wider, and at 769px a section
// heading set in them runs past the viewport (DEC-1017).
async function settledRootBox(page: Page): Promise<RootBox> {
  return page.evaluate(
    () =>
      new Promise<RootBox>((resolve) => {
        const root = document.querySelector('.gv1-root')!;
        const track = document.querySelector('.gv1-selector-track')!;
        const read = () => `${root.scrollLeft}|${track.scrollLeft}`;
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
          const t = track.getBoundingClientRect();
          const p = track.querySelector('.gv1-active')?.getBoundingClientRect();
          resolve({
            docScrollWidth: document.documentElement.scrollWidth,
            rootScrollWidth: root.scrollWidth,
            rootClientWidth: root.clientWidth,
            rootScrollLeft: root.scrollLeft,
            pillInTrack: !!p && p.left >= t.left - 1 && p.right <= t.right + 1,
          });
        };
        void document.fonts.ready.then(() => setTimeout(tick, 50));
      }),
  );
}

for (const width of WIDTHS) {
  test.describe(`DEC-1008 @ ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    test('every deck guide fits the viewport with the root unscrolled', async ({ page }) => {
      test.setTimeout(180_000);
      const offenders: string[] = [];

      for (const deck of await deckIds(page)) {
        await page.goto(`/deck/${deck}`);
        await page.locator('.gv1-perf-grid').waitFor();
        await page.locator('.gv1-selector-track .gv1-active').waitFor();
        const m = await settledRootBox(page);

        const wide = m.rootScrollWidth > m.rootClientWidth + 1 || m.docScrollWidth > width + 1;
        if (wide || m.rootScrollLeft !== 0 || !m.pillInTrack) {
          offenders.push(
            `${deck}: root ${m.rootScrollWidth} / ${m.rootClientWidth}, scrollLeft ${m.rootScrollLeft}, ` +
              `document ${m.docScrollWidth}, active pill ${m.pillInTrack ? 'in' : 'outside'} the rail`,
          );
        }
      }

      expect(offenders, `Deck guides overflowing or shifted at ${width}px`).toEqual([]);
    });
  });
}
