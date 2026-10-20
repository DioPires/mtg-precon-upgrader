**[PRD v4 Amendment 4 draft 5](/Users/dpires/Documents/Personal/code/eternities-mtg-app/wt-dec950-r8/prd_v4.md): GO WITH CHANGES** — F80–F82 close; F84’s example arithmetic is correct, but its universal size claim remains unsupported, alongside two minor wording defects.

**[Plan revision 14](/Users/dpires/Documents/Personal/code/eternities-mtg-app/wt-dec950-r8/docs/decisions/dec950-overhaul-deep-dive.md): GO WITH CHANGES** — The sequence and resolution counts are correct; the new trend statement still undercounts round 5.

Reviewed `e2ac79a` against `756c45a`; read-only inspection and arithmetic only.

| Finding | Status | Evidence in draft 5 |
|---|---|---|
| F80 | RESOLVED | §5.4.9(e) rejects a candidate whose selected vertex is more than 6 m ahead or behind its slot, before capacity counting. |
| F81 | RESOLVED | §5.4.10 caps `t_end` at total path length, guaranteeing a retained endpoint while preserving every referenced vertex. |
| F82 | RESOLVED | F.5 uses `dominaria-example/dominaria/` and `"plane": "dominaria"`; §§4.16.2 and F.0 impose no fixture-parent-directory restriction. |
| F83 | RESOLVED | Round 7 now records 20 resolved + 6 partial = 26; round 8 lists 8 resolved + 4 partial = 12; new-finding severities also reconcile. |
| F84 | PARTLY RESOLVED | The specified Dominaria sequence yields 6,854.37 m and 59.816 mm, but §§5.4.4 and 5.4.12 do not make that example a universal maximum. |
| F77 | RESOLVED | The eligibility restriction and capped trim establish the previously unsupported trailing bound. |
| F50 | RESOLVED | Eligibility precedes capacity; existing void-slot and placement-exhaustion rules, followed by the corrected trim, establish all three gaps. |
| F78 | RESOLVED | The previously completed example now satisfies directory identity without a validation exception. |
| F53 | RESOLVED | The complete example validates as a fixture input under its hero slug, separately from the entry’s curated tables. |

The requested checks:

- **Candidate eligibility:** the half-turn witness selects a vertex about **32.884 m** ahead, so test (e) rejects it. On the specified straight run, a candidate within 4.252 m of the unshifted cluster centre has a nearest vertex at most **4.252 + 0.250 = 4.502 m** along the run from the slot—a conservative bound below 6 m.
- **Gaps:** two initial void slots force a cut and insufficient capacity, so a successful path’s first occupied slot is at 9 or 18 m. Two consecutive interior voids likewise cannot survive; a non-void interior cluster accepting fewer than three exhausts placement. Thus leading and interior gaps are at most **18 m**. Every referenced vertex is at most the last occupied slot + 6 m; the cap cannot increase that. Endpoint rounding forward adds less than 2.75 m, giving **8.75 m < 10 m**.
- **Fixture identity:** F.0 checks the leaf directory and hero slug. §4.16.1 locates the entry’s source tables; it does not forbid separately validated fixture inputs.
- **Arithmetic:** 0.0005° = **8.72664626 µrad**. Nineteen integer widenings give **R = 3,427,185 mm**; displacement over its diameter is **59.815662 mm**. The looser bounds “8.8 µrad” and “7 km” alone yield **61.6 mm**, so the tighter figures are needed.

**F84’s remaining limitation:** §5.4.14 permits a one-region, one-era synthetic fixture. Assigning Dominaria’s 6,271 cards to that single era gives, under the existing formulas:

`r_s = 268,067 mm; b_s = 336,681 mm; R₀ = 708,362 mm`.

Nineteen permitted widenings give **R = 4,332,300 mm**, a diameter of **8,664.6 m** and angular displacement of **75.613 mm**. This defeats the claimed universal bound derived from the example’s `R₀`; it does not invalidate the new requirement to test geometry as built. Smallest fix: label the 59.816 mm calculation as the schema example only, removing “longest segment” and “widest world” claims from the PRD and corresponding plan record.

New findings:

- **F85 — minor — PRD §5.4.9:** adding test (e) leaves “four tests, each on geometry inflated by j” governing five tests, including an arc-length comparison. **Smallest fix:** distinguish four inflated geometry tests, (a)–(d), from the additional arc-length test (e).
- **F86 — minor — Plan §14.5, round-9 rationale:** the newly written trend is **20, 10, 6, 5**, but F43–F63 comprise **21** findings. **Smallest fix:** use **21, 10, 6, 5**, and correct the matching round-7 trend.
- **F87 — minor — PRD §§11.20–11.21:** each now says “no longer a default” but retains the operative sentence “Default: that reading”. **Smallest fix:** remove the default designation or explicitly label those closing sentences as historical.

No NO-GO remains; the changes above are minor corrections.

No further document-review round is required before leg 1’s code read; apply these corrections, with remaining implementation detail assessed in that code read.