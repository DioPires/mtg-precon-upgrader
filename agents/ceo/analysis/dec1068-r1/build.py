# Route A, fix round 1 of PR #31 (DEC-1068, review DEC-1097): build the expected
# Apothecary.test.tsx from the head's file (ab90e26, blob 540bf4dd) and the
# reviewer's kill cases (/tmp/dec1068-review/kill/dec1097-kill.test.tsx).
# The block goes at the end of describe('filter status line (DEC-1068)').
# Changes from the reviewer's run file: the duplicate statusLine helper is
# dropped (the block's parent holds the same body), the describe and case
# names lose the "K1:" style prefixes, the indentation follows the nesting, and
# card() takes `role?: string` (RawCandidate.deck_role is `string | undefined`;
# the run file passed null, which tsc refuses and vitest does not check).
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, 'head-Apothecary.test.tsx')).read().split('\n')
assert src[-1] == '' and src[-2] == '});' and src[-3] == '  });' and src[-4] == '    });', src[-5:]
assert src[-5] == "      expect(statusLine(container).textContent).toBe('');", src[-5]
assert sum(1 for l in src if l.startswith("  describe('filter status line (DEC-1068)'")) == 1
block = open(os.path.join(here, 'block.txt')).read().rstrip('\n').split('\n')
out = src[:-3] + block + src[-3:]
dst = os.path.join(here, 'expected/web/src/__tests__/components/Apothecary.test.tsx')
open(dst, 'w').write('\n'.join(out))
print(dst, len(out) - 1, 'lines')
