"""DEC-549 (DEC-544 build leg 1): emit data/commanders/broodfire-hatchery/deck.json.

The 99 is frozen: every card, primary_role and wincon_style comes verbatim from
agents/ceo/analysis/dec544-build-spec.json. This script only adds the prose the
build issue asks for (strategy overview, categories, highlights, synergies,
sources) and reorders entries by card group for readability.

This script rewrites deck.json from scratch, so it drops the tokens[] block.
Re-run scripts/compute_tokens.py --deck broodfire-hatchery after every run.

Run from repo root:
    uv run python agents/ceo/analysis/dec544-build-deckjson.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = json.loads((ROOT / "agents/ceo/analysis/dec544-build-spec.json").read_text())
OUT = ROOT / "data/commanders/broodfire-hatchery/deck.json"

# Two amendment cards were appended to the spec under a catch-all group.
GROUP_FIX = {"Lightning Greaves": "artifacts", "Beast Within": "interaction"}
GROUP_ORDER = [
    "creatures",
    "artifacts",
    "enchantments",
    "tutors",
    "protection",
    "interaction",
    "ramp",
    "draw",
    "lands",
]

STRATEGY = (
    "Broodfire Hatchery is a Naya combo deck with a single question at its centre: how many Eggs can "
    "you kill this turn? Atla Palani, Nest Tender pays {2} and taps to make a 0/1 Egg token, and whenever "
    "an Egg you control dies she reveals cards from the top of your library until she hits a creature card "
    "and puts it straight onto the battlefield. Every Egg death is therefore a free creature, so the 99 is "
    "stocked almost entirely with bodies that change the game the moment they arrive — Craterhoof Behemoth, "
    "Avacyn, Angel of Hope, Etali, Primal Conqueror, Blightsteel Colossus, Zacama, Primal Calamity, Apex "
    "Altisaur, Titan of Industry. A random flip is never a blank.\n\n"
    "Speed comes from free sacrifice outlets. Ashnod's Altar, Phyrexian Altar, Goblin Bombardment, Skullclamp "
    "and High Market all kill an Egg for no mana, so an Egg can be cashed in the moment it is made. Maskwood "
    "Nexus makes every creature you control every creature type — which means every creature you control is "
    "an Egg — so any free outlet becomes a repeatable \"sacrifice a creature, hatch a new one\" engine; three "
    "of the deck's six Spellbook-verified lines run through it. Thornbite Staff gives Atla \"whenever a creature "
    "dies, untap this creature\", so with Ashnod's Altar the loop is mana-neutral: pay {2} and tap Atla for an "
    "Egg, sacrifice the Egg for {C}{C}, the death untaps Atla, repeat. Because Atla is a Shaman, the Staff "
    "attaches to her for free if it is already on the battlefield when she enters.\n\n"
    "Mirror Entity is the widest line of all. With Atla out, activate Mirror Entity for X=0: every creature you "
    "control has base power and toughness 0/0 and gains all creature types, so the whole board is a pile of Eggs "
    "that dies at once and Atla triggers for each of them. Worldspine Wurm and Vigor shuffle themselves back into "
    "the library whenever they hit the graveyard, so the cascade keeps finding fuel instead of burning out.\n\n"
    "None of this needs an attack step. Purphoros, God of the Forge, Impact Tremors, Warleader's Call and Terror "
    "of the Peaks all trigger on each creature entering, so a mass hatch converts directly into noncombat damage "
    "and kills the table from an empty-looking board. Craterhoof Behemoth is the combat backup when the table is "
    "playing damage prevention. Mondrak, Glory Dominus doubles every Egg token, Roaming Throne (naming Shaman) "
    "doubles Atla's death trigger for two flips per Egg, and Elesh Norn, Mother of Machines doubles every "
    "enters-the-battlefield trigger the hatched creatures cause.\n\n"
    "Support is built for a combo deck: 11 ramp sources, 7 tutors that can find either half of any line, 7 "
    "protection pieces (Deflecting Swat and Flawless Maneuver are free with the commander out, Clever Concealment "
    "phases the board out of a wipe), and interaction chosen for hoser coverage. The deck's number one hate card "
    "is Grafdigger's Cage, which stops creature cards in libraries from entering the battlefield and blanks Atla "
    "outright; Aura Shards answers it every time a creature enters, and Krosan Grip, Force of Vigor, Boseiju, Who "
    "Endures and Beast Within cover artifacts, enchantments and lands so no resolved hoser sticks. Bracket 4 with "
    "8 Game Changers. The deck is tagged brewing until the goldfish simulation confirms the turn-6 kill rate."
)

CATEGORIES = [
    {
        "name": "The Egg Engine",
        "description": (
            "Atla turns Egg deaths into free creatures, so the deck's real mana sink is making more Eggs and "
            "untapping her. Maskwood Nexus makes every creature an Egg, Thornbite Staff untaps Atla on every "
            "death, Mondrak doubles every Egg token, and Roaming Throne (naming Shaman) makes Atla's death "
            "trigger fire twice. Palani's Hatcher and Nesting Dragon keep making Eggs if Atla is answered."
        ),
        "cards": [
            "Maskwood Nexus",
            "Thornbite Staff",
            "Mondrak, Glory Dominus",
            "Roaming Throne",
            "Seedborn Muse",
            "Palani's Hatcher",
            "Nesting Dragon",
            "Elesh Norn, Mother of Machines",
        ],
    },
    {
        "name": "Free Sacrifice Outlets",
        "description": (
            "An Egg is worth nothing until it dies. Every outlet here costs no mana, so an Egg made this turn "
            "hatches this turn, and a board full of Eggs empties in one go."
        ),
        "cards": [
            "Ashnod's Altar",
            "Phyrexian Altar",
            "Goblin Bombardment",
            "Skullclamp",
            "High Market",
            "Birthing Pod",
        ],
    },
    {
        "name": "Damage Converters",
        "description": (
            "Each of these triggers on a creature entering, which is exactly what a mass hatch produces. They "
            "turn the cascade into lethal noncombat damage without ever attacking."
        ),
        "cards": [
            "Purphoros, God of the Forge",
            "Impact Tremors",
            "Warleader's Call",
            "Terror of the Peaks",
        ],
    },
    {
        "name": "Bombs to Hatch",
        "description": (
            "The library is the deck's hand. Every creature here wins, sweeps, or draws the game open on arrival, "
            "so a blind flip off Atla is always worth the Egg. Worldspine Wurm and Vigor shuffle back from the "
            "graveyard and become fuel again."
        ),
        "cards": [
            "Craterhoof Behemoth",
            "Avacyn, Angel of Hope",
            "Etali, Primal Conqueror // Etali, Primal Sickness",
            "Blightsteel Colossus",
            "Zacama, Primal Calamity",
            "Apex Altisaur",
            "Titan of Industry",
            "Vaultborn Tyrant",
            "Worldspine Wurm",
            "Vigor",
        ],
    },
    {
        "name": "Tutors",
        "description": (
            "Seven tutors cover both halves of every line: Enlightened Tutor finds Thornbite Staff, Maskwood Nexus "
            "or either Altar; Worldly Tutor, Eladamri's Call, Chord of Calling and Natural Order find Mirror Entity "
            "or a bomb; Gamble finds anything."
        ),
        "cards": [
            "Enlightened Tutor",
            "Worldly Tutor",
            "Eladamri's Call",
            "Chord of Calling",
            "Natural Order",
            "Gamble",
            "Birthing Pod",
        ],
    },
    {
        "name": "Protection for the Combo Turn",
        "description": (
            "The deck goes off at sorcery speed with the commander on the battlefield, so every protection piece "
            "is chosen to be live on that turn. Deflecting Swat and Flawless Maneuver cost nothing while Atla is "
            "out, and Clever Concealment phases the whole board out of a wipe."
        ),
        "cards": [
            "Deflecting Swat",
            "Flawless Maneuver",
            "Clever Concealment",
            "Heroic Intervention",
            "Lightning Greaves",
            "Vigor",
            "Avacyn, Angel of Hope",
        ],
    },
    {
        "name": "Interaction and Hoser Coverage",
        "description": (
            "Grafdigger's Cage is the card that beats this deck outright — creature cards in libraries can't enter "
            "the battlefield, so Atla stops hatching. Aura Shards destroys an artifact or enchantment every time a "
            "creature enters, and Krosan Grip, Force of Vigor, Boseiju and Beast Within cover artifacts, "
            "enchantments and lands between them."
        ),
        "cards": [
            "Aura Shards",
            "Krosan Grip",
            "Force of Vigor",
            "Boseiju, Who Endures",
            "Beast Within",
            "Swords to Plowshares",
            "Path to Exile",
            "Blasphemous Act",
        ],
    },
    {
        "name": "Ramp and Fixing",
        "description": (
            "Atla wants to land on turn 3 and activate the same turn, so the ramp is cheap and untapped: the "
            "Nature's Lore class fetches shock duals untapped, the auras add mana without diluting the creature "
            "count, and Jeska's Will pays for a whole combo turn."
        ),
        "cards": [
            "Sol Ring",
            "Arcane Signet",
            "Birds of Paradise",
            "Llanowar Elves",
            "Nature's Lore",
            "Three Visits",
            "Farseek",
            "Utopia Sprawl",
            "Wild Growth",
            "Jeska's Will",
            "Smothering Tithe",
        ],
    },
    {
        "name": "Card Advantage",
        "description": (
            "Draw is tied to the plan rather than bolted on: Guardian Project and Garruk's Uprising fire on the "
            "creatures Atla hatches, Skullclamp turns a 0/1 Egg into two cards, and Idol of Oblivion draws off "
            "any turn that made a token."
        ),
        "cards": [
            "Guardian Project",
            "Garruk's Uprising",
            "Sylvan Library",
            "Skullclamp",
            "Idol of Oblivion",
            "Vaultborn Tyrant",
            "Rishkar's Expertise",
        ],
    },
    {
        "name": "Key Lands",
        "description": (
            "36 lands, 35 of them untapped on arrival. Command Beacon recasts Atla past commander tax, High Market "
            "is a sacrifice outlet in a land slot, and Boseiju is removal that costs no card."
        ),
        "cards": [
            "Command Tower",
            "Command Beacon",
            "High Market",
            "Boseiju, Who Endures",
            "Jetmir's Garden",
            "Bountiful Promenade",
            "Clifftop Retreat",
            "Exotic Orchard",
        ],
    },
]

SCRY = {"type": "scryfall", "name": "Scryfall"}

HIGHLIGHTS = [
    (
        "Atla Palani, Nest Tender",
        "€0.75",
        False,
        "Commander. {2}, {T} makes a 0/1 Egg; whenever an Egg you control dies she reveals cards until she hits "
        "a creature card and puts it onto the battlefield. Every line in the deck is a way to kill Eggs faster.",
    ),
    (
        "Mirror Entity",
        "€0.57",
        False,
        "The widest line. Activate for X=0 with Atla out: every creature you control becomes a 0/0 with all "
        "creature types and dies at once, and Atla hatches a bomb for each death.",
    ),
    (
        "Maskwood Nexus",
        "€1.33",
        False,
        "Makes every creature you control every creature type, so every creature is an Egg. Turns any free "
        "sacrifice outlet into a repeatable hatch engine — three of the six verified combo lines run through it.",
    ),
    (
        "Thornbite Staff",
        "€6.28",
        False,
        "Gives Atla \"whenever a creature dies, untap this creature\". With Ashnod's Altar the hatch loop is "
        "mana-neutral. Attaches to Atla for free because she is a Shaman.",
    ),
    (
        "Ashnod's Altar",
        "€14.41",
        False,
        "Free outlet that pays you {C}{C} per Egg. The mana half of the Thornbite loop and the outlet in two of "
        "the six verified combo lines.",
    ),
    (
        "Purphoros, God of the Forge",
        "€22.42",
        False,
        "Converter and indestructible. Two damage to each opponent per hatched creature turns a single mass hatch "
        "into a table kill with no attack step.",
    ),
    (
        "Terror of the Peaks",
        "€26.12",
        False,
        "The heaviest converter: damage equal to each entering creature's power, aimed anywhere. One cascade of "
        "fatties ends the game.",
    ),
    (
        "Roaming Throne",
        "€36.67",
        False,
        "Name Shaman and Atla's death trigger fires twice — two flips per Egg. The single biggest multiplier on "
        "the engine.",
    ),
    (
        "Seedborn Muse",
        "€9.38",
        True,
        "Game Changer. Untaps Atla during every opponent's untap step: an Egg per player per turn cycle (×3 in a "
        "four-player game) while leaving mana open for Chord of Calling and free protection.",
    ),
    (
        "Natural Order",
        "€25.54",
        True,
        "Game Changer. Sacrifice a green Egg — which itself triggers Atla — and put Craterhoof Behemoth, Vigor or "
        "Worldspine Wurm straight onto the battlefield.",
    ),
    (
        "Craterhoof Behemoth",
        "€17.44",
        False,
        "The combat backup. Any board built by a cascade of hatches becomes lethal damage the turn Craterhoof "
        "arrives, hard-cast or flipped.",
    ),
    (
        "Worldspine Wurm",
        "€2.73",
        False,
        "Shuffles itself back into the library from anywhere, so it is permanent fuel for repeated Mirror Entity "
        "activations, and it leaves three 5/5 trample tokens behind each time it dies.",
    ),
]

COMBO_URLS = {
    ("Atla Palani, Nest Tender", "Maskwood Nexus", "Ashnod's Altar"): "240-643-2034",
    ("Atla Palani, Nest Tender", "Maskwood Nexus", "Phyrexian Altar"): "240-643-4050",
    ("Atla Palani, Nest Tender", "Maskwood Nexus", "Goblin Bombardment"): "240-643-5147",
    ("Atla Palani, Nest Tender", "Thornbite Staff", "Ashnod's Altar"): "240-2034-2178",
    ("Atla Palani, Nest Tender", "Mirror Entity", "Worldspine Wurm"): "240-4486-5209",
    ("Atla Palani, Nest Tender", "Mirror Entity", "Vigor"): "240-4120-4486",
}

SYNERGY_TITLES = {
    ("Atla Palani, Nest Tender", "Maskwood Nexus", "Ashnod's Altar"):
        "Maskwood Nexus + Ashnod's Altar = dump the library for mana",
    ("Atla Palani, Nest Tender", "Maskwood Nexus", "Phyrexian Altar"):
        "Maskwood Nexus + Phyrexian Altar = dump the library for colored mana",
    ("Atla Palani, Nest Tender", "Maskwood Nexus", "Goblin Bombardment"):
        "Maskwood Nexus + Goblin Bombardment = dump the library and burn the table",
    ("Atla Palani, Nest Tender", "Thornbite Staff", "Ashnod's Altar"):
        "Thornbite Staff + Ashnod's Altar = mana-neutral repeat hatching",
    ("Atla Palani, Nest Tender", "Mirror Entity", "Worldspine Wurm"):
        "Mirror Entity + Worldspine Wurm = recurring mass hatch",
    ("Atla Palani, Nest Tender", "Mirror Entity", "Vigor"):
        "Mirror Entity + Vigor = second recurring mass hatch",
}

SYNERGY_BODIES = {
    ("Atla Palani, Nest Tender", "Maskwood Nexus", "Ashnod's Altar"):
        "Maskwood Nexus makes every creature you control every creature type, so every creature you control is "
        "an Egg. Sacrifice any creature to Ashnod's Altar for {C}{C}; the Egg death triggers Atla, which puts the "
        "next creature card off the top of your library onto the battlefield; sacrifice that one too. Each "
        "iteration nets {C}{C}, so you can run through the library and finish with a huge mana pool. Any "
        "converter on the battlefield turns the chain into lethal damage.",
    ("Atla Palani, Nest Tender", "Maskwood Nexus", "Phyrexian Altar"):
        "The same line on the colored-mana altar: with Maskwood Nexus out, every creature is an Egg, so each "
        "sacrifice to Phyrexian Altar adds one mana of any color and hatches the next creature. Worth running "
        "alongside the Ashnod's version because the colored mana casts whatever the chain reveals.",
    ("Atla Palani, Nest Tender", "Maskwood Nexus", "Goblin Bombardment"):
        "With Maskwood Nexus out, Goblin Bombardment sacrifices any creature for one damage and each death "
        "hatches the next creature off the library. The chain is its own win condition — no separate converter "
        "needed — because every iteration pings a player for 1 while the board grows.",
    ("Atla Palani, Nest Tender", "Thornbite Staff", "Ashnod's Altar"):
        "Equip Thornbite Staff to Atla (free if the Staff is already out when she enters, since she is a Shaman). "
        "Pay {2} and tap Atla for a 0/1 Egg, sacrifice the Egg to Ashnod's Altar for {C}{C}, and the death untaps "
        "Atla through the Staff. Net mana zero, one hatch per loop, and it is fully deterministic — no Maskwood "
        "Nexus required.",
    ("Atla Palani, Nest Tender", "Mirror Entity", "Worldspine Wurm"):
        "Activate Mirror Entity for X=0 with Atla on the battlefield: every creature you control has base power "
        "and toughness 0/0 and gains all creature types, so they are all Eggs and all die at once. Atla triggers "
        "once per death and hatches a bomb for each. Creatures that arrive afterwards are not shrunk, because the "
        "effect locked in its set of creatures on resolution. Worldspine Wurm shuffles itself back into the "
        "library from the graveyard, so the next activation still has fuel.",
    ("Atla Palani, Nest Tender", "Mirror Entity", "Vigor"):
        "The same mass-Egg activation with Vigor as the recurring fuel: Vigor shuffles itself back into the "
        "library whenever it hits the graveyard, so repeated Mirror Entity activations keep drawing live "
        "creature cards. Vigor also prevents damage to your other creatures and converts it into +1/+1 counters, "
        "which matters when the table answers a hatched board with damage-based removal.",
}


def build_decklist():
    order = {g: i for i, g in enumerate(GROUP_ORDER)}
    rows = []
    for i, card in enumerate(SPEC["decklist"]):
        group = GROUP_FIX.get(card["name"], card["group"])
        entry = {"name": card["name"], "type": card["type"], "primary_role": card["primary_role"]}
        if card.get("wincon_style"):
            entry["wincon_style"] = card["wincon_style"]
        if card.get("quantity"):
            entry["quantity"] = card["quantity"]
        rows.append((order[group], i, entry))
    rows.sort(key=lambda r: (r[0], r[1]))
    return [r[2] for r in rows]


def build_synergies():
    out = []
    for syn in SPEC["spellbook_synergies"]:
        key = tuple(syn["cards"])
        combo_id = COMBO_URLS[key]
        url = f"https://commanderspellbook.com/combo/{combo_id}/"
        out.append(
            {
                "title": SYNERGY_TITLES[key],
                "cards": list(syn["cards"]),
                "description": SYNERGY_BODIES[key] + f" Verified line: {url}",
                "sources": [
                    {
                        "type": "commanderspellbook",
                        "name": "Commander Spellbook — " + " + ".join(syn["cards"][1:]),
                        "url": url,
                        "detail": syn["note"],
                    }
                ],
            }
        )
    return out


deck = {
    "id": SPEC["deck_id"],
    "type": "commander",
    "name": SPEC["display_name"],
    "subtitle": SPEC["subtitle"],
    "commander": SPEC["commander"],
    "bracket": SPEC["bracket"],
    "status": SPEC["status"],
    "gameChangers": SPEC["gameChangers"],
    "lastUpdatedSet": "The Hobbit",
    "archetypes": SPEC["archetypes"],
    "wincon_style": SPEC["deck_wincon_style"],
    "commanderRoles": {
        "primary": SPEC["commanderRoles"]["primary_role"],
        "secondary": SPEC["commanderRoles"]["secondary_role"],
    },
    "sources": [
        {
            "type": "other",
            "name": "Board-supplied example decklist (DEC-544)",
            "detail": (
                "Starting point given by the board on DEC-544. 14 cards carried over (Atla, Sol Ring, Arcane "
                "Signet, Skullclamp, Goblin Bombardment, Phyrexian Altar, Sylvan Library, Heroic Intervention, "
                "Etali, Zacama, Blightsteel Colossus, Titan of Industry, Command Beacon, Command Tower) plus the "
                "Nature's Lore ramp core and the shock/fetch manabase. Stats-only bodies, defensive locks, soft "
                "single-target tricks and tapped lands were dropped against the impact-on-arrival bar."
            ),
        },
        {
            "type": "edhrec",
            "name": "EDHREC — Atla Palani, Nest Tender",
            "url": "https://edhrec.com/commanders/atla-palani-nest-tender",
            "detail": (
                "DEC-402 closing diff run 2026-08-22 on the final 99. Lightning Greaves (51%) and Beast Within "
                "(43%) were added by the diff. Rejected with reasons: Etali, Primal Storm (attack-gated), Zetalpa "
                "and the Ghalta family (stats or combat only), Cultivate / Rampant Growth / Kodama's Reach "
                "(tapped-basic ramp), Dinosaur Egg (dud flip), Swiftfoot Boots, and the tapped-land cycle "
                "(Jungle Shrine, Cinder Glade, Canopy Vista). Deferred: Sundering Growth, Rhythm of the Wild."
            ),
        },
        {
            "type": "commanderspellbook",
            "name": "Commander Spellbook — find-my-combos on the exact 99",
            "url": "https://commanderspellbook.com/",
            "detail": (
                "6 included combo lines, all running through the commander: Maskwood Nexus with each of the three "
                "free outlets, Thornbite Staff + Ashnod's Altar, and Mirror Entity with Worldspine Wurm or Vigor. "
                "273 near-misses triaged and rejected — each one imports a different combo archetype's pieces and "
                "would dilute the flip quality without making the deck faster."
            ),
        },
        {
            "type": "ai-inferred",
            "name": "DEC-544 CEO deck build and soundness review (2026-08-22)",
            "detail": (
                "Strategy A (Egg-death hatching into an all-bombs library) chosen over the Dinosaur-tribal and "
                "token-swarm alternatives, then rebuilt to a true bracket 4 with a free-spell protection suite. "
                "Board-accepted amendments A1-A5. Soundness review passed four checks: metrics reproduction, "
                "full Scryfall mirror sweep (Naya identity, Commander legality, no duplicates, no board-banned "
                "price cards), internal reference check, and clause-by-clause re-derivation of the Mirror Entity "
                "and Thornbite Staff lines. Build spec: agents/ceo/analysis/dec544-build-spec.json."
            ),
        },
        {
            "type": "scryfall",
            "name": "Scryfall — oracle text verification",
            "url": "https://scryfall.com/",
            "detail": "All 100 names (99 + commander) resolved and oracle-verified against the local mirror.",
        },
    ],
    "guideContent": {
        "strategyOverview": STRATEGY,
        "deckCategories": CATEGORIES,
    },
    "winConditions": SPEC["winConditions"],
    "synergies": build_synergies(),
    "highlights": [
        {
            "name": name,
            "price": price,
            "isGameChanger": gc,
            "reason": reason,
            "sources": [dict(SCRY)],
        }
        for name, price, gc, reason in HIGHLIGHTS
    ],
    "decklist": build_decklist(),
}

total = sum(c.get("quantity", 1) for c in deck["decklist"])
assert total == 99, f"decklist total is {total}, expected 99"
spec_names = sorted(c["name"] for c in SPEC["decklist"])
built_names = sorted(c["name"] for c in deck["decklist"])
assert spec_names == built_names, "decklist names drifted from the frozen spec"

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(deck, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {OUT.relative_to(ROOT)}: {len(deck['decklist'])} entries, {total} cards")
