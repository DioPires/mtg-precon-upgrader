"""DEC-935: apply the 11 board-approved swaps (verdict card 5e9a7eeb, 2026-09-30) to
data/commanders/broodfire-hatchery/deck.json and rewrite the guide prose for the combat plan.

    uv run python agents/ceo/analysis/dec935-apply.py
"""
import json

PATH = "data/commanders/broodfire-hatchery/deck.json"
SCRY = {"type": "scryfall", "name": "Scryfall"}
AI = {"type": "ai-inferred", "name": "DEC-935 combat remake (CEO, board-approved 2026-09-30)"}

CUTS = ["Warstorm Surge", "Terror of the Peaks", "Purphoros, God of the Forge", "Solphim, Mayhem Dominus",
        "Mirror Entity", "Idol of Oblivion", "Birthing Pod", "Chord of Calling", "Identity Echo",
        "Shamanic Revelation", "Blasphemous Act"]
ADDS = [
    {"name": "Xenagos, God of Revels", "type": "Legendary Enchantment Creature — God", "primary_role": "payoff"},
    {"name": "Rhythm of the Wild", "type": "Enchantment", "primary_role": "engine"},
    {"name": "Zopandrel, Hunger Dominus", "type": "Legendary Creature — Phyrexian Horror", "primary_role": "payoff"},
    {"name": "Aurelia, the Warleader", "type": "Legendary Creature — Angel", "primary_role": "payoff"},
    {"name": "Combat Celebrant", "type": "Creature — Human Warrior", "primary_role": "payoff"},
    {"name": "Tifa, Martial Artist", "type": "Legendary Creature — Human Monk", "primary_role": "payoff"},
    {"name": "Ghalta and Mavren", "type": "Legendary Creature — Dinosaur Vampire", "primary_role": "wincon", "wincon_style": "combat"},
    {"name": "Annie Joins Up", "type": "Legendary Enchantment", "primary_role": "engine", "secondary_role": "removal-spot"},
    {"name": "Raph & Mikey, Troublemakers", "type": "Legendary Creature — Mutant Ninja Turtle", "primary_role": "engine", "secondary_role": "payoff"},
    {"name": "Aggravated Assault", "type": "Enchantment", "primary_role": "payoff"},
    {"name": "Samut, Hazoret's Champion", "type": "Legendary Creature — Human Warrior Cleric", "primary_role": "engine"},
]
PRICES = {  # Scryfall EUR, 2026-09-30 (information only)
    "Xenagos, God of Revels": "€7.23", "Rhythm of the Wild": "€3.85", "Zopandrel, Hunger Dominus": "€9.96",
    "Aurelia, the Warleader": "€4.49", "Combat Celebrant": "€1.34", "Tifa, Martial Artist": "€1.23",
    "Ghalta and Mavren": "€1.45", "Annie Joins Up": "€2.57", "Raph & Mikey, Troublemakers": "€1.84",
    "Aggravated Assault": "€15.76", "Samut, Hazoret's Champion": "€1.23",
}

d = json.load(open(PATH))

# ---- decklist -----------------------------------------------------------------
names = {c["name"] for c in d["decklist"]}
for c in CUTS:
    assert c in names, c
for a in ADDS:
    assert a["name"] not in names, a["name"]
d["decklist"] = [c for c in d["decklist"] if c["name"] not in CUTS] + ADDS
assert sum(c.get("quantity", 1) for c in d["decklist"]) == 99

# ---- deck-level fields ----------------------------------------------------------
d["wincon_style"] = "combat"
d["lastUpdatedSet"] = "Teenage Mutant Ninja Turtles"
d["commanderRoles"] = {"primary": "engine", "secondary": "tutor"}

