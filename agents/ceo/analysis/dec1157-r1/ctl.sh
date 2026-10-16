#!/bin/bash
# DEC-1157 fix round 1, route A controls (CEO, 2026-10-15).
# Usage: ctl.sh <tree> <log dir> [mutant id ...]   (default: head R1 X4 X2 R5 R6 R7)
# Runs tests/test_generate_candidate_pool.py of <tree> on the head's script and on each
# of the reviewer's surviving mutants (reviewer/mutate.py, unchanged). The tree must be
# clean (commit the expected file first; never push it). Each mutant is restored with
# `git checkout`, and the tree is checked clean after each run.
set -u
TREE="$1"; LOGS="$2"; shift 2
KIT="$(cd "$(dirname "$0")" && pwd)"
IDS=("$@"); [ ${#IDS[@]} -eq 0 ] && IDS=(head R1 X4 X2 R5 R6 R7)
export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"
export PYTHONDONTWRITEBYTECODE=1
G() { HOME="$PAPERCLIP_GITHUB_HOST_HOME" git -C "$TREE" "$@"; }
mkdir -p "$LOGS"
for MUT in "${IDS[@]}"; do
  if [ -n "$(G status --porcelain)" ]; then echo "$MUT: tree not clean before the run"; exit 1; fi
  find "$TREE/scripts" "$TREE/tests" -name __pycache__ -type d -prune -exec rm -rf {} +
  if [ "$MUT" != "head" ]; then
    (cd "$KIT/reviewer" && uv run --no-project python -I mutate.py "$TREE" "$MUT") || exit 1
  fi
  LOG="$LOGS/$MUT.log"
  {
    echo "# $MUT on $(G rev-parse HEAD), test file blob $(G hash-object tests/test_generate_candidate_pool.py)"
    G diff -- scripts/generate_candidate_pool.py
    echo "# pytest"
  } > "$LOG"
  (cd "$TREE" && CI=true uv run --with pytest python -m pytest -q -rfE -p no:cacheprovider tests/test_generate_candidate_pool.py >> "$LOG" 2>&1)
  G checkout -- scripts/generate_candidate_pool.py
  find "$TREE/scripts" "$TREE/tests" -name __pycache__ -type d -prune -exec rm -rf {} +
  echo "$MUT | $(tail -1 "$LOG")"
  grep -E '^(FAILED|ERROR) ' "$LOG" | cut -c1-160 | sed 's/^/    /'
  if [ -n "$(G status --porcelain)" ]; then echo "$MUT: tree not clean after restore"; exit 1; fi
done
