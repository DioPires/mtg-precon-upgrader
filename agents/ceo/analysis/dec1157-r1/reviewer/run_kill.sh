#!/bin/bash
# DEC-1165 review: run one test file from the workspace in a tree, on the head or on one mutant.
# Usage: run_kill.sh <tree> <mutant id or head> <file in the workspace> <log name>
set -u
TREE="$1"; MUT="$2"; FILE="$3"; NAME="$4"
W="$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1165-review"
LOG="$W/kills/$NAME.log"
mkdir -p "$W/kills"
export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"
export PYTHONDONTWRITEBYTECODE=1
G() { HOME="$PAPERCLIP_GITHUB_HOST_HOME" git -C "$TREE" "$@"; }

if [ -n "$(G status --porcelain)" ]; then echo "$NAME: tree not clean before the run"; exit 1; fi
find "$TREE/scripts" "$TREE/tests" -name __pycache__ -type d -prune -exec rm -rf {} +
if [ "$MUT" != "head" ]; then
  (cd "$W" && uv run --no-project python -I mutate.py "$TREE" "$MUT") || exit 1
fi
cp "$W/$FILE" "$TREE/tests/$FILE"
{
  echo "# $FILE (blob $(G hash-object "$TREE/tests/$FILE")) on $(G rev-parse HEAD), mutant $MUT"
  G diff -- scripts/generate_candidate_pool.py
  echo "# pytest"
} > "$LOG"
(cd "$TREE" && CI=true uv run --with pytest python -m pytest -q -rfEs "tests/$FILE" >> "$LOG" 2>&1)
rm "$TREE/tests/$FILE"
G checkout -- scripts/generate_candidate_pool.py
find "$TREE/scripts" "$TREE/tests" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "$NAME | $(tail -1 "$LOG")"
grep -E '^(FAILED|ERROR) ' "$LOG" | cut -c1-220 | sed 's/^/    /'
if [ -n "$(G status --porcelain)" ]; then echo "$NAME: tree not clean after restore"; G status --porcelain; exit 1; fi
