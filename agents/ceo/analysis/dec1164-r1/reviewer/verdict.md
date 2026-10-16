## DEC-1164 verdict: CHANGES (2 B items, both with a kill case to copy)

PR #66 at `ff7ead8` meets rulings 1 to 5 in the code, and the three pages agree in a browser. Two added lines have a surviving mutant that is not equivalent. Each needs one more unit case. Both kill cases are written and tested, so route A fits. Nothing else blocks the merge.

**Basis.** `origin/main` was `561aba7` at the start. It holds PR #59 (`4b0b488`) and PR #56 (`b09f8be`), and not PR #65. `git merge-tree --write-tree 561aba7 ff7ead8` gives `33ad8d7d09cf2d1cc8d48dfa496231b7fa42cb54`. `HEAD^{tree}` in the merged tree is `33ad8d7d09cf2d1cc8d48dfa496231b7fa42cb54` too. `HEAD:web` is `08fd7a7625dae1e79c670d2d6cfd63104c1dd1a5` (the head's own is `967e3692`). At 22:15Z `main` was `32e1057`, with no change under `web/` since `561aba7`, and PR #66's head was still `ff7ead8`.

### B items

**B1. Combo Lab's count: R1 and R2 survive at `ComboLab.tsx:121`.**
- R1 (`count += q;` becomes `count = q;`) reads `Tests  7 passed (7)`. R2 (`count = Math.max(count, q);`) reads `Tests  7 passed (7)`.
- Ruling 4 says that `count` is the sum of the kept quantities. No case reads a store with two kept entries. The mutants are not equivalent: for `[["Sol Ring",2],["Arcane Signet",1]]` the head gives 3, R1 gives 1 and R2 gives 2.
- Kill case: add this row to the `it.each` table at `web/src/__tests__/routes/ComboLab.test.tsx:169-173`: `[[['Sol Ring', 2], ['Arcane Signet', 1]], '3 owned cards on file'],`. The table's `openFleet` writes the store with `JSON.stringify`.
- Kill file: `/Users/dpires/.paperclip/instances/default/workspaces/ddb8e4ee-9ec6-45ae-81b7-144c85a9b26e/dec1155-review/kill/kill-combolab.test.tsx`. It holds the PR's fixtures and that one row.
- Merged head: `Tests  2 passed (2)` (both kill files). R1: `Tests  1 failed (1)`; the title reads `1 owned card on file`, not `3 owned cards on file`. R2: `Tests  1 failed (1)`; the title reads `2 owned cards on file`.

**B2. Names as stored: R9 survives at `ownedCards.ts:42`.**
- R9 (`out.push([n, q])` becomes `out.push([n.trim(), q])`) reads `Tests  29 passed (29)`.
- Ruling 1 says that `readOwnedEntries` gives the entries "with their names as stored". The case "keeps the entries in store order with their names as stored" stores no name with spaces around it, so a trim passes. The mutant is not equivalent: `n` is declared `string`, and a hand-edited store can hold `" Sol Ring "`. The head gives `[" Sol Ring ",1]` and R9 gives `["Sol Ring",1]`. Shopping keys by `frontFace(n)`, which does not trim, so the mutant changes which deck card the entry matches.
- Kill case: in `describe('readOwnedEntries (DEC-1150)')` of `web/src/__tests__/data/ownedCards.test.ts`, store `JSON.stringify([[' Sol Ring ', 1]])` and expect `readOwnedEntries()` to equal `[[' Sol Ring ', 1]]`.
- Kill file: `/Users/dpires/.paperclip/instances/default/workspaces/ddb8e4ee-9ec6-45ae-81b7-144c85a9b26e/dec1155-review/kill/kill-owned.test.ts`.
- Merged head: passes (in the `2 passed (2)` above). R9: `Tests  1 failed (1)`, `expected [ [ 'Sol Ring', 1 ] ] to deeply equal [ [ ' Sol Ring ', 1 ] ]`.

With both kill files in the tree (`web/src/__tests__/dec1164/`), `npm run typecheck` exited 0 and `npx eslint src/__tests__/dec1164/` exited 0. I then removed them, and `git status --porcelain` printed nothing. With the two cases, the pull request adds 39 unit cases, not 37.

### Notes (N)
- **N1.** `Number.isSafeInteger(q)` in place of `Number.isInteger(q)` at `ownedCards.ts:17` survives (`Tests  29 passed (29)`). It is outside the mutant rule, because ruling 2 chose `Number.isInteger`. DEC-1155 already names the limit.
- **N2.** In the browser, the OWNED stat's `innerText` is `OWNED\n×2\nIN INVENTORY`, because CSS sets upper case. The text in the DOM is `in inventory`, as `CardAtlas.tsx:255` writes it.

