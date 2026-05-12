# MTG Domain Knowledge

### Walking Ballista + Mikaeus is NOT Infinite Direct Damage
Walking Ballista + Mikaeus is a **3-piece combo** (Ballista + Mikaeus + any sac outlet for first death). Ballista can only ping itself to loop via undying — pinging opponents leaves it alive as a 1/1. After the first death it self-sustains by removing counters to ping itself. The deck's 6+ death payoffs (Blood Artist, Zulaport, Bastion, Grave Pact, Haruspex, Altar of Dementia) convert the infinite loop into a win. Commander Spellbook lists it as a 2-card combo because the sac outlet is a generic prerequisite.
- Source: session 594ee133, 2026-03-17

### Triskelion + Mikaeus IS Self-Contained Infinite Direct Damage
Triskelion enters with its own 3 counters + 1 undying counter = 4 total (plus Mikaeus buff). Remove 2 counters → deal 2 to opponent, remove 2 counters → deal 2 to itself → dies → undying returns it. Each loop deals 2 damage to opponents. No additional pieces required. Unlike Walking Ballista, this is a true 2-card win.
- Source: session 594ee133, 2026-03-17

### Persist + Mikaeus Undying Loop Mechanic
Persist creatures return with a -1/-1 counter; Mikaeus gives non-Human creatures undying (+1/+1 counter on return). When both apply, the +1/+1 and -1/-1 counters cancel out — the creature returns clean every time. This creates an infinite death loop with any sac outlet. Decks running Mikaeus with sac outlets should evaluate adding persist creatures to complete this engine.
- Source: session 594ee133, 2026-03-17

### Dredge Competes With Draw Engines
Dredge replaces your draw step — it conflicts directly with draw engines like Yawgmoth, Skullclamp, Grim Haruspex, and Greater Good. In decks saturated with these, you almost never want to dredge. Prefer graveyard-filling that doesn't replace draws (Buried Alive, Entomb, Stitcher's Supplier) over dredge creatures.
- Source: session 594ee133, 2026-03-17

### Gravecrawler Requires a Zombie on Board
Gravecrawler can only be cast from the graveyard if you control a Zombie. In Meren or similar decks, Carrion Feeder (itself a Zombie) fills this prerequisite — Spellbook's `notable_prerequisites` confirms this requirement.
- Source: session 594ee133, 2026-03-17

### Urza, Lord High Artificer CMC is 4 (not 5)
Urza costs `{2}{U}{U}` = CMC **4**. This affects simulation castability targets (on-curve at T4), commander tax calculations, and mana base planning. Previously documented as CMC 5 in error.
- Source: session c566e4f7, 2026-03-17

### Extraplanar Lens + Snow-Covered Islands Asymmetry
Extraplanar Lens checks the **exact card name**. Exile "Snow-Covered Island" → only lands named "Snow-Covered Island" get doubled mana. Opponents running regular "Island" receive no benefit. "Island" and "Snow-Covered Island" are both basic lands that tap for {U} but have different names, making this fully asymmetric if opponents don't run snow basics.
- Source: session b4001091, 2026-03-17

### Basalt Monolith + Rings of Brighthearth Loop
Basalt Monolith's untap ability (`{3}: Untap`) is NOT a mana ability — Rings of Brighthearth can copy it. Loop nets +1 colorless per iteration and requires 2 extra mana (from any other source) to bootstrap. The colorless mana produced feeds Urza's `{5}` activation to exile and free-cast cards from the library.
- Source: session b4001091, 2026-03-17

### Urza Stax Parity-Breaking
Tap Winter Orb, Static Orb, or Tangle Wire with Urza's second ability for `{U}` **before your untap step** — this turns off their restriction for your turn while opponents remain locked. Every stax piece effectively becomes a Mox Sapphire when Urza is on board.
- Source: session b4001091, 2026-03-17

