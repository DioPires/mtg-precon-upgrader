#!/bin/bash
# DEC-1103 review: run the kill cases against one mutant of the head.
# $1 = mutant label, $2 = perl program applied to $3 (file under web/), $4.. = spec filters.
set -e
LABEL="$1"; PROG="$2"; FILE="$3"; shift 3
REPO=/Users/dpires/Documents/Personal/code/mtg-precon-upgrader
M=/tmp/dec1071-review/mut
rm -rf "$M/web/tests" "$M/web/src" "$M/web/test-results"
HOME="$PAPERCLIP_GITHUB_HOST_HOME" git -C "$REPO" archive b31d9ea web/tests web/src web/playwright.config.ts | tar -x -C "$M"
/tmp/dec1071-review/kills/apply-kills.sh "$M/web"
cp "$M/web/$FILE" "/tmp/dec1071-review/kill-runs/$LABEL.before"
perl -0pi -e "$PROG" "$M/web/$FILE"
if cmp -s "$M/web/$FILE" "/tmp/dec1071-review/kill-runs/$LABEL.before"; then echo "$LABEL: MUTANT NOT APPLIED"; exit 2; fi
diff "/tmp/dec1071-review/kill-runs/$LABEL.before" "$M/web/$FILE" > "/tmp/dec1071-review/kill-runs/$LABEL.diff" || true
cd "$M/web"
echo "--- $LABEL $(date +%H:%M:%S)" >> /tmp/dec1071-review/kill-runs/proxy.log
set +e
PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright" PROXY_WEB=$PWD GRIMOIRE_E2E_PORT=14622 \
  npx playwright test -c /tmp/dec1071-review/proxy.config.ts "$@" > "/tmp/dec1071-review/kill-runs/$LABEL.log" 2>&1
RC=$?
echo "$LABEL rc=$RC $(grep -E '^\s+[0-9]+ (passed|failed|flaky|did not run)' /tmp/dec1071-review/kill-runs/$LABEL.log | tr -s ' ' | tr '\n' ';')"