# ---- strategy overview ----------------------------------------------------------
d["guideContent"]["strategyOverview"] = (
    "Broodfire Hatchery is a Naya combat deck built on one engine. Atla Palani, Nest Tender pays {2} and taps to make a 0/1 Egg token, "
    "and whenever an Egg you control dies she reveals cards from the top of your library until she hits a creature card and puts it straight "
    "onto the battlefield. The 99 is stocked with bodies that win a combat the moment they arrive — Worldspine Wurm, Blightsteel Colossus, "
    "Apex Altisaur, Zacama, Primal Calamity, Avacyn, Angel of Hope, Etali, Primal Conqueror, Ghalta and Mavren, Raph & Mikey, Troublemakers — "
    "so a random flip is never a blank. The play pattern is the one the board asked for: a big creature enters, big creatures attack.\n\n"
    "Speed comes from free sacrifice outlets. Ashnod's Altar, Phyrexian Altar and Goblin Bombardment kill an Egg for no mana, Skullclamp does it "
    "for {1} and draws two cards, and High Market does it once a turn from a land slot. Maskwood Nexus makes every creature you control every "
    "creature type — so every creature is an Egg and any outlet becomes a repeatable \"sacrifice a creature, hatch a new one\" engine. Thornbite "
    "Staff gives Atla \"whenever a creature dies, untap this creature\", so with Ashnod's Altar the loop is mana-neutral and hatches the library; "
    "with a haste source on the battlefield, everything it hatches attacks the same turn. Because Atla is a Shaman, the Staff attaches to her "
    "for free if it is already on the battlefield when she enters.\n\n"
    "Haste is the hinge. Rhythm of the Wild gives every nontoken creature riot, Samut, Hazoret's Champion gives the team haste for two mana, "
    "Palani's Hatcher gives Dinosaurs haste (every creature, under Maskwood Nexus), and Xenagos, God of Revels hands one creature haste and "
    "+X/+X where X is its power at each of your beginning-of-combat steps. Xenagos chooses its target when the trigger goes on the stack, so "
    "hatch in main phase 1 to use it that combat. Without a haste source, hatch at instant speed on the end step before your turn: Seedborn "
    "Muse untaps Atla during every opponent's untap step, so the Eggs are there and the bombs are ready when your turn starts.\n\n"
    "The amplifiers turn one hatch into several attack steps. Aurelia, the Warleader, Combat Celebrant and Tifa, Martial Artist each untap "
    "every creature you control — Atla included, so she makes another Egg mid-turn — and add a combat phase; Aggravated Assault does the same "
    "for {3}{R}{R} as often as you can pay, at sorcery speed. Raph & Mikey hatch a creature tapped and attacking every time they attack. "
    "Zopandrel, Hunger Dominus doubles the team's power and toughness at every combat, yours and each opponent's, and doubles again in each "
    "extra combat. Annie Joins Up makes every legendary creature's triggered ability trigger twice — Atla hatches two creatures per Egg, "
    "Aurelia and Tifa each add two combats, Zopandrel doubles twice, Xenagos fires twice — and Roaming Throne (naming Shaman) stacks on top. "
    "Mondrak, Glory Dominus and Elspeth, Storm Slayer double every Egg token, and Elesh Norn, Mother of Machines doubles the "
    "enters-the-battlefield triggers of Craterhoof Behemoth, Palani's Hatcher, Etali and Apex Altisaur while blanking every opponent's.\n\n"
    "Support is built for a creature deck that taps out on its own turn: 9 ramp sources for a turn-3 Atla, 4 tutors (Worldly Tutor puts the "
    "next hatch on top of the library; Enlightened Tutor finds Rhythm of the Wild, Annie Joins Up, Aggravated Assault, Maskwood Nexus or an "
    "Altar; Eladamri's Call and Natural Order find a bomb, and Natural Order can sacrifice an Egg as its cost, which also hatches), 7 draw "
    "pieces tied to the hatches, and 6 protection pieces (Deflecting Swat and Flawless Maneuver are free with the commander out; Clever "
    "Concealment phases the board out of a wipe). Interaction is chosen for hoser coverage: Grafdigger's Cage stops creature cards in "
    "libraries from entering the battlefield and blanks Atla outright, so Aura Shards answers it every time a creature enters, and Krosan Grip, "
    "Force of Vigor, Boseiju, Who Endures and Beast Within cover artifacts, enchantments and lands. Winds of Abandon overloaded exiles every "
    "creature the deck's opponents control before an alpha strike. Bracket 4 with 7 Game Changers. The deck is tagged brewing until the "
    "goldfish simulation confirms the turn-6 kill rate."
)

