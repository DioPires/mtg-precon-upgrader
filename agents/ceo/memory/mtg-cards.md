# MTG Card Facts

Verified card text and rulings discovered during deck analysis sessions.

---

### Selfless Safewright
`{3}{G}{G}`, Flash, Convoke — 4/2 Elf Warrior. ETB: choose a creature type; other permanents you control of that type gain hexproof and indestructible until EOT. From Edge of Eternities Commander ("ecl"). Mono-G, legal in Eladamri and any green commander.

Key interactions: triggers elf-tribal payoffs, convoke-free with 5 elves in play, functions as a Heroic Intervention variant on a body without replacing Heroic Intervention itself.
- Source: session 2e15722f, 2026-05-15

---

### Apex Altisaur (ETB Enrage Chain)
10/10 body, ETB Enrage chain can remove 2–4 opponent creatures. Do NOT cut from ramp-heavy green Elf tribal decks (e.g., Verdant Tide / Eladamri). Fills a removal role no other card in those decks provides.

Board pushback confirmed: keep over slower finishers like Worldspine Wurm.
- Source: session 2e15722f, 2026-05-15

---

### Ohran Frostfang — Deathtouch Scope
Ohran Frostfang grants deathtouch only to **attacking** creatures (combat-phase only). It does NOT apply to ETB-fight chains such as Apex Altisaur's Enrage trigger. Don't assume deathtouch boosts ETB-fight interactions.
- Source: session 2e15722f, 2026-05-15

---

### Sword of the Animist — Reliable Cut Candidate
2 CMC equipment with attack-trigger basic land ramp. In green decks already running 14+ other ramp sources (mana dorks, land ramp spells, etc.), Sword of the Animist is the weakest ramp piece and a safe cut when adding a higher-impact card.

Confirmed cut for Verdant Tide (Eladamri) when adding Selfless Safewright.
- Source: session 2e15722f, 2026-05-15

---

### Parting Gust — Flicker/Exile Assessment
Modal flicker+exile effect. B+ tier but adds **redundancy** (not gap-filling) in The White Forge (Gandalf, artifact flicker strategy) which already has 5 flicker effects + Ephemerate. Ephemerate (`{W}` + rebound) dominates it for pure value flickers.

Verdict for The White Forge: Skip unless the deck has a real gap (health 85, zero gaps = skip).
- Source: session 53ec6176, 2026-05-15

---

### Backlash — "Source You Control" Damage Ruling
`{1}{B}{R}` instant MV 3: tap target untapped creature; that creature deals damage equal to its power to its controller. The damage source is the **opponent's creature**, not a source you control. "Source you control" damage multipliers (Solphim, Fiery Emancipation, Twinflame Tyrant) do NOT apply. Only effects that modify life loss (Wound Reflection) apply. At 3 mana for a non-kill tap+ping, loses to existing removal in B/R decks (Bedevil, Bitter Triumph, Infernal Grasp, Deadly Rollick, Fire Covenant).
- Source: session b5a8d370, 2026-05-18

---

### Hall of Storm Giants — Color Identity Bug
Hall of Storm Giants has **blue** color identity `{U}` — it is NOT a colorless land. Illegal in any deck without blue in the commander's color identity (e.g., mono-R Norin the Wary). Verify land color identities via Scryfall; utility lands often have hidden colored activation costs.
- Source: session 9da924f4, 2026-05-18

---

### Theater of Horrors — Color Identity Bug
Theater of Horrors has `{B,R}` color identity — **not** mono-R legal. The card has a black mana symbol in its oracle text that makes it a Rakdos CI card. Illegal in mono-R decks.
- Source: session 9da924f4, 2026-05-18

---

### Hidden Stockpile — Color Identity Bug (Witherbloom)
Hidden Stockpile has `{W,B}` color identity — the `{W}` in its Revolt activation makes it illegal in BG (Witherbloom) decks. The project's `validate_deck_json.py` validator does NOT catch color identity violations. Mandatory cut from any non-white deck.
- Source: session 9d8c30ab, 2026-05-18

---

