# DEC-949 — Cards assessment (2026-10-08)

Board question: should we consider Curse-Marred Demon, Samut (Tyrant of Naktamun), Bloodline Recollector and Hall of Echoes for any deck?

Method: Scryfall oracle + rulings for all four cards (FRA, all Commander-legal); fleet scan of 21 decks for colour identity, archetype, sacrifice/death density, instant-sorcery density, legendary-Wizard count, colourless-land count; Combo Lab artifacts for cut-candidate embedding; `manabase_check.py` for the two Hall of Echoes homes; in-memory `compute_deck_metrics` projection for the three proposed lines (no files written). None of the four is owned (`priv_data/Owned.csv`: 0 copies). Price is information only.

## Verdict

Two cards earn a slot, two do not.

- [ ] **A — titan-convergence: +Hall of Echoes / −Wastes (13 → 12).** Recommended.
- [ ] **B — grave-dividends: +Bloodline Recollector // Ancestral Craving / −Plumb the Forbidden.** Recommended.
- [ ] **C — eternal-harvest: +Hall of Echoes / −Swamp (5 → 4).** Optional; ranked below A.
- Samut, Tyrant of Naktamun: no slot. Reject for gandalf-party-guest (breaks its own combos); defer for tidal-legion and exponential-growth.
- Curse-Marred Demon: no slot. Reject in every red deck; low-priority defer for gathering-shadow and broodfire-hatchery.

## Card 1 — Hall of Echoes

Oracle (FRA 179): Land. `{T}: Add {C}.` `{5}: This land becomes a copy of target creature you control until end of turn. The "legend rule" doesn't apply to permanents you control this turn.`

Rulings that matter (Scryfall, 2026-08-21): the copy does not enter the battlefield, so "when this enters" abilities never fire; both effects expire together, so no legend-rule window opens; counters and attachments are not copied.

What it is good at: for five generic mana it makes a temporary second copy of a static or end-step engine. It is a land, so it dodges creature removal until activated, and it is repeatable.

### A — titan-convergence (colourless, B4-, 39 lands, 13 Wastes)

Copy Zhulodok, Void Gorger in main phase 1, then cast a colourless spell with mana value 7 or more from hand. Two instances of Zhulodok's grant give the spell four cascade triggers. Zhulodok's ruling: "Each instance of cascade triggers and resolves separately." The deck already runs Mirrorpool (one-shot token copy for `{4}{C}` plus the land) and Thespian's Stage, so the pattern is in-deck; Hall is the repeatable version.

Cost of the play: 5 generic for Hall plus 7 or more for the spell, 12 mana on one turn. The deck's Tron, Ancient Tomb and Eldrazi Temple reach that on turn 6 to 8. Caution: Eldrazi Temple and Shrine of the Forsaken Gods restrict their extra mana to colourless spells, so they cannot pay Hall's `{5}`.

Cut: one Wastes (13 → 12). Wayfarer's Bauble is the only basic fetcher and 12 targets remain. The Extraplanar Lens highlight says "10+ Wastes"; 12 keeps it true. Hall taps for `{C}` exactly like Wastes, so no mana loss.

Risk: while animated the land is a 7/4 creature; creature removal in response costs a land. Activate only when the cascade spell is ready to cast.

Projection (in-memory, no files written): global_health 65 → 65; gaps unchanged (card-draw 2/10, removal-spot 4/8, removal-board 2/3, recursion 2/3). Hall does not address a gap. It raises the ceiling, which is what the DEC-369 bar asks of a 4- deck.

### C — eternal-harvest (BG, B4, 35 lands, 5 Swamp)

Copy Meren of Clan Nel Toth in main phase 2. At the beginning of the end step both Merens trigger. Experience counters belong to the player, so the copy reanimates with the same threshold. Copying Drivnod instead makes every death trigger fire three times for the turn.

Manabase after the cut: Karsten B 25.1/20, G 22.0/16 (current B 26.1/20). Land count stays 35. Fourth colourless land in a 68-B-pip deck; passes.

Why ranked below A: DEC-947 closed on 2026-10-07 with no card swap and the counter reset; this line restarts the counter at 1. The deck has no gaps (global 87 → 87 in projection). It is a ceiling add, not a repair.

### Other decks (defer or reject)

