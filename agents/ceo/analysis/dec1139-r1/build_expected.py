# Build the expected Shopping.test.tsx for fix round 1 of PR #53 (DEC-1123, review DEC-1139).
# Usage: python3 -I build_expected.py
# Takes the head's file (d7603be) and the reviewer's kill file, cuts case K1 out of the kill
# file, re-indents it into the DEC-1123 describe block after case b, and makes only the edits
# that the move needs: renderShopping([ALPHA]) for render(<Shopping decks={[ALPHA]} />) (the
# block's idiom; the head's ALPHA holds the same list), and the title without the `K1: `
# prefix, with `(DEC-1139 B1)` at the end. K2 stays out (ruling on DEC-1139 B2).
import os

here = os.path.dirname(os.path.abspath(__file__))
head = open(os.path.join(here, 'head-Shopping.test.tsx')).read()
kill = open(os.path.join(here, 'reviewer', 'Shopping.dec1139-kill.test.tsx')).read()

start = kill.index("  it('K1: ")
end = kill.index("  it('K2: ")
k1 = kill[start:end].rstrip('\n') + '\n'
assert k1.count("  it(") == 1 and k1.endswith('  });\n'), k1[-40:]

old_title = "it('K1: reads `1 unique card` for a one-name file when the list already holds another name', async () => {"
new_title = "it('reads `1 unique card` for a one-name file when the list already holds another name (DEC-1139 B1)', async () => {"
assert k1.count(old_title) == 1
k1 = k1.replace(old_title, new_title)
old_render = "const { container } = render(<Shopping decks={[ALPHA]} />);"
assert k1.count(old_render) == 1
k1 = k1.replace(old_render, "const { container } = renderShopping([ALPHA]);")
k1 = ''.join(('  ' + l if l.strip() else l) for l in k1.splitlines(True))

anchor = (
    "      expect(screen.getByText('4 cards loaded — saved locally')).toBeInTheDocument();\n"
    "    });\n"
    "  });\n"
    "});\n"
)
assert head.count(anchor) == 1
new = head.replace(anchor, anchor[: -len("  });\n});\n")] + '\n' + k1 + "  });\n});\n")
out = os.path.join(here, 'expected', 'web', 'src', '__tests__', 'components', 'Shopping.test.tsx')
open(out, 'w').write(new)
print('wrote', out, len(head.splitlines()), '->', len(new.splitlines()), 'lines')
