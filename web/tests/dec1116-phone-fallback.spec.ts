// DEC-1116: the deck guide on a 320px phone in the fallback faces.
//
// The fallback faces are wider than the web fonts, and `display=swap` draws
// them until the web fonts arrive, and for good when they fail. In Georgia
// five guides ran past a 320px viewport, where the root clips them:
// eternal-agony 373 / 320, grave-dividends 385, broodfire-hatchery 355,
// witherbloom-the-balancer 331 and titan-convergence 325. Three kinds of text
// did it: one word of the Commander's deck name ("Convergence"), the longest
// word of an engine tile's note, and the Commander Spellbook URLs in the
// combo and win-condition texts. Three rules at 768px and below let these
// texts break inside a word: on `.gv1-cmd-deckname`, on the engine tile note,
// and on `.gv1-wincon-desc` and `.gv1-combo-desc`. An engine tile name keeps
// `break-word`, so a card name stays whole with the web fonts.
//
// The first case blocks the web fonts. The second also sets a wider face on
// the decks where each rule acts in it. In that face the DEC-1116 rules leave
// two guides wider than 320px, each from an engine tile name, and the second
// case leaves them out: the-white-forge 337 ("Archaeomancer's") and
// witherbloom-the-balancer 324 ("Remembrance"). Three more ran past it on the
// engine's role title: hidden-legion 336, tidal-legion 338 and
// gandalf-party-guest 338. DEC-1156 makes the title smaller at 768px and
// below, and the second case reads these three too. The other cases pin where
// the rules act, that the engine tiles keep each word whole with the web
// fonts, and that the eternal-agony note that this issue reworded breaks only
// between words in the fallback faces.

import { expect, test, type Page } from './support/test';

// Stand-ins for a face wider than the web fonts, as in
// dec1043-band-rules.spec.ts. Linux has no Verdana or Menlo; DejaVu Sans and
// DejaVu Sans Mono have about the same widths.
const WIDE_FACES =
  ":root { --gv1-serif: Verdana, 'DejaVu Sans', sans-serif; --gv1-serif-italic: Verdana, 'DejaVu Sans', sans-serif;" +
  " --gv1-mono: Menlo, 'DejaVu Sans Mono', monospace; }";

// The texts that the DEC-1116 rules let break inside a word.
const RULED = ['.gv1-cmd-deckname', '.gv1-engine-cards .gv1-card-tile-note', '.gv1-wincon-desc', '.gv1-combo-desc'].join(
  ', ',
);

// Resolve once the fonts are in (or have failed) and the page has not moved
// for 300ms: the selector's smooth scroll is still running at first paint.
async function openSettled(page: Page, deck: string, css?: string): Promise<void> {
  await page.goto(`/deck/${deck}`);
  if (css) await page.addStyleTag({ content: css });
  await page.locator('.gv1-perf-grid').waitFor();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      const root = document.querySelector('.gv1-root');
      const read = () => `${window.scrollY}|${root?.scrollWidth}|${document.body.scrollHeight}`;
      const started = Date.now();
      let last = read();
      let still = 0;
      const tick = () => {
        const now = read();
        still = now === last ? still + 1 : 0;
        last = now;
        if (still >= 6 || Date.now() - started > 5000) resolve();
        else setTimeout(tick, 50);
      };
      setTimeout(tick, 50);
    });
  });
}

type Reading = { scrollWidth: number; clientWidth: number; loadedFaces: number; past: string[] };

// The root's widths, the faces that loaded, and each ruled text that runs past
// its own content edge (so a failure names what to fix).
async function readGuide(page: Page): Promise<Reading> {
  return page.evaluate((ruled) => {
    const root = document.querySelector('.gv1-root')!;
    const past: string[] = [];
    for (const el of document.querySelectorAll(ruled)) {
      const cs = getComputedStyle(el);
      const edge = el.getBoundingClientRect().right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
      const range = document.createRange();
      range.selectNodeContents(el);
      const reach = Math.max(...[...range.getClientRects()].filter((r) => r.width > 0).map((r) => r.right));
      if (reach > edge + 0.5) {
        const cls = (el.getAttribute('class') ?? '').trim().split(/\s+/).join('.');
        const text = (el.textContent ?? '').trim().slice(0, 40);
        past.push(`${cls} "${text}" reaches ${reach.toFixed(1)}, its edge ${edge.toFixed(1)}`);
      }
    }
    return {
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      loadedFaces: [...document.fonts].filter((f) => f.status === 'loaded').length,
      past,
    };
  }, RULED);
}

async function offenders(page: Page, decks: string[], css?: string): Promise<string[]> {
  const out: string[] = [];
  for (const deck of decks) {
    await openSettled(page, deck, css);
    const g = await readGuide(page);
    expect(g.loadedFaces, `${deck}: a web font loaded, so the fallback faces are not under test`).toBe(0);
    if (g.scrollWidth > g.clientWidth || g.past.length > 0) {
      out.push(`${deck}: root ${g.scrollWidth} / ${g.clientWidth}${g.past.map((p) => `; ${p}`).join('')}`);
    }
  }
  return out;
}

