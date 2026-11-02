# DEC-925 Reality Fracture prerelease — verification notes (2026-09-23)

Data: `fra_all_cards.json` (Scryfall `set:fra unique=cards`, 285 cards), `fra_all_prints.json` (`unique=prints`, 461).

## Verified facts
- Set code `fra`, expansion, release 2026-10-02. Prerelease window 2026-09-25..2026-10-01 (WPN). Arena 2026-09-29 (WotC prerelease guide).
- Main set per WotC Collecting article: 71 C / 109 U / 64 R / 26 M (270) + 10 common duals + 10 basics. Scryfall has all 270 + 10 duals + 5 basics = 285 unique. Fully previewed.
- Collector gaps 1, 20, 38, 53, 110 = mythics (Emrakul the Exigent Doom, Return to the Light Realms, Seasoned Cryomancer, Darklight Phoenix, Omnipresence) whose showcase print (438/440/441/444/448) was chosen by `unique=cards`. Not missing cards.
- Booster (WotC + mtgscribe, agree): 5 C; s6 C 98.18%/SPG 1.82%; s7 non-paired U; s8 C ~23% / U ~74%; s9–11 echoed pairs, 2 of 3 = both halves of one pair at same rarity (U 88.9% / R 6.7% / M 1.4%); s12 R 74.4% / M 14.8% / booster-fun rest; s13 foil (C 49.5 / U 40.5 / R 6 / M 1.2); s14 land (dual 43.6%); s15 token.
- Per-pack expectation (normalized model, DEC-926 sim, closed form): C 6.74, U 4.94, R+M 1.32, land 1, of which common duals 0.545. Six packs: ~40 C / ~30 U / ~8 R+M / 6 lands (~3.3 duals). **Dual-rate correction (self-review 2026-09-23):** WotC's land slot is default basic 14.6% + 3.6% foil, tower basic 21.8% + 5.5% foil, common dual 43.6% + 10.9% foil. My first model used 0.436, the non-foil duals only; a foil dual is still a dual, so the rate is 0.545. Cross-checked against taw/magic-search-engine PR #636 (duals weighted 30/55 = 54.5%). Uncommons ≈ 1/3 of pool. My first figure of U 4.81 multiplied the raw published slot weights (which sum to 0.97–0.972 on slots 8, 9–11, 13) without renormalizing each slot; corrected 2026-09-23 per the CEO ruling on DEC-926.
- Mechanics (oracle text, case-insensitive): Surveil 47 cards, Empower Jace 35 (11 C / 15 U / 7 R / 2 M), Prepared 24 (21 `prepare` layout DFCs), Threshold 5, Prowess 9, basic landcycling 5 commons. 77 cards mention "planeswalker". 10 common duals: "enters tapped unless you control a planeswalker".
- Two-color uncommons: 25 (each of 10 pairs has 2–3). Ally pairs: Fatehold WU, Theorix UB, Stingerquill BR, Konstrari RG, Vigorbloom GW (each has a Charm + a prepared DFC + one more). Enemy pairs: BW Twisted Fates/Edgar, GU Mind Meanderer/Kiora, RU Clash of Elements/Saheeli, RW Warrior's Blades/Mabel, BG Primal Witchstalker/Hapatra.
- Planeswalker cards: 8 (Jace Reality Sculptor rare; rest mythic).
- Echoed pairs: WotC 86 cards = 43 pairs. Scryfall watermark `echoverse`/`desparked` on 46 cards. First-name+rarity match pairs 33; 13 unmatched (name differs) + "Way of the ..." cycle multi-matches. Needs a manual pair table.
- Rough removal regex at C+U by color: B 6, R 6, W 5, U 4, G 3. limitedmtg.com (all rarities): B 14 / R 11 / W 7 / U 5 / G 5. Same order. Final graded removal (creature/PW answers only, mono-colour): B 12 (3 C / 4 U / 5 R+M), R 8 (3/3/2), W 7 (2/3/2), G 4 (2/2/0), U 2 (1/1/0).
- Toughness census (front faces, 159 creatures): 48% toughness <=2, 68% <=3, 87% <=4, 94% <=5. Confirms limitedmtg's '3 damage kills 68%'.
- Third-party collation cross-check (taw/magic-search-engine PR #636, fetched via gh 2026-09-23): SPG 1/55 per pack, common/uncommon slot 23/77, rare:mythic 2:1 per card (R 83.3% / M 16.7%), foil slot excludes the duals, echoed pairs weighted per pair U 5 : R 2 : M 1 with the third card drawn from the OTHER pairs (our model draws it independently and may duplicate a half: differs in ~2% of packs, ignored). All consistent with our config except the dual rate above.
- Scryfall has no rulings yet for `prepared` or `empower Jace` (checked 2026-09-23); the cheat sheet relies on the reminder text only.
- Second reviewer used in the self-review: Limited Resources 872 (commons and uncommons, YouTube mLABrUxyTKw, auto-captions). MTG Arena Zone reviews are behind a JavaScript check and could not be fetched.

## Lessons
- Slot percentages that list foil and non-foil versions of the same card class must be summed: the 43.6% figure was the non-foil duals only. Read the whole slot description before taking one number.
- First Empower Jace count was 16: case-sensitive search. Reminder text uses lowercase "empower Jace". Always regex case-insensitive on oracle text.

## Unverified / assumptions
- Prerelease promo pool (assumed 1 date-stamped R/M from the set) — not on WotC or WPN pages.
- Special Guests: 10-card panorama, 1/55 packs — negligible for planning.
- External grades (Draftsim 0–10, limitedmtg) are priors only until cross-checked against oracle text.
