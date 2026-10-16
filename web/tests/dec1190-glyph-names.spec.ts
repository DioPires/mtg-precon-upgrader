// DEC-1190 (DEC-1182 classes C1 to C5): what a screen reader reads for each
// glyph, in Chromium's own accessibility tree (CDP), not in the name that
// Playwright computes.
//
// Each case brings a route to one state (the 23 states of the DEC-1182 census,
// and one for a card's mana cost), waits for document.fonts.ready and reads
// Accessibility.getFullAXTree. In every state:
// - no node that Chromium does not ignore has a name that holds a glyph;
// - no name of an element that holds a hidden glyph starts or ends with a space.
// The other checks read the words that stand in for a glyph that carries meaning.
//
// A glyph: a character outside letters, marks, decimal digits, printable ASCII,
// white space, – — ‘ ’ “ ” …, the middle dot and the R0 signs (DEC-1182). R0 is
// a standard sign in a number or a word: № × ± € © § ∞. A minus sign before a
// digit ("−1") is the sign of that number, as "-1" would be.
//
// Chromium reads text as it shows, so an element with `text-transform:
// uppercase` reads its words in capitals: those checks ignore case.

import { expect, test, type CDPSession, type Page, type Route } from './support/test';

const DECK = 'eternal-agony';
const R0 = '№×±€©§∞';

function glyphsIn(text: string): string[] {
  return [...text.replace(/−(?=\d)/g, '')].filter((ch) => {
    const cp = ch.codePointAt(0)!;
    if (cp >= 0x20 && cp <= 0x7e) return false;
    if (/\s/u.test(ch) || '–—‘’“”…·'.includes(ch) || R0.includes(ch)) return false;
    return !/[\p{L}\p{M}\p{Nd}]/u.test(ch);
  });
}

interface AxNode {
  nodeId: string;
  ignored: boolean;
  role?: { value?: unknown };
  name?: { value?: unknown };
  backendDOMNodeId?: number;
  childIds?: string[];
}

const roleOf = (n: AxNode) => String(n.role?.value ?? '');
const nameOf = (n: AxNode) => String(n.name?.value ?? '');

/** Chromium's accessibility tree of the page, read once after the web fonts load. */
class Tree {
  private readonly byId: Map<string, AxNode>;
  private readonly byBackend: Map<number, AxNode>;

  private constructor(
    private readonly cdp: CDPSession,
    readonly nodes: AxNode[],
  ) {
    this.byId = new Map(nodes.map((n) => [n.nodeId, n]));
    this.byBackend = new Map(nodes.filter((n) => n.backendDOMNodeId).map((n) => [n.backendDOMNodeId!, n]));
  }

  static async read(page: Page): Promise<Tree> {
    await page.evaluate(() => document.fonts.ready.then(() => undefined));
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Accessibility.enable');
    await cdp.send('DOM.enable');
    const { nodes } = await cdp.send('Accessibility.getFullAXTree');
    return new Tree(cdp, nodes as AxNode[]);
  }

  /** Each node that Chromium does not ignore and whose name holds a glyph. */
  glyphNames(): string[] {
    return this.nodes
      .filter((n) => !n.ignored && !['InlineTextBox', 'RootWebArea'].includes(roleOf(n)))
      .filter((n) => glyphsIn(nameOf(n)).length > 0)
      .map((n) => `${roleOf(n)} "${nameOf(n)}"`);
  }

  /** Each named element whose name starts or ends with a space and that holds a hidden glyph. */
  async paddedNames(): Promise<string[]> {
    const out: string[] = [];
    for (const n of this.nodes) {
      const name = nameOf(n);
      if (n.ignored || !n.backendDOMNodeId || !name || name === name.trim()) continue;
      if (['StaticText', 'InlineTextBox', 'RootWebArea'].includes(roleOf(n))) continue;
      const { object } = await this.cdp.send('DOM.resolveNode', { backendNodeId: n.backendDOMNodeId });
      const { result } = await this.cdp.send('Runtime.callFunctionOn', {
        objectId: object.objectId!,
        returnByValue: true,
        functionDeclaration: `function () {
          return this.nodeType === 1 && [...this.querySelectorAll('[aria-hidden="true"]')]
            .some((el) => /[^\\p{L}\\p{M}\\p{Nd}\\x20-\\x7e\\s]/u.test(el.textContent || ''));
        }`,
      });
      if (result.value) out.push(`${roleOf(n)} "${name}"`);
    }
    return out;
  }

