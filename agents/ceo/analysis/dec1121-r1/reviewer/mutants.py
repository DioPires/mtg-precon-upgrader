"""DEC-1121 review, item 6: mutants of PR #41, each run against its test file only.

Run from the basis tree root:
    uv run python /tmp/dec1078-review/mutants.py [ID ...]

For each mutant: remove __pycache__ under scripts/ and tests/ only, apply the
(old, new) replacements (each `old` must occur exactly once), run pytest on the
item's test file with PYTHONDONTWRITEBYTECODE=1, write the original bytes back,
and check `git diff --quiet`. Logs go to /tmp/dec1078-review/mutants/<ID>.log.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
OUT = Path("/tmp/dec1078-review/mutants")
GEN = "scripts/generate_candidate_pool.py"
MET = "scripts/compute_deck_metrics.py"
T_A = "tests/test_generate_candidate_pool.py"
T_C = "tests/test_write_metrics.py"
T_D = "tests/test_metrics_gaps.py"

STEP2_GUARD = "        if count < GAP_SEAT_FLOOR:\n            listed = []"
STEP2_SLICE = "listed[:GAP_SEAT_FLOOR - count]"
GUARD_OLD = 'c.get("seeded_for_gap"))\n                for c in existing'
GUARD_NEW = 'c.get("seeded_for_gap"))\n                for c in out'
RATE_SORT = 'listed.sort(key=lambda t: (-edhrec_rate_for(t[1].get("name", ""), edhrec_rates), t[1].get("name", "")))'
AGE_POP = (
    "                if isinstance(penalties, dict):\n"
    '                    penalties.pop("candidates_age_days", None)\n'
)
MERGE_BODY = (
    '    return role_gaps + [\n'
    '        g for g in resilience_gaps\n'
    '        if role_figures.get(g["resilience_component"]) != (g.get("actual"), g.get("target"))\n'
    '    ]\n'
)

MUTANTS: dict[str, tuple[str, str, list[tuple[str, str]], str]] = {
    # ---- item (a) ----
    "A1": (GEN, T_A, [(STEP2_GUARD, "        if True:\n            listed = []"),
                      (STEP2_SLICE, "listed[:GAP_SEAT_FLOOR - before]")],
           "implementer's M3: step 2 for every gap role, filled from the count before step 1"),
    "A2": (GEN, T_A, [("    top = candidates[:limit] + tail", "    top = candidates[:limit - len(tail)] + tail")],
           "implementer's M4: a seat replaces the last card above the cut"),
    "A3": (GEN, T_A, [('(c.get("name"), bool(c.get("pinned")), ' + GUARD_OLD,
                       '(c.get("name"), bool(c.get("pinned")))\n                for c in existing'),
                      ('(c.get("name"), bool(c.get("pinned")), ' + GUARD_NEW,
                       '(c.get("name"), bool(c.get("pinned")))\n                for c in out')],
           "implementer's M6: the write guard ignores seeded_for_gap"),
    "A4": (GEN, T_A, [('    pool += [c for _s, c, _b, _m in below if c.get("name") in pinned]\n', "")],
           "pins below the cut no longer count toward the floor"),
    "A5": (GEN, T_A, [("                if score > 0:\n                    listed.append((score, c, breakdown, matched))",
                       "                listed.append((score, c, breakdown, matched))")],
           "step 2 appends every listed card, with no score > 0 check"),
    "A6": (GEN, T_A, [('                if role(c) != gap or front_face(c.get("name", "")) in decklist_names:',
                       "                if role(c) != gap:")],
           "step 2 skips no decklist card"),
    "A7": (GEN, T_A, [("if name in pinned or front_face(name) in decklist_names or role(c) != gap:",
                       "if name in pinned or name in decklist_names or role(c) != gap:")],
           "step 1 checks name, not front_face(name), against the decklist"),
    "A8": (GEN, T_A, [('    tail = sorted(tail + step2, key=lambda t: (-t[0], t[1].get("name", "")))',
                       "    tail = sorted(tail + step2, key=lambda t: -t[0])")],
           "the tail sorts by score only"),
    "A9": (GEN, T_A, [(STEP2_SLICE, "listed[:GAP_SEAT_FLOOR - before]")],
           "the step-2 slice is listed[:GAP_SEAT_FLOOR - before]"),
    "A10": (GEN, T_A, [('                breakdown.get("disqualified") == "no archetype match"\n                and ', "                ")],
            "gated takes every card that scores 0 or less and is on the EDHREC file (no check of the reason)"),
    "A10b": (GEN, T_A, [("            if (\n                breakdown.get(\"disqualified\") == \"no archetype match\"\n"
                         "                and edhrec_rate_for(card.get(\"name\", \"\"), edhrec_rates) is not None\n            ):",
                         "            if True:")],
             "gated takes every card that scores 0 or less (no reason check, no EDHREC check)"),
    # added: lines no mutant above touches
    "A11": (GEN, T_A, [("        if before >= GAP_SEAT_FLOOR:\n            continue\n", "")],
            "no skip for a pair that already holds the floor"),
    "A12": (GEN, T_A, [("            if count >= GAP_SEAT_FLOOR:\n                break", "            if count > GAP_SEAT_FLOOR:\n                break")],
            "step 1 stops at 6 (> in place of >=)"),
    "A13": (GEN, T_A, [("if name in pinned or front_face(name) in decklist_names or role(c) != gap:",
                        "if front_face(name) in decklist_names or role(c) != gap:")],
            "step 1 does not skip pins"),
    "A14": (GEN, T_A, [('                if role(c) != gap or front_face(c.get("name", "")) in decklist_names:',
                        '                if front_face(c.get("name", "")) in decklist_names:')],
            "step 2 takes a gated card of any role"),
    "A15": (GEN, T_A, [("if name in pinned or front_face(name) in decklist_names or role(c) != gap:",
                        "if name in pinned or front_face(name) in decklist_names:")],
            "step 1 takes a card of any role"),
    "A16": (GEN, T_A, [("        from_step1 = count - before\n", "        from_step1 = count\n")],
            "the log counts the pool's own cards as step-1 seats"),
    "A17": (GEN, T_A, [("                step2.append(entry)\n                count += 1\n", "                step2.append(entry)\n")],
            "step 2 does not count its seats (log only)"),
    "A18": (GEN, T_A, [(' or t[1].get("name") in seated]', "]")],
            "step-1 seats left out of the tail"),
    "A19": (GEN, T_A, [("    archetype_gate: bool = True,\n", "    archetype_gate: bool = False,\n")],
            "score_card's default opens the archetype gate"),
    "A20": (GEN, T_A, [(RATE_SORT, 'listed.sort(key=lambda t: (edhrec_rate_for(t[1].get("name", ""), edhrec_rates), t[1].get("name", "")))')],
            "step 2 takes the lowest rate first"),
    "A21": (GEN, T_A, [(RATE_SORT, 'listed.sort(key=lambda t: (-t[0], t[1].get("name", "")))')],
            "step 2 sorts by score (implementer's M8)"),
    "A22": (GEN, T_A, [(RATE_SORT, 'listed.sort(key=lambda t: -edhrec_rate_for(t[1].get("name", ""), edhrec_rates))')],
            "step 2 breaks a rate tie by file order (implementer's M11)"),
    "A23": (GEN, T_A, [('c.get("seeded_for_gap"))\n                for c in existing', 'bool(c.get("seeded_for_gap")))\n                for c in existing'),
                       ('c.get("seeded_for_gap"))\n                for c in out', 'bool(c.get("seeded_for_gap")))\n                for c in out')],
            "the write guard compares bool(seeded_for_gap), not the role"),
    "A24": (GEN, T_A, [('            entry["seeded_for_gap"] = seated[c.get("name")]\n', "            pass\n")],
            "the flag is gone (implementer's M5)"),
    "A25": (GEN, T_A, [("                and edhrec_rate_for(card.get(\"name\", \"\"), edhrec_rates) is not None\n", "")],
            "gated without the EDHREC check (implementer's M7)"),
    # ---- item (c) ----
    "C1": (MET, T_C, [(AGE_POP, "")], "implementer's M1: the new exclusion is gone"),
    "C2": (MET, T_C, [(AGE_POP, "                if isinstance(penalties, dict):\n"
                                '                    inputs.pop("penalties", None)\n')],
           "implementer's M2: the exclusion drops the whole penalties block"),
    "C3": (MET, T_C, [(AGE_POP, "                if isinstance(penalties, dict) and doc is new:\n"
                                '                    penalties.pop("candidates_age_days", None)\n')],
           "the age is dropped from new only"),
    "C4": (MET, T_C, [('penalties = inputs.get("penalties") if isinstance(inputs, dict) else None',
                       'penalties = inputs.get("penalties")')],
           "inputs.get with no isinstance(inputs, dict) check"),
    "C5": (MET, T_C, [('                doc.pop("generated_at", None)\n', "")],
           "generated_at stays in the comparison"),
    "C6": (MET, T_C, [("                if isinstance(penalties, dict):\n", "                if penalties is not None:\n")],
           "penalties checked for None, not for dict"),
    "C7": (MET, T_C, [('if isinstance(inputs, dict) else None', 'if inputs is not None else None')],
           "inputs checked for None, not for dict"),
    # ---- item (d) ----
    "O5": (MET, T_D, [(MERGE_BODY,
                       '    resilience_gaps[:] = [\n'
                       '        g for g in resilience_gaps\n'
                       '        if role_figures.get(g["resilience_component"]) != (g.get("actual"), g.get("target"))\n'
                       '    ]\n'
                       '    return role_gaps + resilience_gaps\n')],
           "merge_gaps filters resilience_gaps in place"),
    "E1": (MET, T_D, [(MERGE_BODY, "    if not role_gaps:\n        return resilience_gaps\n" + MERGE_BODY)],
           "merge_gaps returns resilience_gaps itself when role_gaps is empty"),
}


def clean_pycache() -> None:
    for top in ("scripts", "tests"):
        for p in (ROOT / top).rglob("__pycache__"):
            shutil.rmtree(p)


def run(mid: str, test_override: str | None = None, tag: str = "") -> str:
    if mid == "HEAD":
        path, test, edits, desc = GEN, T_A, [], "no mutation"
    else:
        path, test, edits, desc = MUTANTS[mid]
    if test_override:
        test = test_override
    target = ROOT / path
    original = target.read_bytes()
    src = original.decode()
    for old, new in edits:
        n = src.count(old)
        if n != 1:
            raise SystemExit(f"{mid}: pattern occurs {n} times: {old!r}")
        src = src.replace(old, new)
    clean_pycache()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        target.write_text(src)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-rfE", "-p", "no:cacheprovider", test],
            capture_output=True, text=True, env=env,
        )
    finally:
        target.write_bytes(original)
    clean = subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode == 0
    log = proc.stdout + proc.stderr
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{mid}{tag}.log").write_text(f"# {mid}: {desc}\n# file {path}, tests {test}\n" + log)
    count = next((ln for ln in reversed(log.splitlines()) if re.search(r"\d+ (passed|failed|error)", ln)), "?")
    failed = [ln.split(" - ")[0].replace("FAILED ", "") for ln in log.splitlines() if ln.startswith(("FAILED", "ERROR"))]
    status = "KILLED" if failed or proc.returncode != 0 else "SURVIVED"
    return f"{mid}{tag}\t{status}\t{count.strip('= ')}\trestore_clean={clean}\t{desc}\n" + "".join(f"\t\t{f}\n" for f in failed)


def main() -> int:
    args = sys.argv[1:]
    test_override, tag = None, ""
    if args[:1] == ["--test"]:
        test_override, tag, args = args[1], "-" + args[2], args[3:]
    ids = args or list(MUTANTS)
    report = "".join(run(i, test_override, tag) for i in ids)
    print(report, end="")
    with open(OUT / "summary.txt", "a") as fh:
        fh.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
