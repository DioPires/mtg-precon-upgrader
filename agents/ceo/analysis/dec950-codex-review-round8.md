**PRD v4 Amendment 4 draft 4: NO-GO** — The former geometric blockers close, but the new trim does not guarantee its asserted tail bound, and F.5’s output directory contradicts ordinary validation.

**Plan revision 13: GO WITH CHANGES** — The sequence and single-allocator ruling remain sound; correct the resolution counts and carry forward the outstanding dispositions below.

| Finding | Status | Evidence in draft 4 |
|---|---|---|
| F74 | RESOLVED | §§5.4.1, 5.4.4 and 5.4.18 explicitly define integer radii, widening, segment lengths and the exception for rounding polylines when built. |
| F75 | RESOLVED | §5.4.8 tests the actual attachment square against the filled blob, then retries directions and widens locally. |
| F76 | RESOLVED | §5.4.18(10) requires whole-segment boundary clearance and detects polygon containment; §5.4.14 supplies both negative fixtures. |
| F77 | PARTLY RESOLVED | §5.4.10 adds trimming and all three gap assertions, but its endpoint can be undefined and its corridor-distance justification is false: F80–F81. |
| F78 | PARTLY RESOLVED | F.5 supplies the missing fields and uses three kits, but its prescribed directory fails F.0’s identity rule: F82. |
| F79 | RESOLVED | §3.1 now specifies the nearest path vertex, with ties by lower index. |
| F64 | RESOLVED | F74’s explicit integer formulas and intermediate-rounding permission remove the remaining arithmetic contradiction. |
| F43 | RESOLVED | The single implementation now has explicit authority for the numerical choices previously left contradictory. |
| F66 | RESOLVED | The attachment square itself must pass local acceptance; clearance of its anchor alone is no longer sufficient. |
| F46 | RESOLVED | §§5.4.6, 5.4.8 and 5.4.11 now account for both the site’s own blob and external obstacles. |
| F50 | PARTLY RESOLVED | The checker detects excessive tails, but the placement procedure can still produce one: F80. |
| F53 | PARTLY RESOLVED | The example’s content expansion is complete; its claimed ordinary validation still conflicts with its location: F82. |

The requested checks support those dispositions:

- **Radius:** `36,000,000/π = 11,459,155.9026… mm²`; `K_site = 11,459,156` is the nearest integer. For 600 stands, `isqrt(K_site × 600) = 82,918 mm`, giving `b_s = 114,502 mm`. The example’s initial Dominaria diameter is **1,120.736 m**.
- **Attachment frame:** translating by `(10a,10b)` metres translates grid indices by `(2a,2b)`, preserving the square and boundary tie rule. Its maximum radial overreach is `11.5 + √50 − 15 ≈ 3.571 m`, below 3.6 m; external obstacles remain more than their 5 m expansion away.
- **Containment:** the round-7 notch segment at `y=1 m` has only 1 m boundary clearance, below the required 1.502 m. In the same sufficiently large notched rectangle, the segment `(-5,3)–(5,3)` has 3 m minimum clearance and passes. Nested squares now intersect through vertex-inside classification.
- **Gaps:** the asserted bounds—18 m leading, 18 m interior, 10 m trailing—imply §9.3’s criterion in the specified arc-length metric. The defect is establishing those bounds during allocation.
- **F.5:** the fifteen eras cover exactly the dataset’s **37 codes and 6,271 cards**, without duplication. Eleven regions and three kits meet the limits; maximum anchor radius squared is 812,500, and minimum pairwise distance squared is 125,000, exceeding 22,500. The remaining validation contradiction is F82.

**F80 — major — PRD §5.4.10: a nearby corridor vertex need not be nearby along the path.**

The new assertion that a corridor’s vertex lies at most 6 m past its slot does not follow from nearest-vertex selection.

A half-turn counterexample, coordinates in metres:

- Centre `(0,−0.5)`, radius 10.5; entrance `(0,−11)`, exit `(0,10)`, bulging right.
- At an entrance slot, the inward cluster centre can be `(0,−4)`: the 6 m offset plus the permitted 1 m transverse displacement.
- Candidate `(0,0)` is 4 m from that centre, within the 4.252 m candidate radius.
- Its nearest half-turn vertex is the exit, 10 m away spatially but **32.884 m ahead along the rounded, 15°-sampled half-turn**.

Runs extending left and away from the candidate preserve that nearest vertex. A blob containing the cluster and corridor does not exclude this configuration. If this is the last occupied slot, preserving its corridor requires a tail exceeding 32 m, contradicting the asserted 10 m maximum.

**Smallest fix:** explicitly reject candidates whose selected corridor vertex lies more than 6 m ahead of their slot, applying the restriction before capacity counting and preserving the existing exhaustion/widening rules. Keep nearest-vertex selection and the final gap assertions.

**F81 — major — PRD §5.4.10: the requested trim endpoint may not exist.**

For a path of integer arc length **20 m**, with its last occupied slot at **18 m**, `last slot + ρ = 22.5 m`. Even if every corridor ends before 20 m, there is no vertex “at or past” the requested endpoint. No existing rule requires 4.5 m of unused path after the last occupied slot.

**Smallest fix:** use  
`min(original path length, max(last occupied slot + ρ, farthest referenced vertex arc length))`  
before selecting the retained endpoint. This preserves every referenced vertex.

**F82 — major — PRD Appendix F.5 versus F.0: the example’s directory fails ordinary identity validation.**

F.5 places the three files directly under `…/layout/dominaria-example/`. F.0 requires their `plane` to match both the directory and an Appendix C.1 hero slug. `dominaria` fails the directory match; `dominaria-example` fails the hero-slug match.

**Smallest fix:** place the files under `…/layout/dominaria-example/dominaria/`, explicitly emit `"plane": "dominaria"` in all three, and validate that directory without an exception.

**F83 — minor — Plan status, §§14.5–14.6; PRD §12: the resolution counts are wrong.**

The plan’s enumerated resolved list contains **20**, not 21, findings. The partial list contains **six**, not five: F64, F43, F66, F46, F50 and F53. Together they account for all 26.

**Smallest fix:** replace “twenty-one resolved” with “twenty resolved” and “five partials” with “six partials” throughout the new record and scope descriptions.

**F84 — minor — PRD §5.4.18(7): the new 3 km world-diameter bound is unsupported.**

Starting from the example’s `R₀ = 560,368 mm`, nineteen permitted integer widenings produce `R = 3,427,185 mm`: a **6,854.37 m diameter**. Thus the stated “under 3 km” bound cannot justify the associated “under 30 mm” displacement claim.

**Smallest fix:** remove that fixed-size justification; rely on predicates testing the actual table-derived geometry, or provide a bound covering the permitted widening range.

The confirmed owner readings agree with the operative release and sequencing rules. Historical “other kits follow by release” wording in PRD §12 and plan §14.1 needs qualification as photographic upgrades when recording the confirmation; the original “all twenty tables first” wording likewise needs the confirmed second-slice exception. These are decision-record updates, not additional findings.

The smallest coherent change set lifting NO-GO is:

1. Add the corridor arc-distance eligibility test and clamp the trim target to the existing path.
2. Correct the example’s directory identity.
3. Correct the counts and unsupported size claim; update the plan with these actual dispositions.

A narrow document confirmation of F80–F82 is required before leg 1’s code read; remaining implementation choices belong in that code read.

Read-only inspection and arithmetic only; no builds, validator execution or file changes.