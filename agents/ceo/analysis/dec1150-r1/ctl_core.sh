#!/bin/sh
# The CEO's controls for core.py (fix round 1 of PR #60, DEC-1150). Usage: sh ctl_core.sh <repo>
# Each control is a local commit that nothing pushes; no ref moves.
#   A  af1f93b itself: the kill file MISSING, NOT EQUAL.
#   B  origin/main merged into af1f93b, plus the kill file with a reworded comment and a wrapped
#      call: ALL EQUAL.
#   C  B with toBe(1) changed to toBe(2) in K1: the kill file DIFFERENT, NOT EQUAL.
#   D  a simulated main with PR #61 (e882c60) merged, then af1f93b merged into it with the
#      Shopping.test.tsx conflict resolved by keeping both blocks, plus the kill file: ALL EQUAL.
#   E  D with one line of PR #60's DEC-1141 block dropped: resolution BAD, NOT EQUAL.
set -u
REPO=$1
KIT=$(cd "$(dirname "$0")" && pwd)
HEAD=af1f93b51d582bc04f7fb917e9b628f9b9091bf4
PR61=e882c609e98cb83b38fc65d3aa7a763d8a9f9725
KILL=web/src/__tests__/dec1150/kill-shopping.test.tsx
TEST=web/src/__tests__/components/Shopping.test.tsx
export GIT_AUTHOR_NAME=ceo GIT_AUTHOR_EMAIL=ceo@local GIT_COMMITTER_NAME=ceo GIT_COMMITTER_EMAIL=ceo@local
export GIT_AUTHOR_DATE=2026-10-15T16:30:00Z GIT_COMMITTER_DATE=2026-10-15T16:30:00Z
TMP=$(mktemp -d)
g() { git -C "$REPO" "$@"; }

# build <tree> <kill file> [<test file>]: the tree with the kill file (and the test file) replaced.
build() {
  GIT_INDEX_FILE=$TMP/index g read-tree "$1"
  kb=$(g hash-object -w "$2")
  GIT_INDEX_FILE=$TMP/index g update-index --add --cacheinfo "100644,$kb,$KILL"
  if [ $# -ge 3 ]; then
    tb=$(g hash-object -w "$3")
    GIT_INDEX_FILE=$TMP/index g update-index --cacheinfo "100644,$tb,$TEST"
  fi
  GIT_INDEX_FILE=$TMP/index g write-tree
}

# B's kill file: a reworded first comment, and K1's expect wrapped over three lines with a trailing comma.
python3 -I - "$KIT/expected/$KILL" "$TMP/kill-b.tsx" <<'PY'
import sys
s = open(sys.argv[1]).read()
a = "// DEC-1150 review kill cases for PR #60 (DEC-1141). Each case passes on the\n"
assert s.count(a) == 1
s = s.replace(a, "// Kill cases from the DEC-1150 review of PR #60. Each one passes on the\n")
b = "    expect(parseOwnedFile('Name,Quantity\\nSol Ring,abc\\n').get('Sol Ring')).toBe(1);\n"
assert s.count(b) == 1
s = s.replace(b, "    expect(\n      parseOwnedFile('Name,Quantity\\nSol Ring,abc\\n').get('Sol Ring'),\n    ).toBe(1);\n")
open(sys.argv[2], 'w').write(s)
PY
python3 -I - "$TMP/kill-b.tsx" "$TMP/kill-c.tsx" <<'PY'
import sys
s = open(sys.argv[1]).read()
a = "    ).toBe(1);\n"
assert s.count(a) == 1
open(sys.argv[2], 'w').write(s.replace(a, "    ).toBe(2);\n"))
PY

MAINC=$(g rev-parse origin/main)
B=$(g commit-tree "$(build "$(g merge-tree --write-tree "$MAINC" $HEAD)" "$TMP/kill-b.tsx")" -p "$MAINC" -p $HEAD -m 'ctl B')
C=$(g commit-tree "$(build "$(g merge-tree --write-tree "$MAINC" $HEAD)" "$TMP/kill-c.tsx")" -p "$MAINC" -p $HEAD -m 'ctl C')

SM=$(g commit-tree "$(g merge-tree --write-tree "$MAINC" $PR61)" -p "$MAINC" -p $PR61 -m 'ctl simulated main with PR #61')
CT=$(g merge-tree --write-tree "$SM" $HEAD | head -1)
# Keep both blocks: git moves the two closing lines that both sides share below the conflict, so the
# first block gets them back (`    });`, `  });`) and a blank line before the second block.
g show "$CT:$TEST" | python3 -I -c "
import re, sys
out = []
for l in sys.stdin.read().split('\n'):
    if re.match(r'^(<<<<<<<|>>>>>>>)( |$)', l):
        continue
    out += ['    });', '  });', ''] if l == '=======' else [l]
sys.stdout.write('\n'.join(out))
" > "$TMP/test-d.tsx"
D=$(g commit-tree "$(build "$CT" "$KIT/expected/$KILL" "$TMP/test-d.tsx")" -p "$SM" -p $HEAD -m 'ctl D')
python3 -I - "$TMP/test-d.tsx" "$TMP/test-e.tsx" <<'PY'
import sys
s = open(sys.argv[1]).read()
a = "  describe('an owned quantity is a whole number of 1 or more (DEC-1141)', () => {\n"
assert s.count(a) == 1
open(sys.argv[2], 'w').write(s.replace(a, ''))
PY
E=$(g commit-tree "$(build "$CT" "$KIT/expected/$KILL" "$TMP/test-e.tsx")" -p "$SM" -p $HEAD -m 'ctl E')

for c in "A $HEAD origin/main" "B $B origin/main" "C $C origin/main" "D $D $SM" "E $E $SM"; do
  set -- $c
  echo "== $1 ($2, main $3)"
  python3 -I "$KIT/core.py" "$REPO" "$2" "$3"
  echo "exit $?"
done
rm -rf "$TMP"
