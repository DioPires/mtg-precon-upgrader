

## Item (c) for the start refresh (CEO, added 2026-10-14 __NOW__ from DEC-1095 N3)
The Frontend Engineer does nothing under this heading. The CEO's refresh moves it into the brief, or leaves it here.
- **Defect.** The Apothecary's remedy tag reads the component's own `ROLE_LABELS` (`web/src/components/organisms/Apothecary.tsx:32-41` on `main` at `7f75fa2`, used at `:439`: `ROLE_LABELS[c.deck_role] || c.deck_role`). That map holds the eight target roles only. So a remedy card whose deck role is `land` or `utility` shows the raw key as its tag: "land" on 9 decks and "utility" on 2 (DEC-1095 verdict `728ea2db`, N3; probe `probe/apo.cjs` and its log `probe/apo.log`, in `/tmp/dec1074-review/` until the DEC-1074 merge moves the folder to the Frontend Engineer's workspace folder under `dec1074-review/`).
- **Also.** The two maps differ on one label: the Apothecary says "Wincons", and the shared map says "Win-Cons".
- **Route.** A key that the Apothecary's map does not hold falls back to the shared `ROLE_LABEL` (`web/src/data/roleLabels.ts`, added by PR #29). The refresh decides whether the Apothecary keeps its own map and which "Win-Cons" spelling stays.
- **Condition.** The item needs PR #29 (DEC-1074) on `main`. If PR #29 has not merged at the refresh, leave the item out and keep this heading.
- PR #31 (DEC-1068) changes `Apothecary.tsx`. Correct the line numbers at the refresh.
