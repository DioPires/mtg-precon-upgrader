// DEC-1043 band rules (769 to 824px) and the Commander's 420px art column.
// The DEC-1101 review wrote these cases (B1 to B4). Each case reads what a
// user sees in the band and at its two edges, so that a change to one of the
// band's declarations, or to the art column, fails it.

import { expect, test, type Page } from './support/test';

// Stand-ins for a face wider than the web fonts. Linux has no Verdana or
// Menlo; DejaVu Sans and DejaVu Sans Mono have about the same widths.
const WIDE_FACES =
  ":root { --gv1-serif: Verdana, 'DejaVu Sans', sans-serif; --gv1-serif-italic: Verdana, 'DejaVu Sans', sans-serif;" +
  " --gv1-mono: Menlo, 'DejaVu Sans Mono', monospace; }";

async function openSettled(page: Page, path: string, ready: string, css?: string): Promise<void> {
  await page.goto(path);
  if (css) await page.addStyleTag({ content: css });
  await page.locator(ready).first().waitFor();
  await settle(page);
}

// The fonts are in (or have failed), and nothing has moved for 300ms.
async function settle(page: Page): Promise<void> {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      const root = document.querySelector('.gv1-root');
      const read = () => `${window.scrollY}|${root?.scrollLeft}|${document.body.scrollHeight}|${document.body.scrollWidth}`;
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

async function resize(page: Page, width: number): Promise<void> {
  await page.setViewportSize({ width, height: 900 });
  await settle(page);
}

type Cell = { label: string; left: number; right: number; top: number; padL: number; padR: number };
type Strip = { left: number; right: number; cells: Cell[]; bracketGaps: number[]; past: string[] };

// The stats strip's content box, its cells, the space between the rows of
// bracket counts, and every cell or text that passes the strip's content edge
// or its own cell's content edge.
async function readStrip(page: Page): Promise<Strip> {
  return page.evaluate(() => {
    const strip = document.querySelector('.gv1-codex-stats')!;
    const sr = strip.getBoundingClientRect();
    const scs = getComputedStyle(strip);
    const left = sr.left + parseFloat(scs.borderLeftWidth) + parseFloat(scs.paddingLeft);
    const right = sr.right - parseFloat(scs.borderRightWidth) - parseFloat(scs.paddingRight);
    const past: string[] = [];
    const cells = [...strip.querySelectorAll(':scope > .gv1-codex-stat')].map((cell) => {
      const r = cell.getBoundingClientRect();
      const cs = getComputedStyle(cell);
      const label = (cell.firstElementChild?.textContent ?? '').trim();
      const edge = r.right - parseFloat(cs.paddingRight);
      if (r.right > right + 0.5) past.push(`${label} cell ends at ${r.right.toFixed(1)}, strip edge ${right.toFixed(1)}`);
      for (const child of cell.children) {
        const range = document.createRange();
        range.selectNodeContents(child);
        for (const t of range.getClientRects()) {
          if (t.width > 0 && t.right > edge + 0.5) {
            past.push(`${label}: "${(child.textContent ?? '').trim()}" reaches ${t.right.toFixed(1)}, cell edge ${edge.toFixed(1)}`);
            break;
          }
        }
      }
      return {
        label,
        left: r.left,
        right: r.right,
        top: Math.round(r.top),
        padL: parseFloat(cs.paddingLeft),
        padR: parseFloat(cs.paddingRight),
      };
    });
    const rows = [...document.querySelectorAll('.gv1-codex-stat-brackets > .gv1-codex-bracket-row')].map((el) =>
      el.getBoundingClientRect(),
    );
    const tops = [...new Set(rows.map((r) => Math.round(r.top)))].sort((a, b) => a - b);
    const bracketGaps = tops.slice(1).map((top, i) => {
      const above = Math.max(...rows.filter((r) => Math.round(r.top) === tops[i]).map((r) => r.bottom));
      const below = Math.min(...rows.filter((r) => Math.round(r.top) === top).map((r) => r.top));
      return Math.round((below - above) * 10) / 10;
    });
    return { left, right, cells, bracketGaps, past };
  });
}

function rowsOf(cells: Cell[]): Cell[][] {
  const tops = [...new Set(cells.map((c) => c.top))].sort((a, b) => a - b);
  return tops.map((top) => cells.filter((c) => c.top === top));
}

// Distinct left edges of the Codex cards: the number of columns.
async function cardColumns(page: Page): Promise<number> {
  return page.evaluate(
    () => new Set([...document.querySelectorAll('.gv1-codex-grid > .gv1-codex-card')].map((c) => Math.round(c.getBoundingClientRect().left))).size,
  );
}

type Head = { titleLines: number[]; titleOffset: number; noteWidth: number; noteWord: number };

// The Performance heading: the width of each line of the title, the title's
// offset from the heading's left edge, the note's width and its widest word.
async function readPerfHead(page: Page): Promise<Head> {
  return page.evaluate(() => {
    const head = document.querySelector('.gv1-perf .gv1-section-head')!;
    const title = head.querySelector('.gv1-section-title')!;
    const note = head.querySelector('.gv1-mono-xs')!;
    const range = document.createRange();
    range.selectNodeContents(title);
    const byLine = new Map<number, { left: number; right: number }>();
    for (const r of range.getClientRects()) {
      if (r.width === 0) continue;
      const key = Math.round(r.top);
      const line = byLine.get(key) ?? { left: r.left, right: r.right };
      byLine.set(key, { left: Math.min(line.left, r.left), right: Math.max(line.right, r.right) });
    }
    let noteWord = 0;
    const walker = document.createTreeWalker(note, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const text = n.textContent ?? '';
      for (const m of text.matchAll(/\S+/g)) {
        const word = document.createRange();
        word.setStart(n, m.index ?? 0);
        word.setEnd(n, (m.index ?? 0) + m[0].length);
        noteWord = Math.max(noteWord, word.getBoundingClientRect().width);
      }
    }
    return {
      titleLines: [...byLine.values()].map((l) => Math.round((l.right - l.left) * 10) / 10),
      titleOffset: Math.round((title.getBoundingClientRect().left - head.getBoundingClientRect().left) * 10) / 10,
      noteWidth: note.getBoundingClientRect().width,
      noteWord,
    };
  });
}

test.describe('DEC-1101 kill cases, web fonts', () => {
  test.use({ cards: 'seeded', viewport: { width: 769, height: 900 } });

  test('stats strip in the band: the cells fill each row, share it evenly, keep 16px sides, and the bracket rows sit 8px apart', async ({
    page,
  }) => {
    await openSettled(page, '/codex', '.gv1-codex-grid .gv1-codex-card');
    const faults: string[] = [];
    for (const width of [769, 787, 824]) {
      await resize(page, width);
      const strip = await readStrip(page);
      for (const row of rowsOf(strip.cells)) {
        const first = row[0];
        const last = row[row.length - 1];
        if (Math.abs(first.left - strip.left) > 0.5 || Math.abs(last.right - strip.right) > 0.5) {
          faults.push(`${width}px: the row ${row.map((c) => c.label).join(', ')} spans ${first.left.toFixed(1)} to ${last.right.toFixed(1)}, the strip ${strip.left.toFixed(1)} to ${strip.right.toFixed(1)}`);
        }
      }
      // At 824px five even cells fit on one row with room to spare (112px
      // each; the widest value needs 105px with the web fonts).
      if (width === 824) {
        const widths = strip.cells.map((c) => c.right - c.left);
        if (rowsOf(strip.cells).length !== 1 || Math.max(...widths) - Math.min(...widths) > 0.5) {
          faults.push(`${width}px: cells ${widths.map((w) => w.toFixed(1)).join(', ')} on ${rowsOf(strip.cells).length} row(s)`);
        }
      }
      for (const c of strip.cells) {
        if (c.padL !== 16 || c.padR !== 16) faults.push(`${width}px: ${c.label} cell has ${c.padL}px / ${c.padR}px sides`);
      }
      if (strip.bracketGaps.length === 0) faults.push(`${width}px: the bracket counts sit on one row`);
      for (const gap of strip.bracketGaps) if (Math.abs(gap - 8) > 0.5) faults.push(`${width}px: bracket rows ${gap}px apart`);
      faults.push(...strip.past.map((p) => `${width}px: ${p}`));
    }
    expect(faults, 'Codex stats strip in the band').toEqual([]);
  });

  test('Performance heading in the band: the note at its narrowest, a balanced two-line title at 769px, one line at 824px, the base rune track', async ({
    page,
  }) => {
    await openSettled(page, '/deck/eternal-agony', '.gv1-perf-grid');
    await resize(page, 825);
    const base = await readPerfHead(page);
    const faults: string[] = [];
    // The title needs 486px on one line: 12px more than its track at 769px,
    // 43px less than its track at 824px.
    for (const [width, lines] of [
      [769, 2],
      [824, 1],
    ] as const) {
      await resize(page, width);
      const head = await readPerfHead(page);
      if (head.titleLines.length !== lines) faults.push(`${width}px: title on ${head.titleLines.length} lines, expected ${lines}`);
      if (lines === 2 && Math.min(...head.titleLines) < 0.6 * Math.max(...head.titleLines)) {
        faults.push(`${width}px: title lines ${head.titleLines.join(' and ')} px wide are not balanced`);
      }
      if (head.noteWidth > head.noteWord + 0.5) {
        faults.push(`${width}px: note ${head.noteWidth.toFixed(1)}px wide, its widest word ${head.noteWord.toFixed(1)}px`);
      }
      if (head.titleOffset !== base.titleOffset) {
        faults.push(`${width}px: title starts ${head.titleOffset}px from the heading's left edge, ${base.titleOffset}px at 825px`);
      }
    }
    expect(faults, 'Performance heading in the band').toEqual([]);
  });

  test('the band starts at 769px and ends at 824px: two strip cells a row at 768px, two card columns at 769 and 824px, three at 825px', async ({
    page,
  }) => {
    await openSettled(page, '/codex', '.gv1-codex-grid .gv1-codex-card');
    const faults: string[] = [];
    await resize(page, 768);
    const phone = rowsOf((await readStrip(page)).cells).map((row) => row.length);
    if (phone[0] !== 2) faults.push(`768px: strip rows of ${phone.join(', ')} cells, expected 2 a row`);
    for (const [width, columns] of [
      [769, 2],
      [824, 2],
      [825, 3],
    ] as const) {
      await resize(page, width);
      const found = await cardColumns(page);
      if (found !== columns) faults.push(`${width}px: ${found} card columns, expected ${columns}`);
    }
    expect(faults, 'Band bounds').toEqual([]);
  });

  test('Commander: the art column stays 420px wide above 1020px', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openSettled(page, '/deck/titan-convergence', '.gv1-perf-grid');
    const faults: string[] = [];
    for (const width of [1024, 1440]) {
      await resize(page, width);
      const art = await page.evaluate(() => document.querySelector('.gv1-cmd-grid > .gv1-cmd-art-stack')!.getBoundingClientRect().width);
      if (Math.abs(art - 420) > 0.5) faults.push(`${width}px: art column ${art.toFixed(1)}px`);
    }
    expect(faults, 'Commander art column').toEqual([]);
  });
});

test.describe('DEC-1101 kill cases, a face wider than the web fonts', () => {
  test.use({ cards: 'seeded', fonts: 'blocked', viewport: { width: 769, height: 900 } });

  test('stats strip in the band: every cell and value stays inside the strip with Verdana and Menlo', async ({ page }) => {
    await openSettled(page, '/codex', '.gv1-codex-grid .gv1-codex-card', WIDE_FACES);
    const faults: string[] = [];
    for (const width of [769, 787, 800, 810, 824]) {
      await resize(page, width);
      faults.push(...(await readStrip(page)).past.map((p) => `${width}px: ${p}`));
    }
    expect(faults, 'Codex stats strip with a wide face').toEqual([]);
  });
});
