#!/bin/bash
# DEC-1173 route A runs. Usage: TREE=<tree> LOG=<dir> run_kill.sh
# Needs the kill file committed in TREE (web/src/__tests__/components/dec1173-stopline-date.test.tsx)
# and a clean tree. Runs: typecheck, eslint on the file, the file, the full unit suite, then the
# mutants E5 (pricesDate={pricesDate}) and E4 (pricesDate={null}) on Shopping.tsx's <PricePausedLine />,
# each restored from HEAD after its run. Each mutant must fail the file at :96.
set -u
: "${TREE:?set TREE}" "${LOG:?set LOG}"
WEB=$TREE/web
SRC=$WEB/src/components/organisms/Shopping.tsx
KF=src/__tests__/components/dec1173-stopline-date.test.tsx
export HOME="$PAPERCLIP_GITHUB_HOST_HOME"
mkdir -p "$LOG"
cd "$WEB"
[ -z "$(git status --porcelain)" ] || { echo "tree not clean"; git status --porcelain; exit 2; }
[ -f "$KF" ] || { echo "kill file missing: $KF"; exit 2; }
npm run typecheck > "$LOG/typecheck.log" 2>&1; echo "typecheck exit $?"
npx eslint "$KF" > "$LOG/eslint.log" 2>&1; echo "eslint exit $?"
npx vitest run "$KF" > "$LOG/kill-head.log" 2>&1; echo "kill-head exit $?"
npx vitest run > "$LOG/unit-all.log" 2>&1; echo "unit-all exit $?"
for m in E5 E4; do
  case $m in E5) new='pricesDate={pricesDate} />';; E4) new='pricesDate={null} />';; esac
  python3 -I - "$SRC" "$new" <<'PY'
import sys; p, new = sys.argv[1], sys.argv[2]; s = open(p).read(); o = 'pricesDate={shownPricesDate} />\n      </section>'
assert s.count(o) == 1, 'the head line moved: stop and hand back'; open(p, 'w').write(s.replace(o, new + '\n      </section>'))
PY
  git diff -- "$SRC" > "$LOG/mutant-$m.diff"
  npx vitest run "$KF" > "$LOG/kill-$m.log" 2>&1; echo "kill-$m exit $? (must be 1)"
  git checkout HEAD -- "$SRC"
done
grep -h -E 'Test Files|Tests ' "$LOG"/kill-head.log "$LOG"/unit-all.log "$LOG"/kill-E5.log "$LOG"/kill-E4.log
grep -h -A1 'Received' "$LOG"/kill-E5.log "$LOG"/kill-E4.log
echo "porcelain:"; git status --porcelain; echo "(end; empty means clean)"