- the-white-forge (mono W): copy Gandalf the White. Two copies of "triggers an additional time" make three triggers per flicker. Defer to the deck's next review; needs a flicker-turn to matter.
- tidal-legion (mono U): copy Namor. Two token triggers per blue spell for the turn. Defer; five mana on the storm turn is heavy, and the deck is at the 3-GC B3+ cap (Hall is not a GC, but the cap note stands for any later line).
- broodfire-hatchery (RGW, 9 colourless lands): copy Atla Palani doubles egg flips. Defer; DEC-935 is closed and the deck already carries nine colourless lands in three colours.
- creeping-corruption (WUBG, 14 colourless lands): second proliferate at end step. Reject on manabase; a 15th colourless land in four colours.
- eternal-agony: Valgavoth's trigger fires on opponents' turns; the copy ends on ours. Reject.
- hidden-legion, slivers (five colours): reject on manabase.
- zada-hedron-grinder: a second Zada adds no copies (each trigger needs the spell to target only that Zada). Reject.
- Remaining decks: no engine worth five mana per turn. Reject.

## Card 2 — Bloodline Recollector // Ancestral Craving

Oracle (FRA 49): `{1}{B}` Creature — Vampire Warlock 2/2. `At the beginning of each end step, if three or more creatures died this turn, this creature becomes prepared.` Prepare spell Ancestral Craving `{B}` Instant: `Target player draws three cards and loses 3 life.`

Rulings: one copy in exile per preparation; casting it unprepares; it can be prepared again at a later end step. Casting the copy is a real cast (magecraft and cast triggers fire).

Trigger frequency (DEC-477): the check happens at each end step, four per turn cycle. Creatures of any player count, tokens included. A board wipe on an opponent's turn prepares it; the copy is an instant, so it can be cast on that same opponent's turn.

Uptime: the sim has no deaths-per-turn metric, so I cannot quote a percentage. The enabling condition is three deaths in one turn. grave-dividends has Bartolomé as a free instant-speed outlet in the command zone plus seven more outlets in the 99 and recursive fodder (Reassembling Skeleton, Undead Butler, Stitcher's Supplier, Kaya's Ghostform). On any turn with the commander and three bodies, the condition is met at will. The Prepared policy (SOS, DEC-reference) models it as a front-face one-shot in the sim, so the sim will under-read it.

### B — grave-dividends (WB, B4, gaps: card-draw 5/10, ramp 5.5/10, protection 2.5/4, wincon 0.5/1)

Fit: the deck's card-draw gap is the largest role gap. Recollector is a 2-mana body (sac fodder for Bartolomé between preparations), returns with Sun Titan (MV 2 ≤ 3), Living Death and Volrath's Stronghold, and pays three cards for `{B}` each time it prepares. Three life per cast is the deck's normal currency (Reanimate, Dark Prophecy, Deadly Dispute, Black Market Connections).

Cut: Plumb the Forbidden. It is a one-shot instant (sacrifice X, draw X, lose X). Combo Lab usage: 0 included combos, 0 Tier B loops. Carrion Feeder and Umbral Collar Zealot were the other candidates; both are embedded (Carrion Feeder in 33 included combos and 128 Tier B mentions, Zealot in 28 and 164), so neither is a clean cut. Plumb appears in `guideContent.strategyOverview` and the Card Draw category; the apply step edits that prose.

Projection (in-memory, no files written): global_health 89 → 89; gaps unchanged (role tags card-draw → card-draw). The gap stays at 5.0/10 by weight because one draw card replaces one draw card; the quality change is the repeatable draw.

### Other decks

- eternal-harvest (14 outlets, Meren returns it): strong fit. First deferred because DEC-947 found 12 draw cards and no gap. The board asked on 2026-10-08 whether it fits; answer yes, promoted to **line D: +Bloodline Recollector // Ancestral Craving / −Plumb the Forbidden**. Plumb has 0 Combo Lab uses here and three prose references (strategy overview, Card Draw category, one highlight). Projection: global 87 → 87, normalized 91 → 91, components and gaps unchanged. Timing note: the three-deaths check is at the beginning of the end step; cast the Craving before sacrificing Recollector, because the exiled copy exists only while it stays on the battlefield prepared. B and D are independent.
- witherbloom-the-balancer (8 outlets, B3): fits the aristocrats half; defer, no clean cut identified this round.
- hoard-and-bleed (6 outlets, treasure fodder): deaths are fewer because the fodder is artifacts. Defer.
- eternal-agony (3 outlets): reject; three deaths per turn is not the deck's pattern.

