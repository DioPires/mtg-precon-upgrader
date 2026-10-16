# Build the expected web/tests/dec1156-engine-title.spec.ts for fix round 1 of PR #68
# (DEC-1156, review DEC-1168, verdict 54c9d6d5, B1).
# Usage: python3 -I build_expected.py <head spec> <reviewer kill spec> <out>
# The reviewer's kill case (reviewer/short-viewport.spec.ts) goes in as a case of its
# own, right after case 1, inside `DEC-1156 rules: where they act`. That block already
# has `test.use({ cards: 'seeded', fonts: 'blocked' })`, the kill file's only setting,
# so the kill file's import and test.use lines stay out. The case's code is unchanged,
# indented by two spaces, under a two-line comment.
import sys

head_path, kill_path, out = sys.argv[1:4]
head = open(head_path).read()
kill = open(kill_path).read()

ANCHOR = (
    "    expect(got, 'The engine title font-size by viewport width').toEqual(want);\n"
    "  });\n"
)
assert head.count(ANCHOR) == 1, 'case 1 end'
assert head.count("test.describe('DEC-1156 rules: where they act', () => {\n"
                  "  test.use({ cards: 'seeded', fonts: 'blocked' });\n") == 1, 'block use'

start = kill.index("test('on a viewport lower than it is wide")
body = kill[start:]
assert body.endswith('});\n'), 'kill end'
assert "test.use({ cards: 'seeded', fonts: 'blocked' });" in kill[:start], 'kill use'
case = ''.join(('  ' + l) if l.strip() else l for l in body.splitlines(True))

comment = (
    "\n"
    "  // DEC-1168 B1: case 1's viewports are all 900px high, so 10vmin would read as\n"
    "  // 10vw there. On a phone on its side the title still follows the width.\n"
)
new = head.replace(ANCHOR, ANCHOR + comment + case)
open(out, 'w').write(new)
print(out, len(new.splitlines()), 'lines')
