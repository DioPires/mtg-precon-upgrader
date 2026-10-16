# Builds the expected files of fix round 1 of PR #64 (DEC-1162, review DEC-1166) from the head 824d0c0.
# Usage: python3 -I build_expected.py <repo>    (writes expected/web/...; asserts each anchor once)
import os, subprocess, sys

repo = sys.argv[1]
HEAD = '824d0c0ecbd4e229c74b01ca25e13a1b76903381'
here = os.path.dirname(os.path.abspath(__file__))


def head_file(path):
    return subprocess.run(['git', '-C', repo, 'show', f'{HEAD}:{path}'], capture_output=True, text=True,
                          check=True).stdout


def edit(text, old, new):
    assert text.count(old) == 1, (old[:60], text.count(old))
    return text.replace(old, new)


def write(path, text):
    out = os.path.join(here, 'expected', path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w') as f:
        f.write(text)


# 1. The spec: B1 (the reviewer's case, kill file :16) and N1 (the fourth call form, kill file :30).
SPEC = 'web/tests/dec1152-rate-check-post.spec.ts'
s = head_file(SPEC)
s = edit(s,
         "// fail the test: test.fail() expects that failure, as in the H7 case of\n"
         "// dec1131-card-batches.spec.ts. The last two cases read the error that the\n"
         "// fixture throws. The stub answers every request; nothing reaches the live API.\n",
         "// fail the test: test.fail() expects that failure, as in the H7 case of\n"
         "// dec1131-card-batches.spec.ts. One case checks that the real clock counts no\n"
         "// other path. The last two cases read the error that the fixture throws. The\n"
         "// stub answers every request; nothing reaches the live API.\n")
s = edit(s,
         "const LOOKUP = 'https://api.scryfall.com/cards/named?fuzzy=Sol%20Ring';\n",
         "const LOOKUP = 'https://api.scryfall.com/cards/named?fuzzy=Sol%20Ring';\n"
         "const AUTOCOMPLETE = 'https://api.scryfall.com/cards/autocomplete?q=sol';\n")
s = edit(s,
         "test.describe(\"the rate check, the page's clock: a POST counts twice\", () => {\n",
         "test.describe('the rate check, real clock: only /cards/named and /cards/collection count', () => {\n"
         "  // Scryfall allows 10 requests a second on /cards/autocomplete (bucket 2), and\n"
         "  // the app spaces them 120 ms apart, so three at once must pass (DEC-1166 B1).\n"
         "  test('three autocompletes at once pass', async ({ page }) => {\n"
         "    await page.goto('/data/index.json');\n"
         "    await page.evaluate(\n"
         "      (url) => Promise.all([0, 1, 2].map(() => fetch(url).then((r) => r.status))),\n"
         "      AUTOCOMPLETE,\n"
         "    );\n"
         "  });\n"
         "});\n"
         "\n"
         "test.describe(\"the rate check, the page's clock: a POST counts twice\", () => {\n")
s = edit(s,
         "  // The page reads the method of each form of a fetch call.\n"
         "  for (const form of ['fetch(url, init)', 'fetch(request)', \"fetch(url, init), method 'post'\"] as const) {\n",
         "  // The page reads the method of each form of a fetch call. In fetch(request,\n"
         "  // init) the method of init wins over the Request's (DEC-1166 N1).\n"
         "  for (const form of [\n"
         "    'fetch(url, init)',\n"
         "    'fetch(request)',\n"
         "    'fetch(request, init)',\n"
         "    \"fetch(url, init), method 'post'\",\n"
         "  ] as const) {\n")
s = edit(s,
         "            const sent = form === 'fetch(request)' ? fetch(new Request(url, init)) : fetch(url, init);\n",
         "            const sent =\n"
         "              form === 'fetch(request)'\n"
         "                ? fetch(new Request(url, init))\n"
         "                : form === 'fetch(request, init)'\n"
         "                  ? fetch(new Request(url), init)\n"
         "                  : fetch(url, init);\n")
write(SPEC, s)

# 2. The README: N2 (the reviewer's sentence; the paragraph's tail rewrapped).
README = 'web/README.md'
r = head_file(README)
r = edit(r,
         "The app also counts each POST as two starts, and spaces its POSTs 1,200 ms apart, so two\n"
         "batches in 1 s fail the test. A case proves the app's limit only when the app has lookups for\n"
         "two batches or more. A case that sends one batch, or paces its own hovers, reads a low peak\n"
         "whatever the app does. The `scryfall-stub` attachment of each test that sent a Scryfall request\n"
         "gives the count of requests, the peak in 1 s (a POST counts twice) and the number of 429\n"
         "answers (`bucketOne`). The error lists each send of the context with its method.\n",
         "The app also counts each POST as two starts, and spaces its POSTs 1,200 ms apart. Two\n"
         "batches in 1 s start 4 requests and fail the test. A case proves the app's limit only when\n"
         "the app has lookups for two batches or more. A case that sends one batch, or paces its own\n"
         "hovers, reads a low peak whatever the app does. The `scryfall-stub` attachment of each test\n"
         "that sent a Scryfall request gives the count of requests, the peak in 1 s (a POST counts\n"
         "twice) and the number of 429 answers (`bucketOne`). The error lists each send of the context\n"
         "with its method.\n")
write(README, r)

# 3. test.ts: N2's two older sentences (comments only; no code changes).
SUPPORT = 'web/tests/support/test.ts'
t = head_file(SUPPORT)
t = edit(t,
         "// event shows it (DEC-1131 ruling 5, DEC-1149 N3). The check stamps each request\n"
         "// when the browser sends it (the context's `request` event), in real time, so\n"
         "// every case proves the app's limit, also a case whose own route holds an\n"
         "// answer (DEC-1131 N2).\n",
         "// event shows it (DEC-1131 ruling 5, DEC-1149 N3). The check stamps each request\n"
         "// when the browser sends it (the context's `request` event), in real time, so\n"
         "// it also counts the requests of a case whose own route holds an answer\n"
         "// (DEC-1131 N2). A case proves the app's limit only when the app has lookups\n"
         "// for two batches or more (web/README.md, \"The rate check\").\n")
t = edit(t,
         "   *           answers. The limiter paces the lookups, one every 600 ms or more.\n",
         "   *           answers. The limiter paces the lookups, one every 1,200 ms or more.\n")
write(SUPPORT, t)

for p in (SPEC, README, SUPPORT):
    blob = subprocess.run(['git', 'hash-object', os.path.join(here, 'expected', p)], capture_output=True,
                          text=True, check=True).stdout.strip()
    print(blob, p)
