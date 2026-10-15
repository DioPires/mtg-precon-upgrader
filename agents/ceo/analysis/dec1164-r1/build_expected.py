# Build the expected unit files for fix round 1 of PR #66 (DEC-1155, review DEC-1164).
# Usage: python3 -I build_expected.py
# Takes the head's files (ff7ead8, in head/) and the reviewer's kill files (in reviewer/), and
# makes only the edits that the move into the head's files needs. Each edit asserts its anchor.
# 1. ComboLab.test.tsx (B1, mutants R1 and R2): the reviewer's one table row joins the head's
#    it.each table of the DEC-1150 block as its fourth row. The kill file's table and test body
#    are the head's, so the row moves alone.
# 2. ownedCards.test.ts (B2, mutant R9): the reviewer's case as an `it` of the head's
#    describe('readOwnedEntries (DEC-1150)'), after 'reads localStorage when no storage is given'
#    (the other case that reads localStorage), indented by two spaces. Its text is byte for byte.
import os

here = os.path.dirname(os.path.abspath(__file__))


def read(*p):
    return open(os.path.join(here, *p)).read()


def write(rel, text):
    out = os.path.join(here, 'expected', 'web', 'src', '__tests__', rel)
    open(out, 'w').write(text)
    print('wrote', out)


def once(text, old, new):
    assert text.count(old) == 1, (text.count(old), old[:80])
    return text.replace(old, new)


# 1. ComboLab.test.tsx
lab = read('head', 'ComboLab.test.tsx')
kill = read('reviewer', 'kill-combolab.test.tsx')
row = "    [[['Sol Ring', 2], ['Arcane Signet', 1]], '3 owned cards on file'],\n"
assert kill.count(row) == 1
# The kill file's test body is the head's, line for line.
body = (
    "  ])('counts the cards of the store %j: %s', async (store, text) => {\n"
    "    const panel = await openFleet(store);\n"
    "    const chip = within(panel).getByRole('button', { name: 'Owned only' });\n"
    "    expect(chip).toBeEnabled();\n"
    "    expect(chip).toHaveAttribute('title', text);\n"
    "    expect(within(panel).getByText(`${text} — imported in § IX Shopping`)).toBeInTheDocument();\n"
    "  });\n"
)
assert kill.count(body) == 1 and lab.count(body) == 1
anchor = "    [[['Sol Ring', -1], ['Arcane Signet', 1]], '1 owned card on file'],\n"
lab = once(lab, anchor + body[:4], anchor + row + body[:4])
write('routes/ComboLab.test.tsx', lab)

# 2. ownedCards.test.ts
own = read('head', 'ownedCards.test.ts')
okill = read('reviewer', 'kill-owned.test.ts')
case = (
    "it('keeps a stored name with spaces around it as stored', () => {\n"
    "  localStorage.setItem(OWNED_KEY, JSON.stringify([[' Sol Ring ', 1]]));\n"
    "  try {\n"
    "    expect(readOwnedEntries()).toEqual([[' Sol Ring ', 1]]);\n"
    "  } finally {\n"
    "    localStorage.removeItem(OWNED_KEY);\n"
    "  }\n"
    "});\n"
)
assert okill.count(case) == 1
# The kill file's key is the head's.
assert okill.count("const OWNED_KEY = 'grimoire-owned-cards';\n") == 1
assert own.count("const OWNED_KEY = 'grimoire-owned-cards';\n") == 1
indented = ''.join('  ' + l if l.strip() else l for l in case.splitlines(keepends=True))
oanchor = (
    "  it('reads localStorage when no storage is given', () => {\n"
    "    localStorage.setItem(OWNED_KEY, JSON.stringify([['Sol Ring', 1]]));\n"
    "    try {\n"
    "      expect(readOwnedEntries()).toEqual([['Sol Ring', 1]]);\n"
    "    } finally {\n"
    "      localStorage.removeItem(OWNED_KEY);\n"
    "    }\n"
    "  });\n"
)
own = once(own, oanchor, oanchor + "\n" + indented)
write('data/ownedCards.test.ts', own)
