**CHANGES. The code of PR #60 meets rulings 1 to 4 on every reading, but five of my mutants on the added lines survive and are not equivalent. The four B items below ask for test cases only; no line of `Shopping.tsx` needs to change.**

Reviewed: PR #60 head `af1f93b`, merged with `origin/main` `8a8f2fb` (basis at 16:02Z). Scratch folder (below: `R/`): `/Users/dpires/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1141-review/`.

## B items (each is a missing test case)
The kill file is `R/kill/Shopping.dec1150-kill.test.tsx` (4 cases). On the merged head it reads `Tests  4 passed (4)` (`R/kill-logs/kill-head.log`). `npm run typecheck` exit 0 and `npx eslint` on the file exit 0 with the file in the tree; I then removed it.

| B | Survivor (line) | Count line on the unit file | Kill case | Kill on the mutant |
|---|---|---|---|---|
| B1 | R1: `const q = Math.max(read, 1);` (`:106`) | `Tests  41 passed (41)` | K1: `Name,Quantity` with `Sol Ring,abc` gives 1 | `Tests  1 failed \| 3 passed (4)`, K1 fails (NaN) |
| B1 | R2: `const q = read < 1 ? 1 : read;` (`:106`) | `Tests  41 passed (41)` | K1 | `Tests  1 failed \| 3 passed (4)`, K1 fails (NaN) |
| B2 | R5: `typeof n !== 'string'` becomes `typeof n === 'number'` (`:144`) | `Tests  41 passed (41)` | K3: the store `[[null,2],[{"n":"Sol Ring"},2],[["Sol Ring"],2],["Arcane Signet",1]]` gives `1 card loaded — saved locally` | `Tests  1 failed \| 3 passed (4)`, K3 fails: `null.trim()` throws, and the `catch` empties the whole list |
| B3 | R13: `q < 1` becomes `q < 0` (`:145`) | `Tests  41 passed (41)` | K4: the store `[["Sol Ring",0]]` shows the empty list (no `loaded —` text, no Clear owned) | `Tests  1 failed \| 3 passed (4)`, K4 fails: the bar reads `0 cards loaded — saved locally` |
| B4 | R8: `parseInt(..., 10)` drops the radix (`:105`) | `Tests  41 passed (41)` | K2: `Sol Ring,0x10` gives 1 | `Tests  1 failed \| 3 passed (4)`, K2 fails (16) |

- B1 is the CEO's expected gap: no case gives a quantity cell with text. B2 is the other expected gap: no stored name is `null`, an object or an array. B3 is the boundary at 0: the stored cases test -1 and 0.5, not 0.
- B4: the radix `10` is `main`'s, and the pull request kept it. The line is rewritten (`const q = parseInt(...) || 1` became `const read = parseInt(...)`), so the mutant rule puts it in scope. I raise it because the rule says so. The kill is one assertion, so the cost is small. The CEO may waive it.
- Kill logs: `R/kill-logs/kill-<id>.log`. Mutant logs: `R/mutants/mutant-<id>.log`.

