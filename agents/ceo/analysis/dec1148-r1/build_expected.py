# Build the expected DeckSelector.test.tsx for fix round 1 of PR #59 (DEC-1135, review DEC-1148).
# Usage: python3 -I build_expected.py <head file> <reviewer kill file> <out>
# The head's file (a83a297, blob 666c3c1f) gets one new describe block at its end: the
# reviewer's describe block from the kill file, with three edits, each asserted once.
#   1. The describe title names the block as the surrounding blocks do.
#   2. Each case name drops its mutant tag ("M4: " and so on).
#   3. The kill file's own copies of the imports, `makeDecks`, `route` and `Harness` stay out:
#      the head's file holds the same code (asserted below).
import sys

head, kill, out = sys.argv[1:4]
h = open(head).read()
k = open(kill).read()

# The helpers that the kill file copies must equal the head's, character for character.
for part in [
    "function makeDecks(n: number): DeckStub[] {\n  return Array.from({ length: n }, (_, i) => ({\n",
    "let route: (idx: number) => void = () => {};\nfunction Harness({ decks, start }: { decks: DeckStub[]; start: number }) {\n  const [active, setActive] = useState(start);\n  route = setActive;\n  return <DeckSelector decks={decks} activeIdx={active} onSelect={setActive} />;\n}\n",
]:
    assert h.count(part) == 1 and k.count(part) == 1, part
mk = k[k.index("function makeDecks"):k.index("let route")]
assert mk.strip() in h, 'makeDecks differs'
assert h.startswith("import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';\n")

start = "describe('DEC-1148 kill cases', () => {\n"
assert k.count(start) == 1
block = k[k.index(start):]
assert block.endswith("});\n")

edits = [
    (start, "// The review's cases (DEC-1148 B1 to B4). Each one fails on one mutant that the\n// cases above let pass.\ndescribe('DeckSelector focus after a key switch: review cases (DEC-1148)', () => {\n"),
    ("it('M4: moves no focus", "it('moves no focus"),
    ("it('M5: focuses with preventScroll", "it('focuses with preventScroll"),
    ("it('M15: focuses the pill", "it('focuses the pill"),
    ("it(\"M18: reports the key's pick", "it(\"reports the key's pick"),
]
for a, b in edits:
    assert block.count(a) == 1, a
    block = block.replace(a, b)
assert h.endswith("});\n")
open(out, 'w').write(h + "\n" + block)
print('wrote', out)
