#!/bin/bash
# DEC-1149 routing (CEO): run the three kill files on each mutant in a tree.
# Usage: TREE=<tree> LOG=<dir> run_kills.sh M1 M2 ...   (seed_mutants.py sits beside this script)
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$LOG"
cd "$TREE" || exit 1
for m in "$@"; do
  python3 -I "$HERE/seed_mutants.py" "$TREE" "$m" > /dev/null || { echo "$m: APPLY FAILED"; continue; }
  (cd web && npx vitest run src/__tests__/dec1149/ src/__tests__/components/dec1149/ > "$LOG/$m.log" 2>&1)
  git diff > "$LOG/$m.diff"
  git checkout -- web
  echo "$m: $(grep -E '^\s+Tests ' "$LOG/$m.log" | sed 's/^ *//') | porcelain [$(git status --porcelain --untracked-files=no)]"
done
