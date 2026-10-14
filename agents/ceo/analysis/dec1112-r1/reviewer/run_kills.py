"""DEC-1112 item 9 d: run the kill cases on the head, then each on its mutant.

Usage: run_kills.py <tree>. Copies the kill file into <tree>/tests, logs each run to
/tmp/dec1112/kill-<id>.log, and restores the script after each mutant.
"""
import os, shutil, subprocess, sys
from pathlib import Path

sys.path.insert(0, "/tmp/dec1112")
TREE = Path(sys.argv[1])
TARGET = TREE / "scripts" / "fetch_card_metadata.py"
KILL = TREE / "tests" / "test_dec1112_kills.py"
shutil.copy("/tmp/dec1112/kills/test_dec1112_kills.py", KILL)

import importlib.util
spec = importlib.util.spec_from_file_location("mm", "/tmp/dec1112/mutants_mine.py")
src = Path("/tmp/dec1112/mutants_mine.py").read_text()
M = {}
exec(src.split("only = set(")[0].replace("TREE = Path(sys.argv[1])", "TREE = Path('.')")
     .replace("OUT = Path(sys.argv[2])", "OUT = None"), M)
MUTANTS = {m[0]: m for m in M["M"]}
CASE = {
    "S1": "test_s1_page_with_an_inversion_of_one_cent_proves_nothing",
    "S4": "test_s4_non_foil_price_of_zero_counts",
    "R1": "test_r1_search_is_a_get_without_a_body",
    "R4": "test_r4_card_without_top_level_oracle_id_sends_no_oracleid_none_search",
    "R10": "test_r10_two_returned_spellings_join_with_a_semicolon",
    "R14": "test_r14_non_ascii_name_is_written_as_an_escape",
}


def run(label, selector):
    proc = subprocess.run(
        ["uv", "run", "--with", "pytest", "python", "-m", "pytest", "-q", "-rfE",
         "-p", "no:cacheprovider", selector],
        cwd=TREE, capture_output=True, text=True, env={**os.environ, "CI": "true"})
    log = Path(f"/tmp/dec1112/kill-{label}.log")
    log.write_text(f"$ pytest {selector}\n{proc.stdout}{proc.stderr}\nexit {proc.returncode}\n")
    tail = proc.stdout.strip().splitlines()[-1]
    print(f"{label}: exit {proc.returncode}: {tail}  ({log})", flush=True)
    return proc.returncode


original = TARGET.read_text()
try:
    run("head", "tests/test_dec1112_kills.py")
    for mid, case in CASE.items():
        _, what, old, new = MUTANTS[mid]
        assert original.count(old) == 1, mid
        TARGET.write_text(original.replace(old, new))
        try:
            run(mid, f"tests/test_dec1112_kills.py::Dec1112KillCases::{case}")
        finally:
            TARGET.write_text(original)
finally:
    TARGET.write_text(original)
    KILL.unlink()
