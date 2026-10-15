// DEC-1083: the owned-cards import control takes keyboard focus (WCAG 2.1.1).
//
// The control was a <label> for a `hidden` file input. Neither is in the tab
// order, so Tab went from the deck rail's last chip to the `Type` sort button,
// and a keyboard user could not import a list. It is a button now, and the
// input stays hidden.
//
// Each case runs with the web fonts in and with them blocked: the fallback
// faces set the rail and the button at other heights.

import { expect, test, type Locator, type Page } from './support/test';

const OWNED_KEY = 'grimoire-owned-cards';

// Two lines, three cards.
const OWNED_TXT = {
  name: 'owned.txt',
  mimeType: 'text/plain',
  buffer: Buffer.from('Sol Ring\n2x Arcane Signet\n', 'utf8'),
};

function importButton(page: Page): Locator {
  return page.getByRole('button', { name: 'Import owned cards', exact: true });
}

// Focus the rail's last chip where it stands, then Tab once.
async function tabFromLastChip(page: Page): Promise<void> {
  await page.locator('.gv1-shop-chip').last().evaluate((el: HTMLElement) => el.focus({ preventScroll: true }));
  await page.keyboard.press('Tab');
}

// The scroll target is a whole pixel and the button's position is not.
function expectWithin1px(received: number, expected: number): void {
  expect(Math.abs(received - expected), `expected ${expected}, read ${received}`).toBeLessThan(1);
}

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`CHOOSER-CONTROL DEC-1083 owned-cards import, keyboard (fonts ${fonts})`, () => {
    test.use({ fonts });

    for (const key of ['Enter', 'Space'] as const) {
      test(`one Tab from the last rail chip reaches the button, and ${key} imports a list`, async ({ page }) => {
        await page.goto('/shopping');
        await page.locator('.gv1-shop-chip').last().waitFor();

        await tabFromLastChip(page);
        await expect(importButton(page)).toBeFocused();

        // `.gv1-shop-btn` transitions `all`, so the ring is read once it is in.
        const ring = await importButton(page).evaluate(async (el) => {
          await Promise.all(el.getAnimations().map((a) => a.finished));
          const cs = getComputedStyle(el);
          return { style: cs.outlineStyle, width: cs.outlineWidth, offset: cs.outlineOffset };
        });
        expect(ring).toEqual({ style: 'solid', width: '2px', offset: '2px' });

        const chooserOpens = page.waitForEvent('filechooser');
        await page.keyboard.press(key);
        const chooser = await chooserOpens;
        expect(await chooser.element().getAttribute('id')).toBe('gv1-shop-owned-file');
        await chooser.setFiles(OWNED_TXT);

        await expect(page.locator('.gv1-shop-import-ok')).toHaveText(
          /Added 2 unique cards \(3 total\)\. 3 cards loaded\. To replace the list, use Clear owned first\./,
        );
        await expect(page.locator('.gv1-shop-owned-bar')).toContainText('3 cards loaded — saved locally');
        const raw = await page.evaluate((k) => localStorage.getItem(k), OWNED_KEY);
        expect(JSON.parse(raw ?? '[]')).toEqual([['Sol Ring', 1], ['Arcane Signet', 2]]);
      });
    }

    // Where the deck rail pins (DEC-1019), a control on screen under it does
    // not scroll when it takes focus unless it carries a scroll margin.
    for (const { width, height } of [{ width: 768, height: 1024 }, { width: 600, height: 960 }]) {
      test.describe(`@ ${width}×${height}`, () => {
        test.use({ viewport: { width, height } });

        test('focus on the button lands clear of the pinned rail', async ({ page }) => {
          await page.goto('/shopping');
          const rail = page.locator('.gv1-shop-rail');
          const button = importButton(page);
          await rail.waitFor();
          await page.getByRole('button', { name: 'Type', exact: true }).waitFor();
          // A web font that lands after the scroll moves the button off its mark.
          await page.evaluate(() => document.fonts.ready);

          // Put the button 40px down the screen, under the pinned rail. Keys
          // only from here: locator.click() scrolls its target first.
          await button.evaluate((el) => {
            window.scrollTo(0, Math.round(el.getBoundingClientRect().top + window.scrollY) - 40);
          });
          expectWithin1px(await rail.evaluate((el) => el.getBoundingClientRect().top), 0);
          expectWithin1px(await button.evaluate((el) => el.getBoundingClientRect().top), 40);

          await tabFromLastChip(page);
          await expect(button).toBeFocused();

          // Hit-test 15 points across the button, 5 columns by 3 rows.
          const m = await button.evaluate((el) => {
            const box = el.getBoundingClientRect();
            let hits = 0;
            for (const fy of [0.2, 0.5, 0.8]) {
              for (const fx of [0.1, 0.3, 0.5, 0.7, 0.9]) {
                const hit = document.elementFromPoint(box.left + box.width * fx, box.top + box.height * fy);
                if (hit && el.contains(hit)) hits += 1;
              }
            }
            return {
              top: box.top,
              railBottom: document.querySelector('.gv1-shop-rail')!.getBoundingClientRect().bottom,
              hits,
            };
          });
          expect(m.top, `top of the focused button (the rail ends at ${m.railBottom})`).toBeGreaterThanOrEqual(m.railBottom);
          expect(m.hits, 'points on the button that hit the button, of 15').toBe(15);
        });
      });
    }
  });
}

// The look of the button at rest (DEC-1088 B1). The ring check above cannot
// tell whether the button still carries `.gv1-shop-btn`, because the rule
// `.gv1-root :focus-visible` gives every control the same 2 px ring. Each
// value below comes from a CSS rule, not from the font's metrics, so both
// font arms read the same figures.
for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`CHOOSER-CONTROL DEC-1083 owned-cards import, look (fonts ${fonts})`, () => {
    test.use({ fonts, viewport: { width: 1440, height: 900 } });

    test('the import button keeps the look of .gv1-shop-btn at rest', async ({ page }) => {
      await page.goto('/shopping');
      const button = importButton(page);
      await button.waitFor();
      await page.mouse.move(1, 1);
      const look = await button.evaluate(async (el) => {
        await Promise.all(el.getAnimations().map((a) => a.finished));
        const cs = getComputedStyle(el);
        return {
          backgroundColor: cs.backgroundColor,
          color: cs.color,
          border: [cs.borderTop, cs.borderRight, cs.borderBottom, cs.borderLeft],
          padding: [cs.paddingTop, cs.paddingRight, cs.paddingBottom, cs.paddingLeft],
          fontFamily: cs.fontFamily,
          fontSize: cs.fontSize,
          letterSpacing: cs.letterSpacing,
          cursor: cs.cursor,
        };
      });
      const border = '1px solid rgba(232, 225, 207, 0.22)';
      expect(look).toEqual({
        backgroundColor: 'rgb(20, 31, 51)',
        color: 'rgb(232, 225, 207)',
        border: [border, border, border, border],
        padding: ['8px', '14px', '8px', '14px'],
        fontFamily: '"JetBrains Mono", "Fira Code", ui-monospace, "Cascadia Code", monospace',
        fontSize: '12px',
        letterSpacing: '0.48px',
        cursor: 'pointer',
      });
    });
  });
}