## Card 3 — Samut, Tyrant of Naktamun

Oracle (FRA 220): `{1}{U}` Legendary Creature — Human Wizard 2/1. `Instant and sorcery spells you control have split second.`

Rulings: split second does not stop triggered abilities, but "if the resolution of a triggered ability involves casting a spell, that spell can't be cast if a spell with split second is on the stack."

### gandalf-party-guest — reject

On paper the fit is perfect: a 2-mana legendary Wizard (+2 to Gandalf's X) in a deck with 18 legendary Wizards and 26 instants and sorceries. In play it breaks the deck's own win lines. Every Dualcaster Mage and Naru Meha line needs the flash creature cast while your own instant or sorcery is on the stack. With Samut on the battlefield that spell has split second, so you cannot cast Dualcaster or Naru in response to it. Combo Lab lines that stop working: Dualcaster Mage + Twinflame, + Ghostly Flicker, + Displace, + Sublime Epiphany; Naru Meha + Ghostly Flicker, + Displace, + Twinflame, + Sublime Epiphany. Fury Storm lines (+ Storm-Kiln Artist, + Archmage Emeritus, + Deekah) can only target an opponent's spell because you cannot cast Fury Storm while your own split-second spell is on the stack. Narset's Reversal on your own spell stops working for the same reason. I did not check the two Ghostly Flicker + Pinnacle Monk lines. Eight of thirteen included combos die and three more lose their self-targeting mode. There is no sacrifice outlet in the 99 to turn Samut off.

### Other decks

- tidal-legion (36 instants and sorceries): the upside is counter-proof token spells. The cost is a non-Merfolk 2/1 that does not add to Namor's power or make tokens. Defer; the DEC-467 vision is spell density, and the deck's creature slots are Merfolk lords.
- exponential-growth (X spells): protects Zimone's X spell from counters; Unbound Flourishing still copies (triggered). Defer; no clean cut, 2/1 body off-plan.
- armory-protocol, shield-doctrine, creeping-corruption, gathering-shadow, hidden-legion, slivers: no engine that wants split second. Reject.

## Card 4 — Curse-Marred Demon

Oracle (FRA 79): `{2}{R}{R}` Creature — Demon 4/4, flying, trample. `When this creature enters, search your library for a card, put it into your hand, shuffle, then discard a card at random.`

Discard math: with n cards in hand after the search, the tutored card is the random discard with probability 1/n. At four cards in hand that is 25 percent; at two cards it is 50 percent.

- eternal-agony (BR, B4): five tutors already (Demonic, Vampiric, Grim, Diabolic Intent, Beseech). The 4-drop slot holds Sheoldred, Solphim, Mogis, Crypt Ghast, Bloodletter. A 4-mana tutor with a one-in-n discard tax ranks below all five incumbents, and the body does not advance the group-slug plan. Reject.
- hoard-and-bleed (BR, B4-): four tutors; the body is not an artifact and does not feed Smaug. Reject.
- gathering-shadow (UBR, B4-): three tutors; the random discard is cheap under Sauron's "discard your hand, draw four", and a 4/4 flying trampler is real pressure. Low-priority defer; the 4-drop slot is full of Orc engines.
- broodfire-hatchery (RGW): an Atla flip into the Demon tutors any card. But a 4/4 dilutes a flip pool built for titans, and DEC-935 is closed. Low-priority defer.
- zada-hedron-grinder, stampede-acres, armory-protocol, shield-doctrine, gandalf-party-guest: off-plan. Reject.

## Apply plan (only after per-line acceptance)

Per accepted line: edit `decklist` (roles: Hall of Echoes `land`; Recollector `card-draw`/`utility`), edit affected prose (grave-dividends strategy overview and Card Draw category for Plumb), `validate_deck_json`, `refresh_card_pool`, metrics, sim (add the new cards to `card-metadata.json`; Recollector modelled front-face one-shot per the Prepared policy; Hall of Echoes as a colourless land), Combo Lab ×3 (`sync_spellbook_combos`, `build_synergy_candidates`, `build_tier_b_candidates`), `check_kb_coverage` first for the new cards, loader cache bump, commit, push. Trigger-2 counters: eternal-harvest restarts at 1 if C is accepted.
