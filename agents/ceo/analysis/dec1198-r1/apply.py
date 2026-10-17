"""Fix round 1 of PR #81 (DEC-1191), review DEC-1198 verdict 14a16973: route A edits (CEO run 15bb14f0, 2026-10-17).

Usage: python3 -I apply.py <tree>

Makes three edits in <tree>. Each edit finds its old text once or stops, and a second run prints "already":
  B4      scripts/auto_tag_roles.py: `_REPEATABLE_DRAW` also reads "exile this card from your graveyard" as a cost
          that spends the card (the reviewer's alternative, verdict B4, byte for byte; the pattern is wrapped over two
          string literals, which Python joins into one).
  KILL-a  tests/test_auto_tag_roles.py: the reviewer's class ToughnessCutKillTests (B3), byte for byte, after the
          class ToughnessCutTests.
  KILL-b  tests/test_auto_tag_roles.py: the reviewer's classes CantripKillTests (B1), DrawCountKillTests (B2) and
          GraveyardCostFaultTests (B4's case), byte for byte, after the class CantripTests.
The classes come from reviewer/test_dec1198_kill.py in this kit, by their line ranges in that file's syntax tree.
"""
import ast
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
tree = Path(sys.argv[1])

OLD_B4 = (
    '# Read on the draw\'s own line. A cost before ":" makes the draw repeatable,\n'
    "# unless the cost spends the card itself (DEC-478).\n"
    "_REPEATABLE_DRAW = re.compile(\n"
    '    r"\\bwhenever\\b|\\bat the beginning of (?!the next)|^(?:(?!sacrifice this|discard this)[^(\\n])*:"\n'
    ")\n"
)
NEW_B4 = (
    '# Read on the draw\'s own line. A cost before ":" makes the draw repeatable,\n'
    "# unless the cost spends the card itself: it sacrifices the card, discards it,\n"
    "# or exiles it from your graveyard (DEC-478, DEC-1198).\n"
    "_REPEATABLE_DRAW = re.compile(\n"
    '    r"\\bwhenever\\b|\\bat the beginning of (?!the next)|"\n'
    '    r"^(?:(?!sacrifice this|discard this|exile this card from your graveyard)[^(\\n])*:"\n'
    ")\n"
)


def kill_classes() -> dict[str, str]:
    src = (KIT / "reviewer" / "test_dec1198_kill.py").read_text()
    lines = src.splitlines(keepends=True)
    out = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.ClassDef):
            out[node.name] = "".join(lines[node.lineno - 1 : node.end_lineno])
    assert list(out) == ["CantripKillTests", "DrawCountKillTests", "ToughnessCutKillTests", "GraveyardCostFaultTests"]
    return out


def edit(path: Path, label: str, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(new) == 1 and text.count(old) == 0:
        print(f"{label}: already")
        return
    assert text.count(old) == 1, f"{label}: old text found {text.count(old)} times"
    path.write_text(text.replace(old, new))
    print(f"{label}: done")


def insert_before(path: Path, label: str, anchor: str, block: str) -> None:
    text = path.read_text()
    if text.count(block + anchor) == 1:
        print(f"{label}: already")
        return
    assert text.count(anchor) == 1, f"{label}: anchor found {text.count(anchor)} times"
    assert text.count(block) == 0, f"{label}: block present elsewhere"
    path.write_text(text.replace(anchor, block + anchor))
    print(f"{label}: done")


k = kill_classes()
edit(tree / "scripts" / "auto_tag_roles.py", "B4", OLD_B4, NEW_B4)
test = tree / "tests" / "test_auto_tag_roles.py"
insert_before(test, "KILL-a", "class CantripTests(unittest.TestCase):\n", k["ToughnessCutKillTests"] + "\n\n")
insert_before(
    test,
    "KILL-b",
    "class ProtectionPatternTests(unittest.TestCase):\n",
    k["CantripKillTests"] + "\n\n" + k["DrawCountKillTests"] + "\n\n" + k["GraveyardCostFaultTests"] + "\n\n",
)
