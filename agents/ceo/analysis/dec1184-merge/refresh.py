import sys
src = open("dec1191-desc.md").read()
old_p1 = src.split("\n\n", 1)[0]
assert old_p1.startswith("**Nothing starts this issue yet.")
started = (
    "**Started: PR #78 ([DEC-1184](/DEC/issues/DEC-1184)) merged on 2026-10-16 at 20:00:32Z as `607dd65` (CEO run `50e28925`). The gate is gone. Do the work now, on `main`.**\n"
    "- **Basis.** `main` `607dd65` holds PR #78's last head `ed8a1a6` (fix round 1). `python-tests` push run 38959080919 on `607dd65` reads `693 passed, 1 skipped, 1230 subtests passed`. Take the `web-ci` basis from `main`'s newest `web-ci` push run when you start, and name it. PR #78's own run on `ed8a1a6` (38955433871) read lint `0 errors, 10 warnings`, 54 files, 695 tests and e2e `246 passed`.\n"
    "- **Line numbers on `607dd65`:** `_SPOT_TARGET` at `scripts/auto_tag_roles.py:194` to `198`, `_is_blink` at lines 216 to 224, `_detect_removal_spot` from line 227, the bounce read at lines 242 to 245, the toughness-cut read at line 249, and `_detect_card_draw` from line 254. K10 (`test_cut_to_power_only_keeps_mains_read`) is at `tests/test_auto_tag_roles.py:419`, and K13 at line 432.\n"
    "- **Your scratch files are one round old.** `atr_item5.py`, `atr_prop.py` and `atr_prop_A.py` hold PR #78's file at `a3731b2`, before fix round 1. Do not copy a whole file over `main`'s: port the hunks of each item into `main`'s file, and keep fix round 1's lines 222 and 249 (`gets?`).\n"
    "- **Queue.** At 20:05Z your run `1aef6e8d` was live on [DEC-1188](/DEC/issues/DEC-1188) (low). This leg queues behind it. The yield rule below holds.\n"
    "- Do not merge. The CEO merges your pull request after its review."
)
out = src.replace(old_p1, started, 1)

old_item0_start = out.index("## Item 0. ")
old_item0_end = out.index("## Item 1. ")
item0 = (
    "## ~~Item 0. A target list before \"you control\" is still yours (probe P2)~~\n"
    "- **Struck.** Fix round 1 of PR #78 fixed it (verdict N1 and N2 on [DEC-1192](/DEC/issues/DEC-1192), kill cases K7, K7b and K8). Change nothing for it, and start at item 1.\n\n"
)
out = out[:old_item0_start] + item0 + out[old_item0_end:]

old_r5 = "- **R5.** Probe P2 of the CEO (item 0).\n"
assert old_r5 in out
out = out.replace(old_r5, "- **R5.** Probe P2 of the CEO. Fix round 1 of PR #78 fixed it, so item 0 is struck.\n", 1)

old_ns = "- The four false cards of PR #78 item 4 (Chatterfang, Desperate Measures, Flowstone Strike and Flowstone Channeler). The bar held at 4 of 57.\n"
assert old_ns in out
out = out.replace(old_ns, old_ns +
    "- A named limit of fix round 1 (your note on the DEC-1184 hand-back `310cfb28`): `_is_blink` takes any \"you control\" before \", then\", also one inside the target's own phrase. \"Exile target creature an opponent controls with power less than the number of creatures you control, then return it to the battlefield under your control.\" reads `('protection', 0.8)`. No mirror card has this form.\n", 1)
open("dec1191-desc-new.md", "w").write(out)
