APPROVE at 014984a

PR #82 does what the owner's answers A and B ask, and nothing more. Every required mutant fails at least one case. I found no B item. I give two N items: a guard case for R6, and a spec header that the two new cases made wrong.

## 1. Basis
- `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin`: `origin/dec-1199-one-mark` is `014984a8bd67128ecf6b792be15988e417d0a55d`.
- At the start, `origin/main` was `e6d472e`. `git diff --stat e6d472e origin/main -- web data .github` printed nothing.
- During the review, `origin/main` moved to `6b7c40c` (`573e0dd` and `6b7c40c`, CEO notes only). I ran the diff again on `6b7c40c`, and it still printed nothing. `e6d472e` is an ancestor of `6b7c40c`.
- **Basis: the head `014984a`.** Trees: `wt-dec1201` (detached at `014984a`, port 14935) and `wt-dec1201-main` (detached at `e6d472e`, port 14936). `package-lock.json` was the same in both trees (`cmp`). I ran `npm ci` in the head tree and cloned `node_modules` with `cp -cR`.

## 2. Scope
- `git diff --stat e6d472e 014984a` lists the 8 files of the hand-back, all under `web/`, with `74 insertions(+), 17 deletions(-)`: `Compare.test.tsx`, `Shopping.test.tsx`, `Compare.tsx`, `Shopping.tsx`, `ComboLab.tsx`, `states.css`, `dec1177-empty-sigils.spec.ts` and `dec1190-glyph-names.spec.ts`.
- `git diff --stat e6d472e 014984a -- web/src/styles/styles.css web/src/components/atoms/Glyph.tsx` printed nothing.

## 3. The brief's items (head `014984a`)
**A, markup.** `git grep -n gv1-empty--own-rune -- web/src ':!web/src/__tests__'` prints:
```
web/src/components/organisms/Compare.tsx:171:        <div className="gv1-empty gv1-empty--own-rune">
web/src/components/organisms/Shopping.tsx:584:        <div className="gv1-empty gv1-empty--own-rune">
web/src/components/organisms/Shopping.tsx:821:            <div className="gv1-empty gv1-empty--own-rune">
web/src/components/organisms/Shopping.tsx:897:          <div className="gv1-empty gv1-empty--own-rune">
web/src/styles/states.css:76:.gv1-empty--own-rune::before {
```
The first child of each container is a `.gv1-rune` span: `Shopping.tsx:585` (◇), `:822` (◆), `:898` (◇) and `Compare.tsx:172` (◇).

**A, rule.**
- `states.css:76` to `:78` holds `.gv1-empty--own-rune::before { content: none; }`. It comes after `.gv1-empty::before` (`states.css:67`) and uses no `:has()`.
- No later rule sets `::before` on these 4 boxes. Every `::before` rule in `web/src/styles/` is listed here:
  - `styles.css:24`, `:466`, `:479`, `:485`, `:1117`, `:1458` and `:3428`: `.gv1-root`, `.gv1-sel-pill`, `.gv1-apo-remedy`, `.gv1-codex` and `.gv1-atlas`.
  - `combo-lab.css:143` and `:144`: `.gv1-lab-steps summary`.
  - `combo-lab.css:255`.
  
  None of these selects a `.gv1-empty` on /shopping or Compare.
- `main.tsx:6` to `:11` imports `tokens.css`, `deck-theme.css`, `states.css`, `styles.css`, `app.css` and `combo-lab.css`, in that order.
- `combo-lab.css:255` is `[data-gv1-screen="combolab"] .gv1-empty::before`. The only `data-gv1-screen="combolab"` is `ComboLab.tsx:539`. The other two values are `app` (`App.tsx:17`) and `scrying` (`Scrying.tsx:1084`).
- The computed value agrees: on the head, the `::before` of all 4 boxes reads `none` (e2e and my shot spec).

**B.** `ComboLab.tsx:615` is `<span>consulting the curated corpus …</span>`, and `:629` is `<span>consulting the corpus …</span>`. Each holds main's words, unchanged, with no `Glyph`. The import stays at `ComboLab.tsx:21` (`Glyph, GlyphText, GlyphWords`), and the file still uses `<Glyph>`, for example at `:713`, `:724`, `:836` and `:1579`.

**Tests.**
- `expectOneMark` is defined at `dec1177-empty-sigils.spec.ts:65`. The two changed DEC-1177 cases call it at `:80` (case at `:70`) and `:169` (case at `:160`). The two new cases call it at `:88` (case at `:83`) and `:100` (case at `:91`).
- `expectOneLabMark` is defined at `dec1190-glyph-names.spec.ts:201`. The two new cases call it at `:211` (case at `:208`) and `:221` (case at `:215`).
- In Vitest, the helper `expectHiddenSigil` asserts the class at `Shopping.test.tsx:819`. The DEC-1177 case calls it for all 3 /shopping boxes, at `:831`, `:838` and `:845`. `Compare.test.tsx:101` asserts the class on the Compare box.