test.describe('DEC-1116 @ 320px, web fonts blocked', () => {
  test.use({ cards: 'seeded', fonts: 'blocked', viewport: { width: 320, height: 900 } });

  test('the five guides that ran past the viewport in the fallback faces fit it', async ({ page }) => {
    test.setTimeout(60_000);
    const decks = ['eternal-agony', 'grave-dividends', 'broodfire-hatchery', 'witherbloom-the-balancer', 'titan-convergence'];
    expect(await offenders(page, decks), 'Guides wider than a 320px viewport in the fallback faces').toEqual([]);
  });

  test('with Verdana and Menlo, the guides where each rule acts fit the viewport', async ({ page }) => {
    test.setTimeout(60_000);
    const decks = [
      'titan-convergence', // deck name
      'exponential-growth', // deck name
      'eternal-agony', // tile note text (393 / 320 on main)
      'zada-hedron-grinder', // tile note
      'grave-dividends', // win-condition and combo URLs
      'broodfire-hatchery', // combo URLs
      'hidden-legion', // engine role title (DEC-1156; 336 / 320 before it)
      'tidal-legion', // engine role title (338)
      'gandalf-party-guest', // engine role title (338)
    ];
    expect(await offenders(page, decks, WIDE_FACES), 'Guides wider than a 320px viewport in a wide face').toEqual([]);
  });
});

// Each run of non-space characters in an engine tile's name or note that the
// browser splits over two lines, with "|" where the line ends. A line end
// after a hyphen or a dash, or before the "{" of a mana symbol, is an
// ordinary break, and does not count. With `tile`, only the tile of that card
// name is read.
async function wordsBroken(page: Page, tile?: string): Promise<string[]> {
  return page.evaluate((tile) => {
    const out: string[] = [];
    const tiles = [...document.querySelectorAll('.gv1-engine-cards .gv1-card-tile')].filter(
      (t) => !tile || t.querySelector('.gv1-card-tile-name')?.textContent?.trim() === tile,
    );
    if (tile && tiles.length === 0) return [`no engine tile named ${tile}`];
    for (const el of tiles.flatMap((t) => [...t.querySelectorAll('.gv1-card-tile-name, .gv1-card-tile-note')])) {
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const text = n.textContent ?? '';
        const re = /\S+/g;
        for (let m = re.exec(text); m; m = re.exec(text)) {
          const range = document.createRange();
          let marked = '';
          let inside = false;
          let last: number | null = null;
          for (let i = 0; i < m[0].length; i++) {
            range.setStart(n, m.index + i);
            range.setEnd(n, m.index + i + 1);
            const box = [...range.getClientRects()].find((r) => r.width > 0);
            const top: number | null = box ? Math.round(box.top) : last;
            if (last !== null && top !== last) {
              marked += '|';
              if (!/[-‐–—]/.test(m[0][i - 1]) && m[0][i] !== '{') inside = true;
            }
            marked += m[0][i];
            last = top;
          }
          if (inside) out.push(`${el.className.split(' ').pop()}: ${marked}`);
        }
      }
    }
    return out;
  }, tile);
}

test.describe('DEC-1116 @ phone widths, web fonts', () => {
  test.use({ cards: 'seeded' });

  // In the two-column engine, "Archaeomancer's Map" (the-white-forge) and the
  // note "(sac an artifact, enchantment or token)" (eternal-agony) are the
  // longest words that fit a column. A rule that breaks a tile name inside a
  // word, or the note written "artifact/enchantment/token", breaks one of
  // them at these widths.
  test('the engine tiles keep each word whole', async ({ page }) => {
    test.setTimeout(90_000);
    const out: string[] = [];
    for (const width of [320, 330, 341, 360]) {
      await page.setViewportSize({ width, height: 900 });
      for (const deck of ['the-white-forge', 'eternal-agony']) {
        await openSettled(page, deck);
        const faces = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').length);
        expect(faces, `${deck}@${width}: no web font loaded, so the web fonts are not under test`).toBeGreaterThan(0);
        for (const word of await wordsBroken(page)) out.push(`${deck}@${width}: ${word}`);
      }
    }
    expect(out, 'Engine tile words that break inside with the web fonts').toEqual([]);
  });
});

test.describe('DEC-1116 @ 320px, web fonts blocked: the eternal-agony note', () => {
  test.use({ cards: 'seeded', fonts: 'blocked', viewport: { width: 320, height: 900 } });

  // The note of Beseech the Mirror names its three kinds with spaces, so it
  // breaks only between words. Written with a slash ("enchantment/token)"),
  // the note rule breaks that word inside in both faces at 320px.
  test('the note of Beseech the Mirror breaks only between words', async ({ page }) => {
    test.setTimeout(60_000);
    const out: string[] = [];
    for (const [face, css] of [
      ['fallback serif', undefined],
      ['Verdana and Menlo', WIDE_FACES],
    ] as const) {
      await openSettled(page, 'eternal-agony', css);
      for (const word of await wordsBroken(page, 'Beseech the Mirror')) out.push(`${face}: ${word}`);
    }
    expect(out, 'Words of the Beseech the Mirror tile that break inside in a fallback face').toEqual([]);
  });
});

