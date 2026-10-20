p = "dec1191-desc-new.md"
s = open(p).read()
for a, b in [
    ("keep fix round 1's lines 222 and 249 (`gets?`)", "keep fix round 1's line 223 (the `_is_blink` return) and line 249 (`gets?`)"),
    ("changes `scripts/auto_tag_roles.py` at lines 222 and 247, adds one comment line above each, and adds 16 tests. Read every line number again on `main` after PR #78 merges.",
     "changes `scripts/auto_tag_roles.py` at lines 223 and 249 of `main` `607dd65`, and adds 16 tests."),
    ("on the fixed line 247 the second alternative", "on line 249 the second alternative"),
    ("reads `target creature gets?` in line 247, so", "reads `target creature gets?` in line 249, so"),
]:
    assert a in s, a
    s = s.replace(a, b, 1)
open(p, "w").write(s)
