"""DEC-1078 fix round 1, route A (CEO, 2026-10-15): build the two expected test files.

Usage: build_expected.py <head test_generate_candidate_pool.py> <head test_write_metrics.py>
                         <kill test_kill_dec1121_item_a.py> <kill test_kill_dec1121_item_c.py> <out dir>

Takes the head's files (PR #41 at 9923959) and moves the reviewer's 8 kill methods
(DEC-1121 verdict 4e0e4a22) into the classes that they subclass, with their code unchanged:
  tests/test_generate_candidate_pool.py
    - GapSeatKillTests' 5 methods go to the end of GapSeatTests, in the kill file's order
      (after test_pinned_card_counts_and_is_not_seeded).
    - GapSeatWriteKillTests' 1 method goes to the end of GapSeatWriteTests
      (after test_file_that_differs_only_in_the_flag_is_rewritten).
    - No other edit: the test module already imports contextlib, io, json and mock, and
      binds candidate_pool by the same name.
  tests/test_write_metrics.py
    - The helper _seed_raw goes after _seed.
    - The 2 test methods go to the end of WriteMetricsClockFieldTests
      (after test_age_that_crosses_the_bonus_floor_threshold_is_written).
    - The one edit that the move needs: the kill file's `tw._payload(` and `tw.DECK_ID`
      become the module's own `_payload(` and `DECK_ID`.
"""
import ast
import sys
from pathlib import Path

head_a, head_c, kill_a, kill_c, out = (Path(p) for p in sys.argv[1:6])


def one(haystack, needle):
    assert haystack.count(needle) == 1, (needle, haystack.count(needle))
    return haystack.index(needle)


def methods(path, cls):
    src = path.read_text()
    lines = src.splitlines(keepends=True)
    tree = ast.parse(src)
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    out = []
    for fn in node.body:
        assert isinstance(fn, ast.FunctionDef) and not fn.decorator_list, ast.dump(fn)[:80]
        out.append((fn.name, "".join(lines[fn.lineno - 1:fn.end_lineno])))
    return out


# ---- item (a) ----
text = head_a.read_text()
seat = methods(kill_a, "GapSeatKillTests")
write = methods(kill_a, "GapSeatWriteKillTests")
assert [n for n, _ in seat] == [
    "test_step_2_skips_a_listed_card_that_scores_0",
    "test_step_1_skips_a_decklist_card_by_its_front_face",
    "test_tail_breaks_a_score_tie_by_name",
    "test_step_2_seats_only_cards_of_the_gap_role",
    "test_log_counts_only_the_cards_that_step_1_seats",
], seat
assert [n for n, _ in write] == ["test_file_whose_flag_names_another_role_is_rewritten"], write
for _, body in seat + write:
    assert "tg." not in body, body[:60]

at = one(text, "\n\nclass GapSeatWriteTests(unittest.TestCase):")
text = text[:at].rstrip("\n") + "\n" + "".join("\n" + b for _, b in seat) + text[at:]
at = one(text, '\n\nif __name__ == "__main__":')
text = text[:at].rstrip("\n") + "\n" + "".join("\n" + b for _, b in write) + text[at:]
(out / "test_generate_candidate_pool.py").write_text(text)

# ---- item (c) ----
text = head_c.read_text()
got = methods(kill_c, "WriteMetricsShapeKillTests")
assert [n for n, _ in got] == [
    "_seed_raw",
    "test_file_whose_penalties_is_not_a_dict_raises_nothing",
    "test_file_whose_confidence_inputs_is_not_a_dict_raises_nothing",
], got
helper, tests = got[0][1], [b for _, b in got[1:]]
joined = "".join(tests)
assert joined.count("tw._payload(") == 4 and joined.count("tw.DECK_ID") == 2, joined
tests = [b.replace("tw._payload(", "_payload(").replace("tw.DECK_ID", "DECK_ID") for b in tests]
assert "tw." not in "".join(tests) + helper

at = one(text, "    def test_payload_that_differs_only_in_the_clock_fields_writes_nothing(self):")
text = text[:at] + helper + "\n" + text[at:]
at = one(text, '\n\nif __name__ == "__main__":')
text = text[:at].rstrip("\n") + "\n" + "".join("\n" + b for b in tests) + text[at:]
(out / "test_write_metrics.py").write_text(text)
print(f"wrote {out}/test_generate_candidate_pool.py and {out}/test_write_metrics.py")