### Underworld Breach — Game Changer
Underworld Breach is on the official Game Changers list. Illegal in Bracket 3 no-GC builds. Replacement: Past in Flames (similar graveyard recursion, not on GC list).
- Source: session 9da924f4, 2026-05-18

---

### Norin the Wary — Top EDHREC Staples
Commander: Norin the Wary (mono-R ETB-flicker aristocrats). Top EDHREC synergy staples by inclusion %:
- Tome of Legends (85%) — repeatable draw on commander flicker
- Panharmonicon (80%) — doubles all ETB triggers
- Torbran, Thane of Red Fell (79%) — +2 damage from red sources
- War Room — colorless draw for mono-color
- Kher Keep — repeatable 0/1 Kobold token generator (ETB fodder)

These are must-consider for any Norin build; all are Bracket 3-legal (not on GC list).
- Source: session 9da924f4, 2026-05-18

---

### Norin the Wary — Damage Multiplier Stack Formula
Three non-GC multipliers stack multiplicatively in Norin ETB-aristocrats:
- Torbran, Thane of Red Fell: +2 per red damage source
- Mechanized Warfare: +1 per red damage source
- Fiery Emancipation: ×3 total damage

Result: 1 base damage (Impact Tremors ETB) → ×3 (Fiery Emancipation) → +3 (Torbran+Mechanized) = **12 damage per Norin ETB** with all three in play.
- Source: session 9da924f4, 2026-05-18

---

### Wheel of Fortune — Budget Alternative Cards
Wheel of Fortune is typically €50–100+; too expensive for budget-conscious builds. Functional alternatives for mono-R wheel redundancy:
- Wheel of Misfortune (~€4) — player-bid variant
- Memory Jar (~€5) — exile hand, draw 7 for one turn
- Reforge the Soul — miracle cost potential
- Magus of the Wheel — creature body version
- Cathartic Reunion / Wild Guess — loot (discard first)

- Source: session 9da924f4, 2026-05-18

---

### Changeling Omnitype Mechanic
Changelings have ALL creature types simultaneously (Rules 702.73). Practical implications:
- Trigger every tribal payoff at once: Elves, Slivers, Elementals, Dragons, Wolves, Daleks, etc.
- Risen Reef (Elemental ETB) → draws a card on every changeling ETB
- Manaweft Sliver / Cloudshredder Sliver (Sliver payoffs) → changelings get those abilities
- Dragon Tempest / Ur-Dragon Eminence → changelings are Dragons on the stack + battlefield
- Exterminate! → changelings are Daleks
- Voja, Jaws of the Conclave → changelings are both Elves and Wolves
- Source: sessions c56eeeb6, e82508b9; 2026-05-19, 2026-05-20

---

### Ur-Dragon Eminence + Changeling Cost Reduction
Ur-Dragon reduces the cost of Dragon spells by {1} from the command zone. Because changelings are all creature types including Dragon, every changeling creature spell gets the {1} discount. With Morophon the Boundless naming Dragon: Dragon-typed spells cost {WUBRG} less — many changelings effectively cast for free. Nameless Inversion (Kindred Instant — Shapeshifter) is also Dragon-typed on the stack as a changeling and costs {B} (not {1B}) with Eminence active.
- Source: session e82508b9, 2026-05-20

---

### Stinging Study — Ur-Dragon Mass Draw
`{4}{B}` instant: draw X cards / lose X life where X = commander's mana value. With Ur-Dragon at MV 9: draws 9 for 5 mana at the cost of 9 life. Commander MV is constant regardless of zone (command zone or battlefield). Engine-independent — works even from empty board. Pairs with Patriarch's Bidding as a 2-card wipe-recovery package (Bidding refills board, Study refills hand).
- Source: session e82508b9, 2026-05-20

---

