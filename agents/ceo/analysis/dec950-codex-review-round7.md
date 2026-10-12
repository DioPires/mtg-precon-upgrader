**PRD v4 Amendment 4 draft 3: NO-GO** — Most prior findings close, but attachment availability and geometric containment remain unsound, and the fixture and path-length guarantees still contradict their procedures.

**Plan revision 12: GO WITH CHANGES** — The recosted sequence and code-review gate are sound; §14.5 must record the remaining partials rather than claim every finding closed.

**Structural ruling:** One pipeline allocator is a sound replacement for two implementations. Integer pack poses, independent checkers and the leg-1 Codex code review preserve useful safeguards without requiring a second allocator. Unnamed operations may be defined in reviewed reference code. What remains necessary is consistency between that permission and §5.4.18’s explicit arithmetic restrictions; F74 identifies the remaining conflict. Fixtures detect regressions but do not prove correctness for unrepresented inputs.

| Finding | Status | Evidence in draft 3 |
|---|---|---|
| F64 | PARTLY RESOLVED | Signed rounding, integer inputs, wide arithmetic and the single implementation close most issues; root evaluation and intermediate rounding still conflict with §5.4.18. See F74. |
| F65 | RESOLVED | §5.4.8 retries an empty path over eighteen directions, then invokes bounded site widening. |
| F66 | PARTLY RESOLVED | The approach improves attachment construction, but its clearance does not guarantee an unblocked containing cell. See F75. |
| F67 | RESOLVED | Invariant 11 explicitly relaxes ordering to **cluster order**; §5.4.10 recomputes yaw before testing final geometry. This does not establish monotonic corridor positions across clusters, but no longer requires them. |
| F68 | RESOLVED | §5.4.5 rejects empty and zero-area cells exactly before widening; §5.4.6 limits its growth argument to positive-area cells. |
| F69 | RESOLVED | §4.13 stores corridor vertex indices and recomputes selected-keyword precedence and the differing era region. |
| F70 | RESOLVED | F.0 types acceptance members and restricts numeric syntax; F.2 identifies one serializer; §4.16 separates validity from acceptance status. |
| F71 | RESOLVED | Product keywords must be empty; F.6 covers the dataset’s fifty codes exactly once in ten families and thirteen eras. |
| F72 | RESOLVED | Recalculation supports the revised initial diameters: Dominaria ≈1,121 m, Blind Eternities ≈1,075 m, Rabiah ≈271 m; a 600-card site ≈229 m. |
| F73 | RESOLVED | Leg A precedes acceptance; the allocator precedes Unity consumption; spotlight identities are dataset-validated printing IDs; second Q1/Q5 rejection explicitly stops. |
| F43 | PARTLY RESOLVED | Withdrawing the C# mirror removes the cross-language problem; the remaining internal arithmetic contradictions are F74. |
| F44 | RESOLVED | Equal-end trimming and tapered joins remain; empty first sweeps now retry and widen under §5.4.8. |
| F46 | PARTLY RESOLVED | Routing retains obstacle expansion and corner protection, but attachment availability remains unproved and demonstrably false. See F75. |
| F47 | RESOLVED | §5.4.10 now computes final yaw before symmetric exclusion tests; the newly specified predicate defect is reported separately as F76. |
| F48 | RESOLVED | §5.4.12 explicitly preserves every widened radius and widening count across placement restarts and world widening. |
| F49 | RESOLVED | Anchor validation and explicit zero-area rejection close both outstanding cases. |
| F50 | PARTLY RESOLVED | Two void slots now bound gaps between retained slots, but placement can leave a long unoccupied path tail. See F77. |
| F51 | RESOLVED | Selected-keyword semantics, explicit cluster ordering and chapter/region destinations now agree with the revised requirement. |
| F52 | RESOLVED | Integer poses, vertex-index corridor joins and selected-keyword/era-region assertions supply the missing pack guarantees. |
| F53 | PARTLY RESOLVED | Region anchors and mappings are supplied, but F.5 contradicts the fixture exceptions and still omits required field values. See F78. |
| F55 | RESOLVED | §§5.4.13–15 and risk 22 now distinguish initial diameters, widened results and assumed keyword redistribution. |
| F57 | RESOLVED | Family assignment cannot be overridden; F.6 demonstrates the ceiling against the actual fifty-code dataset. |
| F58 | RESOLVED | Canonical serialization and accepted/stale/absent status now have one consistent interpretation. |
| F60 | RESOLVED | §9.6 explicitly assigns STOP after the second Q1/Q5 rejection. |
| F61 | RESOLVED | The sidecar preserves printing IDs and validates against the pinned dataset; row K gates allocator/checker results. |
| F62 | RESOLVED | Plan §14.4 costs prerequisite tooling before acceptance and the pipeline allocator before Unity, eliminating the deferred dependency. |

**New findings**

**F74 — major — PRD §§5.4.1, 5.4.4, 5.4.18: the numerical rules still prohibit operations the procedure requires.**

