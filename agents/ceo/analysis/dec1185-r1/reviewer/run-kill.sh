#!/bin/zsh
# Usage: run-kill.sh <variant> ...  variant: head | main | <mutant id of /tmp/dec1185/mutate.py>.
# The kill copies of Shopping.test.tsx and the spec stand in the tree; a copy of the spec with the fonts blocked runs too.
set -u
TREE=/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1185-review
WEB=$TREE/web
OUT=/tmp/dec1185/kill/logs
export HOME="$PAPERCLIP_GITHUB_HOST_HOME" GRIMOIRE_E2E_PORT=14911 PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"
FILES=(web/src/components/organisms/Shopping.tsx web/src/components/organisms/Compare.tsx web/src/styles/states.css web/src/styles/combo-lab.css)
for m in "$@"; do
  cd $TREE && git checkout -q HEAD -- $FILES web/src/__tests__/components/Shopping.test.tsx web/tests/dec1177-empty-sigils.spec.ts
  if [ "$m" = main ]; then git checkout -q origin/main -- $FILES; elif [ "$m" != head ]; then python3 -I /tmp/dec1185/mutate.py $WEB $m >/dev/null || { echo "$m APPLY-FAILED"; continue; }; fi
  cp /tmp/dec1185/kill/Shopping.test.tsx $WEB/src/__tests__/components/Shopping.test.tsx
  cp /tmp/dec1185/kill/dec1177-empty-sigils.spec.ts $WEB/tests/dec1177-empty-sigils.spec.ts
  cp /tmp/dec1185/kill/zz-dec1185-kill-blocked.spec.ts $WEB/tests/
  git diff HEAD > $OUT/$m.diff
  cd $WEB
  npx vitest run src/__tests__/components/Shopping.test.tsx > $OUT/$m.unit-shop.log 2>&1
  npx playwright test tests/dec1177-empty-sigils.spec.ts tests/zz-dec1185-kill-blocked.spec.ts --workers=3 > $OUT/$m.e2e.log 2>&1
  rm tests/zz-dec1185-kill-blocked.spec.ts
  US=$(grep -E "^\s+Tests " $OUT/$m.unit-shop.log | sed 's/\x1b\[[0-9;]*m//g' | tr -s ' ')
  E=$(grep -E "^\s+[0-9]+ (passed|failed)" $OUT/$m.e2e.log | tr -s ' ' | tr '\n' ' ')
  F=$(sed 's/\x1b\[[0-9;]*m//g' $OUT/$m.e2e.log | grep -oE "^\s+[0-9]+\) \[chromium\] › tests/[a-z0-9-]+\.spec\.ts:[0-9]+" | sed -E 's/.*tests\///' | tr '\n' ' ')
  echo "$m | shop:$US | e2e (live + blocked): $E| failed at: $F"
done
cd $TREE && git checkout -q HEAD -- $FILES web/src/__tests__/components/Shopping.test.tsx web/tests/dec1177-empty-sigils.spec.ts && git status --porcelain
