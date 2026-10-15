"""DEC-1157 fix round 1, route A (CEO, 2026-10-15): build the expected test file.

Usage: build_expected.py <head test_generate_candidate_pool.py> <kill test_dec1165_kill_cases.py> <out file>

Takes the head's file (PR #67 at f5eda73, blob 494b8754) and moves the reviewer's
3 kill methods (DEC-1165 verdict 7c96121f, kill file blob d04d750a) to the end of
GapSeatWriteTests, after test_file_that_differs_only_in_role_pool_is_rewritten,
in the kill file's order: K1, K2, K3. The code of each method is unchanged.
No other edit: the kill class binds GapSeatWriteTests' own DECK_ID, setUp,
tearDown, _run and _edit_pool, and the test module already imports json.
"""
import ast
import sys
from pathlib import Path

head, kill, out = (Path(p) for p in sys.argv[1:4])


def one(haystack, needle):
    assert haystack.count(needle) == 1, (needle, haystack.count(needle))
    return haystack.index(needle)


src = kill.read_text()
lines = src.splitlines(keepends=True)
node = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == "Dec1165KillTests")
binds = [n for n in node.body if isinstance(n, ast.Assign)]
assert [ast.unparse(n) for n in binds] == [
    "DECK_ID = base.GapSeatWriteTests.DECK_ID",
    "setUp = base.GapSeatWriteTests.setUp",
    "tearDown = base.GapSeatWriteTests.tearDown",
    "_run = base.GapSeatWriteTests._run",
    "_edit_pool = base.GapSeatWriteTests._edit_pool",
], [ast.unparse(n) for n in binds]
fns = [n for n in node.body if isinstance(n, ast.FunctionDef)]
assert len(binds) + len(fns) == len(node.body)
assert [f.name for f in fns] == [
    "test_file_that_is_not_valid_json_is_rewritten",
    "test_run_that_writes_nothing_prints_no_wrote_line",
    "test_written_text_has_two_space_indent_utf8_and_final_newline",
], [f.name for f in fns]
bodies = []
for f in fns:
    assert not f.decorator_list
    body = "".join(lines[f.lineno - 1:f.end_lineno])
    assert "base." not in body, body[:60]
    bodies.append(body)

text = head.read_text()
one(text, "    def test_file_that_differs_only_in_role_pool_is_rewritten(self):")
at = one(text, '\n\nif __name__ == "__main__":')
assert text[:at].rstrip("\n").endswith('self.assertEqual(pool["role_pool"], before["role_pool"])')
text = text[:at].rstrip("\n") + "\n" + "".join("\n" + b for b in bodies) + text[at:]
out.write_text(text)
print(f"wrote {out}")
