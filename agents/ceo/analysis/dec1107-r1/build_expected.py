"""DEC-1092 fix round 1, route A (CEO, 2026-10-14): build the expected tests/test_scryfall_limit.py.

Usage: build_expected.py <head test_scryfall_limit.py> <kill test_k1_threads.py> <kill test_f1_429_time.py> <out>

Takes the head's file (0febfb6, blob c34457b8) and adds the reviewer's two kill classes from
DEC-1107 (verdict f6d485e5) unchanged, with two edits that the new home needs:
  1. `import threading` joins the import list (the K1 class uses it).
  2. The F1 class's `AT` becomes `AT_10_41_07`, the head's constant with the same value
     (2026-10-14T10:41:07Z). The kill file defined `AT` at module level.
TimeOfThe429Tests goes after StopTests (before StopTextTests); TwoThreadsTests goes after
CrossProcessTests (before the `if __name__` block).
"""
import sys
from pathlib import Path

head, k1, f1, out = (Path(p) for p in sys.argv[1:5])
text = head.read_text()
k1_text = k1.read_text()
f1_text = f1.read_text()


def one(haystack, needle):
    assert haystack.count(needle) == 1, (needle, haystack.count(needle))
    return haystack.index(needle)


def klass(source, name):
    start = one(source, f"class {name}(")
    end = one(source, '\n\nif __name__ == "__main__":')
    return source[start:end].rstrip("\n") + "\n"


two_threads = klass(k1_text, "TwoThreadsTests")
time_of_429 = klass(f1_text, "TimeOfThe429Tests")
assert time_of_429.count("AT + ") == 2
time_of_429 = time_of_429.replace("AT + ", "AT_10_41_07 + ")

one(text, "import tempfile\nimport time\n")
text = text.replace("import tempfile\nimport time\n", "import tempfile\nimport threading\nimport time\n")

at = one(text, "class StopTextTests(unittest.TestCase):")
text = text[:at] + time_of_429 + "\n\n" + text[at:]

at = one(text, '\n\nif __name__ == "__main__":')
text = text[:at].rstrip("\n") + "\n\n\n" + two_threads + text[at:]

out.write_text(text)
print(f"wrote {out}")
