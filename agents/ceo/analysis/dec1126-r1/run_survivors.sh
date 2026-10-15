#!/bin/bash
# DEC-1126 route A control (CEO): apply each surviving mutant's diff to the tree, run the test file, restore.
# Usage: run_survivors.sh <tree> <diffs dir> <log dir> ID [ID ...]
set -u
tree=$1; diffs=$2; logs=$3; shift 3
mkdir -p "$logs"
cd "$tree" || exit 3
git diff --quiet || { echo "tree has changes"; exit 3; }
for id in "$@"; do
  git apply "$diffs/$id.diff" || { echo "$id: does not apply"; continue; }
  find . -name __pycache__ -type d -prune -exec rm -rf {} +
  PYTHONDONTWRITEBYTECODE=1 uv run --with pytest python -m pytest -q -rfEs -p no:cacheprovider tests/test_card_lookup.py > "$logs/$id.txt" 2>&1
  echo "$id: exit $? | $(tail -1 "$logs/$id.txt")"
  git checkout -q -- scripts/card_lookup.py
  git diff --quiet || { echo "restore failed"; exit 3; }
done
