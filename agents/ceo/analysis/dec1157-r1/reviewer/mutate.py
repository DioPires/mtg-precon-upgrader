"""DEC-1165 review: apply one mutant to scripts/generate_candidate_pool.py.

Usage: python mutate.py <tree> <mutant id>
Each mutant is one exact text replacement that must match exactly once.
M1 (the whole old file) is applied by the runner with git show, not here.
"""
import sys
from pathlib import Path

NC_PRINT = "print(f\"  [{deck_id}] no change ({len(out['candidates'])} candidates).\", file=sys.stderr)\n"
NEW_TEXT = 'new_text = json.dumps(out, indent=2, ensure_ascii=False) + "\\n"'
MAIN_WRITE = 'out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\\n")'

MUTANTS = {
    # head mutants
    "M3": ('doc.pop("generated_at", None)\n',
           'doc.pop("generated_at", None)\n                doc.pop("candidates", None)\n'),
    "R1": ("except json.JSONDecodeError:\n            pass\n",
           "except json.JSONDecodeError:\n            return False\n"),
    "R2": ("    if out_path.exists():\n        try:\n", "    if True:\n        try:\n"),
    "R3": ("for doc in (old, new):", "for doc in (old,):"),
    "R4": ("    out_path.write_text(new_text)\n    return True\n", "    out_path.write_text(new_text)\n    return False\n"),
    "R5": (NEW_TEXT, 'new_text = json.dumps(out, indent=2, ensure_ascii=False)'),
    "R6": (NEW_TEXT, NEW_TEXT.replace("indent=2", "indent=1")),
    "R7": (NEW_TEXT, NEW_TEXT.replace("ensure_ascii=False", "ensure_ascii=True")),
    "R8": (NC_PRINT, NC_PRINT.replace("len(out['candidates'])", "len(out['candidates']) - 1")),
    "X1": ("for doc in (old, new):", "for doc in (new,):"),
    "X2": (NC_PRINT + "            continue\n", NC_PRINT),
    "X3": ("new = json.loads(new_text)", "new = out"),
    "X4": ("except json.JSONDecodeError:\n            pass\n", "except json.JSONDecodeError:\n            raise\n"),
    # main mutants (second tree at origin/main, line 995)
    "R5m": (MAIN_WRITE, 'out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))'),
    "R6m": (MAIN_WRITE, MAIN_WRITE.replace("indent=2", "indent=1")),
    "R7m": (MAIN_WRITE, MAIN_WRITE.replace("ensure_ascii=False", "ensure_ascii=True")),
}


def main() -> int:
    tree, mutant = Path(sys.argv[1]), sys.argv[2]
    path = tree / "scripts" / "generate_candidate_pool.py"
    old, new = MUTANTS[mutant]
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        print(f"{mutant}: expected 1 match, found {count}", file=sys.stderr)
        return 1
    path.write_text(text.replace(old, new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
