#!/bin/bash
# DEC-1165 review: run one mutant against the full suite in one tree.
# Usage: run_mutant.sh <tree> <mutant id> [extra pytest args...]
set -u
TREE="$1"; MUT="$2"; shift 2
W="$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1165-review"
LOG="$W/mutants/$MUT.log"
mkdir -p "$W/mutants"
export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"
export PYTHONDONTWRITEBYTECODE=1
G() { HOME="$PAPERCLIP_GITHUB_HOST_HOME" git -C "$TREE" "$@"; }

if [ -n "$(G status --porcelain)" ]; then echo "$MUT: tree not clean before the run"; exit 1; fi
find "$TREE/scripts" "$TREE/tests" -name __pycache__ -type d -prune -exec rm -rf {} +
if [ "$MUT" = "M1" ]; then
  G show origin/main:scripts/generate_candidate_pool.py > "$TREE/scripts/generate_candidate_pool.py"
elif [ "$MUT" != "base" ]; then
  (cd "$W" && uv run --no-project python -I mutate.py "$TREE" "$MUT") || exit 1
fi
{
  echo "# mutant $MUT on $(G rev-parse HEAD)"
  G diff -- scripts/generate_candidate_pool.py
  echo "# pytest"
} > "$LOG"
(cd "$TREE" && CI=true uv run --with pytest python -m pytest -q -rfEs "$@" >> "$LOG" 2>&1)
G checkout -- scripts/generate_candidate_pool.py
find "$TREE/scripts" "$TREE/tests" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "$MUT | $(tail -1 "$LOG")"
grep -E '^(FAILED|ERROR) ' "$LOG" | sed 's/^/    /'
if [ -n "$(G status --porcelain)" ]; then echo "$MUT: tree not clean after restore"; G status --porcelain; exit 1; fi