## Notes
- **N1 (check 4, readers outside PR #60).** The CEO's two readings are correct. Table and recommendation are in check 4. I recommend **A**.
- **N2 (a reading, not a B item).** A CSV cell of 309 or more digits makes `parseInt` give `Infinity` (node: `parseInt('1'.repeat(400), 10)` is `Infinity`). Line 106 keeps it, because `Infinity >= 1`. By reading, the message and the bar then show `Infinity`, and `saveOwned` writes `null` for it (`JSON.stringify([["Sol Ring",Infinity]])` is `[["Sol Ring",null]]`), so the next load drops the card. Ruling 2's text keeps every reading of 1 or more, so this meets ruling 2 but not the "whole number" of ruling 1. No real export holds such a cell. If the CEO wants it closed, `Number.isFinite(read) && read >= 1` does it.
- **N3.** `main` moved during the review, to `a4897e2` at the end, with no change under `web/` or `data/`. PR #61 was still `OPEN` at start and at end.

## Setup
- `git rev-parse origin/main`: `8a8f2fb842a0f761eff04f39781f6c5e1b107d46`. **PR #51 (`5554161`) merged after the CEO's 15:12Z reading, so the merged head holds it.** `git diff --stat 4fdcbb8 8a8f2fb -- web data` prints nothing. The `web` subtree of the merged head is `f2b76d58`, equal to the head's. No `web-ci` push run followed PR #51 (only `python-tests` 38764071244), so the totals basis stays run 38751901902.
- Merged head (detached): HEAD `d3bfd2f`. `git rev-parse HEAD^{tree}`: `11fe4eb949c5e2f073ea2635a6bbdf87286e74ee`. `git merge-tree --write-tree origin/main af1f93b`: `11fe4eb949c5e2f073ea2635a6bbdf87286e74ee`. Equal. It differs from the CEO's `77d5a708` only because `main` moved outside `web/`.
- `npm ci` exit 0, `npm run build` exit 0. Port 14821: `lsof` printed nothing before each run.

## Check 1: the code against the ruling
1. **CSV path (ruling 2).** `:105` `const read = parseInt((r[qi] || '1').trim(), 10);` and `:106` `const q = read >= 1 ? read : 1;`. A reading of 1 or more takes the true branch. `0` gives 0 and `-1` gives -1; both take the else branch, 1. An empty cell and a row with no quantity cell (`r[qi]` is `''` or `undefined`) take the default `'1'`, so 1. Text gives `NaN`; `NaN >= 1` is false, so 1. `2.5` gives 2.
2. **Stored list (ruling 3).** `:142` `if (!Array.isArray(entry) || entry.length !== 2) return;` drops an entry that is not an array and an array of one or three items. `:144` `if (typeof n !== 'string' || !n.trim()) return;` drops a name that is not a string and a name with only spaces. `:145` `if (!Number.isInteger(q) || q < 1) return;` drops a quantity that is not a number (`Number.isInteger` does not coerce, so `"2"` fails), a number that is not whole, and a number below 1.
3. **Not JSON, not an array.** `:133` `if (raw)` passes for each of the five strings. `not json`: `JSON.parse` at `:141` throws `SyntaxError`. `{}`, `"x"` and `5`: `.forEach` at `:141` throws `TypeError: ... is not a function`. `null`: `:141` throws `TypeError: Cannot read properties of null (reading 'forEach')` (node, all five). The `catch` at `:151-153` ignores it, and `:154` `return new Map();` returns the empty list. An empty or missing store skips `:133` and also ends at `:154`.
4. **The load writes nothing back.** `Shopping.tsx` writes `localStorage` only through `saveOwned`; the one direct use is `getItem` at `:132`. `saveOwned` has two calls. `:487` is in `onFile`, which only the file input's `onChange` starts (`:663`), after a pick through Import owned cards. `:520` is in `clearOwned`, which only the Clear owned button's `onClick` starts (`:681`), after `window.confirm` returns true. `loadOwned` runs only as the `useState` initializer at `:382`, and it calls neither. The browser read in check 5 confirms it: the store was byte for byte the same after the load.
5. **Nothing else changed (ruling 4).** `git diff origin/main...af1f93b -- web/src/components/organisms/Shopping.tsx` has two hunks: `:100-106` (the CSV quantity) and `:133-145` (the stored list). The text path (`:113-125`), the messages (`:474-514`), the owned bar (`:674-682`) and `cardNoun` keep `main`'s lines.

## Check 2: the hand-back's mutants (hand-back in brackets)
Runner: `R/run_mutants.py`. Before each mutant it checks that `git status --porcelain` prints nothing. After the edit it checks that only ` M web/src/components/organisms/Shopping.tsx` shows. It restores with `git checkout -- <file>` and checks that `git status --porcelain` prints nothing. Command: `npx vitest run src/__tests__/components/Shopping.test.tsx` in `web/`. Baseline: `Tests  41 passed (41)`.
- M3: `Tests  2 failed | 39 passed (41)` [`Tests  2 failed | 39 passed (41)`]. Failed: `parseOwnedFile > counts a CSV quantity below 1 as 1 ...` and `counts a CSV quantity of -1 as 1 in the import message and the owned bar`.
- M9: `Tests  2 failed | 39 passed (41)` [same]. Failed: `drops a stored entry whose name has no text` and `drops a stored entry whose name is not a string`.
- M12: `Tests  1 failed | 40 passed (41)` [same]. Failed: `drops a stored quantity of 1 or more that is not a whole number`.
- M13: `Tests  1 failed | 40 passed (41)` [same]. Failed: `drops a stored quantity below 1`.
- **M1: I agree that it is equivalent.** `read >= 1 ? read : 1` and `read > 1 ? read : 1` differ only when `read === 1`, and both then give 1. For `NaN` both tests are false, so both give 1.

## Check 3: my mutants
| Mutant (line) | Count line | Result |
|---|---|---|
| R1 `Math.max(read, 1)` (`:106`) | `Tests  41 passed (41)` | survived: B1 |
| R2 `read < 1 ? 1 : read` (`:106`) | `Tests  41 passed (41)` | survived: B1 |
| R3 `entry.length < 2` (`:142`) | `Tests  1 failed \| 40 passed (41)` | killed (`drops a stored entry that is not a two-item array`) |
| R4 `q <= 1` (`:145`) | `Tests  6 failed \| 35 passed (41)` | killed (5 DEC-1141 cases and `persists imported owned cards in localStorage on mount ...`) |
| R5 `typeof n === 'number'` (`:144`) | `Tests  41 passed (41)` | survived: B2 |
| R6 default `'1'` becomes `'0'` (`:105`) | `Tests  41 passed (41)` | equivalent |
| R7 drop `.trim()` (`:105`) | `Tests  41 passed (41)` | equivalent |
| R8 drop the radix `10` (`:105`) | `Tests  41 passed (41)` | survived: B4 |
| R9 `\|\|` becomes `&&` (`:142`) | `Tests  1 failed \| 40 passed (41)` | killed (`... not a two-item array`) |
| R10 `\|\|` becomes `&&` (`:145`) | `Tests  2 failed \| 39 passed (41)` | killed (`... below 1`, `... 1 or more that is not a whole number`) |
| R11 `\|\|` becomes `&&` (`:144`) | `Tests  2 failed \| 39 passed (41)` | killed (`... name has no text`, `... name is not a string`) |
| R12 `Number.isInteger` becomes `Number.isFinite` (`:145`) | `Tests  1 failed \| 40 passed (41)` | killed (`... 1 or more that is not a whole number`) |
| R13 `q < 0` (`:145`) | `Tests  41 passed (41)` | survived: B3 |
| R14 `read >= 2` (`:106`) | `Tests  41 passed (41)` | equivalent |
| R15 else branch `1` becomes `0` (`:106`) | `Tests  2 failed \| 39 passed (41)` | killed (the two CSV -1 cases) |
| R16 `entry.length > 2` (`:142`) | `Tests  41 passed (41)` | equivalent |
| R17 `!n.trim()` becomes `!n` (`:144`) | `Tests  1 failed \| 40 passed (41)` | killed (`... name has no text`) |

Why the four survivors are equivalent on every input (each also passes the kill file, `Tests  4 passed (4)`):
- **R6.** The default applies only when the cell is empty or missing. The head reads 1 and keeps it. The mutant reads 0 and takes the else branch, 1.
- **R7.** `parseInt` trims leading white space with the same rule as `trim()` (the spec's TrimString), and it stops at the first character that is not a digit, so trailing space never counts. Node: `parseInt('﻿  3 \n', 10)` is 3 with and without `.trim()`.
- **R14.** It differs from the head only when `read === 1`, and both then give 1 (as M1).
- **R16.** It differs only for arrays of 0 or 1 item. Line 144 drops the empty array (`n` is `undefined`), and line 145 drops the one-item array (`Number.isInteger(undefined)` is false). `JSON.parse` makes no sparse arrays.

## Check 4: the other readers of the same store (notes only)
By reading the code on the merged head (no browser read):

| Store | Shopping bar | Card Atlas, Sol Ring (`CardAtlas.tsx:252-255`) | Combo Lab note (`ComboLab.tsx:1809`) |
|---|---|---|---|
| `[["Sol Ring",0.5],["Arcane Signet",2]]` | `2 cards loaded — saved locally` | `×0.5`, `in inventory` | `2 owned cards on file — imported in § IX Shopping` |
| `[["Sol Ring",-1],["Arcane Signet",1]]` | `1 card loaded — saved locally` | `—`, `not imported` (-1 is not above 0) | `2 owned cards on file — imported in § IX Shopping` |
| `[["Sol Ring"]]` | the empty list (`// .csv (Name,Quantity) or .txt (one card per line)`, no Clear owned) | `—`, `not imported` (`0 + undefined` is `NaN`, and `NaN \|\| 0` at `:117` is 0) | `1 owned cards on file — imported in § IX Shopping` |

- The CEO's readings are correct: Card Atlas shows `×0.5` for the first store, and Combo Lab reads `2 owned cards on file` for the second while Shopping reads `1 card loaded — saved locally`.
- Combo Lab's "Owned only" filter counts Sol Ring as owned in all three stores: `loadOwnedCollection` takes a key from every entry's name (`String(n)`).
- A store with one entry whose name is not a string (for example `[7,2]`) makes `frontFace(n)` throw in `loadOwnedMap` (`cardAtlas.ts:172`). The `catch` then gives Card Atlas an empty map, so it shows no owned card at all.
- Combo Lab counts entries, not cards. A valid store `[["Sol Ring",2]]` reads `1 owned cards on file` in Combo Lab and `2 cards loaded` in Shopping. That is older than PR #60, and so is the plural `1 owned cards`.
- **Recommendation: A.** The three readers already disagree on one store. `web/src/data/ownedCards.ts` holds `OWNED_KEY` and `saveOwned`, and `cardAtlas.ts` defines the key a second time. One shared reader there ends the drift. The follow-up brief must say which count Combo Lab shows (entries or cards). Priority low: the app never writes a damaged store.

## Check 5: browser read on the merged head
Script: `R/browser-read.mjs` (Chromium, 1440 × 900, `animations: 'disabled'` for screenshots, every request to `api.scryfall.com` and Moxfield aborted). Server: `npx vite preview --port 14821 --strictPort` in `web/`, stopped before check 6. Log: `R/check5.log`. Screenshots: `R/check5-2-loaded.png`, `R/check5-3-imported.png`.
1. Store set before the page's scripts ran: `[["Sol Ring",0.5],["Arcane Signet",2]]`. The owned bar reads `2 cards loaded — saved locally`. After the load the store reads `[["Sol Ring",0.5],["Arcane Signet",2]]`: 38 bytes, byte for byte equal (`===` true).
2. Clear owned (confirm accepted): the bar reads `// .csv (Name,Quantity) or .txt (one card per line)`, and the store reads `[]`.
3. Import through the file input of `Name,Quantity` with the rows `Sol Ring,-1` and `Arcane Signet,1`. Status message: `Added 2 unique cards (2 total). 2 cards loaded. To replace the list, use Clear owned first.` Owned bar: `2 cards loaded — saved locally`. Store: `[["Sol Ring",1],["Arcane Signet",1]]`.

## Check 6: the suite on the merged head
1. In `web/`: `npm run lint` exit 0, `✖ 10 problems (0 errors, 10 warnings)`. `npm run typecheck` exit 0. `npx vitest run`: `Test Files  43 passed (43)` and `Tests  484 passed (484)`.
2. `GRIMOIRE_E2E_PORT=14821 npx playwright test tests/dec1083-shop-import-keyboard.spec.ts tests/dec942-owned-quota.spec.ts tests/smoke.spec.ts`: `22 passed (5.7s)`. By file: `dec1083-shop-import-keyboard.spec.ts` 10 passed, `dec942-owned-quota.spec.ts` 1 passed, `smoke.spec.ts` 11 passed. No case was flaky, also not `dec1083-shop-import-keyboard.spec.ts:42`. Log: `R/e2e-3specs.log`.
3. Basis: `web-ci` push run 38751901902 on `4fdcbb8` (the newest push run on `main` that changed `web/`). Its own log: lint `✖ 10 problems (0 errors, 10 warnings)`, `Test Files  43 passed (43)`, `Tests  475 passed (475)`, `150 passed (12.5m)`.
4. `git diff origin/main...af1f93b` adds 9 `it(` cases in `Shopping.test.tsx` and changes no file under `web/tests/`. Expected on the head: 43 files, 475 + 9 = 484 tests, 150 e2e cases. Read in run 38753502675's own log (both jobs `success`): `Test Files  43 passed (43)`, `Tests  484 passed (484)`, `150 passed (10.4m)`, lint `✖ 10 problems (0 errors, 10 warnings)`. They match.

## Check 7: the review tree
`git -C wt-dec1141-review status --porcelain` printed nothing. `git worktree remove wt-dec1141-review` exit 0, then `git worktree prune`. **`wt-dec1141-review` is removed.** I did not touch `wt-dec1141`.

## Steps that I changed or skipped
- Check 6.2: I ran the three specs in one Playwright run, not three. I took each file's count from the list reporter.
- Check 4: I gave a reading of the code only, with no browser read.
- Equivalence is shown by argument for R6, R7, R14 and R16. A passing kill file on them is support, not proof.
