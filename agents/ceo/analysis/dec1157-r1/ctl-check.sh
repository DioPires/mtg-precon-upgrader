#!/bin/bash
# DEC-1157 fix round 1: controls of check.py (CEO, 2026-10-15). Usage: ctl-check.sh <repo>
# Builds four control commits on f5eda73 (local objects only; no ref, never pushed) and runs
# check.py on them and on the head, SIM (the head plus the expected file) and SIM merged with main.
set -u
R="$1"
KIT="$(cd "$(dirname "$0")" && pwd)"
CF="$KIT/ctl-files"
E="$KIT/expected/tests/test_generate_candidate_pool.py"
export HOME="$PAPERCLIP_GITHUB_HOST_HOME" UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"
IDX="$(mktemp -d)/index"
mk() {
  rm -f "$IDX"
  GIT_INDEX_FILE="$IDX" git -C "$R" read-tree f5eda73
  GIT_INDEX_FILE="$IDX" git -C "$R" update-index --cacheinfo "100644,$(git -C "$R" hash-object -w "$1"),tests/test_generate_candidate_pool.py"
  if [ -n "${2:-}" ]; then
    GIT_INDEX_FILE="$IDX" git -C "$R" update-index --cacheinfo "100644,$(git -C "$R" hash-object -w "$2"),scripts/generate_candidate_pool.py"
  fi
  git -C "$R" commit-tree "$(GIT_INDEX_FILE="$IDX" git -C "$R" write-tree)" -p f5eda73 -m "DEC-1157 r1 control (CEO scratch, never pushed)"
}
CG=$(mk "$CF/good.py"); CB=$(mk "$CF/bad.py"); CS=$(mk "$E" "$CF/script-touched.py")
for c in "head f5eda73" "SIM f31be8d649c391542f3b2eb554565f9fc74f8a1d" "SIM+main a2379a00d8080d7aef72029e9c8b1f7df40854e2" \
         "good $CG" "bad $CB" "script $CS"; do
  set -- $c
  echo "== control $1 ($2)"
  uv run --no-project python -I "$KIT/check.py" "$R" "$2"
  echo "exit $?"
done