# ---- categories -----------------------------------------------------------------
d["guideContent"]["deckCategories"] = [
    {"name": "The Egg Engine",
     "description": "Atla turns Egg deaths into free creatures, so the deck's real mana sink is making more Eggs and untapping her. Maskwood Nexus makes every creature an Egg, Thornbite Staff untaps Atla on every death, Mondrak and Elspeth, Storm Slayer each double every Egg token (with both out one activation makes four), Annie Joins Up and Roaming Throne (naming Shaman) each make Atla's hatch trigger fire an additional time, Seedborn Muse untaps her on every opponent's turn, Palani's Hatcher and Nesting Dragon add Eggs without spending Atla's tap, and Elesh Norn doubles the enters-the-battlefield triggers the hatched creatures cause.",
     "cards": ["Maskwood Nexus", "Thornbite Staff", "Mondrak, Glory Dominus", "Elspeth, Storm Slayer", "Annie Joins Up", "Roaming Throne", "Seedborn Muse", "Palani's Hatcher", "Nesting Dragon", "Elesh Norn, Mother of Machines"]},
    {"name": "Free Sacrifice Outlets",
     "description": "An Egg is worth nothing until it dies. Ashnod's Altar, Phyrexian Altar and Goblin Bombardment cost no mana and have no limit, so an Egg made this turn hatches this turn and a board full of Eggs empties at instant speed — including on the end step before your turn, when the hatched bombs need no haste. Skullclamp kills an Egg for {1} and draws two; High Market does it once a turn from a land slot; Natural Order can sacrifice an Egg as its additional cost.",
     "cards": ["Ashnod's Altar", "Phyrexian Altar", "Goblin Bombardment", "Skullclamp", "High Market", "Natural Order"]},
    {"name": "Haste",
     "description": "A hatched bomb without haste waits a turn, so the deck runs three team-wide sources plus a targeted one. Rhythm of the Wild gives every nontoken creature riot (haste or a +1/+1 counter, your choice per creature), Samut, Hazoret's Champion is a 2-mana anthem Atla can hatch, Palani's Hatcher gives Dinosaurs haste (every creature under Maskwood Nexus), and Xenagos, God of Revels hands one creature haste and doubles its power at each of your beginning-of-combat steps — hatch in main phase 1, because Xenagos picks its target when the trigger goes on the stack. Lightning Greaves protects Atla and lets her make an Egg the turn she lands.",
     "cards": ["Rhythm of the Wild", "Samut, Hazoret's Champion", "Xenagos, God of Revels", "Palani's Hatcher", "Lightning Greaves"]},
    {"name": "Extra Combats and Untaps",
     "description": "Each of these turns one hatch into two or three attack steps. Aurelia (first attack each turn), Combat Celebrant (exert) and Tifa (a power-7-or-more creature connects, first combat only) untap every creature you control — Atla included, so she makes a fresh Egg between combats — and add a combat phase. Aggravated Assault adds a combat for {3}{R}{R} at sorcery speed with no limit per turn. Raph & Mikey hatch a creature tapped and attacking every time they attack, so every extra combat is another hatch. Annie Joins Up doubles the Aurelia, Tifa and Raph & Mikey triggers. Note: Tifa's extra combat has no main phase between combats, so hatches between them must be instant-speed.",
     "cards": ["Aurelia, the Warleader", "Combat Celebrant", "Tifa, Martial Artist", "Aggravated Assault", "Raph & Mikey, Troublemakers", "Annie Joins Up"]},
    {"name": "Power Multipliers",
     "description": "Zopandrel doubles the team's power and toughness at every combat (yours and each opponent's) and doubles again in each extra combat. Xenagos doubles one creature at each beginning of combat; resolve Zopandrel first, then Xenagos, and Worldspine Wurm attacks as a 60/60. Craterhoof Behemoth is the mass finisher and has haste of its own. Ghalta and Mavren add a tapped-and-attacking X/X trampler on every attack, X being the greatest power among the other attackers. Garruk's Uprising gives the whole team trample so the doubled power goes through blockers.",
     "cards": ["Zopandrel, Hunger Dominus", "Xenagos, God of Revels", "Craterhoof Behemoth", "Ghalta and Mavren", "Garruk's Uprising"]},
    {"name": "Bombs to Hatch",
     "description": "The library is the deck's hand. Every creature here wins a combat, sweeps, or draws the game open on arrival, so a blind flip off Atla is always worth the Egg. Eight of them have printed power 7 or more, which turns on Tifa. Worldspine Wurm and Vigor shuffle back from the graveyard and become fuel again; Blightsteel Colossus with Xenagos is 22 infect trample, lethal to one player in a single hit.",
     "cards": ["Craterhoof Behemoth", "Avacyn, Angel of Hope", "Etali, Primal Conqueror // Etali, Primal Sickness", "Blightsteel Colossus", "Zacama, Primal Calamity", "Apex Altisaur", "Vaultborn Tyrant", "Worldspine Wurm", "Vigor", "Ghalta and Mavren", "Raph & Mikey, Troublemakers", "Zopandrel, Hunger Dominus", "Aurelia, the Warleader"]},
    {"name": "Tutors",
     "description": "Four tutors, each with a job: Worldly Tutor puts a creature on top of the library, which is exactly where Atla's next hatch comes from; Enlightened Tutor finds Rhythm of the Wild, Annie Joins Up, Aggravated Assault, Maskwood Nexus, Thornbite Staff or either Altar; Eladamri's Call puts Samut or a bomb in hand; Natural Order sacrifices an Egg (which hatches) and puts Craterhoof, Vigor, Worldspine Wurm or Zopandrel onto the battlefield.",
     "cards": ["Enlightened Tutor", "Worldly Tutor", "Eladamri's Call", "Natural Order"]},
    {"name": "Protection",
     "description": "The deck taps out on its own turn with the commander on the battlefield, so every protection piece is chosen to be live then. Deflecting Swat and Flawless Maneuver cost nothing while Atla is out, Clever Concealment phases the whole board out of a wipe, Lightning Greaves gives Atla shroud, and Vigor and Avacyn make the hatched board survive damage-based and destroy-based wipes.",
     "cards": ["Deflecting Swat", "Flawless Maneuver", "Clever Concealment", "Lightning Greaves", "Vigor", "Avacyn, Angel of Hope"]},
    {"name": "Interaction and Hoser Coverage",
     "description": "Grafdigger's Cage is the card that beats this deck outright — creature cards in libraries can't enter the battlefield, so Atla stops hatching. Aura Shards destroys an artifact or enchantment every time a creature enters, and Krosan Grip, Force of Vigor, Boseiju and Beast Within cover artifacts, enchantments and lands so no resolved hoser sticks. Swords to Plowshares and Path to Exile answer blockers and opposing commanders at instant speed, Annie Joins Up deals 5 to a creature or planeswalker on entry, and Winds of Abandon overloaded exiles every creature your opponents control before an alpha strike while the Egg board stays put.",
     "cards": ["Aura Shards", "Krosan Grip", "Force of Vigor", "Boseiju, Who Endures", "Beast Within", "Swords to Plowshares", "Path to Exile", "Annie Joins Up", "Winds of Abandon"]},
    {"name": "Ramp and Fixing",
     "description": "Atla wants to land on turn 3 and activate the same turn, so the ramp is cheap and untapped: the Nature's Lore class fetches shock duals untapped, Rootbound Crag is the 37th land (untapped with any Mountain or Forest on the battlefield), and Jeska's Will pays for an Aggravated Assault activation or a whole hatch turn.",
     "cards": ["Sol Ring", "Arcane Signet", "Birds of Paradise", "Llanowar Elves", "Nature's Lore", "Three Visits", "Farseek", "Jeska's Will", "Smothering Tithe"]},
    {"name": "Card Advantage",
     "description": "Draw is tied to the plan rather than bolted on: Guardian Project and Garruk's Uprising fire on the creatures Atla hatches, Vaultborn Tyrant draws for every power-4-or-more body that enters, Skullclamp turns a 0/1 Egg into two cards, Greater Good cashes a doomed bomb in for a hand, and Caretaker's Talent draws the first time tokens enter under your control each turn — with Smothering Tithe that is every turn of the cycle. The hatch itself is the deck's real card advantage: every Egg is a free creature.",
     "cards": ["Guardian Project", "Garruk's Uprising", "Sylvan Library", "Skullclamp", "Caretaker's Talent", "Greater Good", "Vaultborn Tyrant"]},
    {"name": "Key Lands",
     "description": "37 lands, 36 of them untapped on arrival. Command Beacon recasts Atla past commander tax, High Market is a sacrifice outlet in a land slot, Boseiju is removal that costs no card, and Eiganjo channels from hand for 4 damage to an attacking or blocking creature ({1} cheaper per legendary creature you control — 13 in the deck).",
     "cards": ["Command Tower", "Command Beacon", "High Market", "Boseiju, Who Endures", "Jetmir's Garden", "Bountiful Promenade", "Clifftop Retreat", "Exotic Orchard", "Eiganjo, Seat of the Empire", "Rootbound Crag"]},
]