### Check 1: the code against the ruling (lines on the merged head)
1. **One reader.** A missing store, `''` and `not json` throw in `JSON.parse(storage.getItem(OWNED_KEY) ?? '')` at `ownedCards.ts:32`, and `:34` returns `[]`. `{}`, `"x"`, `5` and `null` parse, and `if (!Array.isArray(stored)) return [];` at `:36` returns `[]`. The function's only storage call is `storage.getItem` at `:32`, so it writes nothing. The unit case checks `storage.setCalls` 0 and the stored string unchanged.
2. **The 12 entries of Ask 2b.** `:39` (`!Array.isArray(entry) || entry.length !== 2`) drops `null`, `["Sol Ring"]` and `["Sol Ring",2,"foil"]`. At `:41`, `typeof n !== 'string'` drops `[null,2]`, `[{"n":"Sol Ring"},2]` and `[["Sol Ring"],2]`. `!n.trim()` drops `["  ",2]`. `!isOwnedQuantity(q)` drops 0, -1, 0.5, 1.5 and `"2"` (`Number.isInteger` does not convert a string). The mutants confirm the split: R3 (`break` at `:39`) fails the 3 rows of `:39` only, and R4 (`break` at `:41`) fails the 9 rows of `:41` only.
3. **One quantity test.** CSV, `Shopping.tsx:114-115`: `const read = parseInt((r[qi] || '1').trim(), 10);` and `const q = isOwnedQuantity(read) ? read : 1;`. Text, `:129-130`: `const read = parseInt(m[1], 10);` and `const q = isOwnedQuantity(read) ? read : 1;`. On the CSV path `parseInt` gives NaN, an integer, -0, `Infinity` or `-Infinity`, and never a finite fraction. `main`'s `read >= 1 ? read : 1` and the head agree on each of them except `Infinity`, which `main` keeps and the head counts as 1 (the N2 fix). On the text path `\d+` gives an integer of 0 or more, or `Infinity`. `main`'s `parseInt(m[1], 10) || 1` gives 1 for 0 and n for n of 1 or more, and so does the head. Only `Infinity` changes.
4. **Each reader keeps its own keys.** Shopping `:149` `const key = frontFace(n);`. Card Atlas `cardAtlas.ts:173` `const key = frontFace(n).toLowerCase();`. Combo Lab `ComboLab.tsx:120` `for (const k of nameKeys(n)) keys.add(k);`. `git grep -n "grimoire-owned-cards\|OWNED_KEY" -- web/src` finds source lines only in `web/src/data/ownedCards.ts` (`:13`, `:32`, `:78`, `:85`). Every other hit is a test file: `Shopping.test.tsx:318`, `cardAtlas.test.ts:11-332`, `loaderEnvelope.test.ts:105,113`, `ownedCards.test.ts:9-111`, `dec1150/kill-shopping.test.tsx:8`, `dec325-roundtrip.test.ts:11` and `ComboLab.test.tsx:77-158`.
5. **Combo Lab counts cards.** `:118` `let count = 0;` and `:121` `count += q;` run over `readOwnedEntries()` (`:119`). `:1803` and `:1811` read `` `${owned.count} owned ${cardNoun(owned.count)} on file` `` (the note adds ` — imported in § IX Shopping`). With no kept entry the loop runs 0 times, so `count` is 0. Then `:1799` `disabled={owned.count === 0}` disables the chip, and `:1802` gives the first title, `Import your collection in § IX Shopping first`. The unit case "disables the chip for a store with no kept entry" passes.
6. **Nothing else changed.** `CardAtlas.tsx` has no diff, so `:250-256` keeps `main`'s lines. Shopping's hunks cover `:20-26`, `:108-118`, `:125-133` and `:140-155` only. The import message (`:539`) and the owned bar (`:710-713`) are outside them. `ownedCards.ts` has one hunk (`@@ -6,9 +6,44 @@`) that removes no line, so `saveOwned` is unchanged.

