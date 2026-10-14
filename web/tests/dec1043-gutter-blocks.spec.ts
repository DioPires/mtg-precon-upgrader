// DEC-1043: from 769px to 824px three blocks sat in the right gutter, past the
// page's content edge but inside the viewport: the Codex card grid (55.5px
// past at 769px), the Codex stats strip (45.9px) and the deck guide's
// Performance heading (12.3px). Each kept tracks that its content sets. The
// root's width cannot see a block in the gutter, so the first case reads each
// block's furthest right edge against its content edge.
//
// The fallback faces are wider than the web fonts, and `display=swap` draws
// them until the web fonts arrive. In them the same blocks ran past the
// viewport, where the root clips them: at 769px /codex read 773 / 769 and
// every deck guide 860 / 769. At 1024px one word of the Commander's deck name
// pushed the dossier past it (titan-convergence 1042 / 1024). The second case
// fails the web-font requests and reads the root. It also reads each value of
// the Codex stats strip against its cell: with even tracks "3.16" (97px in
// Georgia) ran under the next cell, which hid its last digit.

import { expect, test, type Page } from './support/test';

type Block = { name: string; selector: string; edge: string };

const CODEX_BLOCKS: Block[] = [
  { name: 'Codex card grid', selector: '.gv1-codex-grid', edge: '.gv1-codex' },
  { name: 'Codex stats strip', selector: '.gv1-codex-stats', edge: '.gv1-codex' },
];
const GUIDE_BLOCKS: Block[] = [
  { name: 'Performance heading', selector: '.gv1-perf .gv1-section-head', edge: '.gv1-perf' },
];

// Resolve once the fonts are in (or have failed) and the page has not moved
// for 300ms: the selector's smooth scroll is still running at first paint.
async function openSettled(page: Page, path: string, ready: string): Promise<void> {
  await page.goto(path);
  await page.locator(ready).first().waitFor();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      const root = document.querySelector('.gv1-root');
      const read = () => `${window.scrollY}|${root?.scrollLeft}|${document.body.scrollHeight}`;
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

// Each block's furthest right edge (its own box, or any box inside it, since
// a grid's tracks can run past the grid's box) and its content edge: the
// right edge of the edge element's content box.
async function blocksPastEdge(page: Page, blocks: Block[]): Promise<string[]> {
  return page.evaluate((list) => {
    const out: string[] = [];
    for (const { name, selector, edge } of list) {
      const block = document.querySelector(selector);
      const host = document.querySelector(edge);
      if (!block || !host) {
        out.push(`${name}: ${block ? edge : selector} not found`);
        continue;
      }
      let reach = block.getBoundingClientRect().right;
      for (const el of block.querySelectorAll('*')) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) reach = Math.max(reach, r.right);
      }
      const cs = getComputedStyle(host);
      const contentRight =
        host.getBoundingClientRect().right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
      if (reach > contentRight + 0.5) {
        out.push(`${name}: reaches ${reach.toFixed(1)} against the content edge at ${contentRight.toFixed(1)}`);
      }
    }
    return out;
  }, blocks);
}

type RootReading = { scrollWidth: number; clientWidth: number; loadedFaces: number; past: string[] };

// The root's widths, the faces that loaded, and the outermost boxes that pass
// the viewport (so a failure names what to fix). A box that a scroll
// container inside the root clips, such as a pill of the selector rail, does
// not count.
async function readRoot(page: Page): Promise<RootReading> {
  return page.evaluate(() => {
    const root = document.querySelector('.gv1-root')!;
    const vw = root.clientWidth;
    const clipped = (el: Element) => {
      for (let p = el.parentElement; p && p !== root; p = p.parentElement) {
        if (getComputedStyle(p).overflowX !== 'visible') return true;
      }
      return false;
    };
    const past: string[] = [];
    for (const el of root.querySelectorAll('*')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.right <= vw + 0.5 || clipped(el)) continue;
      const parent = el.parentElement;
      if (parent && parent !== root && parent.getBoundingClientRect().right > vw + 0.5) continue;
      const cls = (el.getAttribute('class') ?? '').trim().split(/\s+/).join('.');
      past.push(`${el.tagName.toLowerCase()}${cls ? '.' + cls : ''} at ${r.right.toFixed(1)}`);
    }
    return {
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      loadedFaces: [...document.fonts].filter((f) => f.status === 'loaded').length,
      past,
    };
  });
}

