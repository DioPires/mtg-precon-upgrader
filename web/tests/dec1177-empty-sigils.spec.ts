// DEC-1177 (DEC-1173 N2): a screen reader reads each empty state's message
// alone. The ◇ of `.gv1-empty::before` has empty alternative text, and the
// sigil span of each /shopping empty state has aria-hidden. Both still show.
//
// Each case reads Chromium's own accessibility tree (CDP), not the name that
// Playwright computes: the text of a ::before is in Chromium's tree only.

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