# ---- win conditions -------------------------------------------------------------
d["winConditions"] = [
    {"title": "Hatch and Swing", "kind": "combat",
     "cards": ["Rhythm of the Wild", "Samut, Hazoret's Champion", "Xenagos, God of Revels", "Zopandrel, Hunger Dominus", "Craterhoof Behemoth", "Worldspine Wurm", "Blightsteel Colossus", "Etali, Primal Conqueror // Etali, Primal Sickness"],
     "description": "Kill Eggs in main phase 1, the hatched bombs have haste (Rhythm of the Wild, Samut, or Xenagos on the biggest one), and they attack. Zopandrel doubles the team at the start of combat; Xenagos doubles one body on top of that, so a hatched Worldspine Wurm attacks as a 60/60 trampler and Blightsteel Colossus as 22 infect. Craterhoof Behemoth finishes a wide board."},
    {"title": "Extra Combat Chain", "kind": "combat",
     "cards": ["Aurelia, the Warleader", "Tifa, Martial Artist", "Combat Celebrant", "Aggravated Assault", "Raph & Mikey, Troublemakers", "Annie Joins Up"],
     "description": "Aurelia, Combat Celebrant and Tifa untap every creature you control, Atla included, and add a combat phase; Aggravated Assault adds more for {3}{R}{R} each. Between combats Atla makes a fresh Egg, a free outlet kills it, and the new bomb attacks in the next combat. Raph & Mikey hatch another creature tapped and attacking on every attack, and Annie Joins Up doubles every one of these legendary triggers."},
    {"title": "Thornbite Hatch Engine", "kind": "combo", "pieces": ["Thornbite Staff", "Ashnod's Altar"],
     "cards": ["Thornbite Staff", "Ashnod's Altar", "Phyrexian Altar", "Goblin Bombardment"],
     "description": "Equip Thornbite Staff to Atla. Pay {2},{T} for an Egg, sacrifice it to Ashnod's Altar for {C}{C}, and the death untaps Atla via the Staff. Each mana-neutral loop hatches a creature off the top of the library; with a haste anthem out the whole library attacks that turn."},
]

