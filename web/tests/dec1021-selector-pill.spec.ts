// DEC-1021: on the active selector pill, the NOW SCRYING flag and the BREWING
// badge cover nothing, and a brewing deck's pill has a dashed border.
//
// The flag sat in the pill's top-right corner, over the right end of the top
// row: the BREWING badge on a brewing deck, the mana pips on a built one. And
// `.gv1-sel-pill-brewing` never applied, because `.gv1-sel-pill` reset the
// border after it.
//
// Every deck is loaded because what sits under the flag depends on the deck:
// its status, its number of pips and the length of its commander line.

import { expect, test, type Page } from '@playwright/test';

const WIDTHS = [390, 1280];

type IndexDeck = { id: string; status?: string };
type Rect = { left: number; right: number; top: number; bottom: number };
type PillParts = Record<'flag' | 'badge' | 'num' | 'pips' | 'name' | 'cmd' | 'bracket', Rect | null>;
type PillBorder = { brewing: boolean; active: boolean; borderStyle: string };

// What the flag and the badge must stay clear of.
const CONTENT = ['num', 'pips', 'name', 'cmd', 'bracket'] as const;

async function indexDecks(page: Page): Promise<IndexDeck[]> {
  const r = await page.request.get('/data/index.json');
  return ((await r.json()) as { commanders: IndexDeck[] }).commanders;
}

async function openDeck(page: Page, deck: string): Promise<void> {
  await page.goto(`/deck/${deck}`);
  await page.locator('.gv1-selector-track .gv1-active').waitFor();
}

// Rects are relative to the pill's top-left corner and come from one
// synchronous read, so they do not depend on how far the selector's smooth
// scroll has moved the pill.
async function activePillParts(page: Page): Promise<PillParts> {
  return page.evaluate(async () => {
    await document.fonts.ready;
    const pill = document.querySelector('.gv1-selector-track .gv1-active')!;
    const o = pill.getBoundingClientRect();
    const rect = (sel: string) => {
      const b = pill.querySelector(sel)?.getBoundingClientRect();
      return b
        ? { left: b.left - o.left, right: b.right - o.left, top: b.top - o.top, bottom: b.bottom - o.top }
        : null;
    };
    return {
      flag: rect('.gv1-sel-pill-flag'),
      badge: rect('.gv1-brewing-pill'),
      num: rect('.gv1-sel-pill-top > .gv1-dim'),
      pips: rect('.gv1-pips'),
      name: rect('.gv1-sel-pill-name'),
      cmd: rect('.gv1-sel-pill-cmd'),
      bracket: rect('.gv1-sel-pill-bracket'),
    };
  });
}

async function pillBorders(page: Page): Promise<PillBorder[]> {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll('.gv1-selector-track .gv1-sel-pill'), (pill) => ({
      brewing: pill.classList.contains('gv1-sel-pill-brewing'),
      active: pill.classList.contains('gv1-active'),
      borderStyle: getComputedStyle(pill).borderStyle,
    })),
  );
}

const intersects = (a: Rect, b: Rect) =>
  a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

const box = (r: Rect) =>
  `x ${r.left.toFixed(1)}–${r.right.toFixed(1)}, y ${r.top.toFixed(1)}–${r.bottom.toFixed(1)}`;

for (const width of WIDTHS) {
  test.describe(`DEC-1021 @ ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    test('the flag and the BREWING badge cover nothing on any active pill', async ({ page }) => {
      test.setTimeout(120_000);
      const offenders: string[] = [];

      for (const deck of await indexDecks(page)) {
        await openDeck(page, deck.id);
        const m = await activePillParts(page);

        if (!m.flag) {
          offenders.push(`${deck.id}: the active pill has no NOW SCRYING flag`);
          continue;
        }
        if (deck.status === 'brewing' && !m.badge) {
          offenders.push(`${deck.id}: a brewing deck, but its pill has no BREWING badge`);
        }
        if (m.badge && intersects(m.flag, m.badge)) {
          offenders.push(`${deck.id}: the flag (${box(m.flag)}) covers the badge (${box(m.badge)})`);
        }
        for (const part of CONTENT) {
          const r = m[part];
          if (!r) {
            offenders.push(`${deck.id}: the active pill has no ${part}`);
            continue;
          }
          if (intersects(m.flag, r)) {
            offenders.push(`${deck.id}: the flag (${box(m.flag)}) covers the ${part} (${box(r)})`);
          }
          if (m.badge && intersects(m.badge, r)) {
            offenders.push(`${deck.id}: the badge (${box(m.badge)}) covers the ${part} (${box(r)})`);
          }
        }
      }

      expect(offenders, `Active pills with covered content at ${width}px (pill coordinates)`).toEqual([]);
    });

    test('a brewing pill has a dashed border and a built pill a solid one, active or not', async ({
      page,
    }) => {
      const decks = await indexDecks(page);
      const brewing = decks.find((d) => d.status === 'brewing');
      const built = decks.find((d) => d.status !== 'brewing');
      test.skip(!brewing || !built, 'the index needs one brewing deck and one built deck');

      // The brewing deck's page gives the active brewing pill; the built
      // deck's page gives the active built pill. Each gives the other two.
      const seen: Record<string, Set<string>> = {};
      for (const deck of [brewing!, built!]) {
        await openDeck(page, deck.id);
        for (const p of await pillBorders(page)) {
          const kind = `${p.brewing ? 'brewing' : 'built'}, ${p.active ? 'active' : 'not active'}`;
          (seen[kind] ??= new Set()).add(p.borderStyle);
        }
      }

      const styles = Object.fromEntries(Object.entries(seen).map(([k, v]) => [k, [...v].sort()]));
      expect(styles).toEqual({
        'brewing, active': ['dashed'],
        'brewing, not active': ['dashed'],
        'built, active': ['solid'],
        'built, not active': ['solid'],
      });
    });
  });
}
