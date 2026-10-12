**PRD v4 Amendment 4 draft 2: NO-GO** — The revised allocator still rejects constructible inputs, lacks reproducible numerical operations, and makes guarantees its procedures do not establish.

**Plan rev 12: GO WITH CHANGES** — The two-leg sequence is reasonable, but validation prerequisites, reference-implementation sequencing and terminal outcomes need explicit correction before scheduling.

| Finding | Status | Evidence |
|---|---|---|
| F43 | PARTLY RESOLVED | §5.4.18 specifies much more arithmetic, but contradicts its rounding rule and leaves essential geometry operations unspecified. |
| F44 | PARTLY RESOLVED | Equal-end trimming and tapered wobble repair joins, but the new floor radius permits an empty first sweep. |
| F45 | RESOLVED | Explicit radii clear the original pad overlap, and chapter stones occupy separately tested lattice candidates. |
| F46 | PARTLY RESOLVED | Expanded obstacles and corner rules improve routing, but attachment cells can remain unavailable through every world widening. |
| F47 | PARTLY RESOLVED | Symmetric final-geometry tests repair exclusions, but fixed yaw conflicts with the final-facing requirement. |
| F48 | PARTLY RESOLVED | Placement restarts discard dependencies, but world widening explicitly preserves counters without explicitly preserving every widened radius. |
| F49 | PARTLY RESOLVED | Anchors now fit, but a nonempty, zero-area power cell still defeats the claimed eventual admissibility. |
| F50 | PARTLY RESOLVED | Partial and tiny clusters are defined, but two consecutive void slots still permit a 27 m gap against §9.3’s 20 m criterion. |
| F51 | PARTLY RESOLVED | Keyword precedence and several destinations are repaired; sorting within clusters does not establish chapter order across clusters. |
| F52 | PARTLY RESOLVED | Integer poses and identity joins are present, but integer corridor endpoints need not lie exactly on their path segments, and regional validation checks presence rather than winning-keyword assignment. |
| F53 | PARTLY RESOLVED | F.5 contains exactly the 37 bearing codes, but still supplies no complete region rows, anchors or era-to-region mapping for its executable fixture. |
| F54 | RESOLVED | Whole-site avoidance and the relocated-volume fixture agree; synthetic row minima have an explicit exception. |
| F55 | PARTLY RESOLVED | Large-world approximations broadly match the formula, but the 600-card diameter and “starting radii” description remain wrong. |
| F56 | RESOLVED | Parsed locators, printing/face references, sentence review and region-source display address the original provenance gaps. |
| F57 | PARTLY RESOLVED | Family membership is explicit, but product keywords can override it, and no fifty-set ceiling preflight is supplied. |
| F58 | PARTLY RESOLVED | Acceptance binds all three files, but canonical bytes are underspecified and stale-record validation contradicts development fallback. |
| F59 | RESOLVED | Core and twelve kits are mandatory, with manifest hashes, versions, locations and startup rejection. |
| F60 | PARTLY RESOLVED | Most branches terminate; a second Q1/Q5 rejection still says “owner decision” without assigning STOP. |
| F61 | PARTLY RESOLVED | Reduced bench and allocator row are present, but the oracle-only sidecar does not preserve printing-level spotlight identity or specify dataset validation. |
| F62 | PARTLY RESOLVED | Twenty engineer-days replaces the unsupported week, but required pre-slice validation is budgeted after the slice. |
| F63 | RESOLVED | The four identified live references now use medium, cluster streaming, marker stones and hero-era updates. |

**New findings and defects in the replacement rules**

1. **F64 — blocker — §5.4.18: the numerical contract remains contradictory and incomplete.** Adding \(2^{29}\) then floor-dividing rounds −0.5 to 0, contrary to half-away-from-zero. There is no normative π representation, inverse-angle/yaw procedure, vector normalization, strip join/cap construction, inset/expansion construction, residual sampling rule or corner normal. JSON anchors also lack conversion into the declared thousandths representation. Squared cross products used in distance predicates can exceed int64 even below 10 km. **Smallest fix:** specify these operations, signed rounding, exact decimal conversion and wide intermediate types, with adversarial numerical vectors.

2. **F65 — blocker — §5.4.8: lowering the floor creates a valid empty path.** Set \(r_s=9\) m, amplitudes `(1000,200,1000)`, phases `(180°,0°,180°)`, and sweep direction +x. The symmetric z extent centres the single sweep at z=0. Its chord runs from −7.2 to +7.527273 m; shortening removes 6 m, leaving **8.727273 m**, below the 9 m minimum. The build fails before capacity widening. **Smallest fix:** treat an empty path as a bounded site-widening condition, using the same dependency restart, or establish a sufficient floor with proof.

