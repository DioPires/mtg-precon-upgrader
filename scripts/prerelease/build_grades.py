"""Turn a hand-written grade file into grades.json for the Sealed simulator.

    uv run python scripts/prerelease/build_grades.py --set-dir DIR

Reads DIR/grades_src.py (a plain Python file holding a list named `G` of
`(name, grade, roles, note, synergy)` tuples), the card dump in DIR, and the
tag rules in DIR/tags.json (falling back to the rules shipped next to this
script). Writes DIR/grades.json and prints a summary so the grader can see
the shape of the set at a glance.

It refuses to write when the grade file does not cover the set exactly: a
missing name, a name that is not in the set, or a duplicate all stop the run.
Basic lands are not graded.
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from setlib import WUBRG, load_cards, oracle_text  # noqa: E402

DEFAULT_TAGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tags_default.json")


def load_grade_source(set_dir: str) -> list:
    """Import DIR/grades_src.py and return its `G` list."""
    path = os.path.join(set_dir, "grades_src.py")
    if not os.path.exists(path):
        raise SystemExit(f"missing {path}")
    spec = importlib.util.spec_from_file_location("grades_src", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.G)


def load_tag_rules(set_dir: str) -> list:
    path = os.path.join(set_dir, "tags.json")
    if not os.path.exists(path):
        path = DEFAULT_TAGS
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["rules"], path


def provides(card: dict, rules: list) -> list:
    """Tags this card supplies, used by the synergy grades."""
    text, type_line = oracle_text(card), card["type_line"].lower()
    tags = set()
    for rule in rules:
        oracle_pat, type_pat = rule.get("oracle"), rule.get("type_line")
        if (oracle_pat and re.search(oracle_pat, text)) or (
            type_pat and re.search(type_pat, type_line)
        ):
            tags.add(rule["tag"])
    return sorted(tags)


def check_coverage(card_names: set, graded_names: list) -> None:
    missing = sorted(card_names - set(graded_names))
    extra = sorted(set(graded_names) - card_names)
    counts = collections.Counter(graded_names)
    duplicate = sorted(n for n, c in counts.items() if c > 1)
    if missing or extra or duplicate:
        print("MISSING:", missing)
        print("EXTRA:", extra)
        print("DUP:", duplicate)
        raise SystemExit(1)


def build(cards: list, graded: list, rules: list) -> list:
    """One grades.json entry per graded card."""
    by_name = {c["name"]: c for c in cards if "Basic" not in c["type_line"]}
    check_coverage(set(by_name), [g[0] for g in graded])
    out = []
    for name, grade, roles, note, synergy in graded:
        card = by_name[name]
        entry = {
            "name": name,
            "rarity": card["rarity"],
            "colors": card.get("colors", []),
            "mana_cost": card.get("mana_cost")
            or (card.get("card_faces") or [{}])[0].get("mana_cost", ""),
            "type_line": card["type_line"],
            "grade": grade,
            "roles": roles,
            "provides": provides(card, rules),
            "note": note,
        }
        if synergy:
            entry["needs"], entry["needs_threshold"], entry["grade_synergy"] = synergy
        # A grade of 8 or more is a bomb by definition; tag it so the sim can count it.
        if grade >= 8 and "bomb" not in roles:
            entry["roles"] = roles + ["bomb"]
        out.append(entry)
    return out


def summarise(entries: list, rules: list) -> None:
    print("entries:", len(entries))
    print("grade hist:", dict(sorted(collections.Counter(e["grade"] for e in entries).items())))
    print(
        "removal:",
        sum("removal" in e["roles"] for e in entries),
        "bombs:",
        sum("bomb" in e["roles"] for e in entries),
    )
    by_color = collections.defaultdict(list)
    for entry in entries:
        key = "".join(sorted(entry["colors"])) or "C"
        if len(key) == 1:
            by_color[key].append(entry)
    for color in WUBRG:
        group = by_color[color]
        if not group:
            continue
        print(
            "%s n=%d mean=%.2f playable(>=4)=%d removal=%d bombs=%d"
            % (
                color,
                len(group),
                sum(e["grade"] for e in group) / len(group),
                sum(e["grade"] >= 4 for e in group),
                sum("removal" in e["roles"] for e in group),
                sum("bomb" in e["roles"] for e in group),
            )
        )
    counts = " ".join(
        f"{r['tag']}: {sum(r['tag'] in e['provides'] for e in entries)}" for r in rules
    )
    print("provides", counts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--set-dir", required=True)
    args = ap.parse_args()

    cards = load_cards(args.set_dir)
    graded = load_grade_source(args.set_dir)
    rules, rules_path = load_tag_rules(args.set_dir)
    entries = build(cards, graded, rules)

    out_path = os.path.join(args.set_dir, "grades.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=1)
    print("tag rules:", rules_path)
    summarise(entries, rules)
    print("wrote", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