// Each child of each Codex stat cell against the cell's content edge. A
// child's box is as wide as the cell, so its text is read too: a value wider
// than the cell runs past the box, under the next cell.
async function statsPastCell(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const out: string[] = [];
    for (const cell of document.querySelectorAll('.gv1-codex-stats > .gv1-codex-stat')) {
      const cs = getComputedStyle(cell);
      const edge = cell.getBoundingClientRect().right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
      const label = (cell.firstElementChild?.textContent ?? '').trim();
      for (const child of cell.children) {
        let reach = child.getBoundingClientRect().right;
        const range = document.createRange();
        range.selectNodeContents(child);
        for (const r of range.getClientRects()) if (r.width > 0) reach = Math.max(reach, r.right);
        if (reach > edge + 0.5) {
          const cls = (child.getAttribute('class') ?? '').trim().split(/\s+/).join('.');
          const text = (child.textContent ?? '').trim().replace(/\s+/g, ' ');
          out.push(
            `${label} cell, ${child.tagName.toLowerCase()}.${cls} "${text}": reaches ${reach.toFixed(1)} against the content edge at ${edge.toFixed(1)}`,
          );
        }
      }
    }
    return out;
  });
}

test.describe('DEC-1043 @ 769px, web fonts', () => {
  test.use({ cards: 'seeded', viewport: { width: 769, height: 900 } });

  test('the Codex card grid, the stats strip and the Performance heading stay inside their content edge', async ({
    page,
  }) => {
    await openSettled(page, '/codex', '.gv1-codex-grid .gv1-codex-card');
    const codex = await blocksPastEdge(page, CODEX_BLOCKS);
    await openSettled(page, '/deck/eternal-agony', '.gv1-perf-grid');
    const guide = await blocksPastEdge(page, GUIDE_BLOCKS);

    expect([...codex, ...guide], 'Blocks past their content edge at 769px').toEqual([]);
  });
});

test.describe('DEC-1043, web fonts blocked', () => {
  test.use({ cards: 'seeded', fonts: 'blocked' });

  test('/codex and a deck guide at 769px, and titan-convergence at 1024px, fit the viewport; every Codex stat shows whole', async ({
    page,
  }) => {
    const pages = [
      { path: '/codex', width: 769, ready: '.gv1-codex-grid .gv1-codex-card' },
      { path: '/deck/eternal-agony', width: 769, ready: '.gv1-perf-grid' },
      { path: '/deck/titan-convergence', width: 1024, ready: '.gv1-perf-grid' },
    ];
    const offenders: string[] = [];

    for (const { path, width, ready } of pages) {
      await page.setViewportSize({ width, height: 900 });
      await openSettled(page, path, ready);
      const root = await readRoot(page);

      expect(root.loadedFaces, `${path}: a web font loaded, so the fallback faces are not under test`).toBe(0);
      if (root.scrollWidth > root.clientWidth) {
        offenders.push(`${path} @ ${width}px: root ${root.scrollWidth} / ${root.clientWidth}; ${root.past.join(', ')}`);
      }
    }

    expect(offenders, 'Pages wider than the viewport in the fallback faces').toEqual([]);

    const cut: string[] = [];
    for (const width of [769, 824]) {
      await page.setViewportSize({ width, height: 900 });
      await openSettled(page, '/codex', '.gv1-codex-grid .gv1-codex-card');
      for (const line of await statsPastCell(page)) cut.push(`/codex @ ${width}px: ${line}`);
    }

    expect(cut, 'Codex stats past their cell in the fallback faces').toEqual([]);
  });
});
