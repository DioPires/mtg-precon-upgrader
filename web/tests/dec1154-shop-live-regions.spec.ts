// DEC-1154 Part B (DEC-1149 P1): the import message and the stop line of
// /shopping are live regions that are in the page from the first paint and
// empty until their text comes. Many screen readers do not read a region that
// enters the page with its text.
//
// Each case reads Chromium's own accessibility node of each region (CDP)
// while it is empty, then shows that the same DOM node holds the text.
//
// DEC-1167 (DEC-1163 N1): the stop line's section stays in the page while no
// deck is selected, so its region is one node through Clear and a new selection.

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Locator, type Page } from './support/test';

const DATA = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data');
const PRICES_AS_OF = (JSON.parse(readFileSync(resolve(DATA, 'card-metadata.meta.json'), 'utf8')) as { prices_as_of: string })
  .prices_as_of;
const BUCKET_ONE = /^https:\/\/api\.scryfall\.com\/cards\/(named|collection)(\?|$)/;

const IMPORT_STATUS = '.gv1-shop-owned-bar ~ [role="status"]';
const IMPORT_ALERT = '.gv1-shop-owned-bar ~ [role="alert"]';
const STOP_LINE = '.gv1-shop-summary ~ [role="status"]';
// The stop line's section follows the import's section, also while no deck is selected and no summary shows.
const STOP_SECTION = 'section:has(.gv1-shop-owned-bar) + section';
const STOP_REGION = `${STOP_SECTION} > [role="status"]`;

const textFile = (name: string, body: string) => ({ name, mimeType: 'text/plain', buffer: Buffer.from(body, 'utf8') });

/** Chromium's accessibility node of the element that `selector` finds. */
async function axNode(page: Page, selector: string) {
  const cdp = await page.context().newCDPSession(page);
  try {
    await cdp.send('Accessibility.enable');
    const { result } = await cdp.send('Runtime.evaluate', { expression: `document.querySelector(${JSON.stringify(selector)})` });
    const { nodes } = await cdp.send('Accessibility.getPartialAXTree', { objectId: result.objectId, fetchRelatives: false });
    const node = nodes[0];
    const prop = (name: string) => node.properties?.find((p) => p.name === name)?.value.value;
    return { role: node.role?.value, ignored: node.ignored, live: prop('live'), atomic: prop('atomic') };
  } finally {
    await cdp.detach();
  }
}

/** True when `locator` finds the node that `handle` held. */
async function sameNode(locator: Locator, handle: Awaited<ReturnType<Locator['elementHandle']>>): Promise<boolean> {
  return locator.evaluate((el, node) => el === node, handle);
}

test('the import regions are in the page and empty before a message, and the same nodes hold it after', async ({ page }) => {
  await page.goto('/shopping');
  await page.locator('.gv1-shop-row').first().waitFor();
  const status = page.locator(IMPORT_STATUS);
  const alert = page.locator(IMPORT_ALERT);

  await expect(status).toBeEmpty();
  await expect(alert).toBeEmpty();
  expect(await axNode(page, IMPORT_STATUS)).toEqual({ role: 'status', ignored: false, live: 'polite', atomic: true });
  expect(await axNode(page, IMPORT_ALERT)).toEqual({ role: 'alert', ignored: false, live: 'assertive', atomic: true });
  const statusNode = await status.elementHandle();
  const alertNode = await alert.elementHandle();

  // A file of cards: the count goes to the status region.
  await page.locator('#gv1-shop-owned-file').setInputFiles(textFile('owned.txt', 'Sol Ring\n2x Arcane Signet\n'));
  await expect(status).toHaveText(/^◆Added 2 unique cards \(3 total\)\. 3 cards loaded\./);
  await expect(alert).toBeEmpty();
  expect(await sameNode(status, statusNode)).toBe(true);

  // A file with no card: the error goes to the alert region, and the status region is empty again.
  await page.locator('#gv1-shop-owned-file').setInputFiles(textFile('empty.txt', '\n'));
  await expect(alert).toHaveText('⚠No cards detected in that file.');
  await expect(status).toBeEmpty();
  expect(await sameNode(alert, alertNode)).toBe(true);
});

test.describe('the stop line', () => {
  test.use({ scryfall429From: 1, rateClock: 'page' });

  test('its region is in the page and empty before the stop, and the same node holds the line after', async ({ page }) => {
    test.setTimeout(60_000);
    // The spec holds the first answers of bucket 1, so that the page can be
    // read before the stop starts; then the stub answers them with 429.
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route(BUCKET_ONE, async (route) => {
      await held;
      await route.fallback();
    });
    const firstAsk = page.waitForRequest(BUCKET_ONE);
    // Every price of the file is older than 24 h, so each row asks for a refresh.
    await page.clock.install({ time: Math.max(Date.now(), Date.parse(PRICES_AS_OF) + 25 * 3_600_000) });
    await page.goto('/shopping');
    await page.locator('.gv1-shop-row').first().waitFor();
    await firstAsk;

    const region = page.locator(STOP_LINE);
    await expect(region).toBeEmpty();
    expect(await axNode(page, STOP_LINE)).toEqual({ role: 'status', ignored: false, live: 'polite', atomic: true });
    const regionNode = await region.elementHandle();

    release();
    const line = page.getByRole('status').filter({ hasText: 'Price refresh paused' });
    await expect(line).toHaveCount(1);
    await expect(region).toContainText('Price refresh paused.');
    expect(await sameNode(region, regionNode)).toBe(true);
  });

  test('its region is one node through Clear and a new selection while the stop holds (DEC-1167)', async ({ page }) => {
    test.setTimeout(60_000);
    await page.clock.install({ time: Math.max(Date.now(), Date.parse(PRICES_AS_OF) + 25 * 3_600_000) });
    await page.goto('/shopping');
    await page.locator('.gv1-shop-row').first().waitFor();
    const section = page.locator(STOP_SECTION);
    const region = page.locator(STOP_REGION);
    await expect(region).toContainText('Price refresh paused.');
    // The clock stops before the stop ends, so the stop holds through every step.
    await page.clock.pauseAt((await page.evaluate(() => Date.now())) + 500);
    const status = { role: 'status', ignored: false, live: 'polite', atomic: true };

    // A deck is selected: the section has its class and holds the summary and the line.
    await expect(section).toHaveAttribute('class', 'gv1-section gv1-shop-section');
    await expect(section.locator('.gv1-shop-summary')).toHaveCount(1);
    expect(await axNode(page, STOP_REGION)).toEqual(status);
    const regionNode = await region.elementHandle();

    // No deck is selected: the section has no class and no height, and the same region is empty.
    await page.getByRole('button', { name: 'Clear', exact: true }).click();
    await expect(page.locator('.gv1-shop-summary')).toHaveCount(0);
    await expect(region).toBeEmpty();
    expect(await section.evaluate((el) => [el.getAttribute('class'), el.getBoundingClientRect().height])).toEqual([null, 0]);
    expect(await axNode(page, STOP_REGION)).toEqual(status);
    expect(await sameNode(region, regionNode)).toBe(true);

    // A deck is selected again: the same region holds the line.
    await page.locator('.gv1-shop-chip').first().click();
    await expect(section.locator('.gv1-shop-summary')).toHaveCount(1);
    await expect(section).toHaveAttribute('class', 'gv1-section gv1-shop-section');
    await expect(region).toContainText('Price refresh paused.');
    expect(await axNode(page, STOP_REGION)).toEqual(status);
    expect(await sameNode(region, regionNode)).toBe(true);
  });
});
