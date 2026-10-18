#!/bin/zsh
# Controls for core.py (CEO run 15bb14f0, 2026-10-17). Usage: ctl.sh <scratch tree at 699cb7e, after apply.py and the
# pool run, with no other change>. It makes local commits only (never pushed) and runs core.py on each:
#   A   699cb7e itself                                      expect NOT EQUAL (4 paths DIFFERENT)
#   B   the round: apply.py and the two regenerated pools   expect ALL EQUAL
#   B2  B with a docstring reworded, a comment reworded and a call wrapped   expect ALL EQUAL
#   C1  B with mutant G3 ("exile this card")               expect NOT EQUAL (scripts DIFFERENT)
#   C2  B with anvil-chorus's pool from 699cb7e            expect NOT EQUAL (that pool DIFFERENT)
#   C3  B with one more line in docs/role-taxonomy.md      expect NOT EQUAL (CHANGED docs/role-taxonomy.md)
set -e
K=${0:A:h}
T=$1
R=/Users/dpires/Documents/Personal/code/mtg-precon-upgrader
export HOME="$PAPERCLIP_GITHUB_HOST_HOME" UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"
core() { echo "== $1"; uv run --no-project python -I "$K/core.py" "$R" "$2" || true; }
cd "$T"
core A 699cb7e
if [ -n "$(git status --porcelain)" ]; then
  git add -A scripts tests data
  git commit -q -m "ctl B (local, never pushed)"
fi
[ "$(git rev-parse HEAD^)" = "$(git rev-parse 699cb7e)" ]
B=$(git rev-parse HEAD)
core B "$B"
python3 - <<'EOF'
from pathlib import Path
t = Path("tests/test_auto_tag_roles.py"); s = t.read_text()
old = '    """Each count word of `_DRAW` reads card-draw (DEC-1198 B2)."""'
assert s.count(old) == 1; s = s.replace(old, '    """Every count word that `_DRAW` names reads card-draw (reworded)."""')
old = '  # kills X9: the cantrip read takes "draw" only'
assert s.count(old) == 1; s = s.replace(old, '  # reworded comment')
old = 'card = _card("Tallyhorn Census", "Sorcery", "Draw a card for each creature you control.")'
assert s.count(old) == 1; s = s.replace(old, 'card = _card(\n            "Tallyhorn Census",\n            "Sorcery",\n            "Draw a card for each creature you control.",\n        )')
t.write_text(s)
EOF
git commit -q -am "ctl B2"; core B2 "$(git rev-parse HEAD)"; git reset -q --hard "$B"
python3 - <<'EOF'
from pathlib import Path
p = Path("scripts/auto_tag_roles.py"); s = p.read_text()
old = "exile this card from your graveyard)"; assert s.count(old) == 1
p.write_text(s.replace(old, "exile this card)"))
EOF
git commit -q -am "ctl C1"; core C1 "$(git rev-parse HEAD)"; git reset -q --hard "$B"
git show 699cb7e:data/commanders/anvil-chorus/candidates.json > data/commanders/anvil-chorus/candidates.json
git commit -q -am "ctl C2"; core C2 "$(git rev-parse HEAD)"; git reset -q --hard "$B"
echo "" >> docs/role-taxonomy.md
git commit -q -am "ctl C3"; core C3 "$(git rev-parse HEAD)"; git reset -q --hard "$B"
git status --porcelain
