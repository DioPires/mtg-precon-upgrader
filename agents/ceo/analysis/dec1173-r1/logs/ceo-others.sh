#!/bin/bash
# The kill file on main + PR #72 + each other open pull request that touches what the case reads.
set -u
TREE=/tmp/dec1173-ceo/sim
L=/tmp/dec1173-ceo/logs
C=$(cat /tmp/dec1173-ceo/merged-commit.txt)
K=src/__tests__/components/dec1173-stopline-date.test.tsx
export HOME="$PAPERCLIP_GITHUB_HOST_HOME" GIT_AUTHOR_NAME=ceo GIT_AUTHOR_EMAIL=ceo@local GIT_COMMITTER_NAME=ceo GIT_COMMITTER_EMAIL=ceo@local
for pr in 66:3c3a151 70:a75bcc2 74:7cba124 75:e5e95b4; do
  n=${pr%%:*}; h=${pr#*:}
  git -C $TREE checkout -q --detach $C
  if git -C $TREE merge -q --no-edit $h > $L/with-pr$n-merge.log 2>&1; then
    (cd $TREE/web && npx vitest run $K src/__tests__/components/Shopping.test.tsx > $L/kill-with-pr$n.log 2>&1); echo "PR #$n ($h) merge ok, vitest exit $?"
    grep -E 'Test Files|Tests ' $L/kill-with-pr$n.log
  else
    echo "PR #$n ($h) merge FAILED"; git -C $TREE merge --abort
  fi
done
git -C $TREE checkout -q --detach $C
git -C $TREE status --porcelain