- `r_s = √(36n/π)` is generally irrational, whereas every quantity must be rational and square roots are restricted to integer `isqrt`. The claimed absence of π applies to wobble, not the radius formula.
- `isqrt(2Σb_s²)` also needs an integer argument, which rational radii do not guarantee.
- Arc lengths explicitly use **rounded segment endpoints before allocation finishes**, contradicting “rounding once, at emission.”

**Smallest fix:** Declare which mathematical formulas use code-defined rational approximations, and explicitly permit the intermediate quantization used for arc lengths. Pin those choices in leg 1’s reviewed reference code and adversarial fixtures. No restored two-language numerical specification is necessary.

**F75 — blocker — PRD §§5.4.8, 5.4.11: the approach’s containing cell can still be blocked.**

A point anywhere in a 5 m square can be almost **7.071 m** from a corner. The document incorrectly uses **3.54 m**, the centre-to-corner bound.

A numerical witness using permitted local parameters:

- `r_s = 9 m`, amplitudes `(1000,1000,1000)`, phases all zero, sweep direction `119°`.
- Shortened run ≈10.812 m; head `H ≈ (3.395, −5.280)`.
- Approach point `P ≈ (9.614, −14.953)`, approximately **9.976 m clear of the blob**.
- Its containing cell is `[5,10] × [−15,−10]`; corner `(5,−10)` is only **3.231 m from the blob**, so the cell intersects the 5 m expansion.

The local approach and stone tests can pass. Table quantization and the 2 mm margin cannot cover this metre-scale discrepancy. Translating the site by 10 m preserves the failure.

**Smallest fix:** Test the actual attachment square during local acceptance, then retry direction or widen the site when blocked. The grid alignment is already known because site translations are multiples of 10 m. Do not send this unchanged local failure through world widening.

**F76 — blocker — PRD §5.4.18(10): the new strip-containment predicate is false.**

For a concave polygon, distant endpoints plus no centreline crossing do not establish clearance along the segment.

Example in metres: take a large rectangle with a bottom notch `−1 ≤ x ≤ 1` reaching `y=0`. The segment from `(-5,1)` to `(5,1)` has endpoints more than 4 m from the notch and crosses no boundary. Nevertheless, its 3 m strip reaches `y=−0.5` inside the notch, outside the polygon. The stated predicate accepts it.

The distance definition also needs containment handling: nested squares can overlap without edge crossings while every vertex-to-edge distance is positive.

**Smallest fix:** Require whole-segment clearance from polygon boundaries, together with inside classification. Filled-shape distance must be zero on containment as well as crossing. Add negative fixtures for both cases to both checkers. Exact distance predicates remain sufficient; offset constructions are unnecessary.

**F77 — major — PRD §§5.4.9–10, 9.3: the path cut does not bound the unoccupied tail.**

The cut responds to **void candidates**, while placement stops when all cards are assigned. Later non-void slots can remain empty.

For example, nine cards can fill eight positions at slot 9 m and one at slot 18 m. If the otherwise valid path continues to 45 m, its last **27 m** contains no occupied cluster. Neither rule cuts that tail. Thus the pad-to-end twenty-metre criterion does not follow from the bound between occupied slots.

**Smallest fix:** After placement, bound the actual leading and trailing gaps as well as interior gaps, and trim unused path tails. Preserve corridor vertices referenced by accepted stands; recheck connectivity and exclusions after trimming.

**F78 — major — PRD Appendix F.5 versus §5.4.14: the supposedly executable example remains invalid and incomplete.**

F.5 uses **seven kits** and says `--fixture` relaxes the three-kit ceiling. §5.4.14 says the flag relaxes row minima and acceptance **“and nothing else.”** Both cannot govern the same fixture.

The region table also lacks required `sentence` and `sources` values; the era mapping lacks explicit required `name` and `years` values. The placeholder prescription supplies era paragraphs only.

**Smallest fix:** Keep the example within three kits and supply every required value, directly or through an explicit deterministic expansion rule. Then require validation of those exact three generated files under the single documented fixture policy.

**F79 — minor — PRD §3.1, Corridor row: the definition retains the superseded attachment rule.**

It still says “nearest point” of the path; §§5.4.9 and 4.13 require the nearest **vertex**.

**Smallest fix:** Update the entity definition to the vertex rule.

**Smallest coherent change set lifting NO-GO**

1. Make §5.4.18 internally consistent while retaining reference-code authority and the leg-1 code gate.
2. Replace the attachment-cell guarantee and incorrect containment predicate with the explicit tests above.
3. Validate occupied-path gaps after placement and trim unused tails.
4. Complete F.5 under one fixture policy; correct the Corridor definition.
5. Update plan §14.5 with these actual dispositions. Retain §14.6’s owner confirmations and §11.1’s distribution gate.

Read-only review and arithmetic checks only; no builds or file changes.