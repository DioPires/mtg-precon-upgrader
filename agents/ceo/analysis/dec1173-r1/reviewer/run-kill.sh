#!/bin/bash
# DEC-1173: runs the kill case on the head, on E5 and on E4, then typechecks once with it in the tree.
set -u
WEB=/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1173-review/web
SRC=$WEB/src/components/organisms/Shopping.tsx
DST=$WEB/src/__tests__/components/dec1173-stopline-date.test.tsx
K=/tmp/dec1173/kill
export HOME="$PAPERCLIP_GITHUB_HOST_HOME"
cd "$WEB"
cp $K/dec1173-stopline-date.test.tsx "$DST"
run() { npx vitest run src/__tests__/components/dec1173-stopline-date.test.tsx > "$K/$1.log" 2>&1; echo "$1 exit $?"; }
run kill-head
for m in E5 E4; do
  case $m in
    E5) python3 - "$SRC" <<'PY'
import sys; p=sys.argv[1]; s=open(p).read(); o='pricesDate={shownPricesDate} />\n      </section>'; assert s.count(o)==1; open(p,'w').write(s.replace(o,'pricesDate={pricesDate} />\n      </section>'))
PY
    ;;
    E4) python3 - "$SRC" <<'PY'
import sys; p=sys.argv[1]; s=open(p).read(); o='pricesDate={shownPricesDate} />\n      </section>'; assert s.count(o)==1; open(p,'w').write(s.replace(o,'pricesDate={null} />\n      </section>'))
PY
    ;;
  esac
  git diff -- "$SRC" > "$K/kill-$m.diff"
  run kill-$m
  git checkout HEAD -- "$SRC"
done
npm run typecheck > $K/typecheck.log 2>&1; echo "typecheck exit $?"
rm "$DST"
git status --porcelain; echo "status printed above (empty means clean)"