### Bloodline Bidding — Does Not Fit Token Aristocrats
`{6}{B}{B}` sorcery (Convoke): choose a creature type; return all creatures of that type from YOUR graveyard to battlefield. Fails in token-heavy aristocrats decks because:
1. Tokens don't go to graveyard when they die — invisible to Bidding
2. Low tribal density in hybrid decks (top type ~7 creatures) → 3-5 returns mid-game
3. Strictly worse than Living Death (already in most builds) which returns ALL types
4. Affinity math doesn't rescue it when most cheap creatures are unreturnable tokens
In Witherbloom Balance specifically: Faerie/Snake/Spawn/Saproling/Plant/Citizen/Insect tokens are all unreturnable. Verdict: skip.
- Source: session e2ac880e, 2026-05-19

---

### Tendershoot Dryad — Correct Oracle Text
**2/2** creature (no Reach). Oracle: "Ascend (if you control 10+ permanents, you get the city's blessing for the rest of the game). At the beginning of each upkeep, create a **1/1 green Saproling** creature token. Saprolings you control get **+2/+2** as long as you have the city's blessing." The token generation is **unconditional** (every upkeep, no city's blessing required). Agent previously misquoted as "Reach, conditional tokens, +1/+1" — all wrong.
- Source: session bd142394, 2026-05-19

---

### Ghalta Name Variants — Don't Confuse Them
The deck Verdant Tide (Eladamri) contains **Ghalta, Stampede Tyrant** — not Ghalta, Primal Hunger. They are completely different cards:
- **Ghalta, Stampede Tyrant** (`{6}{G}{G}`, flat 8 CMC): ETB cheats creatures from hand onto battlefield. Value engine in creature-heavy decks.
- **Ghalta, Primal Hunger** (`{10}{G}{G}`, cost-reduced by total power): vanilla 12/12 Trample. No ETB. Purely a beatstick.
Always verify WHICH Ghalta is in a deck before analyzing interactions. Same pattern applies to all cards with multiple same-name variants (e.g., different Elspeth, Liliana, Jace versions).
- Source: session bd142394, 2026-05-19

---

### Unnatural Growth — Affects ALL Creatures
`{1}{G}{G}{G}{G}` enchantment: "At the beginning of each combat, double the power and toughness of each creature you control until end of turn." Note: in Verdant Tide with Ghalta, Stampede Tyrant, Unnatural Growth doubles Stampede Tyrant to 24/24 trample on swing AND doubles all creatures it cheats into play via its ETB trigger. This is a genuine synergy (not a "makes Ghalta cheaper" effect, which would be the wrong Ghalta). Downside: does not apply to opponents' creatures being blocked or after blockers declared.
- Source: session bd142394, 2026-05-19

---

### Llanowar Tribe — Ranking vs. 3-CMC Alternatives
For non-attacking decks (e.g., Verdant Tide / Eladamri), 3-CMC mana dork ranking: **Llanowar Tribe > Joraga Treespeaker > Fyndhorn Elves**.
- Llanowar Tribe (`{G}{G}{G}`, 3/3): taps for {G}{G}{G} → highest net mana T1–T7; 3/3 body has defensive value; GGG pip enables cards requiring multiple green pips (e.g., Unnatural Growth {1GGGG})
- Joraga Treespeaker (1/1, level up): ceiling ~{GGG} but rarely reaches L5 in a kill-by-T6 deck; Elf subtype wins on Eladamri trigger count
- Fyndhorn Elves (1/1): 4th vanilla 1-G dork — pure redundancy in a deck already running Llanowar Elves, Elvish Mystic, Arbor Elf
Badgermole Cub is **2 CMC** (not 3), so does not compete in the 3-drop slot.
- Source: sessions bd142394; 2026-05-19

---

### Pattern of Rebirth — Reactive Without Sac Outlet
`{G}` aura on a creature: when enchanted creature dies, search your library for any creature card and put it onto the battlefield. In Verdant Tide (Eladamri), the deck had **no creature sac outlet** at time of assessment — Pattern becomes fully reactive, waiting for opponent removal or a board wipe. Aura is also vulnerable to exile removal (creature exiled instead of dying = no trigger). Useful in decks with a free sac outlet (e.g., Phyrexian Altar) but only a defensive reactive tool otherwise. Rank: below Unnatural Growth for impact in Verdant Tide.
- Source: session bd142394, 2026-05-19
