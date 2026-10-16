// DEC-1168 kill case for mutant VMIN (10vw -> 10vmin): the title's size follows
// the viewport's width, also when the viewport is lower than it is wide (a
// phone turned on its side). Every viewport of dec1156-engine-title.spec.ts
// case 1 is 900px high, so 10vmin equals 10vw at each of its widths below 900px.
import { expect, test } from '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1156-review/web/tests/support/test';

test.use({ cards: 'seeded', fonts: 'blocked' });

test('on a viewport lower than it is wide, the role title follows the width', async ({ page }) => {
  const want: Record<string, string> = { '740x360': '42px', '390x300': '39px', '320x280': '32px' };
  const got: Record<string, string> = {};
  await page.setViewportSize({ width: 740, height: 360 });
  await page.goto('/deck/shield-doctrine');
  await page.locator('.gv1-perf-grid').waitFor();
  for (const size of Object.keys(want)) {
    const [width, height] = size.split('x').map(Number);
    await page.setViewportSize({ width, height });
    got[size] = await page.evaluate(() => getComputedStyle(document.querySelector('.gv1-engine-panel-head h3')!).fontSize);
  }
  expect(got, 'The engine title font-size by viewport width x height').toEqual(want);
});
