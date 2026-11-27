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
//
// The index has had no brewing deck since 2026-11-27, so the cases mark one
// (markable below): each deck is read as it is and again as a brewing deck.

import { expect, test, type Page } from './support/test';

const WIDTHS = [390, 1280];

type IndexDeck = { id: string; name: string; status?: string };
type Rect = { left: number; right: number; top: number; bottom: number };
type PillParts = Record<'flag' | 'badge' | 'num' | 'pips' | 'name' | 'cmd' | 'bracket', Rect | null>;
type PillBorder = { name: string; active: boolean; badge: boolean; borderStyle: string };

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

// The app reads a deck's status from its deck.json (normalize.ts). While
// `marked.id` names a deck, its deck.json is answered with status "brewing".
// The deck data cache is dropped before each load, so every load fetches the
// files again and a deck marked before reads as it is. `brewing` holds, for
// each deck id, whether the deck.json the route last served says brewing:
// the state a case expects is read from there.
type Marked = { id: string | null; brewing: Record<string, boolean> };
async function markable(page: Page): Promise<Marked> {
  const marked: Marked = { id: null, brewing: {} };
  await page.addInitScript(() => {
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith('gv1-deck-data-')) localStorage.removeItem(key);
    }
  });
  await page.route('**/data/commanders/*/deck.json', async (route) => {
    const response = await route.fetch();
    const id = new URL(route.request().url()).pathname.split('/').at(-2)!;
    const deck = (await response.json()) as { status?: string };
    const json = id === marked.id ? { ...deck, status: 'brewing' } : deck;
    marked.brewing[id] = json.status === 'brewing';
    await route.fulfill({ response, json });
  });
  return marked;
}

// Rects are relative to the pill's top-left corner and come from one
// synchronous read, so they do not depend on how far the selector's smooth
// scroll has moved the pill. A part the browser does not show (display: none,
// visibility: hidden, opacity 0) is missing (null).
async function activePillParts(page: Page): Promise<PillParts> {
  return page.evaluate(async () => {
    await document.fonts.ready;
    const pill = document.querySelector('.gv1-selector-track .gv1-active')!;
    const o = pill.getBoundingClientRect();
    const rect = (sel: string) => {
      const el = pill.querySelector(sel);
      const shown = el?.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
      const b = shown ? el!.getBoundingClientRect() : null;
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

// Each pill by its deck's name, so a case reads it by the deck it shows, not
// by the class the selector gave it.
async function pillBorders(page: Page): Promise<PillBorder[]> {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll('.gv1-selector-track .gv1-sel-pill'), (pill) => ({
      name: pill.querySelector('.gv1-sel-pill-name')?.textContent?.trim() ?? '',
      active: pill.classList.contains('gv1-active'),
      badge:
        pill.querySelector('.gv1-brewing-pill')?.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }) ??
        false,
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
      test.setTimeout(240_000);
      const offenders: string[] = [];
      const marked = await markable(page);

      for (const deck of await indexDecks(page)) {
        for (const mark of [false, true]) {
          marked.id = mark ? deck.id : null;
          const label = mark ? `${deck.id} (marked brewing)` : deck.id;
          await openDeck(page, deck.id);
          const m = await activePillParts(page);
          const brewing = marked.brewing[deck.id];
          expect(brewing, `${label}: the route served its deck.json`).toBeDefined();

          if (!m.flag) {
            offenders.push(`${label}: the active pill has no NOW SCRYING flag`);
            continue;
          }
          if (brewing && !m.badge) {
            offenders.push(`${label}: a brewing deck, but its pill has no BREWING badge`);
          }
          if (!brewing && m.badge) {
            offenders.push(`${label}: a built deck, but its pill has a BREWING badge`);
          }
          if (m.badge && intersects(m.flag, m.badge)) {
            offenders.push(`${label}: the flag (${box(m.flag)}) covers the badge (${box(m.badge)})`);
          }
          for (const part of CONTENT) {
            const r = m[part];
            if (!r) {
              offenders.push(`${label}: the active pill has no ${part}`);
              continue;
            }
            if (intersects(m.flag, r)) {
              offenders.push(`${label}: the flag (${box(m.flag)}) covers the ${part} (${box(r)})`);
            }
            if (m.badge && intersects(m.badge, r)) {
              offenders.push(`${label}: the badge (${box(m.badge)}) covers the ${part} (${box(r)})`);
            }
          }
        }
      }

      expect(offenders, `Active pills with covered content at ${width}px (pill coordinates)`).toEqual([]);
    });

    test('a brewing pill has a dashed border and a built pill a solid one, active or not', async ({
      page,
    }) => {
      const decks = await indexDecks(page);
      const marked = await markable(page);
      // The first deck, marked brewing, and another deck the index lists as built.
      const brewing = decks[0];
      const built = decks.find((d) => d.id !== brewing.id && d.status !== 'brewing');
      expect(built, 'a built deck besides the marked one').toBeDefined();
      marked.id = brewing.id;

      // The brewing deck's page gives the active brewing pill; the built
      // deck's page gives the active built pill. Each gives the other two.
      // Every pill is read by its deck, brewing or built as the deck.json the
      // route served says.
      const idByName = Object.fromEntries(decks.map((d) => [d.name, d.id]));
      const seen: Record<string, Set<string>> = {};
      for (const deck of [brewing, built!]) {
        await openDeck(page, deck.id);
        const pills = await pillBorders(page);
        expect(pills.map((p) => p.name).sort(), 'one pill for each deck of the index').toEqual(
          decks.map((d) => d.name).sort(),
        );
        for (const p of pills) {
          const served = marked.brewing[idByName[p.name]];
          expect(served, `${p.name}: the route served its deck.json`).toBeDefined();
          const kind = `${served ? 'brewing' : 'built'}, ${p.active ? 'active' : 'not active'}`;
          (seen[kind] ??= new Set()).add(`${p.borderStyle}${p.badge ? ', BREWING badge' : ''}`);
        }
      }

      const styles = Object.fromEntries(Object.entries(seen).map(([k, v]) => [k, [...v].sort()]));
      expect(styles).toEqual({
        'brewing, active': ['dashed, BREWING badge'],
        'brewing, not active': ['dashed, BREWING badge'],
        'built, active': ['solid'],
        'built, not active': ['solid'],
      });
    });
  });
}
