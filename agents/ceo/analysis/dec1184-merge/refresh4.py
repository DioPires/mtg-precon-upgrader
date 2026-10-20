p = "dec1191-desc-new.md"
s = open(p).read()
a = "Take the `web-ci` basis from `main`'s newest `web-ci` push run when you start, and name it. PR #78's own run on `ed8a1a6` (38955433871) read lint `0 errors, 10 warnings`, 54 files, 695 tests and e2e `246 passed`."
b = "`web-ci` push run 38959081104 on `607dd65` reads lint `0 errors, 10 warnings`, `Test Files  54 passed (54)`, `Tests  695 passed (695)` and e2e `246 passed`. If `main` moves before you start, take `main`'s newest push runs as the basis, and name them."
assert a in s; s = s.replace(a, b, 1)
open(p, "w").write(s)