# ---- highlights -----------------------------------------------------------------
keep = {h["name"]: h for h in d["highlights"]}
def hl(name, reason, gc=False, price=None):
    h = {"name": name, "price": price or PRICES.get(name) or keep.get(name, {}).get("price", ""), "isGameChanger": gc, "reason": reason, "sources": [SCRY]}
    return h
d["highlights"] = [
    keep["Atla Palani, Nest Tender"] | {"reason": "Commander. {2}, {T} makes a 0/1 Egg; whenever an Egg you control dies she reveals cards until she hits a creature card and puts it onto the battlefield. Every line in the deck is a way to kill Eggs faster and attack with what hatches."},
    hl("Rhythm of the Wild", "Riot for every nontoken creature you control, which covers every hatch: the bomb enters with haste (or a +1/+1 counter if it already has haste) and attacks the turn it arrives. Creature spells can't be countered."),
    hl("Samut, Hazoret's Champion", "{1}{R} 2/2: creatures you control have haste. The cheapest team-wide haste in the colours, and a creature, so Atla can hatch her."),
    hl("Xenagos, God of Revels", "At each of your beginning-of-combat steps another target creature gains haste and +X/+X where X is its power. Indestructible enchantment (a creature only at devotion 7). Hatch in main phase 1: the target is chosen when the trigger goes on the stack."),
    hl("Zopandrel, Hunger Dominus", "Hatchable 4/6 reach that doubles the power and toughness of every creature you control at the beginning of each combat — yours and each opponent's — and again in every extra combat. Resolve it before Xenagos: 15 → 30 → 60."),
    hl("Annie Joins Up", "Legendary enchantment: 5 damage to a creature or planeswalker on entry, then every legendary creature's triggered ability triggers an additional time. Atla hatches two creatures per Egg, Aurelia and Tifa each add two combats, Raph & Mikey hatch twice per attack, Zopandrel doubles twice."),
    hl("Aurelia, the Warleader", "Hatchable 3/4 flying vigilance haste. The first time she attacks each turn, untap all creatures you control (Atla included, so she makes another Egg) and add a combat phase."),
    hl("Tifa, Martial Artist", "Whenever one or more creatures you control with power 7 or greater deal combat damage to a player, untap all your creatures, and in the first combat of your turn add a combat phase. Eight bombs in the deck have printed power 7 or more; Zopandrel and Xenagos lift the rest."),
    hl("Raph & Mikey, Troublemakers", "7/7 trample haste. Whenever they attack, reveal until a creature card and put it onto the battlefield tapped and attacking — Atla's hatch on an attack trigger, once per combat, doubled by Annie Joins Up and (under Maskwood Nexus) by Roaming Throne."),
    hl("Aggravated Assault", "{3}{R}{R}: untap all creatures you control and add a combat phase and a main phase, as often as you can pay. The repeatable extra combat on an enchantment; Enlightened Tutor finds it."),
    hl("Maskwood Nexus", "Makes every creature you control every creature type, so every creature is an Egg (any free outlet hatches the library) and every creature is a Dinosaur (Palani's Hatcher gives them all haste)."),
    keep["Thornbite Staff"],
    keep["Ashnod's Altar"] | {"reason": "Free outlet that pays you {C}{C} per Egg. The mana half of the Thornbite loop and the outlet that lets a whole board hatch at instant speed on the end step before your turn."},
    keep["Roaming Throne"],
    keep["Seedborn Muse"] | {"reason": "Game Changer. Untaps Atla during every opponent's untap step: an Egg per player per turn cycle (×3 in a four-player game) and the reason the deck can hatch on the end step before its turn with no haste source at all."},
    keep["Natural Order"] | {"reason": "Game Changer. Sacrifice a green Egg — which itself triggers Atla — and put Craterhoof Behemoth, Zopandrel, Vigor or Worldspine Wurm straight onto the battlefield."},
    keep["Craterhoof Behemoth"] | {"reason": "The mass finisher, with haste of its own. Any board built by a turn of hatches becomes lethal the moment Craterhoof arrives, hard-cast or flipped; Elesh Norn doubles its trigger."},
    keep["Worldspine Wurm"] | {"reason": "15/15 trample that shuffles itself back into the library from anywhere, so it is permanent fuel for the Thornbite loop, and it leaves three 5/5 trample tokens behind each time it dies. The best Xenagos target in the deck: 30/30, or 60/60 after Zopandrel."},
]
for h in d["highlights"]:
    h.setdefault("sources", [SCRY])

