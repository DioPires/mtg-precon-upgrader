# Build the expected unit files for fix round 1 of PR #61 (DEC-1142, review DEC-1151).
# Usage: python3 -I build_expected.py
# Takes the head's files (e882c60, in head/) and the reviewer's kill files (in reviewer/), and
# makes only the edits that the move into the head's files needs. Each edit asserts its anchor.
# 1. Shopping.test.tsx (B1): the reviewer's case as a fifth `it` at the end of the DEC-1142
#    block. The block's idiom: renderShopping() for render(<Shopping ... />), and the block's
#    buyHead()/ownHead() helpers for the case's own consts (the same queries).
# 2. cardNoun.test.ts (B2): 1.5 joins the it.each list after 0.5; the comment names the
#    rounding mutants.
# 3. Engine.test.tsx (N2, ruling on DEC-1151): the reviewer's offered case as a third `it`, with
#    the role built by the file's role() helper and `count` set to 1.
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


# 1. Shopping.test.tsx
shop = read('head', 'Shopping.test.tsx')
kill = read('reviewer', 'dec1151-kill-shopping.test.tsx')
for line in (
    "    localStorage.setItem(STORAGE_KEY, JSON.stringify([['Solo A Commander', 1]]));\n",
    "    render(<Shopping decks={[SOLO_A, SOLO_B]} />);\n",
    "    fireEvent.click(screen.getByRole('button', { name: /Select all/i }));\n",
    "    const buyHead = screen.getByRole('heading', { name: 'Need to buy' }).parentElement!;\n",
    "    const ownHead = screen.getByRole('button', { name: /Already own/ });\n",
    "    expect(within(buyHead).getByText('· 2 unique · 3 cards')).toBeInTheDocument();\n",
    "    expect(within(ownHead).getByText('· 1 unique · 1 card')).toBeInTheDocument();\n",
):
    assert kill.count(line) == 1, line
# The head's block defines the same fixtures and the same two queries as the kill file.
for line in (
    "      list: [group('Commander', ['Solo A Commander']), group('Ramp (1)', ['Sol Ring'])],\n",
    "      list: [group('Commander', ['Solo B Commander']), group('Ramp (1)', ['Sol Ring'])],\n",
    "    const buyHead = () => screen.getByRole('heading', { name: 'Need to buy' }).parentElement!;\n",
    "    const ownHead = () => screen.getByRole('button', { name: /Already own/ });\n",
):
    assert shop.count(line) == 1, line
case = (
    "\n"
    "    // The user owns Solo A Commander alone. With both decks selected, Need to buy holds\n"
    "    // Solo B Commander and two Sol Rings (2 unique, 3 cards) and Already own holds one\n"
    "    // card, so each header must read the counts of its own section.\n"
    "    it('reads `2 unique · 3 cards` to buy and `1 unique · 1 card` owned when the sections hold different counts', () => {\n"
    "      localStorage.setItem(STORAGE_KEY, JSON.stringify([['Solo A Commander', 1]]));\n"
    "      renderShopping([SOLO_A, SOLO_B]);\n"
    "      fireEvent.click(screen.getByRole('button', { name: /Select all/i }));\n"
    "      expect(within(buyHead()).getByText('· 2 unique · 3 cards')).toBeInTheDocument();\n"
    "      expect(within(ownHead()).getByText('· 1 unique · 1 card')).toBeInTheDocument();\n"
    "    });\n"
)
anchor = (
    "      expect(within(ownHead()).getByText('· 1 unique · 2 cards')).toBeInTheDocument();\n"
    "    });\n"
)
shop = once(shop, anchor, anchor + case)
write('components/Shopping.test.tsx', shop)

# 2. cardNoun.test.ts
noun = read('head', 'cardNoun.test.ts')
noun = once(
    noun,
    "  // Each count holds the helper to its declared type (`count: number`): 0 and 0.5\n"
    "  // fail `count <= 1` and `count < 2`, 2 fails `count > 1 ? 'cards' : 'card'`, and\n"
    "  // -1 fails `Math.abs(count) === 1`.\n",
    "  // Each count holds the helper to its declared type (`count: number`): 0 and 0.5\n"
    "  // fail `count <= 1` and `count < 2`, 2 fails `count > 1 ? 'cards' : 'card'`, and\n"
    "  // -1 fails `Math.abs(count) === 1`. 0.5 fails `Math.round` and `Math.ceil`, and\n"
    "  // 1.5 fails `Math.floor` and `Math.trunc`.\n",
)
noun = once(noun, "it.each([0, 2, -1, 0.5, NaN])", "it.each([0, 2, -1, 0.5, 1.5, NaN])")
assert "expect(cardNoun(1.5)).toBe('cards');" in read('reviewer', 'dec1151-kill-cardNoun.test.ts')
write('lib/cardNoun.test.ts', noun)

# 3. Engine.test.tsx
eng = read('head', 'Engine.test.tsx')
ekill = read('reviewer', 'dec1151-kill-engine.test.tsx')
assert ekill.count("  count: 1,\n") == 1
assert ekill.count("['Sol Ring', 'Arcane Signet']") == 1
assert ekill.count("expect(screen.getByRole('tabpanel')).toHaveTextContent('1 card · hover for full frame');") == 1
ecase = (
    "\n"
    "  // A role keeps `count` and `cards` apart, and the line reads `count`. normalize.ts\n"
    "  // builds no role whose two differ today; this case holds the line to its type.\n"
    "  it('reads `1 card` for a role of count 1 that lists two tiles', () => {\n"
    "    render(<Engine engine={[{ ...role('Ramp', ['Sol Ring', 'Arcane Signet']), count: 1 }]} />);\n"
    "    expect(screen.getByRole('tabpanel')).toHaveTextContent('1 card · hover for full frame');\n"
    "  });\n"
)
eanchor = (
    "    expect(screen.getByRole('tabpanel')).toHaveTextContent('2 cards · hover for full frame');\n"
    "  });\n"
)
eng = once(eng, eanchor, eanchor + ecase)
write('components/Engine.test.tsx', eng)
