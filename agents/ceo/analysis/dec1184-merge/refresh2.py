p = "dec1191-desc-new.md"
s = open(p).read()
a = "the bounce read at lines 242 to 245"
assert a in s; s = s.replace(a, "the bounce read at lines 242 to 246", 1)
b = "- **Census against item 0.** Your census on `35aeaa4`"
assert b in s; s = s.replace(b, "- **Census against `main` `607dd65`.** Your census on `35aeaa4`", 1)
c = "- Read every line number again on your tree. On PR #78's implementer head `a3731b2`: `_is_blink` is at `scripts/auto_tag_roles.py:216` to `223`, the toughness-cut read at line 247, `_detect_card_draw` from line 252, `_SPOT_TARGET` at lines 194 to 198, and the bounce read at lines 241 to 245.\n"
assert c in s; s = s.replace(c, "- Read every line number again on your tree. The \"Started\" section gives them on `main` `607dd65`.\n", 1)
open(p, "w").write(s)