# ---- synergies ------------------------------------------------------------------
d["synergies"] = [s for s in d["synergies"] if "Mirror Entity" not in s["cards"]]
for s in d["synergies"]:
    if s["title"].startswith("Thornbite Staff"):
        s["description"] = s["description"].rstrip() + " With Rhythm of the Wild or Samut on the battlefield, everything the loop hatches attacks the same turn."
d["synergies"] += [
    {"title": "Atla + Annie Joins Up = two hatches per Egg", "cards": ["Atla Palani, Nest Tender", "Annie Joins Up"],
     "description": "Atla is a legendary creature, so Annie Joins Up makes her dies trigger fire twice: every Egg death reveals until a creature card twice and puts both onto the battlefield. No Maskwood Nexus or Roaming Throne needed; with Roaming Throne naming Shaman as well, each Egg hatches three creatures (each \"additional time\" adds one).",
     "sources": [SCRY, AI]},
    {"title": "Aurelia / Combat Celebrant / Tifa untap Atla mid-turn", "cards": ["Atla Palani, Nest Tender", "Aurelia, the Warleader", "Combat Celebrant", "Tifa, Martial Artist"],
     "description": "All three untap every creature you control (Celebrant: every other creature) when they add a combat phase, and Atla is a creature. Pay {2}, tap her for a new Egg, kill it with a free outlet, and the bomb it hatches attacks in the extra combat with haste from Rhythm of the Wild or Samut. Tifa's extra combat has no main phase in between, so this has to happen at instant speed.",
     "sources": [SCRY, AI]},
    {"title": "Raph & Mikey + extra combats = a hatch every attack", "cards": ["Raph & Mikey, Troublemakers", "Aurelia, the Warleader", "Aggravated Assault"],
     "description": "Raph & Mikey reveal until a creature card and put it onto the battlefield tapped and attacking whenever they attack, so each extra combat from Aurelia, Tifa, Combat Celebrant or Aggravated Assault is one more hatch that swings immediately. The hatched creature was not declared as an attacker, so attack triggers do not fire for it, but it deals combat damage like any other attacker.",
     "sources": [SCRY, AI]},
    {"title": "Zopandrel + Xenagos on one body = 60 trample", "cards": ["Zopandrel, Hunger Dominus", "Xenagos, God of Revels", "Worldspine Wurm"],
     "description": "Both trigger at the beginning of your combat. Order Zopandrel to resolve first: Worldspine Wurm becomes 30/30, then Xenagos gives it +30/+30 and haste (X is calculated as the Xenagos trigger resolves). Blightsteel Colossus on the same line is 44 infect trample. Xenagos must target a creature already on the battlefield, so hatch the target in main phase 1.",
     "sources": [SCRY, AI]},
    {"title": "Palani's Hatcher + Maskwood Nexus = every creature has haste", "cards": ["Palani's Hatcher", "Maskwood Nexus"],
     "description": "Palani's Hatcher gives other Dinosaurs you control haste. Maskwood Nexus makes every creature you control every creature type, so every hatched bomb is a Dinosaur with haste. The Hatcher's own beginning-of-combat Egg sacrifice also hatches a creature before attackers are declared.",
     "sources": [SCRY, AI]},
]