async function open(page: Page, deck: string): Promise<void> {
  await page.goto(`/deck/${deck}`);
  await page.locator('.gv1-perf-grid').waitFor();
  await page.evaluate(() => document.fonts.ready);
}

// What the deck name and the ruled texts compute, and the name's box against
// its parent's content box.
async function readRules(page: Page) {
  return page.evaluate(() => {
    const name = document.querySelector('.gv1-cmd-deckname')!;
    const cs = getComputedStyle(name);
    const parent = name.parentElement!;
    const ps = getComputedStyle(parent);
    const track =
      parent.getBoundingClientRect().width -
      parseFloat(ps.paddingLeft) -
      parseFloat(ps.paddingRight) -
      parseFloat(ps.borderLeftWidth) -
      parseFloat(ps.borderRightWidth);
    const wrap = (sel: string) => {
      const el = document.querySelector(sel);
      return el ? getComputedStyle(el).overflowWrap : 'missing';
    };
    return {
      fontSize: cs.fontSize,
      maxWidth: cs.maxWidth,
      width: Math.round(name.getBoundingClientRect().width * 10) / 10,
      track: Math.round(track * 10) / 10,
      wrap: {
        name: cs.overflowWrap,
        tileName: wrap('.gv1-engine-cards .gv1-card-tile-name'),
        tileNote: wrap('.gv1-engine-cards .gv1-card-tile-note'),
        wincon: wrap('.gv1-wincon-desc'),
        combo: wrap('.gv1-combo-desc'),
        otherTileName: wrap('.gv1-wincon .gv1-card-tile-name, .gv1-combo .gv1-card-tile-name'),
        otherTileNote: wrap('.gv1-wincon .gv1-card-tile-note, .gv1-combo .gv1-card-tile-note'),
      },
    };
  });
}

// The rules' place in the stylesheet: the 768px block, the engine tile note
// only, and the deck name's other values in that block. Cases from the
// review of PR #50 (DEC-1134, K1 to K3).
test.describe('DEC-1116 rules: where they act', () => {
  test.use({ cards: 'seeded', fonts: 'blocked' });

  test('at 768px and below the deck name is 56px and spans its track', async ({ page }) => {
    const out: string[] = [];
    for (const width of [320, 390, 768]) {
      await page.setViewportSize({ width, height: 900 });
      for (const deck of ['titan-convergence', 'eternal-agony']) {
        await open(page, deck);
        const r = await readRules(page);
        if (r.fontSize !== '56px' || r.maxWidth !== 'none' || Math.abs(r.width - r.track) > 0.5) {
          out.push(`${deck}@${width}: font-size ${r.fontSize}, max-width ${r.maxWidth}, width ${r.width} of ${r.track}`);
        }
      }
    }
    expect(out, 'Deck names at 768px and below that are not 56px across their track').toEqual([]);
  });

  test('at 768px and below the tile rule reaches only the engine tile note', async ({ page }) => {
    const out: string[] = [];
    for (const width of [320, 390, 768]) {
      await page.setViewportSize({ width, height: 900 });
      await open(page, 'eternal-agony');
      const { tileName, tileNote, otherTileName, otherTileNote } = (await readRules(page)).wrap;
      if (tileName !== 'break-word' || tileNote !== 'anywhere' || otherTileName !== 'break-word' || otherTileNote !== 'break-word') {
        out.push(
          `@${width}: engine tile name ${tileName}, note ${tileNote}; combo or win-condition tile name ${otherTileName}, note ${otherTileNote}`,
        );
      }
    }
    expect(out, 'Widths where the tile rule does not reach exactly the engine tile note').toEqual([]);
  });

  // DEC-1046 scales the deck name from 769px to about 1000px, so the 88px
  // size is pinned from 1024px only.
  test('above 768px the DEC-1116 rules do not apply, and the deck name is 88px from 1024px', async ({ page }) => {
    const out: string[] = [];
    const want = { name: 'break-word', tileName: 'break-word', tileNote: 'break-word', wincon: 'normal', combo: 'normal' };
    for (const width of [769, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await open(page, 'eternal-agony');
      const r = await readRules(page);
      const wrap = { name: r.wrap.name, tileName: r.wrap.tileName, tileNote: r.wrap.tileNote, wincon: r.wrap.wincon, combo: r.wrap.combo };
      if ((width >= 1024 && r.fontSize !== '88px') || JSON.stringify(wrap) !== JSON.stringify(want)) {
        out.push(`@${width}: font-size ${r.fontSize}, overflow-wrap ${JSON.stringify(wrap)}`);
      }
    }
    expect(out, 'Widths above 768px where the deck name or a ruled text differs from main').toEqual([]);
  });
});