  private async node(expression: string): Promise<AxNode> {
    const { result } = await this.cdp.send('Runtime.evaluate', { expression });
    expect(result.objectId, `no element for ${expression}`).toBeDefined();
    const { node } = await this.cdp.send('DOM.describeNode', { objectId: result.objectId! });
    const ax = this.byBackend.get(node.backendNodeId);
    expect(ax, `no accessibility node for ${expression}`).toBeDefined();
    return ax!;
  }

  /** The role and the name that Chromium computes for the element that `expression` returns, spaces collapsed. */
  async named(expression: string): Promise<{ role: string; name: string }> {
    const n = await this.node(expression);
    return { role: roleOf(n), name: nameOf(n).replace(/\s+/g, ' ') };
  }

  /**
   * The text that Chromium reads under that element: its text nodes in order,
   * joined, spaces collapsed. An image is one item, read by its name: the
   * platform layer hands a screen reader no child of an image.
   */
  async spoken(expression: string): Promise<string> {
    const read: string[] = [];
    const walk = (n: AxNode) => {
      if (n.ignored && roleOf(n) !== 'none') return;
      if (roleOf(n) === 'image') return void read.push(` ${nameOf(n)} `);
      if (roleOf(n) === 'StaticText') read.push(nameOf(n));
      for (const id of n.childIds ?? []) walk(this.byId.get(id)!);
    };
    walk(await this.node(expression));
    return read.join('').replace(/\s+/g, ' ').trim();
  }

  async detach() {
    await this.cdp.detach();
  }
}

/** Reads the tree, checks the two rules of every state, and hands the tree to `more`. */
async function state(page: Page, label: string, more?: (tree: Tree) => Promise<void>) {
  const tree = await Tree.read(page);
  try {
    expect(tree.glyphNames(), `${label}: names that hold a glyph`).toEqual([]);
    expect(await tree.paddedNames(), `${label}: names with a space beside a hidden glyph`).toEqual([]);
    await more?.(tree);
  } finally {
    await tree.detach();
  }
}

/** A role and a name, the name in lower case. */
async function lower(named: Promise<{ role: string; name: string }>) {
  const { role, name } = await named;
  return { role, name: name.toLowerCase() };
}

/** The element of `selector` whose text holds `text`, as a page expression. */
const withText = (selector: string, text: string) =>
  `[...document.querySelectorAll(${JSON.stringify(selector)})].find((el) => el.textContent.includes(${JSON.stringify(text)}))`;

/** Holds every /data/ request until `release` runs, so the route shows its loading line. */
async function holdData(page: Page) {
  const held: Route[] = [];
  let open = false;
  await page.route('**/data/**', (route) => {
    if (open) return route.continue();
    held.push(route);
  });
  return async () => {
    open = true;
    for (const r of held) await r.continue();
  };
}

test.describe.configure({ mode: 'parallel' });

for (const [label, path, text] of [
  ['loading-codex', '/codex', 'scrying the codex'],
  ['loading-atlas', '/atlas', 'charting the atlas'],
  ['loading-compare', '/compare', 'scrying the codex'],
  ['loading-shopping', '/shopping', 'shelving the tomes'],
  ['loading-deck', `/deck/${DECK}`, `scrying ${DECK}`],
  ['loading-scrying', `/scrying/${DECK}`, `scrying ${DECK}`],
  ['loading-combos-fleet', `/combos?mode=fleet&deck=${DECK}`, 'consulting the curated corpus'],
] as const) {
  test(`${label}: the loading line reads its words alone`, async ({ page }) => {
    const release = await holdData(page);
    await page.goto(path);
    await expect(page.getByText(text).first()).toBeVisible();
    await state(page, label);
    await release();
  });
}

