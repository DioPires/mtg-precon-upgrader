#!/bin/bash
# DEC-1103 review: run the host unit file (with the proposed DNS case) against one mutant of guard.ts.
LABEL="$1"; PROG="$2"
REPO=/Users/dpires/Documents/Personal/code/mtg-precon-upgrader
M=/tmp/dec1071-review/mut
rm -rf "$M/web/tests" "$M/web/src"
HOME="$PAPERCLIP_GITHUB_HOST_HOME" git -C "$REPO" archive b31d9ea web/tests web/src | tar -x -C "$M"
/tmp/dec1071-review/kills/apply-kills.sh "$M/web"
F="$M/web/tests/support/guard.ts"
cp "$F" "/tmp/dec1071-review/kill-runs/$LABEL.before"
perl -0pi -e "$PROG" "$F"
if cmp -s "$F" "/tmp/dec1071-review/kill-runs/$LABEL.before"; then echo "$LABEL: MUTANT NOT APPLIED"; exit 2; fi
diff "/tmp/dec1071-review/kill-runs/$LABEL.before" "$F" > "/tmp/dec1071-review/kill-runs/$LABEL.diff"
cd "$M/web" && npx vitest run src/__tests__/data/e2eGuardHosts.test.ts > "/tmp/dec1071-review/kill-runs/$LABEL.log" 2>&1
echo "$LABEL rc=$? $(grep -E '^\s+Tests ' /tmp/dec1071-review/kill-runs/$LABEL.log | tr -s ' ') | failed: $(grep -cE '^\s+×' /tmp/dec1071-review/kill-runs/$LABEL.log) ($(grep -E '^\s+×' /tmp/dec1071-review/kill-runs/$LABEL.log | sed -E 's/.*host tests > //; s/ [0-9]+ms$//' | cut -c1-40 | tr '\n' '|'))"
