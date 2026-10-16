# Route A edits for fix round 1 of PR #75 (DEC-1172, review DEC-1174, verdict bab1dab3).
# Usage: python3 -I apply.py <tree>     (run it after the round's merge of origin/main)
# 1. Copies the reviewer's kill file (B1) from expected/ to the same path in <tree>.
# 2. Makes the reviewer's N1 and N2 edits in web/tests/dec1102-card-data.spec.ts.
# 3. Makes the N3 and N4 wording edits in web/src/data/cardCache.ts, web/README.md and the
#    spec header.
# Each edit finds its old text exactly once, or the script stops and names the edit. An edit
# whose new text is already there and whose old text is gone prints "already" (a second run
# changes nothing). core.py imports EDITS from this file.
import os, shutil, sys

KILL = 'web/src/__tests__/components/DecklistNoRefresh.test.tsx'
SPEC = 'web/tests/dec1102-card-data.spec.ts'
CACHE = 'web/src/data/cardCache.ts'
README = 'web/README.md'

EDITS = [
    # N2: the deck page hover case runs on old prices, as the header says.
    (SPEC, 'N2',
     "  await page.clock.install({ time: PRICES_ARE_FRESH });\n  await page.goto('/deck/creeping-corruption');\n"
     "  const names = page.locator('.gv1-apo-pin[data-card-name], article[data-card-name]');\n",
     "  await page.clock.install({ time: pricesAreOld() });\n  await page.goto('/deck/creeping-corruption');\n"
     "  const names = page.locator('.gv1-apo-pin[data-card-name], article[data-card-name]');\n"),
    # N1: look again after a batch's time, so that main's tile fails the case in every run.
    (SPEC, 'N1',
     "    await expect.poll(async () => (await cardKeys()).filter((key) => USD.has(key)).length).toBe(0);\n"
     "    // Only the faces that the file does not hold as names stay.\n",
     "    await expect.poll(async () => (await cardKeys()).filter((key) => USD.has(key)).length).toBe(0);\n"
     "    // No tile asks for a refresh, which would store a key for its name: look again after a batch's time.\n"
     "    await page.waitForTimeout(3_000);\n"
     "    expect((await cardKeys()).filter((key) => USD.has(key))).toEqual([]);\n"
     "    // Only the faces that the file does not hold as names stay.\n"),
    # N4: the spec header.
    (SPEC, 'N4-spec',
     "// after the file's `prices_as_of`. A deck page sends no request for a deck card\n"
     "// at any date, so its cases run on a clock at which every price is older than\n"
     "// 24 h. tests/dec1131-card-batches.spec.ts holds the refresh.\n",
     "// after the file's `prices_as_of`. A deck page sends no price request for a\n"
     "// deck card at any date, so its cases run on a clock at which every price is\n"
     "// older than 24 h. tests/dec1131-card-batches.spec.ts holds the refresh.\n"),
    # N3 and N4: the cardCache.ts header.
    (CACHE, 'N3+N4-cache',
     "//     /shopping rows alone; a deck page sends no request for a deck card at any\n"
     "//     date, DEC-1172). Only the price and its date change. A deck guide tile\n"
     "//     that shows the cache's price shows a live refresh too. When the file is\n"
     "//     newer than the refresh, the file's price wins. A refresh that gets no\n"
     "//     price (not found, a 400 or 422, or `usd` null) keeps the price shown, and\n"
     "//     nobody asks again for 24 h.\n",
     "//     /shopping rows alone; a deck page sends no price request for a deck card\n"
     "//     at any date, DEC-1172). Only the price and its date change. A deck guide\n"
     "//     tile that shows the cache's price shows the price that /shopping\n"
     "//     refreshed in this browser inside 24 h, and asks for none itself. When the\n"
     "//     file is newer than the refresh, the file's price wins. A refresh that\n"
     "//     gets no price (not found, a 400 or 422, or `usd` null) keeps the price\n"
     "//     shown, and nobody asks again for 24 h.\n"),
    # N4: README, the test clock passage.
    (README, 'N4-readme-clock',
     "  page sends no request for a deck card at any date, so a deck page case that proves \"no\n"
     "  request\" sets the clock to more than 24 h after. Write no date into a spec: read it from the\n"
     "  meta file.\n",
     "  page sends no price request for a deck card at any date, so a deck page case that proves\n"
     "  \"no request\" sets the clock to more than 24 h after. Write no date into a spec: read it from\n"
     "  the meta file.\n"),
    # N4: README, the refresh bullet of "Scryfall requests".
    (README, 'N4-readme-bullet',
     "- /shopping alone asks again for a price older than 24 h. A deck page sends no request for a\n"
     "  deck card at any date: a tile shows the deck file's highlight price first, else the cache's\n"
     "  price (the file's, or the price that /shopping refreshed in this browser inside 24 h). A\n"
     "  refresh changes only the price and its date, and lives 24 h under `gv1-card:` next to the\n"
     "  file's entry; the file's price wins when the file is newer. A refresh that gets no price\n"
     "  keeps the price shown and is not asked again inside 24 h.\n",
     "- /shopping alone asks again for a price older than 24 h. A deck page sends no price request\n"
     "  for a deck card at any date: a tile shows the deck file's highlight price first, else the\n"
     "  cache's price (the file's, or the price that /shopping refreshed in this browser inside\n"
     "  24 h). A refresh changes only the price and its date, and lives 24 h under `gv1-card:` next\n"
     "  to the file's entry; the file's price wins when the file is newer. A refresh that gets no\n"
     "  price keeps the price shown and is not asked again inside 24 h.\n"),
]


def edit_text(path, text, log=print):
    """Apply every edit of `path` to `text`; return the new text. Stops on a missing span."""
    for p, name, old, new in EDITS:
        if p != path:
            continue
        n_old, n_new = text.count(old), text.count(new)
        if n_old == 1:
            text = text.replace(old, new)
            log(f'{name}: done')
        elif n_old == 0 and n_new == 1:
            log(f'{name}: already')
        else:
            raise SystemExit(f'{name}: STOP, old text found {n_old} times and new text {n_new} times in {path}')
    return text


def main(tree):
    here = os.path.dirname(os.path.abspath(__file__))
    dst = os.path.join(tree, KILL)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(here, 'expected', KILL), dst)
    print(f'B1: {KILL} copied')
    for path in (SPEC, CACHE, README):
        full = os.path.join(tree, path)
        with open(full, encoding='utf-8', newline='') as f:
            text = f.read()
        out = edit_text(path, text)
        if out != text:
            with open(full, 'w', encoding='utf-8', newline='') as f:
                f.write(out)


if __name__ == '__main__':
    main(sys.argv[1])