test('codex: the № sort chip reads "deck number"', async ({ page }) => {
  await page.goto('/codex');
  await page.locator('.gv1-codex-card').first().waitFor();
  await state(page, 'codex', async (tree) => {
    expect(await tree.named(`document.querySelector('.gv1-codex-toolbar-l .gv1-chip')`)).toEqual({
      role: 'button',
      name: 'deck number',
    });
  });
});

test('atlas: the hint and a card read no glyph', async ({ page }) => {
  await page.goto('/atlas');
  await expect(page.getByText('Start typing', { exact: false })).toBeVisible();
  await state(page, 'atlas-hint');
  await page.getByPlaceholder(/Sol Ring/).fill('Sol Ring');
  await page.getByRole('option').first().click();
  await page.locator('.gv1-atlas-usage-list, .gv1-atlas-empty').first().waitFor();
  await state(page, 'atlas-card');
});

test('deck: a Game Changer reads "(Game Changer)" after its name, and Copy reads "Copied"', async ({
  page,
  context,
}) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto(`/deck/${DECK}`);
  await page.locator('.gv1-dl-row').first().waitFor();
  await page.locator('.gv1-card-tile.gv1-card-gc').first().waitFor();
  await state(page, 'deck', async (tree) => {
    const tile = `document.querySelector('.gv1-card-tile.gv1-card-gc')`;
    const tileName = await page.locator('.gv1-card-tile.gv1-card-gc').first().getAttribute('data-card-name');
    // The element that a test or a feature reads as the card's name keeps the name alone.
    await expect(page.locator('.gv1-card-tile.gv1-card-gc .gv1-card-tile-name').first()).toHaveText(tileName!);
    expect(await tree.spoken(tile)).toContain(`${tileName} (Game Changer)`);

    const row = `document.querySelector('.gv1-dl-row.gv1-dl-gc')`;
    const rowName = await page.locator('.gv1-dl-row.gv1-dl-gc').first().getAttribute('data-card-name');
    expect(await tree.spoken(row)).toMatch(new RegExp(`^${rowName!.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')} \\(Game Changer\\)`));

    // GV1ManaPips names the colours: Eternal Agony is black and red.
    expect(await tree.named(`document.querySelector('.gv1-cmd-body .gv1-pips')`)).toEqual({
      role: 'image',
      name: 'Color identity: black, red',
    });
  });

  await page.getByRole('button', { name: 'Copy decklist' }).click();
  await expect(page.getByRole('button', { name: /Copied/ })).toBeVisible();
  await state(page, 'deck-copied', async (tree) => {
    expect(await lower(tree.named(withText('button', 'Copied')))).toEqual({ role: 'button', name: 'copied' });
  });
});

test('mana cost: one image whose name says the cost in words', async ({ page }) => {
  await page.goto(`/deck/${DECK}`);
  const row = page.locator('.gv1-dl-row[data-card-name="Sheoldred, the Apocalypse"]');
  await row.locator('.gv1-mv').waitFor();
  await state(page, 'mana-cost', async (tree) => {
    expect(
      await tree.named(`document.querySelector('.gv1-dl-row[data-card-name="Sheoldred, the Apocalypse"] .gv1-mv')`),
    ).toEqual({ role: 'image', name: 'Mana cost: 2 generic, black, black' });
    expect(await tree.named(`document.querySelector('.gv1-dl-row[data-card-name="Exsanguinate"] .gv1-mv')`)).toEqual({
      role: 'image',
      name: 'Mana cost: X variable, black, black',
    });
  });
});