# ---- sources --------------------------------------------------------------------
d["sources"].append({
    "type": "ai-inferred",
    "name": "Swap round 3 — DEC-935 combat remake (board-approved 2026-09-30)",
    "detail": "Board direction: turn the deck into a combat deck (big creature enters, big creatures attack) and drop the enters-the-battlefield damage layer; buying is fine. Verdict card 5e9a7eeb, 11 of 13 lines approved: ADD Xenagos, God of Revels / CUT Warstorm Surge; ADD Rhythm of the Wild / CUT Terror of the Peaks; ADD Zopandrel, Hunger Dominus / CUT Solphim, Mayhem Dominus; ADD Aurelia, the Warleader / CUT Purphoros, God of the Forge; ADD Combat Celebrant / CUT Mirror Entity (Eggs keep defender under Mirror Entity, and X above 0 shrinks the bombs); ADD Tifa, Martial Artist / CUT Idol of Oblivion; ADD Ghalta and Mavren / CUT Birthing Pod; ADD Annie Joins Up / CUT Chord of Calling; ADD Raph & Mikey, Troublemakers / CUT Identity Echo; ADD Aggravated Assault / CUT Shamanic Revelation; ADD Samut, Hazoret's Champion / CUT Blasphemous Act. Rejected by the board: Rising of the Day / Caretaker's Talent (card draw kept) and Raphael, the Nightwatcher / Nesting Dragon (Egg-producer count to be re-evaluated). An adversarial review (14 findings) corrected the proposal before approval: Xenagos targets when it triggers (hatch in main phase 1), 6 printed-power-7+ bodies before / 8 after, Elesh Norn kept for her ETB doubling, trigger rates counted per combat. wincon_style retagged combo -> combat.",
})
d["sources"].append({
    "type": "scryfall",
    "name": "Scryfall — oracle text verification (DEC-935 adds)",
    "detail": "All 11 adds resolved and oracle-verified via the Scryfall API on 2026-09-30 (Raph & Mikey, Troublemakers: Teenage Mutant Ninja Turtles, set tmt, released 2026-03-06).",
})

json.dump(d, open(PATH, "w"), indent=2, ensure_ascii=False)
open(PATH, "a").write("\n")
print("applied; decklist entries", len(d["decklist"]), "sum", sum(c.get("quantity", 1) for c in d["decklist"]))
