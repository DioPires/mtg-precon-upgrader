#!/bin/bash
# CEO control runs at the routing: the expected file on the head, then three
# of the reviewer's mutants (one per B item group). Scratch tree wt-dec1101-ceo, port 14611.
set -u
W=/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1101-ceo/web
L=/tmp/dec1101-ceo/logs
M=/tmp/dec1043-review/mutants
export PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"
export GRIMOIRE_E2E_PORT=14611
cd $W
cp src/styles/styles.css /tmp/dec1101-ceo/styles-head.css
for name in head M18-stat-padding-removed M22-perfhead-auto M09-band-max-825 M02-cmdgrid-400; do
  [ -n "$(lsof -nP -iTCP:14611 -sTCP:LISTEN)" ] && { echo "$name: 14611 busy" >> $L/summary.txt; break; }
  if [ "$name" = head ]; then cp /tmp/dec1101-ceo/styles-head.css src/styles/styles.css; else cp $M/$name.css src/styles/styles.css; fi
  npx playwright test tests/dec1043-band-rules.spec.ts tests/dec1043-gutter-blocks.spec.ts --workers 1 > $L/$name.txt 2>&1; rc=$?
  echo "$name: exit $rc $(grep -E '^\s+[0-9]+ (passed|failed|flaky)' $L/$name.txt | tr -s ' ' | tr '\n' ' ')" >> $L/summary.txt
done
cp /tmp/dec1101-ceo/styles-head.css src/styles/styles.css
echo done >> $L/summary.txt
