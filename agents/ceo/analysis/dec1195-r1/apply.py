# Route A edits for fix round 1 of PR #80 (DEC-1188, review DEC-1195, verdict 80e28807).
# Usage: python3 -I apply.py <tree>     (run it after the round's merge of origin/main, if any)
# 1. Copies the reviewer's test file (B1, B2 and the B3 case) from expected/ to the same path
#    in <tree>.
# 2. Makes B3 in web/src/data/scryfallLimiter.ts: the reviewer's condition and comment line.
# 3. Makes the wording edits: N4 (the `settle` doc and web/README.md), N5 (web/README.md) and
#    D1 (the doc of fetchWithTimeout, which B3 would make wrong for a 429).
# Each edit finds its old text exactly once, or the script stops and names the edit. An edit
# whose new text is already there and whose old text is gone prints "already" (a second run
# changes nothing). core.py imports EDITS from this file.
import os, shutil, sys

TEST = 'web/src/__tests__/dec1188/body-timeout.test.ts'
LIMITER = 'web/src/data/scryfallLimiter.ts'
README = 'web/README.md'

EDITS = [
    # B3: a 429 is a stop at its head, so the limiter does not read its body (the reviewer's text).
    (LIMITER, 'B3',
     "      const response = await Promise.race([fetching, timeout]);\n"
     "      if (response && wholeBody) {\n",
     "      const response = await Promise.race([fetching, timeout]);\n"
     "      // A 429 is a stop at its head: nobody reads its body.\n"
     "      if (response && wholeBody && response.status !== 429) {\n"),
    # N4: the `settle` doc. A body can also fail before `settle` runs (case B2).
    (LIMITER, 'N4-settle',
     "   * REQUEST_TIMEOUT_MS after the request started, whichever comes first. The\n"
     "   * body of the answer has ended when it runs (DEC-1188).\n",
     "   * REQUEST_TIMEOUT_MS after the request started, whichever comes first. When\n"
     "   * it runs, the body of the answer has ended or has failed (DEC-1188).\n"),
    # D1: the doc of fetchWithTimeout. After B3 a 429 comes at its head.
    (LIMITER, 'D1-fetchWithTimeout',
     "   * that rejects. With `wholeBody`, the answer comes when its body has ended: a\n"
     "   * copy of the body is read inside the same REQUEST_TIMEOUT_MS (DEC-1188). The\n"
     "   * caller's abort aborts the fetch.\n",
     "   * that rejects. With `wholeBody`, an answer other than a 429 comes when its\n"
     "   * body has ended: a copy of the body is read inside the same\n"
     "   * REQUEST_TIMEOUT_MS (DEC-1188). The caller's abort aborts the fetch.\n"),
    # N4: README, the timeout bullet.
    (README, 'N4-readme',
     "  `fetch`. The card cache's batch has its answer only when the body has ended, so a body that\n"
     "  has not ended 20 s after the start counts the same. An abort by the caller is no failure.\n",
     "  `fetch`. The card cache's batch has its answer only when the body has ended or failed, so a\n"
     "  body that has not ended 20 s after the start counts the same. An abort by the caller is no\n"
     "  failure.\n"),
    # N5: README, the stop bullet. The request that met the stop goes first in its own tab only.
    # The bullet is wrapped again at the file's width (94), as the bullet on main is.
    (README, 'N5-readme',
     "- **The stop.** A 429, a rejected `fetch` or the timeout stops both buckets for 30 s; the\n"
     "  request that met it goes first when the stop ends. If that one fails too, the stop doubles,\n"
     "  up to 300 s, and a success resets it. The stop record holds its end, its length and a\n"
     "  number: a request can double or end only the stop whose number it noted when it started. A\n"
     "  record that ended more than 300 s ago counts as none. A clock that went back cannot stretch\n"
     "  a stop past now plus its length, also when the stop lives in memory. The record lives in\n"
     "  `localStorage`, so a reload and a second tab obey it.\n",
     "- **The stop.** A 429, a rejected `fetch` or the timeout stops both buckets for 30 s; the\n"
     "  request that met it goes first in its tab when the stop ends. If that one fails too, the\n"
     "  stop doubles, up to 300 s, and a success resets it. The stop record holds its end, its\n"
     "  length and a number: a request can double or end only the stop whose number it noted when it\n"
     "  started. A record that ended more than 300 s ago counts as none. A clock that went back\n"
     "  cannot stretch a stop past now plus its length, also when the stop lives in memory. The\n"
     "  record lives in `localStorage`, so a reload and a second tab obey it.\n"),
]


def edit_text(path, text, log=print):
    """Apply every edit of `path` to `text`; return the new text. Stops on a missing span."""
    for p, name, old, new in EDITS:
        if p != path:
            continue
        n_old, n_new = text.count(old), text.count(new)
        if n_old == 1:
            text = text.replace(old, new)
            log(f'{name}: done')
        elif n_old == 0 and n_new == 1:
            log(f'{name}: already')
        else:
            raise SystemExit(f'{name}: STOP, old text found {n_old} times and new text {n_new} times in {path}')
    return text


def main(tree):
    here = os.path.dirname(os.path.abspath(__file__))
    dst = os.path.join(tree, TEST)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(here, 'expected', TEST), dst)
    print(f'B1, B2, B3 case: {TEST} copied')
    for path in (LIMITER, README):
        full = os.path.join(tree, path)
        with open(full, encoding='utf-8', newline='') as f:
            text = f.read()
        out = edit_text(path, text)
        if out != text:
            with open(full, 'w', encoding='utf-8', newline='') as f:
                f.write(out)


if __name__ == '__main__':
    main(sys.argv[1])
