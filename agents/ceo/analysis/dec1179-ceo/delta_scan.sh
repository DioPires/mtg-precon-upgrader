#!/bin/zsh
# DEC-1179: scan what reached DioPires/mtg-precon-upgrader after the scanned states
# (engineer mirror at 10:28Z, CEO delta at 10:44Z). Read only on GitHub.
# Usage: zsh delta_scan.sh   -> prints counts; exit 0 = clean, 3 = a hit to read.
set -u
export HOME="$PAPERCLIP_GITHUB_HOST_HOME"
S=/Users/dpires/.paperclip/instances/default/workspaces/f9427c33-d719-4fd5-a3c5-cd2f65dd01e8/dec1179-check
D=/Users/dpires/.paperclip/instances/default/workspaces/ddb8e4ee-9ec6-45ae-81b7-144c85a9b26e/dec-scan
R=https://github.com/DioPires/mtg-precon-upgrader.git
TS=$(date -u +%Y%m%dT%H%M%SZ)
O=$S/now-$TS; mkdir -p $O/gh
RX='eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.|PAPERCLIP_API_KEY["'"'"']?[ ]*[=:][ ]*["'"'"']?[^ $"'"'"'{}()<>]{8,}|Bearer [A-Za-z0-9._-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-ant-[A-Za-z0-9_-]{10,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|AKIA[0-9A-Z]{16}|xox[abposr]-[A-Za-z0-9-]{10,}|BEGIN [A-Z ]*PRIVATE KEY'
HIT=0
echo "time: $TS"
git -C $S/delta.git fetch -q --prune $R '+refs/heads/*:refs/now/heads/*' '+refs/pull/*:refs/now/pull/*' || { echo "fetch failed"; exit 2; }
echo "refs now: $(git -C $S/delta.git for-each-ref refs/now | wc -l | tr -d ' ')"
OLD=($(git -C $D/mirror.git for-each-ref --format='%(objectname)') $(git -C $S/delta.git for-each-ref --format='%(objectname)' refs/new))
NEWREFS=($(git -C $S/delta.git for-each-ref --format='%(objectname)' refs/now | sort -u))
git -C $S/delta.git rev-list $NEWREFS --not $OLD > $O/new-commits.txt
echo "new commits: $(wc -l < $O/new-commits.txt | tr -d ' ') (merges: $(git -C $S/delta.git rev-list --merges $NEWREFS --not $OLD | wc -l | tr -d ' '))"
if [ -s $O/new-commits.txt ]; then
  gitleaks git $S/delta.git --log-opts="$NEWREFS --not $OLD" --redact --report-format json --report-path $O/gitleaks.json > $O/gitleaks.log 2>&1; g=$?
  grep -E 'commits scanned|leaks found|no leaks' $O/gitleaks.log | sed -E 's/\x1b\[[0-9;]*m//g'
  [ $g -ne 0 ] && HIT=1
  n=$(git -C $S/delta.git log -p $NEWREFS --not $OLD | grep -c -E "$RX"); echo "patterns in patches and messages: $n"; [ $n -gt 0 ] && HIT=1
  for m in $(git -C $S/delta.git rev-list --merges $NEWREFS --not $OLD); do
    for p in $(git -C $S/delta.git diff-tree --cc --name-only -r $m | tail -n +2); do
      n=$(git -C $S/delta.git show "$m:$p" 2>/dev/null | grep -c -E "$RX"); echo "merge ${m[1,7]} resolves $p: $n hits"; [ $n -gt 0 ] && HIT=1
    done
  done
fi
SINCE=2026-10-16T10:28:00Z
gh api --paginate "repos/DioPires/mtg-precon-upgrader/issues/comments?since=$SINCE&per_page=100" --jq '.[].body' > $O/gh/issue-comments.txt
gh api --paginate "repos/DioPires/mtg-precon-upgrader/pulls/comments?since=$SINCE&per_page=100" --jq '.[].body' > $O/gh/review-comments.txt
gh api --paginate "repos/DioPires/mtg-precon-upgrader/pulls?state=all&per_page=100" --jq ".[] | select(.updated_at >= \"$SINCE\") | .title + \"\n\" + (.body // \"\")" > $O/gh/pr-bodies.txt
echo "github texts since $SINCE: $(cat $O/gh/*.txt | wc -c | tr -d ' ') bytes"
n=$(cat $O/gh/*.txt | grep -c -E "$RX"); echo "patterns in github texts: $n"; [ $n -gt 0 ] && HIT=1
gitleaks dir $O/gh --redact --report-format json --report-path $O/gitleaks-gh.json > $O/gitleaks-gh.log 2>&1 || HIT=1
grep -E 'scanned|leaks found|no leaks' $O/gitleaks-gh.log | sed -E 's/\x1b\[[0-9;]*m//g'
echo "folder: $O"
[ $HIT -eq 0 ] && { echo "VERDICT: CLEAN"; exit 0; } || { echo "VERDICT: READ THE HITS (first 4 characters and length only)"; exit 3; }