### Check 2: the hand-back's mutants (`npx vitest run <unit file>`, merged head)
| Mutant | Count line | Hand-back | Failed case |
|---|---|---|---|
| O2 `ownedCards.ts:29` | `1 failed \| 28 passed (29)` | `1 failed \| 28 passed (29)` | reads localStorage when no storage is given |
| O10c `ownedCards.ts:41` | `5 failed \| 24 passed (29)` | `5 failed \| 24 passed (29)` | the rows `0`, `-1`, `0.5`, `1.5` and `"2"` |
| S3 `Shopping.tsx:130` | `1 failed \| 50 passed (51)` | `1 failed \| 50 passed (51)` | counts a text line count of 400 digits as 1 |
| S7 `Shopping.tsx:150` | `1 failed \| 50 passed (51)` | `1 failed \| 50 passed (51)` | adds a stored double-faced name and its front face into one card |
| C4 `ComboLab.tsx:120` | `1 failed \| 6 passed (7)` | `1 failed \| 6 passed (7)` | keeps a completion that names the front face of a stored double-faced name |

### Check 3: my mutants
After each run the runner restored the file with `git checkout -- <file>`, and `git status --porcelain` printed nothing every time.

| Mutant | Line | Change | Count line | Result |
|---|---|---|---|---|
| R1 | `ComboLab.tsx:121` | `count = q;` | `7 passed (7)` | **survived: B1** |
| R2 | `ComboLab.tsx:121` | `count = Math.max(count, q);` | `7 passed (7)` | **survived: B1** |
| R3 | `ownedCards.ts:39` | `break` | `3 failed \| 26 passed (29)` | killed |
| R4 | `ownedCards.ts:41` | `break` | `9 failed \| 20 passed (29)` | killed |
| R5 | `ownedCards.ts:32` | `storage.getItem(OWNED_KEY) as string` | `29 passed (29)` | survived: equivalent |
| R6 | `Shopping.tsx:115` | `Number.isFinite(read) && read >= 1` | `51 passed (51)` | survived: equivalent |
| R7 | `cardAtlas.ts:172` | `readOwnedEntries()` | `23 passed (23)` | survived: equivalent in a browser |
| R8 | `Shopping.tsx:130` | `read >= 1 ? read : 1` | `1 failed \| 50 passed (51)` | killed |
| R9 | `ownedCards.ts:42` | `out.push([n.trim(), q])` | `29 passed (29)` | **survived: B2** |
| R10 | `ownedCards.ts:41` | `!n` for `!n.trim()` | `1 failed \| 28 passed (29)` | killed |
| R11 | `ownedCards.ts:39` | `entry.length > 2` | `29 passed (29)` | survived: equivalent |
| R12 | `ownedCards.ts:39` | drop `!Array.isArray(entry) \|\| ` | `1 failed \| 28 passed (29)` | killed |
| R13 | `ownedCards.ts:36` | `typeof stored !== 'object' \|\| stored === null` | `1 failed \| 28 passed (29)` | killed |
| R14 | `ownedCards.ts:17` | `> 1` | `15 failed \| 14 passed (29)` | killed |
| R15 | `ownedCards.ts:32` | `?? '[]'` | `29 passed (29)` | survived: equivalent |
| R16 | `Shopping.tsx:148` | `readOwnedEntries(sessionStorage)` | `13 failed \| 38 passed (51)` | killed |
| R17 | `ComboLab.tsx:119` | `readOwnedEntries(sessionStorage)` | `4 failed \| 3 passed (7)` | killed |
| R18 | `ComboLab.tsx:1803` | `cardNoun(owned.keys.size)` | `1 failed \| 6 passed (7)` | killed |
| R19 | `ComboLab.tsx:1811` | `cardNoun(owned.keys.size)` | `1 failed \| 6 passed (7)` | killed |
| R20 | `Shopping.tsx:115` | `? read : 0` | `3 failed \| 48 passed (51)` | killed |
| R21 | `Shopping.tsx:130` | `? read : 0` | `1 failed \| 50 passed (51)` | killed |
| R22 | `Shopping.tsx:129` | `Number(m[1])` | `51 passed (51)` | survived: equivalent |
| N1 | `ownedCards.ts:17` | `Number.isSafeInteger(q)` | `29 passed (29)` | outside the rule (note N1) |

The equivalence readings:
- **R5: I agree with the CEO.** `getItem` is declared `string | null`. For `null`, `JSON.parse` reads the text `null` and gives `null`, so `:36` returns `[]`; the head throws at `:32` and returns `[]` at `:34`. For a string the two lines are the same.
- **R6: I agree with the CEO.** `parseInt` never gives a finite fraction, so the two tests agree on each value that it returns. A node check of 200,000 random cells (digits, signs, `.`, `e`, `x`, spaces and commas) found 0 differences.
- **R7: equivalent in a browser.** There `window` is the global object, so the default argument `localStorage` and `window.localStorage` are the same object. Where `window` is undefined, `:170` returns before the call.
- **R11.** An entry of length 0 has `n` undefined, and `typeof` at `:41` drops it. An entry of length 1 has `q` undefined, and `isOwnedQuantity` drops it. So `> 2` and `!== 2` keep the same entries.
- **R15.** A missing store parses to `[]`, the loop adds nothing, and the result is `[]`, as on the head.
- **R22.** `m[1]` holds ASCII digits only. `Number` and `parseInt(…, 10)` agree on such strings, with leading zeros and with 309 or more digits (`Infinity`). A node check of 200,000 strings of 1 to 400 digits found 0 differences.

