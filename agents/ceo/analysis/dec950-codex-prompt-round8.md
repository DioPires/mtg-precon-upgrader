You are the independent senior reviewer of this product's PRD v4. On 2026-10-12 you reviewed Amendment 4 three times: round 5 (findings F43 to F63), round 6 (the first confirmation pass: F64 to F73) and round 7 (the confirmation pass on draft 3: a status for each of F64 to F73 and the sixteen round-5 partials, the structural ruling that one pipeline allocator is sound, and new findings F74 to F79; your round-7 review is reproduced below for reference). The CEO accepted all six round-7 findings and wrote draft 4 of the amendment. The owner then chose, on 2026-10-12 at 17:40Z, one more confirmation pass on draft 4 before accepting the amendment. This is that pass.

Scope. For each of F74 to F79, and for each item you marked PARTLY RESOLVED in round 7 (F64 and F43, closed by F74; F66 and F46, closed by F75; F50, closed by F77; F53, closed by F78), say whether draft 4 resolves it, with one line of evidence. Name any new defect that draft 4 introduced in the text it changed. Do not re-review text that draft 4 did not change unless a draft-4 change contradicts it. Do not rewrite the documents. Do not run builds or modify any file. You may run read-only commands (grep, sed, python3 -I for arithmetic) in the repository.

Three facts since round 7, for your reading of the documents. (a) The owner confirmed reading 11.20 (every kit ships in the first release, the temperate kit at the photographic standard and the other eleven at basic) and reading 11.21 (Dominaria's tables are written first, the second slice proves the schema on them, the other nineteen are drafted against the proven schema, nothing is distributed before all twenty are accepted). They are now the owner's decisions, not the CEO's compromises. (b) The owner left the single-allocator ruling (8.3.3, plan 14.5) to the CEO, so it stands as written. (c) Draft 4 still prints 11.20 and 11.21 as open questions with defaults and prints the ruling as overrulable; the next draft records them as decided. Do not count that pending bookkeeping as a finding, but do flag any text in either document that contradicts the confirmed readings or the ruling.

What draft 4 changed (commit 756c45a against draft 3 at e1e2530; 81 lines in `prd_v4.md`, 27 in the plan). In `prd_v4.md`: the status line (the "Amendment 4 draft 4" sentence); the Corridor row of 3.1; 5.4.1 (K_site = 11,459,156 mm², r_s = max(9,000 mm, isqrt(K_site × n)), b_s = ⌈6 r_s ⁄ 5⌉ + 15,000 mm, integer widening steps); 5.4.4 (R₀ with every b_s an integer); 5.4.6 (the attachment square in the site's frame); 5.4.8 (the approach test on the attachment square itself, retried over sweep directions then by widening); 5.4.9 (the trim after placement; kept vertices keep their indices); 5.4.10 (the three gap bounds the checker asserts: pad to first occupied slot at most 18 m, between occupied slots at most 18 m, last occupied slot to the end at most 10 m); 5.4.11 (what can and cannot block the attachment square); 5.4.12 (integer widening steps; the trim in the order of computation); 5.4.14 (the two negative predicate fixtures: the notch and the nested squares); 5.4.18 (rules (3), (5), (7), (10) and (13) rewritten: polylines rounded when built as the one named exception, integer segment and arc lengths, exact on-segment samples, table directions for every unit vector and normal, filled-shape distance zero on containment, strip containment by vertex-inside plus segment-to-edge clearance, the list of code-defined constants and approximations); 9.3 (the gap criterion as the checker asserts it); Appendix F.5 (three kits, every era named, an expansion rule and a committed script, validated under the ordinary rules with no flag); the section 12 row "Amendment 4 draft 4". In `docs/decisions/dec950-overhaul-deep-dive.md`, revision 13: the status paragraph, 14.5 (the round-7 verdicts, the resolution check with the partials recorded, the F74 to F79 triage table, the choice put to the owner) and 14.6.

Read, from the repository root:

1. `prd_v4.md`, Amendment 4 draft 4: the sections listed above, with 5.4 in full for context (5.4.1 to 5.4.18) and Appendix F.5 in full. Check the arithmetic: that K_site × n under isqrt gives the integer radius the formula 36 m² per stand intends (36 ⁄ π ≈ 11.4592 m² so K_site = 11,459,156 mm² gives r_s² ≈ 11.459 m² × n); that the attachment-square test as written is decided in the site's frame and is the same test in the world's frame (site centres on a 10 m lattice, a 5 m grid anchored at the origin); that the gap bounds of 5.4.10 together imply the 9.3 criterion; that the containment predicate of 5.4.18 (10) rejects your round-7 notch and nested-squares counterexamples and accepts a strip that does lie inside a concave polygon; that the F.5 expansion rule produces three files that validate under 4.16.2 with no flag.
2. `docs/decisions/dec950-overhaul-deep-dive.md`, the plan at revision 13: 14.5 (the round-7 part) and 14.6.
3. For reference: `web/public/data/a5846bec28d1447e/planes.json`.

Output format: a verdict per document (GO, GO WITH CHANGES, NO-GO) with one sentence of reason; a status table (RESOLVED, PARTLY RESOLVED, NOT RESOLVED, with one line of evidence) for F74 to F79 and for the six partials; then any new findings numbered from F80 with a severity (blocker, major, minor), the section, the defect, and the smallest fix; then the smallest coherent change set that lifts a NO-GO, if any; then one sentence on whether a further document-review round is required before leg 1's code read, or whether the remaining detail belongs in that code read. Be concrete: a counterexample with numbers beats an opinion.

Your round-7 review, for reference only (do not re-review the old text):

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