**The "All cards owned" case** (`dec1177-empty-sigils.spec.ts:91`).
- `:96` writes `grimoire-owned-cards` with `[name, 99]` for every `.gv1-shop-row`. This is `OWNED_KEY` (`ownedCards.ts:13`). `readOwnedEntries` (`ownedCards.ts:29`) keeps an entry with a non-empty name and a whole number of 1 or more, so it keeps each of these.
- A fallback cannot pass the case. A store that does not parse gives `[]`, so the page keeps cards to buy, and the "All cards owned" box does not render.
- Check T1 proves it. I deleted the write at `:96` (`void names;`). The case then failed at `toHaveCount(1)` with `Received: 0` (`mut/mut-T1.log`).

## 4. Suites (head `014984a`)
| Suite | Count line | Log |
|---|---|---|
| lint | `✖ 10 problems (0 errors, 10 warnings)` | `lint.log` |
| typecheck | exit 0 (`tsc -b --noEmit && tsc -p tsconfig.e2e.json`) | `typecheck.log` |
| Vitest | `Test Files  57 passed (57)` and `Tests  719 passed (719)` | `vitest.log` |
| Playwright (full, `--workers=3`, port 14935) | `270 passed (3.3m)` | `e2e-full.log` |

All four match the brief. The 18 `✘` marks in `e2e-full.log` belong to the `test.fail()` cases of 5 specs: `dec1071-moxfield-check` (6), `dec1073-own-route-named` (1), `dec1110-harness` (2), `dec1131-card-batches` (2) and `dec1152-rate-check-post` (7). Playwright counts them as passed. The log has no `failed`, `flaky` or `skipped` line.

## 5. Shots
I ran `kit/shots.spec.ts` with `DEC1199_TAG=before` on `wt-dec1201-main` (18 passed) and with `DEC1199_TAG=after` on `wt-dec1201` (18 passed), with `DEC1199_SHOTS=/tmp/dec1201/shots/`. My control spec (`control.spec.ts`) ran in the same runs. I deleted both spec files after each run.

**Where I differ from the brief:** neither tree has `pngjs` in `node_modules`. Playwright bundles it, so I passed `node_modules/playwright-core/lib/utilsBundle.js` as `diff.cjs`'s first argument. That file exports pngjs's `PNG`.

My 14 lines of `kit/diff.cjs` output are byte for byte the same as `kit/diff-result.txt` (`diff` printed nothing).

| State | Width | Box before | Box after | Changed px |
|---|---|---|---|---|
| shopping-no-decks-loaded | 1280 | 1008×235 | 1008×191 | n/a (size differs) |
| shopping-no-decks-loaded | 390 | 326×235 | 326×191 | n/a (size differs) |
| shopping-all-owned | 1280 | 1008×235 | 1008×191 | n/a (size differs) |
| shopping-all-owned | 390 | 326×249 | 326×205 | n/a (size differs) |
| shopping-no-decks-selected | 1280 | 1008×235 | 1008×191 | n/a (size differs) |
| shopping-no-decks-selected | 390 | 326×249 | 326×205 | n/a (size differs) |
| compare-no-decks-loaded | 1280 | 1008×235 | 1008×191 | n/a (size differs) |
| compare-no-decks-loaded | 390 | 326×235 | 326×191 | n/a (size differs) |
| combos-fleet-loading | 1280 | 756×420 | 756×420 | 1,522 |
| combos-fleet-loading | 390 | 342×420 | 342×420 | 1,522 |
| combos-paste-loading | 1280 | 756×420 | 756×420 | 1,179 |
| combos-paste-loading | 390 | 342×420 | 342×420 | 1,179 |
| control-combos-paste-empty | 1280 | 756×420 | 756×420 | 0 |
| control-combos-paste-empty | 390 | 342×420 | 342×420 | 0 |
| **control-wincons-empty (mine, outside Combo Lab)** | 1280 | 1136×185 | 1136×185 | **0** |
| **control-wincons-empty (mine, outside Combo Lab)** | 390 | 358×185 | 358×185 | **0** |