Runner and logs: `/Users/dpires/.paperclip/instances/default/workspaces/ddb8e4ee-9ec6-45ae-81b7-144c85a9b26e/dec1155-review/` (`mutate.py`, `mutants/<id>.log`, summary `mutants-run.txt`, node check `equiv.mjs`).

### Check 4: the three pages agree (browser, merged head)
The scratch spec is `.../dec1155-review/e2e/three-pages.spec.ts`. It imports `test` and `expect` from the tree's `tests/support/test`. `page.addInitScript` writes `JSON.stringify([["Sol Ring",2],["Arcane Signet",1],["Sol Ring",0.5],[7,2]])` before the page's scripts on each load. Port 14871, `--workers 1`, and `lsof` printed nothing before the run. Result: `3 passed (8.9s)`.
1. `/shopping`: the owned bar reads `3 cards loaded — saved locally`.
2. `/atlas`, Sol Ring opened as `dec942-owned-quota.spec.ts` does: the OWNED stat reads `×2` and `in inventory` (see N2).
3. `/combos?mode=fleet&deck=titan-convergence`, after the pool scan note: the Owned only chip is enabled. Its title reads `3 owned cards on file`, and the note reads `3 owned cards on file — imported in § IX Shopping`.
4. After each load and a 1.5 s wait, the store read `[["Sol Ring",2],["Arcane Signet",1],["Sol Ring",0.5],[7,2]]`. It was equal (`===`) to the written string on all three pages.

### Check 5: the suite on the merged head
1. In `web/`: `npm run lint` exit 0, `✖ 10 problems (0 errors, 10 warnings)`. `npm run typecheck` exit 0. `npx vitest run`: `Test Files  51 passed (51)`, `Tests  647 passed (647)`.
2. Local, `--workers 1`, port 14871 (`lsof` empty before each): `tests/smoke.spec.ts` `11 passed (10.1s)`, `tests/dec942-owned-quota.spec.ts` `1 passed (4.2s)`, `tests/combo-lab.spec.ts` `9 passed (7.6s)`. No case was flaky.
3. Basis CI: `web-ci` push run 38792978708 on `b09f8be` (PR #56), both jobs `success`. The commits `b09f8be..561aba7` change nothing under `web/`, `data/` or the workflow, so `web-ci` did not run on them. The run's log reads `✖ 10 problems (0 errors, 10 warnings)`, `Test Files  51 passed (51)`, `Tests  610 passed (610)` and `179 passed (9.4m)`.
4. From `git diff 561aba7...ff7ead8` on the test files: `ownedCards.test.ts` has 4 `it` and two `it.each` tables of 12 and 9 rows (25). `Shopping.test.tsx` has 3, `cardAtlas.test.ts` has 4, and `ComboLab.test.tsx` has 2 `it` and 3 rows (5). That is 37 unit cases and 0 e2e cases (no file under `web/tests/` changed). Expected sum: 610 + 37 = 647. Local count: 647. They match. The expected Playwright count after the branch update is 179 + 0 = 179.

### Check 6: tree removed
`git -C wt-dec1155-review status --porcelain` printed nothing. `git worktree remove wt-dec1155-review` exited 0 without `--force`, and `git worktree prune` ran. The tree was detached, so there is no branch to delete. I did not touch `wt-dec1155` or `wt-dec1156`.

### Steps that I changed
- The basis is `561aba7` and not `4b0b488`, because `main` moved before this run started (PR #56 and CEO notes). So the basis CI run is 38792978708, not 38791532167. `main` moved to `32e1057` during the review, with no change under `web/`.
- Playwright's `testDir` is fixed to the tree's `tests/`. To keep the spec out of the tree, I ran it with a scratch config (`.../dec1155-review/pw.config.ts`). It imports the tree's config and changes only `testDir`, `outputDir` and the server's `cwd`. The scratch folder holds a `package.json` with `"type": "module"`, so that it can import the tree's ESM config.
- I added mutants R8 to R22 beyond the brief's list.
