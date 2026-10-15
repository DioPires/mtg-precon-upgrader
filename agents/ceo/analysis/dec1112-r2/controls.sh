#!/bin/bash
# Controls for agents/ceo/analysis/dec1112-r2/check_bump.py. Scratch commits only; no ref moves.
set -u
export HOME="$PAPERCLIP_GITHUB_HOST_HOME" UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"
R=/Users/dpires/Documents/Personal/code/mtg-precon-upgrader; cd $R
W=/tmp/dec1112-r2/ctl
L=web/src/data/loader.ts; T=web/src/__tests__/data/loaderEnvelope.test.ts
M=$(git commit-tree b510f2a27e9ac9fb3f2ce4d180d0ed0bdd4c2cbf -p origin/main -p f1a0c73 -m "scratch merge (DEC-1112 r2 control, no ref)")
mk() {
  export GIT_INDEX_FILE=$W/idx-$1; rm -f $GIT_INDEX_FILE; git read-tree $M
  git update-index --cacheinfo 100644,$(git hash-object -w $W/$2),$L
  git update-index --cacheinfo 100644,$(git hash-object -w $W/$3),$T
  if [ $# -ge 4 ]; then git update-index --cacheinfo 100644,$(git hash-object -w $W/$5),$4; fi
  tree=$(git write-tree); unset GIT_INDEX_FILE
  git commit-tree $tree -p $M -m "scratch $1 (no ref)"
}
run() { h=$(mk "$@"); echo "=== control $1 ($h)"; uv run -q python agents/ceo/analysis/dec1112-r2/check_bump.py $R $h; echo "exit $?"; }
run good loader.good test.good
run v158 loader.v158 test.good
run nocomment loader.nocomment test.good
run extra loader.extra test.good
run testhalf loader.good test.half
run otherpath loader.good test.good data/card-metadata.meta.json meta.bad
echo "=== control merge only ($M)"; uv run -q python agents/ceo/analysis/dec1112-r2/check_bump.py $R $M; echo "exit $?"
echo "=== control head f1a0c73"; uv run -q python agents/ceo/analysis/dec1112-r2/check_bump.py $R f1a0c73; echo "exit $?"