**My control outside Combo Lab (ruling 1).**
- The box is `WinCons.tsx:18` on `/deck/eternal-agony`. It has no modifier and no `.gv1-rune` span. It is under `states.css` and `styles.css` only.
- No deck in `data/commanders/` has an empty `winConditions`, `synergies` or engine category list, and every deck has `metrics.json` and `candidates.json`. So the stub does not reach `WinCons.tsx:18`, `Combos.tsx:18`, `Engine.tsx:23` or `Apothecary.tsx:158` unaided.
- I used `page.route` on `**/commanders/eternal-agony/deck.json`. It fetches the real file and empties `winConditions`, as the PR's own cases do for `index.json`.
- The `::before` computes `"◇" / ""` on both trees and at both widths (`shots/control-wincons-empty-*.json`). The box is 185 px tall on both trees, with 0 changed pixels.

**By eye** (`pairs/*.png`; each image puts before on the left and after on the right, with 1280 above 390):
- Each A "after" shows one mark, the 32 px span (◇, or ◆ on "All cards owned"), above the same words. The 24 px ◇ above it is gone.
- Each B "after" shows one ◇ (the box's `::before`) above the same words. The inline ◇ is gone.
- Both controls look the same before and after.

**Nothing else changes (my counts).**
- *A boxes* (`ink.cjs`, `ink-result.txt`). In "before", rows 61 to 104 hold 47 bright pixels, which is the `::before` ◇ alone. Below that band, the bright pixels of "after" (the marks and the words) sit where those of "before" sit after a move of 44 rows up. At most 2 pixels per state and width are on one side only. Of the 376 to 1,077 pixels in each pair, 50 to 150 differ in colour. I read them as edge pixels that blend with a different part of the grid and the gradient behind the box after the move. The pairs show no change in shape. Above the band, both sides have 0 bright pixels.
  - A plain pixel diff does not work here. The page grid behind the box stays in place while the contents move up 44 px (`band-result.txt`).
- *B boxes* (`band-result.txt`). The changed pixels fall in two areas. One is the words' row (y225 to 242). The other is the `::before` ◇ (y186 to 201, 14 px wide).
  - The line `<span>` is 20 px tall on `main` and 19 px on the head (`bline-before.json` and `bline-after.json`). The inline ◇ in its fallback font made the line box 1 px taller.
  - The box is a centred flex column, so the ◇ and the words move down 0.5 px. The box stays 420 px.

**Ruling 2, the 44 px.** I accept it. My reading (`measure-*.json`) explains it:
- `styles.css:1819` and `:1820` (`display: grid; gap: 12px`) load after `states.css` and replace its flex column.
- The `::before` is a 32 px grid row: a 24 px font with `line-height: normal`. One 12 px gap follows it.
- Before: 1 + 60 + **32 + 12** + 43 + 12 + 14 + 60 + 1 = 235 px (border, padding, `::before`, gap, span, gap, words, padding, border).
- After: the 32 + 12 goes, so the box is 191 px.
- At 390 px, the words of two boxes wrap to 28 px. Those boxes go from 249 px to 205 px.

## 6. Mutants
Each mutant ran on Vitest and on the two specs (`--workers=3`, port 14935). The runner restored `src` and `tests` after each run. `git status --porcelain` printed nothing in both trees before I removed them.
- M1 to M5 used the implementer's runner, copied to `/tmp/dec1201/mutants.sh` and `/tmp/dec1201/mutate.py`. I changed the tree path, the port, the path of `mutate.py` and the log path.
- R1 to R8 and T1 used my own runner (`rmutants.sh` and `rmutate.py`).

| Mutant | Result | Failing case | Log |
|---|---|---|---|
| M1 (no modifier on `Shopping.tsx:897`) | killed | Vitest `Shopping … (DEC-1177)`; e2e `dec1177:70` | `mut/mut-M1.log` |
| M2 (no modifier on `Compare.tsx:171`) | killed | Vitest `Compare … (DEC-1177)`; e2e `dec1177:160` | `mut/mut-M2.log` |
| M3 (rule deleted) | killed | e2e `dec1177:70`, `:83`, `:91` and `:160` | `mut/mut-M3.log` |
| M4 (fleet inline ◇ back) | killed | e2e `dec1190:208` | `mut/mut-M4.log` |
| M5 (paste inline ◇ back) | killed | e2e `dec1190:215` | `mut/mut-M5.log` |
| R1 (no modifier on `Shopping.tsx:584`) | killed | Vitest `Shopping … (DEC-1177)`; e2e `dec1177:83`: expected `"none"`, received `"\"◇\" / \"\""` | `mut/mut-R1.log` |
| R2 (no modifier on `Shopping.tsx:821`) | killed | Vitest `Shopping … (DEC-1177)`; e2e `dec1177:91`: expected `"none"`, received `"\"◇\" / \"\""` | `mut/mut-R2.log` |
| R3 (`content: ''`) | killed | e2e `dec1177:70`, `:83`, `:91` and `:160`: received `"\"\""` | `mut/mut-R3.log` |
| R4 (rule above `.gv1-empty::before`) | killed | e2e `dec1177:70`, `:83`, `:91` and `:160`: received `"\"◇\" / \"\""` | `mut/mut-R4.log` |
| R5 (`◇ consulting the curated corpus …` as plain text) | killed | Vitest `dec1190/glyph-source.test.ts`; e2e `dec1190:188` and `:208` | `mut/mut-R5.log` |
| R6 (modifier on `WinCons.tsx:18`, guard) | **survives** (28 passed, 719 passed) | none; see N1 | `mut/mut-R6.log` |
| R7 (`…` becomes `...` on `:629`, a rewritten line) | killed | e2e `dec1190:215` | `mut/mut-R7.log` |
| R8 (`<span>` dropped on `:615`, a rewritten line) | **survives, equivalent** | none | `mut/mut-R8.log`, `shots-r8/` |
| T1 (test check: no `localStorage` write at `dec1177:96`) | killed | e2e `dec1177:91`: `toHaveCount(1)`, received 0 | `mut/mut-T1.log` |

**R8 is not a B item.** R8 removes the `<span>` from `ComboLab.tsx:615`, so the words become an anonymous flex item. I took the fleet line on the head and on R8: 0 changed pixels at 1280 and at 390 (`shots-r8/r8-diff.txt`). The ARIA snapshot is the same: `- text: consulting the curated corpus …`. No behaviour changes, so a test can kill R8 only by asserting the markup. If you count it under the mutant rule anyway, the kill is one line in `expectOneLabMark`: `await expect(box.locator(':scope > span')).toHaveText(text);`. I do not recommend it.

## 7. B items
None.

## 8. N items
**N1. R6 survives: no case guards a box that has no `.gv1-rune` span.**
- If the modifier spreads to such a box, the box loses its only mark. Nothing in the suite fails.
- Proposed action: add this case to `dec1177-empty-sigils.spec.ts`, after the Compare case. It uses the spec's own `beforeGlyph`. I ran it as a scratch file:
  - It passes on `014984a`.
  - It fails on R6: `Expected pattern: /^"◇"/`, `Received string: "none"` (`mut/guard-R6.log`).
  - `eslint` and `tsc -p tsconfig.e2e.json` exit 0 on it.
```ts
// A box with no `.gv1-rune` span keeps the ◇ of `.gv1-empty::before`, its only mark (DEC-1199).
// No deck in the repository has an empty `winConditions`, so the route empties it.
test('the deck page with no win conditions keeps the ◇ of its empty state (DEC-1199)', async ({ page }) => {
  await page.route('**/commanders/eternal-agony/deck.json', async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), winConditions: [] } });
  });
  await page.goto('/deck/eternal-agony');
  const message = "No documented win conditions in this deck's dossier yet.";
  const empty = page.locator('.gv1-empty').filter({ hasText: message });
  await expect(empty).toHaveCount(1);
  await expect(empty.locator('.gv1-rune')).toHaveCount(0);
  expect(await beforeGlyph(page, message)).toMatch(/^"◇"/);
});
```

**N2. The header of `dec1177-empty-sigils.spec.ts` now names the wrong case.**
- `:9` to `:11` say "Every case but the third reads Chromium's own accessibility tree (CDP) … The third reads the stylesheet that the page loads."
- On `main`, the third case was the stylesheet case. The PR puts its two new cases second and third, so the stylesheet case is now the fifth.
- Neither new case reads the accessibility tree.
- Proposed text for `:9` to `:11`:
```ts
// Each DEC-1177 case but the stylesheet case reads Chromium's own accessibility
// tree (CDP), not the name that Playwright computes: the text of a ::before is in
// Chromium's tree only. The stylesheet case reads the stylesheet that the page
// loads. The two DEC-1199 cases read the computed `::before` only.
```

## Evidence and trees
- Evidence: `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1201/`. It also has a copy of `/tmp/dec1201/`. It holds the suite logs, `shots/` (68 files), `pairs/`, `shots-r8/`, `mut/` (18 logs), the scratch specs and scripts, and this verdict as `verdict.md`.
- I removed `wt-dec1201` and `wt-dec1201-main` with `git worktree remove` (no `--force`), after `git status --porcelain` printed nothing in each. Then I ran `git worktree prune`.
- I did not touch `wt-dec1199`, `/tmp/dec1199/` or the implementer's workspace. I sent no request to `api.scryfall.com` or `cards.scryfall.io`.
