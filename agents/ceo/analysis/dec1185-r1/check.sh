#!/bin/zsh
# Kill runs for fix round 1 of PR #76 (DEC-1177, review DEC-1185, route A).
# Usage: check.sh <tree>/web <label> <variant>...    variant: head | a mutant id of reviewer/mutate.py
#   O1-shop-nodecks-noclass O2-shop-allowned-noclass (B1), O6-lab-fontsize O8-lab-color (B2).
# For each variant: the whole Shopping.test.tsx, then the spec with the fonts live and a scratch copy
# with the fonts blocked (made from the tree's own spec). Logs go to <kit>/logs/<label>/.
# Restores the four source files and removes the scratch copy at the end.
set -u
WEB=$1; LABEL=$2; shift 2
KIT=${0:A:h}
OUT=$KIT/logs/$LABEL
mkdir -p $OUT/pristine
export HOME="$PAPERCLIP_GITHUB_HOST_HOME" PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"
export GRIMOIRE_E2E_PORT=${GRIMOIRE_E2E_PORT:?set GRIMOIRE_E2E_PORT to the value of your tree}
FILES=(src/components/organisms/Shopping.tsx src/components/organisms/Compare.tsx src/styles/states.css src/styles/combo-lab.css)
if git -C $WEB rev-parse --git-dir >/dev/null 2>&1; then
  git -C $WEB diff --quiet HEAD -- $FILES || { echo "the tree's source files differ from HEAD: restore them first"; exit 2; }
fi
for f in $FILES; do cp $WEB/$f $OUT/pristine/${f:t}; done
BLOCKED=$WEB/tests/zz-dec1185-kill-blocked.spec.ts
python3 -I - $WEB/tests/dec1177-empty-sigils.spec.ts $BLOCKED <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
imp = "import { expect, test, type Page } from './support/test';\n"
assert s.count(imp) == 1, 'import line not found once'
open(dst, 'w', encoding='utf-8').write(s.replace(imp, imp + "\ntest.use({ fonts: 'blocked' });\n"))
PY
for m in "$@"; do
  for f in $FILES; do cp $OUT/pristine/${f:t} $WEB/$f; done
  if [ "$m" != head ]; then python3 -I $KIT/reviewer/mutate.py $WEB $m >/dev/null || { echo "$m APPLY-FAILED"; continue; }; fi
  (cd $WEB && npx vitest run src/__tests__/components/Shopping.test.tsx > $OUT/$m.unit-shop.log 2>&1)
  (cd $WEB && npx playwright test tests/dec1177-empty-sigils.spec.ts tests/zz-dec1185-kill-blocked.spec.ts --workers=3 > $OUT/$m.e2e.log 2>&1)
  US=$(perl -pe 's/\e\[[0-9;]*m//g' $OUT/$m.unit-shop.log | grep -E "^\s+Tests " | tr -s ' ')
  E=$(perl -pe 's/\e\[[0-9;]*m//g' $OUT/$m.e2e.log | grep -E "^\s+[0-9]+ (passed|failed)" | tr -s ' ' | tr '\n' ' ')
  echo "$m | shop:$US | e2e (live + blocked): $E" | tee -a $OUT/summary.txt
done
for f in $FILES; do cp $OUT/pristine/${f:t} $WEB/$f; done
rm -f $BLOCKED
