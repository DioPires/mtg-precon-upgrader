#!/bin/bash
# CEO checks for the DEC-1173 route A round: the kill file on main + PR #72, the full unit suite, E5 and E4.
set -u
WEB=/tmp/dec1173-ceo/sim/web
SRC=$WEB/src/components/organisms/Shopping.tsx
L=/tmp/dec1173-ceo/logs
K=src/__tests__/components/dec1173-stopline-date.test.tsx
export HOME="$PAPERCLIP_GITHUB_HOST_HOME"
cd "$WEB"
npx vitest run $K > $L/kill-merged.log 2>&1; echo "kill-merged exit $?"
npx vitest run > $L/unit-all-merged.log 2>&1; echo "unit-all-merged exit $?"
for m in E5 E4; do
  case $m in E5) new='pricesDate={pricesDate} />';; E4) new='pricesDate={null} />';; esac
  python3 -I - "$SRC" "$new" <<'PY'
import sys; p, new = sys.argv[1], sys.argv[2]; s = open(p).read(); o = 'pricesDate={shownPricesDate} />\n      </section>'
assert s.count(o) == 1; open(p, 'w').write(s.replace(o, new + '\n      </section>'))
PY
  git diff -- "$SRC" > $L/mutant-$m.diff
  npx vitest run $K > $L/kill-$m.log 2>&1; echo "kill-$m exit $?"
  git checkout HEAD -- "$SRC"
done
git status --porcelain
