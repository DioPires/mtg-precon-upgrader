**Owner card answered; A/B leg open (CEO run `2eaaabd9`, 08:48Z).** The owner chose the recommended option on both questions of card `345bc3b0` (08:43Z), so I opened [DEC-1199](/DEC/issues/DEC-1199) for the Design System Engineer.

- **A:** the 3 /shopping boxes and the Compare box keep the larger `.gv1-rune` mark (◇, or ◆ on "All cards owned"). One modifier class on those 4 containers and one `states.css` rule turn off their `.gv1-empty::before` ◇. No other empty box changes.
- **B:** the two Combo Lab loading lines (`ComboLab.tsx:616` and `:632` on `e6d472e`) drop their inline `<Glyph>◇ </Glyph>`. The `combo-lab.css` `::before` ◇ stays as their one mark.
- Screen readers already skip all these marks (PR #76 and PR #79), so only what users see changes.
- The leg changes the two "the two glyphs still show" assertions of `dec1177-empty-sigils.spec.ts`, adds a class check to the DEC-1177 Vitest cases, and kills 5 named mutants. It takes box shots before and after at 1280 px and 390 px, with a control box that must read 0 changed pixels. Budget: about 1.5 hours.
- The leg's run `f1453c46` started at 08:47:36Z. Its hand-back comes to DEC-1199. The review then goes to an engineer who is not the implementer.
- DEC-1182 closes when DEC-1199's pull request merges. It stays `in_review` with a fallback monitor at 12:30Z.
