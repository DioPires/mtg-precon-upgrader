# Build the expected unit file for fix round 1 of PR #69 (DEC-1146, review DEC-1169).
# Usage: python3 -I build_expected.py
# Takes the head's file (64f2146, in head/) and the reviewer's kill file (in reviewer/kill/), and
# makes only the edits that the move into the head's file needs. Each edit asserts its anchor.
# 1. The kill file's harness AutoFocusGuide, with its comment, goes after the head's Guide.
#    The kill file's makeDecks and `let route` are the head's, so they do not move.
# 2. The kill file's case K1 goes into describe('... no key started (DEC-1146)') as its last
#    `it`, after 'moves no focus when focus is on an element outside the track that stays'.
#    Its body is byte for byte. Its name drops the review's "K1: " label, as the DEC-1148
#    review case in the head's file has no label.
import os

here = os.path.dirname(os.path.abspath(__file__))


def read(*p):
    return open(os.path.join(here, *p)).read()


def once(text, old, new):
    assert text.count(old) == 1, (text.count(old), old[:80])
    return text.replace(old, new)


head = read('head', 'DeckSelector.test.tsx')
kill = read('reviewer', 'kill', 'DeckSelector.dec1169-kill.test.tsx')

# The kill file's shared parts are the head's, line for line.
make = head[head.index('function makeDecks('):head.index('\n}\n', head.index('function makeDecks(')) + 3]
assert kill.count(make) == 1, 'makeDecks differs'
decl = 'let route: (idx: number) => void = () => {};\n'
assert kill.count(decl) == 1 and head.count(decl) == 1

# 1. The harness.
harness = kill[kill.index('// The guide around the selector: a chip that each deck mounts anew, and a\n'):
               kill.index("describe('DEC-1169 kill cases for PR #69'")]
assert harness.startswith('// The guide around the selector') and harness.endswith('}\n\n'), harness[-40:]
assert harness.count('function AutoFocusGuide(') == 1
guide_end = (
    "      <button type=\"button\">Stays</button>\n"
    "    </>\n"
    "  );\n"
    "}\n"
    "\n"
)
anchor1 = guide_end + "describe('DeckSelector focus after a key switch (DEC-1135)', () => {\n"
out = once(head, anchor1, guide_end + harness + anchor1[len(guide_end):])

# 2. The case.
start = kill.index("  it('K1: ")
case = kill[start:kill.index('\n  });\n', start) + len('\n  });\n')]
assert case.count("  it(") == 1 and case.endswith('  });\n')
case = once(case, "  it('K1: moves no focus", "  it('moves no focus")
last = (
    "    act(() => route(5));\n"
    "    expect(tabs[4]).toHaveAttribute('aria-selected', 'true');\n"
    "    expect(document.activeElement).toBe(stays);\n"
    "    expect(focus).not.toHaveBeenCalled();\n"
    "  });\n"
    "});\n"
)
assert out.endswith(last), 'the DEC-1146 block is not the file\'s last block'
comment = (
    "  // DEC-1169 B1 (mutant R1): case (a) needs focus on `body`. Here the new deck\n"
    "  // focuses its own field in the same update, and that focus stays.\n"
)
out = out[:-len('});\n')] + "\n" + comment + case + "});\n"

dst = os.path.join(here, 'expected', 'web', 'src', '__tests__', 'components', 'DeckSelector.test.tsx')
open(dst, 'w').write(out)
print('wrote', dst, len(out.splitlines()), 'lines')