3. **F66 — blocker — §5.4.11: attachment failure is invariant under world widening.** With \(r_s=30.087\) m, all amplitudes 1000, all phases zero and direction +x, the first pad is approximately `(−29.147,−10.5)` relative to its site centre. Every eligible 5 m cell within 10 m behind it intersects the blob’s 5 m expansion; even the most separated candidate square is less than 3.9 m from the blob. Site centres move in 10 m increments, preserving this grid alignment through every R pass. **Smallest fix:** reserve a constructible attachment during site acceptance, with bounded alternatives or site widening; validate its final strip against actual exclusions, including stones.

4. **F67 — major — §5.4.9–10, invariant 11: local ordering is mistaken for global ordering.** Adjacent slots are 9 m apart, while longitudinal centre displacement and candidate radius permit overlapping path-position intervals of roughly ±5.75 m. A later cluster can therefore contain an earlier path position than the preceding cluster’s last accepted stand. Separately, displaced stands retain yaw but must face their fixed corridor endpoint. **Smallest fix:** enforce nondecreasing final corridor arc length across cluster boundaries and compute yaw from final geometry before exclusion testing.

5. **F68 — major — §5.4.5–6: “nonempty” does not imply positive area.** Use anchors `(0,0)`, `(−0.25,0)`, `(0.25,0)`, `(0,0.5)` with weights `0.5,1.14,1.14,0.5`. The middle anchor’s two horizontal power inequalities reduce to x≥0 and x≤0: its cell is a nonempty line, with no usable interior at any R. All stated anchor and weight limits pass. **Smallest fix:** reject zero-area cells explicitly before widening; state the admissibility claim only for positive-area cells.

6. **F69 — major — §4.13.3/5: exact integer corridor joins are not generally representable.** An integer segment from `(0,0)` to `(500,1)` has no interior integer lattice point. A nearest-point projection onto its interior cannot both be rounded to integer millimetres and satisfy the decoder’s exact on-path assertion. **Smallest fix:** choose a representable attachment rule, such as an emitted path vertex, or store a segment index and exact rational parameter; derive corridor geometry consistently. Regional assertions must also recompute selected-keyword precedence and the era-region comparison, not merely find any matching keyword.

7. **F70 — major — Appendix F.0/F.2, §4.16.2/5: acceptance still lacks one validatable interpretation.** Sorted keys, UTF-8 and no whitespace do not settle `1` versus `1.0`, Unicode escaping or negative zero. The `accepted` members lack individual types/formats. §4.16.2 makes digest mismatch a validation failure, while §4.16.5 permits stale acceptance only when tables validate. **Smallest fix:** define canonical serialization completely, type every acceptance member, and separate structural validity from acceptance status.

8. **F71 — major — Appendix F.2/F.3, §5.4.3: product-family geography can still be overridden.** Product keywords may be nonempty. A card assigned to its Commander-family era can match a keyword targeting another family and move there, despite the promise that every card stands in its family’s region. **Smallest fix:** require empty product keywords or reject every cross-family keyword assignment; supply a fifty-code family/era preflight demonstrating the chosen ceiling.

9. **F72 — major — §5.4.15, risk 22: the explanatory scale calculation is wrong.** Dataset arithmetic gives approximate initial **diameters** of Dominaria 1,056 m, Blind Eternities 963 m, Ravnica 691 m, Innistrad 598 m and Rabiah 175 m. A 600-card site has bounding diameter **217 m**, not 100 m. Tiny worlds start at 106 m; 141 m is after three R widenings. **Smallest fix:** correct the site diameter, distinguish initial from widened dimensions, and label the quoted world figures as diameters; Dominaria’s calculation also needs its assumed absence of keyword redistribution stated.

10. **F73 — major — §9.6, plan §14.4: prerequisites depend on deferred work.** Leg 1 requires green pipeline lore validation and an acceptance digest, but their implementation is assigned five days after both legs. The slice also judges C# divergence while excluding the Python reference and its generated fixtures. The longer schedule cannot absorb these dependencies implicitly. **Smallest fix:** move and cost validation/digest tooling before table acceptance; define an interim C# fixture-review gate and the later Python parity gate. Specify dataset-bound, printing-identifying spotlight input and explicitly label a second Q1/Q5 rejection STOP.

**Smallest coherent change set lifting NO-GO**

- Close the numerical and geometry contract, including F64–F69; preserve all widened radii across R passes, and enforce or relax the occupied-cluster gap criterion explicitly.
- Supply a complete executable F.5 fixture; reconcile the three-one-card fixture’s claimed three chapter stones with the after-first rule, which produces two.
- Close acceptance serialization, product-family assignment, pack joins and corrected scale statements.
- Move prerequisite tooling into the costed sequence and close every matrix outcome.
- Independently re-review the revised allocator contract before implementation; retain §14.6’s confirmation of both CEO readings and §11.1’s distribution gate.