test('compare: "Sorted by" reads the direction, and the Scale legend reads three ranges', async ({ page }) => {
  await page.goto('/compare');
  await page.locator('.gv1-cmp-th-btn').first().waitFor();
  const sorted = withText('.gv1-cmp-summary-stat', 'SORTED BY') + `.querySelector('.gv1-serif-lg')`;
  const shown = () => page.locator('.gv1-cmp-summary-stat', { hasText: 'SORTED BY' }).locator('[aria-hidden="true"]').innerText();
  const words = { '▲': 'ascending', '▼': 'descending' } as Record<string, string>;
  let first = '';
  await state(page, 'compare', async (tree) => {
    first = await shown();
    expect(await tree.spoken(sorted)).toMatch(new RegExp(` ${words[first]}$`));
    const pills = await Promise.all(
      [0, 1, 2].map((i) => tree.spoken(`document.querySelectorAll('.gv1-cmp-legend-pill')[${i}]`)),
    );
    expect(pills).toEqual(['75 or more', '50 to 74', 'under 50']);
  });
  // The other direction: one click on the active column header turns it.
  await page.locator('.gv1-cmp-th--active .gv1-cmp-th-btn').click();
  await expect.poll(shown).not.toBe(first);
  const tree = await Tree.read(page);
  try {
    expect(await tree.spoken(sorted)).toMatch(new RegExp(` ${words[await shown()]}$`));
  } finally {
    await tree.detach();
  }
});

test('shopping: the list and Copy read no glyph', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/shopping');
  await page.locator('.gv1-shop-row').first().waitFor();
  await state(page, 'shopping');
  await page.getByRole('button', { name: 'Copy buy list' }).click();
  await expect(page.getByRole('button', { name: /Copied/ })).toBeVisible();
  await state(page, 'shopping-copied', async (tree) => {
    expect(await lower(tree.named(withText('button', 'Copied')))).toEqual({ role: 'button', name: 'copied' });
  });
});

test('combos fleet: the export buttons, the Spellbook links, a near miss, an edge and the colour identity read words', async ({
  page,
}) => {
  await page.goto(`/combos?mode=fleet&deck=${DECK}`);
  await expect(page.locator('.gv1-lab-combo').first()).toBeVisible();
  await page.locator('.gv1-lab-near-row').first().waitFor();
  await page.locator('.gv1-lab-edge').first().waitFor();
  await expect(page.getByText('legal in Commander', { exact: false })).toBeVisible();
  await state(page, 'combos-fleet', async (tree) => {
    const exports = `document.querySelectorAll('.gv1-lab-export-btn')`;
    expect(await lower(tree.named(`${exports}[2]`))).toEqual({ role: 'button', name: 'download .txt' });
    expect(await lower(tree.named(`${exports}[3]`))).toEqual({ role: 'button', name: 'download .md' });

    const links = await page.locator('a.gv1-lab-link[target="_blank"]').count();
    expect(links).toBeGreaterThan(1);
    const names = new Set<string>();
    for (let i = 0; i < links; i++) {
      const { role, name } = await lower(tree.named(`document.querySelectorAll('a.gv1-lab-link[target="_blank"]')[${i}]`));
      expect(role).toBe('link');
      names.add(name);
    }
    expect([...names].sort()).toEqual(['spellbook (opens in a new tab)', 'why? — commander spellbook (opens in a new tab)']);

    expect(await tree.spoken(`document.querySelector('.gv1-lab-near-produce')`)).toMatch(/^produces \S/i);
    const chip = page.locator('.gv1-lab-dist').first();
    expect(await tree.spoken(`document.querySelector('.gv1-lab-dist')`)).toBe(await chip.getAttribute('title'));

    const edge = await tree.spoken(`document.querySelector('.gv1-lab-edge')`);
    expect(edge).toMatch(/^\S.* to \S.* · \S.* pairs with \S.*$/);

    expect(await tree.spoken(withText('.gv1-lab-note', 'legal in'))).toContain(
      'Color identity black, red · legal in Commander',
    );
    // The rail's folio "§ XII" is decoration, like the folio of each section head.
    expect(await tree.spoken(withText('.gv1-lab-block-head', 'Contents'))).not.toContain('§');
  });
});

