// DEC-1177 (DEC-1173 N2): a screen reader reads each empty state's message
// alone. The ◇ of `.gv1-empty::before` has empty alternative text, and the
// sigil span of each /shopping empty state has aria-hidden. Both still show.
//
// The first two cases read Chromium's own accessibility tree (CDP), not the
// name that Playwright computes: the text of a ::before is in Chromium's tree
// only. The third reads the stylesheet that the page loads.

import { expect, test, type Page } from './support/test';

/** The text nodes that Chromium's accessibility tree holds under the `.gv1-empty` that holds `text`. */
async function spokenText(page: Page, text: string): Promise<string[]> {
  const cdp = await page.context().newCDPSession(page);
  try {
    await cdp.send('Accessibility.enable');
    await cdp.send('DOM.enable');
    const expression = `[...document.querySelectorAll('.gv1-empty')].find((el) => el.textContent.includes(${JSON.stringify(text)}))`;
    const { result } = await cdp.send('Runtime.evaluate', { expression });
    const { node } = await cdp.send('DOM.describeNode', { objectId: result.objectId });
    const { nodes } = await cdp.send('Accessibility.getFullAXTree');
    const byId = new Map(nodes.map((n) => [n.nodeId, n]));
    const root = nodes.find((n) => n.backendDOMNodeId === node.backendNodeId);
    expect(root, `no accessibility node for the empty state that holds "${text}"`).toBeDefined();
    const read: string[] = [];
    const walk = (id: string) => {
      const n = byId.get(id)!;
      if (n.role?.value === 'StaticText' && !n.ignored) read.push(String(n.name?.value ?? ''));
      (n.childIds ?? []).forEach(walk);
    };
    walk(root!.nodeId);
    return read;
  } finally {
    await cdp.detach();
  }
}

/** The glyph that the `::before` of the `.gv1-empty` that holds `text` shows. */
async function beforeGlyph(page: Page, text: string): Promise<string> {
  return page
    .locator('.gv1-empty')
    .filter({ hasText: text })
    .evaluate((el) => getComputedStyle(el, '::before').content);
}

test('/shopping with no deck selected reads its message alone (DEC-1177)', async ({ page }) => {
  await page.goto('/shopping');
  await page.locator('.gv1-shop-row').first().waitFor();
  await page.getByRole('button', { name: 'Clear', exact: true }).click();
  const message = 'No decks selected. Pick at least one above to build a list.';
  const empty = page.locator('.gv1-empty').filter({ hasText: message });
  await expect(empty).toHaveCount(1);

  // `.gv1-mono-xs` sets text-transform: uppercase, and Chromium reads the text as shown.
  expect(await spokenText(page, message)).toEqual([message.toUpperCase()]);
  // The two glyphs still show.
  await expect(empty.locator('.gv1-rune')).toHaveText('◇');
  expect(await beforeGlyph(page, message)).toMatch(/^"◇"/);
});

// combo-lab.css has its own `.gv1-empty::before` for the Combo Lab screen.
test('the Combo Lab empty state reads its text alone (DEC-1177)', async ({ page }) => {
  await page.goto('/combos?mode=paste');
  const title = 'Paste a decklist to consult the corpus';
  await expect(page.locator('.gv1-empty').filter({ hasText: title })).toHaveCount(1);

  expect(await spokenText(page, title)).toEqual([
    title,
    'One card per line, quantities welcome. The match runs entirely in your browser.',
    // `.gv1-empty-hint` sets text-transform: uppercase.
    'OR PRESS “LOAD EXAMPLE” FOR A CLASSIC COMBO PILE',
  ]);
  expect(await beforeGlyph(page, title)).toMatch(/^"◇"/);
});

// A browser that cannot parse `content: '◇' / ''` drops that declaration and
// keeps the one before it. Vite's default build targets include Firefox 78 and
// Safari 14; the form with alternative text came in Firefox 128 and Safari 17.4.
// Chromium parses both, so only the shipped stylesheet shows the first one.
test('each `.gv1-empty::before` rule that the page loads keeps a plain `content` before the form with alternative text (DEC-1177)', async ({ page }) => {
  await page.goto('/shopping');
  const css = await page.evaluate(async () => {
    const links = [...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')];
    const files = await Promise.all(links.map((link) => fetch(link.href).then((r) => r.text())));
    return [...files, ...[...document.querySelectorAll('style')].map((style) => style.textContent ?? '')].join('\n');
  });
  // Quotes, `::` and spaces as the minifier writes them do not matter here.
  const tidy = (text: string) => text.trim().replace(/'/g, '"').replace(/::/g, ':').replace(/\s*([:/])\s*/g, '$1');
  const rules = [...css.matchAll(/([^{}]*\.gv1-empty::?before)\s*\{([^}]*)\}/g)].map(([, selector, body]) => ({
    selector: tidy(selector).replace(/"/g, ''),
    content: body.split(';').map(tidy).filter((declaration) => declaration.startsWith('content:')),
  }));

  expect(rules).toEqual([
    { selector: '.gv1-empty:before', content: ['content:"◇"', 'content:"◇"/""'] },
    { selector: '[data-gv1-screen=combolab] .gv1-empty:before', content: ['content:"◇"', 'content:"◇"/""'] },
  ]);
});