### Polymorph / Proteus Staff Creature Constraint
For reliable Polymorph/Proteus Staff lines, the deck must contain **exactly the intended targets** as creatures. If you add additional creatures (Deadeye Navigator, tutors like Tribute Mage, etc.), you risk hitting them instead of Tidespout Tyrant or Hullbreaker Horror. Non-creature support cards (Conjurer's Closet, Lightning Greaves, tutors) don't interfere.
- Source: session b4001091, 2026-03-17

### Shorikai Is a Vehicle, Not a Creature
Shorikai, Genesis Engine is a Legendary Artifact — Vehicle. It is NOT a creature when not crewed: it dodges creature removal, summoning sickness, and Cursed Totem. Its `{1}, {T}` activated ability works on the Vehicle without crewing. Taps immediately on cast. Pilots crew as power 3 (not 1); under Humility they crew as power 1, requiring 8 Pilots to reach crew 8.
- Source: session b4001091, 2026-03-17

### Humility + Crewing Interaction
Under Humility, all creatures become 1/1 with no abilities. Pilot tokens lose their "crews as though its power were 2 greater" bonus and crew as power 1. You'd need 8 Pilot tokens to reach crew 8 for Shorikai. If crewed under Humility, Shorikai becomes a 1/1 creature with no abilities. Generally: don't crew under Humility — use Shorikai purely as a draw engine.
- Source: session b4001091, 2026-03-17

### Elspeth, Storm Slayer Doubles All Token Creation
Elspeth, Storm Slayer's static ability doubles ALL tokens created under your control. With Shorikai, each activation makes 2 Pilots instead of 1. Stacks with White Sun's Twilight, Martial Coup, and any other token-producing effects. Unaffected by Humility (planeswalker, not a creature).
- Source: session b4001091, 2026-03-17

### Simulacrum Synthesizer Token Threshold
Simulacrum Synthesizer needs ~8-10 artifacts at MV 3+ in the deck to be consistently worth a slot. At that density you trigger it 2-4 times per game. Below ~6-7 triggers per game it's marginal. Excels when combined with blink/flicker effects or artifact recursion that replay the same 3+ MV artifacts.
- Source: session b4001091, 2026-03-17

### Back to Basics: Which Nonbasics Are Unaffected
Under Back to Basics (nonbasic lands don't untap), these land types are largely unaffected:
- **Fetch lands** — sac immediately, never need to untap
- **Artifact lands** (Seat of the Synod, Darksteel Citadel) — Urza taps them for `{U}` as artifacts, and Unwinding Clock untaps all artifacts on each opponent's turn
- **Channel lands** (Otawara) — channel from hand, never need to be on the battlefield
- **Sagas** (Urza's Saga) — progress via lore counters, not tapping; Chapter III tutor is the primary value
- **One-shot ETB lands** (Mystic Sanctuary) — value already realized on entry
Truly hurt: Academy Ruins, Inventors' Fair (activated abilities locked), Ancient Tomb (after early game), Reliquary Tower.
- Source: session b4001091, 2026-03-17

### Copy Artifact Counts as an Artifact on the Battlefield
Copy Artifact (`{1}{U}`) enters as both an enchantment and an artifact (it is a copy of the target artifact). On the battlefield it functions as an artifact — Urza can tap it for `{U}`, it contributes to artifact count for Construct tokens and affinity costs. When replacing a tutor like Transmute Artifact, Copy Artifact fills a different role (clones best artifact in play vs. finding a specific one) but provides a net improvement as an Urza tap target.
- Source: session f4a29b04, 2026-03-17

### Rest in Peace Anti-Synergy Cards
Under Rest in Peace (cards go to exile instead of graveyard):
- **Delve cards** (Dig Through Time) — delve never functions, effectively uncastable
- **Graveyard-targeting lands** (Mystic Sanctuary) — ETB ability dead since graveyard is always empty
- **Graveyard recursion** (Sevinne's Reclamation) — never finds targets
- **Skullclamp** — token deaths still trigger equip draw, but tokens exiled not dead. VERIFY: tokens still draw because Skullclamp's trigger is "when equipped creature dies" — check if exile-as-death counts
- **Dredge** — always replaced by exile, never works
Deploy Rest in Peace after using Skullclamp or before you no longer need graveyard recursion.
- Source: session c566e4f7, 2026-03-17

### Swan Song Requires Timetwister to Loop
Swan Song is a 1-mana counterspell that creates a 2/2 Bird token for the opponent. It does NOT generate recurring value on its own and cannot be used as a win condition without Timetwister to loop it. Documented as a "swan song loop" win con in some sources, but that requires Timetwister in the deck.
- Source: session c566e4f7, 2026-03-17

### Leonardo (Mutant Multiplication) Once-Per-Turn Rule
Leonardo's counter-spreading ability says "Do this only once each turn." With 6 creatures in play, Leonardo puts 6 total counters on your board per turn — not 6 per token ETB. Previously misread as triggering per token (would have been 15+ counters per token-creation turn).
- Source: session 38d5d3ef, 2026-03-18

### Donatello (Mutant Multiplication) Singular Mutagen Per Event
Donatello is a replacement effect that adds exactly **1 Mutagen token per token-creation event**, regardless of how many tokens are created in that batch. Voice of Victory Mobilize 2 creates 2 Warriors (one event) → Donatello adds 1 Mutagen = 3 tokens total, not 4.
- Source: session 38d5d3ef, 2026-03-18

### Caretaker's Talent Once-Per-Turn Limit
Caretaker's Talent card draw triggers "only once each turn." Tireless Provisioner + Academy Manufactor creating 3 token types per landfall does NOT chain 3 Talent triggers — still only 1 draw per turn. Aura Shards has no such limit (triggers per artifact/enchantment entering).
- Source: session 38d5d3ef, 2026-03-18

### Twilight Diviner Is Reanimation Payoff, Not Card Draw
Twilight Diviner (ETB surveil 2, then copies creatures entering from graveyard once/turn) is a reanimation payoff, not a card draw piece. Categorizing it as "Card Advantage" is correct but it should not be listed alongside Skullclamp/Grim Haruspex/Greater Good as draw sources.
- Source: session 9605b2a1, 2026-03-18

### Formidable Speaker > Fauna Shaman in Meren
In a Meren deck, Formidable Speaker's ETB tutor is strictly better than Fauna Shaman's tap activation: ETB triggers immediately (no summoning sickness), Meren reanimating it = free creature tutor every end step, and it discards ANY card (not just creatures). Fauna Shaman's advantage is repeatability without dying — irrelevant when Meren is on board.
- Source: session 9605b2a1, 2026-03-18

### Umbral Collar Zealot > Grim Haruspex in Meren
In Meren, Umbral Collar Zealot (active sac outlet: {1},{T}: sac creature/artifact → surveil 1) outvalues Grim Haruspex (passive: draw when non-token creature dies). Zealot generates Meren XP, enables Grave Pact, controls when sacrifice happens. Haruspex is passive and needs OTHER sac outlets to trigger. Being a sac outlet matters more than redundant passive draw in a deck with Skullclamp/Greater Good/Yawgmoth.
- Source: session 9605b2a1, 2026-03-18

### Teferi Who Slows the Sunset vs Unwinding Clock
In an artifact-heavy deck, Unwinding Clock strictly outclasses Teferi, Who Slows the Sunset at the untap role: Clock untaps ALL artifacts on EACH opponent's untap step (3× per turn cycle in a pod), Teferi untaps ONE artifact on YOUR turn only. If Unwinding Clock is already in the deck, Teferi's +1 untap synergy is fully redundant.
- Source: session e811faa3, 2026-03-18

### Force of Will / Force of Negation Pitch Target Threshold
FoW and FoN need 12+ blue cards in the deck to be reliably pitchable. Adding them without sufficient blue cards undermines the package. When upgrading a deck to B4 that wasn't blue-heavy, add blue spells alongside (Rhystic Study, Swan Song, Rapid Hybridization) to reach the threshold. Count existing blue cards first.
- Source: session ccb0e567, 2026-03-18

### Mana Vault Weakness in Multi-Color Decks
Mana Vault produces {C}{C}{C} colorless. In a 3-color deck with no untap effects it's mediocre — can't pay colored mana costs and draws 1 damage per turn without untapping. Chrome Mox is better for colored mana in multi-color: exiles a card to produce a color of your choice, no upkeep cost.
- Source: session ccb0e567, 2026-03-18

### Bracket 3 Cards: Blasphemous Act, Cultivate, Kodama's Reach
Per Command Zone episode 731: Blasphemous Act, Cultivate, and Kodama's Reach are "bracket 3 cards" that should be replaced in B4+ decks. Blasphemous Act → free removal or more efficient wraths. Sorcery ramp → fast mana (Chrome Mox, Ancient Tomb) or 1-2 mana ramp spells (Rampant Growth, Nature's Lore).
- Source: session ccb0e567, 2026-03-18

### Emblems Belong in Tokens Array
Emblems are stored in the `tokens` array of `deck.json`, following the same schema as other tokens. Use `type_line: "Emblem"` (or `"Emblem — CardName"` per Scryfall's exact data). Omit `power`/`toughness` fields. UI handles emblems without code changes — they display like non-creature tokens (image + name + produced_by). Dark Dominion's "The Ring" is the existing precedent.
- Source: session 672b44a9, 2026-03-18

### Commodore Guff: PW Commander Survives Humility
Guff is a planeswalker commander, not a creature — Humility does not affect him. All other Jeskai commander options (Narset, Elsha, Kykar) are creatures that become vanilla 1/1s under Humility, losing their key abilities. This makes Guff uniquely suited as commander for a Humility-based superfriends shell in Jeskai.
- Source: session e1ddc605, 2026-03-19

### Sarkhan the Masterless +1 is Catastrophic Under Humility
Sarkhan's +1 turns all your planeswalkers into 4/4 Dragon creatures until end of turn. Under Humility, those creatures immediately lose ALL abilities — including their loyalty abilities. Your entire planeswalker board becomes useless 1/1s with no loyalty activations. Never activate Sarkhan the Masterless +1 while Humility is in play.
- Source: session e1ddc605, 2026-03-19

### Humility Blanks Deepglow Skate ETB
Deepglow Skate's ETB (double all counters on permanents you control) is a triggered ability. Under Humility, Skate enters as a 1/1 with no abilities — the ETB trigger never fires. It's a dead draw in Humility mode but devastating when Humility isn't out.
- Source: session e1ddc605, 2026-03-19

### Stasis + Smothering Tithe Hard Lock
Stasis prevents all players from untapping; the upkeep cost of {U} keeps it alive. Smothering Tithe generates Treasures when opponents draw, providing mana to pay Stasis upkeep even when your own lands don't untap. Planeswalkers don't need to untap to activate — they generate free value under the lock. Never deploy Stasis without Smothering Tithe or Teferi, Who Slows the Sunset already in play.
- Source: session e1ddc605, 2026-03-19

### Stasis + Teferi, Master of Time: Permanent Phase-Out
Teferi MoT's -3 phases out a target creature. Phased-out permanents normally return during the controller's untap step — but Stasis causes all players to skip their untap steps entirely. Under Stasis, phased-out creatures never return, making Teferi MoT -3 effectively permanent removal.
- Source: session e1ddc605, 2026-03-19

### Teferi, Who Slows the Sunset: Stasis Upkeep Backup
Teferi WStS +1 untaps a land you control. Under Stasis, this lets you pay the {U} upkeep cost to keep Stasis alive even without Smothering Tithe Treasures. Provides redundant insurance for maintaining the Stasis lock.
- Source: session e1ddc605, 2026-03-19

### Puzzle Box + Narset, Parter of Veils Soft Lock
Teferi's Puzzle Box forces each player to put their hand on the bottom of their library at the start of their draw step, then draw that many cards. Narset restricts opponents to drawing 1 card per turn. Combined: opponents shuffle their entire hand away and draw exactly 1 card — they can never accumulate resources. Puzzle Box without Narset is just chaos disruption; Narset must already be out for the lock to function.
- Source: session e1ddc605, 2026-03-19

### Norn's Annex + Humility: Net-Negative Attacks
Norn's Annex requires opponents to pay {W/P}{W/P} (or 2 life) per attacking creature. Under Humility, all creatures are 1/1 with no abilities. An opponent pays 2 life to attack with a 1/1 — net -1 life per attacking creature (pay 2 to deal 1). This makes attacking planeswalkers essentially irrational, stronger than in a typical build where creatures deal more than 1 damage.
- Source: session e1ddc605, 2026-03-19

### High Noon Color Identity is Red-White (Not Just White)
High Noon has a sacrifice clause that costs {4}{R}. This places red in its color identity, making it RW — not mono-white. Relevant when checking color identity legality for non-Jeskai commanders.
- Source: session e1ddc605, 2026-03-19

### Sphere of Safety Explicitly Protects Planeswalkers
Sphere of Safety oracle text reads: "Creatures can't attack you **or planeswalkers you control** unless their controller pays {X} for each creature, where X is the number of enchantments you control." This is explicit — Sphere protects PWs directly, not just you. It scales with enchantment count, making it especially powerful in enchantment-heavy stax shells.
- Source: session e1ddc605, 2026-03-19

### Elspeth Storm Slayer Doubles Smothering Tithe Treasures
Elspeth, Storm Slayer's static doubles ALL tokens created under your control, not just creature tokens. Smothering Tithe creates Treasure tokens. With Storm Slayer in play, every Treasure from Tithe is doubled — significant ramp acceleration in a shell running both enchantments.
- Source: session e1ddc605, 2026-03-19

### Spirit Water Revival + Waterbend in Artifact Decks
Spirit Water Revival is a {1}{U}{U} sorcery: base mode draws 2; Waterbend {6} shuffles graveyard into library, draws 7, removes max hand size. Waterbend is paid by tapping artifacts or creatures. In Urza (Azure Dominion) with 30+ artifacts, hitting 6 tappables by T4-5 is trivial. In Shorikai (Genesis Protocol), RIP anti-synergy undermines the graveyard shuffle clause (graveyard is already exile), and fewer cheap tappables make the cost harder to assemble.
- Source: session 244db025, 2026-03-19

### Mana Base Reliability: Frank Karsten Methodology
Karsten's Monte Carlo method is the gold standard for colored source requirements. Key thresholds to reliably cast spells on curve (91-95% probability): a 1-pip spell on T1 needs 13 sources; double-pip on T2 needs 19 sources; triple-pip needs 24 sources. These numbers account for dual lands that produce multiple colors. Hypergeometric distribution is insufficient when dual lands or conditional untapped lands are involved — Monte Carlo required.
- Source: session b27105d7, 2026-03-21

### Mana Base Metrics: Salubrious Snail Benchmarks
Salubrious Snail is the most rigorous Commander mana base web tool. It computes per-spell Cast Rate and Average Delay, factoring in conditional untapped lands. Benchmark targets: Cast Rate ≥ 90%, Average Delay ≤ 0.3 turns = strong mana base. Cast Rate 80%, Avg Delay 0.6 = needs improvement. These metrics are more actionable than raw source counts for multi-color decks.
- Source: session b27105d7, 2026-03-21

### EDHREC Synergy Score: Definition
EDHREC synergy score = (% of decks with this commander that include the card) − (% of decks in the same color identity that include the card). A +75% synergy means the card is disproportionately played with that specific commander vs. the color identity baseline. This is the most useful signal for "is this card good specifically in THIS deck?" — prefer it over raw inclusion rate.
- Source: session b27105d7, 2026-03-21

### Combo Assembly Speed Benchmarks (Monte Carlo)
From Monte Carlo simulations of draw-to-win: ~41 cards drawn past the opening hand to assemble a 2-card combo on average. Each additional combo piece needed requires ~20 more cards of draw. Adding 2 redundant combo pieces reduces draw-to-win by ~14% — equivalent to adding ~6 draw spells. Practical implication: 2-card combos are dramatically faster to assemble than 3-card combos; redundancy (running 2 copies of a combo piece) meaningfully reduces variance.
- Source: session b27105d7, 2026-03-21

### Eladamri, Korvecdal — Commander Profile
Mono-green, {1}{G}{G}, 3/3 Elf Warrior, from Modern Horizons 3. Three abilities: (1) look at top of library any time; (2) cast creature spells from top of library; (3) {G},{T}, tap two untapped creatures you control: put a creature card from your hand or the top of your library onto the battlefield. Strategy archetype: Elfball / Token Army. Optimal creature density: ~45% (44–49 creatures in 99-card list) to maximize ability #2 topcasting probability. Simulation result: commander by T3 ~85.7%, median T3.
- Source: session dc2f99ba, 2026-04-06

### Eladamri Ability #3: X-Cost Creatures Are Anti-Synergy
When Eladamri's third ability puts a creature directly onto the battlefield, X = 0. X-cost hydras (Voracious Hydra, Primordial Hydra, Lifeblood Hydra, Goldvein Hydra, Benevolent Hydra, Steelbane Hydra) enter as 0/0 creatures and immediately die to state-based actions. The same issue applies to ability #2 (casting from top of library sets X = 0). Never include X-cost creatures in an Eladamri deck unless they have a default non-zero base power/toughness.
- Source: session fd90e34c, 2026-04-06

### Champions of the Perfect — Correct Card Text
Champions of the Perfect costs {3}{G} and is a 6/6 Elf Warrior. Behold mechanic: exile an Elf you control as it enters (additional cost). When you cast a creature spell, draw a card. When it dies, return the exiled Elf to its owner's hand. It does NOT have cascade, anthem effects, or any buff to other creatures. Eladamri's ability #3 can cheat it into play bypassing the Behold exile cost entirely, making it a free 6/6 draw engine.
- Source: session 6bb9b26f, 2026-04-06

### Purchase Limit: Commander Is Excluded
In this project's deck-building constraint system, the commander card itself does NOT count toward the maximum purchase limit (e.g., "max 10 purchases"). All 10 buy slots are available for the 99-card deck. This was explicitly clarified by the board during Eladamri deck review.
- Source: session 6bb9b26f, 2026-04-06

### Game Changers List — Key Inclusions and Exclusions
Cards confirmed ON the game-changers list (56 total): Ancient Tomb, Gaea's Cradle, Seedborn Muse, Natural Order, Crop Rotation, Survival of the Fittest, Cyclonic Rift, Rhystic Study, Smothering Tithe, Fierce Guardianship, Deadly Rollick, Deflecting Swat, Dockside Extortionist, Ad Nauseam. Cards confirmed NOT on the list: Sensei's Divining Top, Doubling Season, Skullclamp, Parallel Lives, Lightning Greaves. The full list is at `data/game-changers.json` — always check at runtime, never rely on memory.
- Source: session fd90e34c, 2026-04-06

### SOC Set (Starter Commander Omnibus) Cards Not Commander-Legal
Cards from the SOC set (e.g., Primo, the Unbounded; Lattice Library; certain Dina variants) are NOT legal in the Commander format. They may appear in Scryfall searches with `legalities.commander: "not_legal"`. Always verify Commander legality via Scryfall before including any card. The SOC product is a supplemental set that is not sanctioned for Commander.
- Source: session e6b85099, 2026-04-06

### Meren Reanimates Creatures ONLY — Not Planeswalkers
Meren of Clan Nel Toth's experience counter ability puts creature cards onto the battlefield. She cannot reanimate planeswalkers. Recommending planeswalkers as Meren recursion targets is an error. Confirmed by board correction in DEC-67.
- Source: session 60e50238, 2026-04-06

### Meren CMC Reanimation Thresholds
Meren can reanimate a creature at end step if you have ≥ that creature's CMC in experience counters. Practical targets: CMC 3 creatures are reliably reanimatable from mid-game (~turn 4+); CMC 5 requires 5+ XP (~turn 6-7). Design decks to have strong 3-CMC creatures as recurring ETB engines.
- Source: session e6b85099, 2026-04-06

### Gandalf the White: Doubling Ability Precise Scope
Gandalf the White doubles triggered abilities caused by **legendary permanents or artifacts entering or leaving the battlefield**. Does NOT double: cast triggers, static abilities, replacement effects. The Spirit token from Ugin the Ineffable's +1 is a token (not a legendary or artifact) — its LTB draw trigger is NOT doubled by Gandalf.
- Source: session e6b85099, 2026-04-06

### High-Society Hunter: Correct Oracle Text
High-Society Hunter draws a card whenever **any nontoken creature dies** (not just on attack sac). In a sacrifice/aristocrats deck, every Plaguecrafter trigger, every Grave Pact death, every opponent's creature dying draws a card. Also has a built-in sac outlet on attack. Much stronger than the common user description implies.
- Source: session e6b85099, 2026-04-06

### Stitch Together: Threshold Mechanic
Stitch Together costs {B}{B}. Without threshold (< 7 graveyard cards): returns a creature card from graveyard to hand (Raise Dead). With threshold (7+ cards): returns directly to battlefield — a 2-mana Reanimate without life loss. Decks with active self-mill hit threshold by T4-5. Mana efficiency advantage over Necromancy (3 mana + loses creature when enchantment leaves).
- Source: session e6b85099, 2026-04-06

### Altar of Dementia: Required in Mikaeus+Ballista Loop
Altar of Dementia is a necessary piece in the Mikaeus + Walking Ballista loop — sacrifice outlet that enables infinite death triggers. Do not cut it from Meren decks running this combo. It pairs with Ballista + Mikaeus to loop infinite death triggers and convert them via death payoffs (Blood Artist, Zulaport, etc.) into a win.
- Source: session e6b85099, 2026-04-06

### Liliana, Dreadhorde General: Best Aristocrats Draw Engine
Liliana, Dreadhorde General has a **static ability** (not triggered): whenever a creature dies, draw a card. This draws on ALL creature deaths — yours and opponents'. In aristocrats/sacrifice decks, this generates more raw cards than Grim Haruspex (requires non-tokens) or Skullclamp (requires sac + equip). She's a planeswalker, not a creature — Meren cannot reanimate her.
- Source: session 60e50238, 2026-04-06

### Forsaken Monument + Basalt Monolith: Infinite Colorless Mana
Forsaken Monument grants +1 colorless mana whenever you tap a colorless permanent. Basalt Monolith taps for {C}{C}{C}. With Monument: Monolith taps for 4, pay 3 to untap, net +1 per loop = infinite colorless mana. This combo is relevant in any artifact/colorless-matters deck running both pieces.
- Source: session e6b85099, 2026-04-06; session a1a821dd, 2026-04-06

### Ardyn, the Usurper: Anti-Synergy in Graveyard Decks
Ardyn, the Usurper has an ability that exiles the graveyard. This is hard anti-synergy in any graveyard-based deck (Meren, Karador, etc.). At 8 CMC it's also overcosted for what amounts to a hate piece that hurts your own engine. Hard pass for graveyard decks.
- Source: session dce6351b, 2026-04-06

### Fiery Inscription Density Threshold for Group Slug
Fiery Inscription (deals 1 damage to each opponent whenever you cast an instant or sorcery) is justified in a group slug deck with ~19+ instants/sorceries (29%+ density). Eternal Agony has 12 instants + 7 sorceries = 19 total, generating 48-60 passive damage per game across 3 opponents. Below ~12-15 noncreature spells the trigger rate is too low to justify a slot.
- Source: session e350bd34, 2026-04-06

### Eladamri Ability #3: Static Effects Survive Cheat-Into-Play
Eladamri's ability #3 puts a creature directly onto the battlefield without casting it. Cast triggers (e.g., "whenever you cast this spell") do NOT fire. However, **static abilities** (continuous effects like Void Winnower's "opponents can't cast spells with even mana values") are always active once the permanent is on the battlefield regardless of how it arrived. This makes cards with powerful static effects ideal cheat targets for Eladamri — including Void Winnower's mana-parity lock. Only avoid cards whose primary value is a cast trigger (e.g., Eldrazi with "when you cast this" ETBs that drain opponents).
- Source: session c4b05b83, 2026-04-07

### Urza's Incubator: Generic Mana Reduction Only
Urza's Incubator reduces the generic ({X}) portion of a chosen creature type's mana cost only — it does NOT reduce colored pips. A {G} elf still costs {G}; an {1}{G} elf costs {G} (generic part reduced). A claim that Incubator makes 1-drop elves "free" is wrong — {G} elves still require green mana. Incubator is most valuable in decks with high-CMC creatures that have significant generic costs (e.g., Eldrazi, Angels).
- Source: session c4b05b83, 2026-04-07

### Nature's Rhythm: Harmonize Mechanic (Tarkir: Dragonstorm)
Nature's Rhythm costs {X}{G}{G}. Harmonize keyword: can be cast from graveyard by tapping a creature you control and reducing the mana cost by that creature's power. In a creature-heavy Elfball deck, tapping a large elf (e.g., 4-power elf) effectively reduces cost to {X} = free for most targets. Strictly better than Chord of Calling for proactive creature strategies: lower base cost ({X}{G}{G} vs {X}{G}{G}{G}), double-use (hand + graveyard), easier cost reduction (power-based vs convoke's 1-per-creature tap). Board confirmed preference over Chord of Calling in Verdant Tide.
- Source: session c4b05b83, 2026-04-07

### Haywire Mite: Self-Sacrifice Mechanic
Haywire Mite sacrifices **itself** as its own cost — no external artifact, Treasure, or sac outlet is needed. A common error is assuming Treasures are relevant to its activation (they aren't). When evaluating it as an artifact-hate or graveyard-setup piece, treat it as a 1-shot sacrifice with built-in ETB value.
- Source: session 7aa0cb5c, 2026-04-08

### Teval's Judgment: Card Profile
Teval's Judgment costs {2}{B} and is an Enchantment that is Commander-legal. It creates both a Treasure token and a 2/2 black Zombie Druid creature token. Relevant for aristocrats/sacrifice decks needing Zombie synergies, Treasure generation, and graveyard fodder. In Eternal Harvest (Meren), it replaced Stitcher's Supplier as an engine piece in the Graveyard Setup category.
- Source: session ace36d83, 2026-04-08

### Turbulent Fen: Commander Playability
Turbulent Fen is a land with both Swamp and Forest subtypes. It enters tapped unless opponents collectively control 8 or more lands. In 4-player Commander pods, opponents typically control 3+ lands each by turn 3 (9+ total), making this consistently untapped from mid-game onward. Fetchable by Farseek and similar effects. Recommended budget dual for B/G decks as a land slot upgrade over a basic.
- Source: session fa1524fb, 2026-04-16; session 53cc5fb4, 2026-04-16

### Priest of Forgotten Gods: Multi-Function Sacrifice Engine
Priest of Forgotten Gods costs {1}{B} and has a {B}, tap + sacrifice two creatures activation: each opponent loses 2 life and sacrifices a creature, you add {B}{B} and draw a card. Five simultaneous functions per activation: sac outlet, mana generation, forced opponent sacrifice, life drain, and card draw. Not a Human, so Mikaeus undying doesn't apply, but the repeatable tap ability makes it a core loop enabler in Meren decks. Strictly better than Orcish Bowmasters for sacrifice-loop strategies because every function feeds Meren's engine.
- Source: session fa1524fb, 2026-04-16; session 64e3dffd, 2026-04-16

### Immoral Bargain: Sacrifice-Synergistic Removal
Immoral Bargain costs {1}{B}{G} and is a Sorcery. Additional cost: sacrifice X creatures. Effect: destroy X nonland permanents. In sacrifice-focused decks (Meren, aristocrats), the "cost" is also a benefit — each sacrificed creature generates death triggers for Meren XP, Blood Artist, Grave Pact, etc. Effectively combines scalable removal with sacrifice triggers. Replaces cards like High-Society Hunter (6 CMC death-draw) as a role upgrade: lower CMC, proactive board impact, and synergizes with every death-trigger payoff.
- Source: session 53cc5fb4, 2026-04-16; session f1206cbc, 2026-04-16

### Nether Traitor: Cheap Recursion Engine for Meren
Nether Traitor costs {1}{B}, has shadow and haste. Pay {B} to return it from the graveyard to the battlefield whenever another creature dies. Generates repeated death triggers by cycling back to the graveyard and reactivating on subsequent deaths. In Meren: each loop adds Meren XP, triggers Blood Artist/Zulaport/Grave Pact, and requires only {B} to restart. Shadow makes it useful for attacking without blocking and for avoiding chump block trade-offs in non-shadow-heavy pods.
- Source: session fa1524fb, 2026-04-16; session f1206cbc, 2026-04-16

### SOS Prepare Mechanic: Casting Cost Is the Creature Face
Soaring Skies (SOS) introduced the Prepare mechanic on DFCs where the front face is a creature and the back face is a spell. When evaluating or adding these to a deck, the relevant casting cost is the CREATURE face — not the spell face and not the combined string. Examples: Emeritus of Woe // Demonic Tutor costs {3}{B} to cast (not {1}{B}); Grave Researcher // Reanimate costs {2}{B} to cast (not {B}). In card-metadata.json, always use the creature face mana cost for these cards.
- Source: session bbb82b17, 2026-04-24

### Emeritus of Woe // Demonic Tutor: Card Profile (SOS)
{3}{B} Creature — Vampire Warlock, 5/4. Enters prepared. Prepared spell: Demonic Tutor ({1}{B}) — search library for any card, put in hand. Repreps at the end step if 2+ creatures died this turn. In aristocrats/sacrifice decks (Meren), the reprep condition is trivially met — effectively a free Demonic Tutor attached to a 5/4 that Meren can loop from the graveyard. Strictly better than standalone Demonic Tutor in a deck that reanimates creatures repeatedly.
- Source: session bbb82b17, 2026-04-24

### Grave Researcher // Reanimate: Card Profile (SOS)
{2}{B} Creature — Troll Warlock, 3/3. Upkeep: surveil 1, then if 3+ creatures are in your graveyard, becomes prepared. Prepared spell: Reanimate ({B}) — put target creature from any graveyard onto the battlefield under your control, you lose life equal to its mana value. In graveyard-heavy decks (Meren), the 3+ creature threshold is met by turn 2-3. Provides repeatable Reanimate on a 3-CMC body that Meren can recur.
- Source: session bbb82b17, 2026-04-24

### Cauldron of Essence: Card Profile (SOS)
{1}{B}{G} Artifact. Death trigger: each opponent loses 1 life, you gain 1 life. Activated: {1}{B}{G}, {T}, sacrifice a creature → return target creature card from any graveyard to the battlefield (sorcery speed). Three-in-one: passive drain engine, sacrifice outlet, and reanimation. As an artifact, it's among the most resilient permanent types. In Meren (Eternal Harvest), fills the role of 5th drain effect plus combined sac outlet/reanimation activation in one card.
- Source: session bbb82b17, 2026-04-24; session d4c9436a, 2026-04-24

### Shigeki, Jukai Visionary: Correct Oracle Text
Shigeki does NOT produce counters. Actual abilities: {1}{G}, {T}, return to hand — reveal top 4 cards of your library, put a land onto the battlefield tapped, rest go to your graveyard. Channel — {X}{X}{G}{G}, Discard: return X target nonlegendary cards from your graveyard to your hand. Shigeki is a REPEATABLE LAND-FETCH ENGINE that self-bounces (not a counter-generating creature). Especially strong in landfall decks — each cast from hand re-enables the bounce. Board corrected misidentification of this card as a "counter producer" in DEC-73.
- Source: session 6d2839ed, 2026-04-24

### Exalted Sunborn: Card Profile (SOS)
{3}{W}{W} Creature — Angel Wizard, 4/5, Flying, Lifelink. Static: if one or more tokens would be created under your control, twice that many of those tokens are created instead (token doubler). Has Warp {1}{W} for temporary early deployment. In token-doubler-reliant decks (Mutant Multiplication), this is the same function as Parallel Lives / Doubling Season on a flying lifelink body. Strong include when the deck already runs 6+ token doublers and needs more redundancy.
- Source: session 203ce085, 2026-04-24

### Tombstone Stairwell: Meren Finisher Evaluation
Tombstone Stairwell is a {2}{B}{B} Enchantment with cumulative upkeep {B}. Each upkeep (all players'), each player creates a 2/2 black Zombie token for each creature card in their graveyard (Tombspawn tokens), then at the end of each end step all Tombspawn tokens are destroyed. In a 4-player game with populated graveyards, this generates 15-30+ death triggers per turn cycle. Devastating with Grave Pact (each Tombspawn death forces opponent sacrifices) and Blood Artist (80+ drain per cycle). Evaluated and skipped for Eternal Harvest (Meren) — powerful but win-more; the deck wins before needing it. Cumulative upkeep also becomes untenable past turn 3-4.
- Source: session 7e843c6b, 2026-04-24

### Eternal Agony: Asymmetric Punisher Preference
The Lord of Pain's built-in static ability disables *opponent* lifegain only. This means symmetric "Players can't gain life" cards (Sulfuric Vortex, Sunspine Lynx, Rampaging Ferocidon) are downgrades — they shut down the deck's own lifegain sources (Sheoldred the Apocalypse, Valgavoth payoffs). Similarly, symmetric draw punishers (Spiteful Visions) fuel opponents, and symmetric land-tap punishers (Manabarbs, Ankh of Mishra) hit the deck's land-mana-based play equally. All three were explicitly rejected by the board (DEC-101, 2026-05-03). Prefer effects that trigger on "each opponent" or "an opponent" only — pure asymmetry.
- Source: session fd3ef271, 2026-05-03

### Eternal Agony: Board-Confirmed Candidate Evaluation (DEC-101)
Full top-50 triage result for eternal-agony per-deck adoption pass, 2026-05-03:
**Include:** Mogis, God of Slaughter (asymmetric sac-tax each opponent upkeep; cut Ankh of Mishra — symmetric land-entry trigger); Fear of Burning Alive (asymmetric ETB burst; cut Vial Smasher — random first-spell variance); Tectonic Giant (asymmetric removal tax on attack; cut Coruscation Mage — 5th redundant noncreature-spell pinger, fragile 1/2 body).
**Defer:** Syr Konrad the Grim — 5 CMC + reanimator-conditional triggers don't fit the deck's t1-3 pressure shape.
**Reject:** Mirkwood Bats (deck produces very few tokens; lifelink-drain trigger negligible), Kaervek the Merciless (6 CMC; symmetric punishment for land-mana deck).
**Confirmed cuts:** Ankh of Mishra, Vial Smasher, Coruscation Mage.
- Sources: session fd3ef271, 2026-05-03 (multiple board follow-up rounds)
