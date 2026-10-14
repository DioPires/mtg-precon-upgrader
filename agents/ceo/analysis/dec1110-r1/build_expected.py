"""Build the route A copy of kill-limiter.test.ts for PR #38 fix round 1 (DEC-1102).

Source: the reviewer's run file /tmp/dec1110/route-a/kill-limiter.test.ts
(blob ea36e4fc). Drops the three READING cases (K4, K5, P2) and the K5 kill
case, which pins the head's 600 ms re-read and fails once B1 writes the
capped last start back. Drops the LAST_START_KEY import that only those
cases used. Every other line is the reviewer's.
"""
import sys
src, out = sys.argv[1], sys.argv[2]
s = open(src).read()
old_hdr = ("// DEC-1110 reviewer's kill cases and readings for scryfallLimiter.ts and cardCache.ts.\n"
           "// Each case passes on 58ca0b3 and fails on the mutant named in its title, unless\n"
           "// its title says READING (a reading of the head, not a kill case).\n")
assert s.startswith(old_hdr)
s = s.replace(old_hdr, "// DEC-1110 reviewer's kill cases for scryfallLimiter.ts and cardCache.ts.\n"
                       "// Each case passes on 58ca0b3 and fails on the mutant named in its title.\n", 1)
assert s.count("  LAST_START_KEY,\n") == 1
s = s.replace("  LAST_START_KEY,\n", "", 1)
t_old = "describe('K4 readStop() and K5 lastStartOf(): a clock that went back', () => {"
assert s.count(t_old) == 1
s = s.replace(t_old, "describe('K4 readStop(): a clock that went back', () => {", 1)
# READING K4, READING K5 and K5: from the READING K4 case to the end of the describe.
a = s.index("  it('READING K4 (passes on the head)")
b = s.index("describe('K10 enqueue()")
block = s[a:b]
assert "READING K5" in block and "it('K5: bucket 1 reads" in block and block.count("  it(") == 3
assert block.endswith("  });\n});\n\n")
# s[:a] ends with the K4 case's "  });\n\n"; keep "});\n\n" to close the describe.
assert s[:a].endswith("  });\n\n")
s = s[:a].rstrip("\n") + "\n});\n\n" + s[b:]
# P2 READING describe: whole block.
a = s.index("describe('P2 READING: the stop record after its end'")
b = s.index("describe('A13 formatPricesDate()")
assert s[a:b].count("  it(") == 1
s = s[:a] + s[b:]
assert "READING" not in s and "LAST_START_KEY" not in s and "console.log" not in s
open(out, "w").write(s)
