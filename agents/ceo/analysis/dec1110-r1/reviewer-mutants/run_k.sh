#!/bin/zsh
# DEC-1110: runs one reviewer mutant. The unit suite and the reviewer's kill file
# first; the e2e spec only when the unit suite does not kill it (or E2E=always);
# for H mutants the scratch harness spec and the 6d case too. Restores the tree after.
set -u
M=$1
D=/tmp/dec1110/kmutants
WEB=/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1110-review/web
cd $WEB
export HOME="$PAPERCLIP_GITHUB_HOST_HOME"
export PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"
python3 $D/apply_k.py $M > $D/$M.log 2>&1 || { echo "apply failed"; cat $D/$M.log; exit 1; }
git diff >> $D/$M.log
npx vitest run > $D/$M-unit.log 2>&1
KILL=kill-limiter.test.ts npx vitest run -c /tmp/dec1110/unit/vitest.config.mjs > $D/$M-kill.log 2>&1
unit=$(grep -E "^ +Tests " $D/$M-unit.log)
if [[ "$unit" != *failed* || "${E2E:-}" == always || $M == H* ]]; then
  GRIMOIRE_E2E_PORT=14661 npx playwright test tests/dec1102-card-data.spec.ts --reporter=list --workers 3 > $D/$M-e2e.log 2>&1
fi
if [[ $M == H* ]]; then
  (cd /tmp/dec1110/e2e && E2E_WEB=$WEB E2E_DIR=/tmp/dec1110/e2e/review E2E_OUT=/tmp/dec1110/e2e/out-$M GRIMOIRE_E2E_PORT=14661 \
    npx playwright test -c pw.config.ts harness.spec.ts readings.spec.ts -g "rate check|item 6d" > $D/$M-harness.log 2>&1)
fi
git checkout -- src tests
echo "porcelain after restore: [$(git status --porcelain)]" >> $D/$M.log
echo "== $M"; echo "unit: $unit"; echo "kill file: $(grep -E '^ +Tests ' $D/$M-kill.log)"
[[ -f $D/$M-e2e.log ]] && echo "e2e: $(grep -E '^ +[0-9]+ (passed|failed|flaky)' $D/$M-e2e.log | tr '\n' ' ')"
[[ -f $D/$M-harness.log ]] && echo "harness: $(grep -E '^ +[0-9]+ (passed|failed|flaky)' $D/$M-harness.log | tr '\n' ' ')"
tail -1 $D/$M.log
