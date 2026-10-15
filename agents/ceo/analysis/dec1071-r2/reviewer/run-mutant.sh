#!/bin/bash
# DEC-1103 delta 2: put one mutant into the export of 2ce4f20, then run.
# $1 label, $2 perl program for $3 (a file under web/), $4 mode: unit | e2e | e2e-logger,
# $5.. Playwright arguments. Port 14625; the logger listens on 127.0.0.1:14626.
set -e
LABEL="$1"; PROG="$2"; FILE="$3"; MODE="$4"; shift 4
TREE=/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1071-delta2
D=/tmp/dec1071-delta2
M=$D/mut
O=$D/mutants
REV=$(cat $D/export.rev)
rm -rf "$M/web/tests" "$M/web/src" "$M/web/playwright.config.ts" "$M/web/test-results"
HOME="$PAPERCLIP_GITHUB_HOST_HOME" git -C "$TREE" archive "$REV" web/tests web/src web/playwright.config.ts | tar -x -C "$M"
for f in $EXTRA_SPEC; do cp "$f" "$M/web/tests/"; done
if [ -n "$PROG" ]; then
  cp "$M/web/$FILE" "$O/$LABEL.before"
  perl -0pi -e "$PROG" "$M/web/$FILE"
  if cmp -s "$M/web/$FILE" "$O/$LABEL.before"; then echo "$LABEL: MUTANT NOT APPLIED"; exit 2; fi
  diff -u "$O/$LABEL.before" "$M/web/$FILE" | tail -n +3 > "$O/$LABEL.diff" || true
fi
# Safety: a run whose flag lacks the Moxfield block must map Moxfield to the logger.
if [ "$MODE" != unit ] && ! grep -q '\.\.\.MOXFIELD_DOMAINS\]' "$M/web/tests/support/guard.ts"; then
  grep -q "MAP \*moxfield\* 127.0.0.1:14626" "$M/web/tests/support/guard.ts" || { echo "$LABEL: NO MOXFIELD BLOCK AND NO SCRATCH RULE, NOT RUN"; exit 3; }
  [ "$MODE" = e2e-logger ] || { echo "$LABEL: scratch rule needs mode e2e-logger"; exit 3; }
  lsof -nP -iTCP:14626 -sTCP:LISTEN >/dev/null || { echo "$LABEL: logger not listening, NOT RUN"; exit 3; }
fi
cd "$M/web"
set +e
case "$MODE" in
  unit) npx vitest run src/__tests__/data/e2eGuardHosts.test.ts > "$O/$LABEL.log" 2>&1 ;;
  e2e|e2e-logger)
    [ "$MODE" = e2e-logger ] && echo "--- $LABEL $(date +%H:%M:%S)" >> "$D/logger.log"
    PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright" GRIMOIRE_E2E_PORT=14625 \
      npx playwright test --reporter=list "$@" > "$O/$LABEL.log" 2>&1 ;;
esac
RC=$?
echo "$LABEL rc=$RC"