test('combos paste: Analyze reads its word, and a loop trace reads "then"', async ({ page }) => {
  await page.goto('/combos?mode=paste');
  await expect(page.getByText('Paste a decklist to consult the corpus')).toBeVisible();
  await state(page, 'combos-paste-empty', async (tree) => {
    expect(await lower(tree.named(`document.querySelector('.gv1-lab-analyze')`))).toEqual({ role: 'button', name: 'analyze' });
  });
  await page
    .locator('.gv1-lab-textarea')
    .fill('1 Basalt Monolith\n1 Forsaken Monument\n1 Sheoldred, the Apocalypse\n1 Peer into the Abyss\n12345');
  await page.getByRole('button', { name: /analyze/i }).click();
  await expect(page.getByRole('region', { name: /verified loops/i })).toBeVisible();
  const trace = page.locator('details', { hasText: 'Loop trace' }).first();
  await trace.locator('summary').click();
  await expect(trace.locator('.gv1-lab-step').first()).toBeVisible();
  await state(page, 'combos-paste-report', async (tree) => {
    const steps = await trace.locator('.gv1-lab-step p').count();
    const read = [];
    for (let i = 0; i < steps; i++) {
      read.push(await tree.spoken(`[...document.querySelectorAll('details')].find((d) => d.open && d.textContent.includes('Loop trace')).querySelectorAll('.gv1-lab-step p')[${i}]`));
    }
    expect(read.some((line) => / then /.test(line)), read.join(' | ')).toBe(true);
  });
});

test('scrying: a swap reads "to" for each arrow and no star', async ({ page }) => {
  await page.goto(`/scrying/${DECK}`);
  await page.locator('[data-gv1-screen="scrying"]').waitFor();
  await state(page, 'scrying');
  // Cut Vampiric Tutor (a Game Changer in a synergy): the delta shows the → rows, ★ −1 and a ⚠ row.
  await page.getByLabel('Select a card to cut').selectOption({ label: 'Vampiric Tutor' });
  await page.getByLabel('Search for a card to add').fill('an');
  const result = page.locator('.gv1-scry-search-result').first();
  await result.waitFor();
  await result.click();
  await page.locator('.gv1-scry-delta').waitFor();
  const row = (label: string, part: string) =>
    `[...document.querySelectorAll('.gv1-scry-delta-row')].find((r) => r.querySelector('.gv1-scry-delta-label').textContent === ${JSON.stringify(label)}).querySelector(${JSON.stringify(part)})`;
  await state(page, 'scrying-delta', async (tree) => {
    expect(await tree.spoken(row('Mana value', '.gv1-scry-delta-detail'))).toMatch(/^\d+ to \d+$/);
    expect(await tree.spoken(row('Avg mana value', '.gv1-scry-delta-detail'))).toMatch(/^\d+\.\d\d to \d+\.\d\d$/);
    expect(await tree.spoken(row('Game Changers', '.gv1-scry-delta-detail'))).toMatch(/^−1 GC · (\d+) to \d+$/);
    expect(await tree.spoken(row('Game Changers', '.gv1-scry-delta-change'))).toBe('−1');
  });
});

test('mobile: the deck page and the open topbar menu read no glyph', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/m/${DECK}`);
  await page.waitForLoadState('networkidle');
  await state(page, 'mobile');
  await page.goto('/codex');
  await page.locator('.gv1-topbar-mobile-btn').click();
  await page.locator('.gv1-topbar-mobile-menu').waitFor();
  await state(page, 'topbar-mobile-open', async (tree) => {
    // The label's "§I" is decoration, as the desktop nav's rune is.
    expect(await tree.spoken(`document.querySelector('.gv1-topbar-mobile-label')`)).not.toContain('§');
  });
});

test('not found: the 404 page reads no glyph', async ({ page }) => {
  await page.goto('/no-such-page');
  await page.locator('#nf-title').waitFor();
  await state(page, 'not-found');
});
