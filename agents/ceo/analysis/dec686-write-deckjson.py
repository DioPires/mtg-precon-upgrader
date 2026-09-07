#!/usr/bin/env python3
"""DEC-686: generate data/commanders/anvil-chorus/deck.json from the board-approved v4 99.

v4 = v1 + v2 (−Ancient Tomb/+Plains, −Teferi's Protection/+Clever Concealment,
−Wayfarer's Bauble/+Deep Gnome Terramancer) + v3 (−Irregular Cohort/−Far Traveler/+2 Plains)
+ v4 (−2 Plains/+Emeria's Call/+Witch Enchanter, −Fell the Mighty/+Razorgrass Ambush).
Sign-off: interaction 87205607, accepted 2026-09-07.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
mirror = json.load(open(ROOT / "priv_data/scryfall-oracle.json"))
by_name = {c["name"]: c for c in mirror}
front = {}
for c in mirror:
    if " // " in c["name"]:
        front.setdefault(c["name"].split(" // ", 1)[0], c["name"])


def full(name):
    if name in by_name:
        return name
    if name in front:
        return front[name]
    raise SystemExit(f"unresolved: {name}")


# (name, primary_role, secondary_role, wincon_style, is_mdfc_land, quantity)
SPEC = [
    # Dwarven fuel (16)
    ("Kíli the Resourceful", "card-draw", "utility", None),
    ("Dáin, Lord of the Iron Hills", "protection", "utility", None),
    ("Bofur, Reliable Guardian", "protection", None, None),
    ("Tataru Taru", "card-draw", "ramp", None),
    ("Priest of Ancient Lore", "card-draw", None, None),
    ("Stoic Farmer", "ramp", None, None),
    ("Fairgrounds Warden", "removal-spot", None, None),
    ("Deadeye Harpooner", "removal-spot", None, None),
    ("Ori, Plate Stacker", "removal-board", None, None),
    ("Master Skald", "recursion", None, None),
    ("Aviary Mechanic", "utility", "engine", None),
    ("Stockpiling Celebrant", "utility", "engine", None),
    ("Aethergeode Miner", "engine", None, None),
    ("Iron Hills Blacksmith", "utility", "payoff", None),
    ("Shattered Acolyte", "removal-spot", None, None),
    ("Hammers of Moradin", "threat", "utility", None),
    # Changelings (4)
    ("Mirror Entity", "wincon", "payoff", "combat"),
    ("Flock Impostor", "utility", "engine", None),
    ("Bloodline Pretender", "utility", None, None),
    ("Universal Automaton", "utility", None, None),
    # Blink value + combo (9)
    ("Felidar Guardian", "wincon", "engine", "combo"),
    ("Restoration Angel", "wincon", "protection", "combo"),
    ("Skyclave Apparition", "removal-spot", None, None),
    ("Solemn Simulacrum", "ramp", "card-draw", None),
    ("Esper Sentinel", "card-draw", None, None),
    ("Bennie Bracks, Zoologist", "card-draw", None, None),
    ("Mondrak, Glory Dominus", "engine", "payoff", None),
    ("Roaming Throne", "engine", None, None),
    ("Moonshaker Cavalry", "wincon", "payoff", "combat"),
    # Ramp creature (1)
    ("Deep Gnome Terramancer", "ramp", None, None),
    # Flicker suite (5)
    ("Ephemerate", "engine", "protection", None),
    ("Eerie Interlude", "engine", "protection", None),
    ("Semester's End", "engine", "protection", None),
    ("Teleportation Circle", "engine", None, None),
    ("Conjurer's Closet", "engine", None, None),
    # Multipliers (2)
    ("Panharmonicon", "engine", None, None),
    ("Anointed Procession", "engine", "payoff", None),
    # Anthems and finishers (4)
    ("Cathars' Crusade", "payoff", "wincon", "combo"),
    ("An Unexpected Party", "payoff", None, None),
    ("Flowering of the White Tree", "payoff", None, None),
    ("The Arkenstone", "payoff", "card-draw", None),
    # Glue (1)
    ("Maskwood Nexus", "engine", "utility", None),
    # Removal (5)
    ("Swords to Plowshares", "removal-spot", None, None),
    ("Get Lost", "removal-spot", None, None),
    ("Generous Gift", "removal-spot", None, None),
    ("Winds of Abandon", "removal-board", None, None),
    ("Austere Command", "removal-board", None, None),
    # Protection (2)
    ("Flawless Maneuver", "protection", None, None),
    ("Clever Concealment", "protection", None, None),
    # Draw engines (3)
    ("The One Ring", "card-draw", None, None),
    ("Tocasia's Welcome", "card-draw", None, None),
    ("Caretaker's Talent", "card-draw", "payoff", None),
    # Tutor (1)
    ("Enlightened Tutor", "tutor", None, None),
    # Ramp (7)
    ("Sol Ring", "ramp", None, None),
    ("Arcane Signet", "ramp", None, None),
    ("Pearl Medallion", "ramp", None, None),
    ("Herald's Horn", "ramp", "card-draw", None),
    ("Smothering Tithe", "ramp", None, None),
    ("Land Tax", "ramp", None, None),
    ("Archaeomancer's Map", "ramp", None, None),
]

LANDS = [
    ("Plains", 29),
    ("Eiganjo, Seat of the Empire", None),
    ("Minas Tirith", None),
    ("Three Tree City", None),
    ("War Room", None),
    ("Windbrisk Heights", None),
    ("Emeria, the Sky Ruin", None),
    ("Castle Ardenvale", None),
]

MDFCS = [
    ("Emeria's Call", "payoff"),
    ("Witch Enchanter", "removal-spot"),
    ("Razorgrass Ambush", "removal-spot"),
]

decklist = []
for entry in SPEC:
    name, pri, sec, ws = entry
    fname = full(name)
    card = {"name": fname, "type": by_name[fname]["type_line"], "primary_role": pri}
    if sec:
        card["secondary_role"] = sec
    if ws:
        card["wincon_style"] = ws
    decklist.append(card)

for name, qty in LANDS:
    fname = full(name)
    card = {"name": fname, "type": by_name[fname]["type_line"], "primary_role": "land"}
    if qty:
        card["quantity"] = qty
    decklist.append(card)

for name, pri in MDFCS:
    fname = full(name)
    decklist.append({
        "name": fname,
        "type": by_name[fname]["type_line"],
        "primary_role": pri,
        "is_mdfc_land": True,
    })

total = sum(c.get("quantity", 1) for c in decklist)
assert total == 99, f"decklist sums to {total}, not 99"

N = lambda n: full(n)  # noqa: E731 — short alias for card lists below

EDHREC_SRC = {
    "type": "edhrec",
    "name": "EDHREC — Fíli the Pathfinder",
    "url": "https://edhrec.com/commanders/fili-the-pathfinder",
    "detail": "12-deck page; card-by-card closing diff 2026-09-07 (DEC-402)",
}
AI_SRC = {
    "type": "ai-inferred",
    "name": "DEC-686 — board-approved v4 build (sign-off 2026-09-07)",
}
SPELLBOOK_SRC = {
    "type": "commanderspellbook",
    "name": "Commander Spellbook — Felidar Guardian + Restoration Angel",
    "url": "https://commanderspellbook.com/combo/1090-2781/",
    "detail": "Infinite ETB loop, confirmed included",
}
SCRYFALL_SRC = {
    "type": "scryfall",
    "name": "Scryfall pool sweeps",
    "detail": "id<=W t:dwarf f:commander (53 cards) + full 15-changeling and 8-MDFC sweeps, oracle-verified 2026-09-07",
}

deck = {
    "id": "anvil-chorus",
    "type": "commander",
    "name": "Anvil Chorus",
    "subtitle": "Dwarf ETB Token Engine",
    "commander": "Fíli the Pathfinder",
    "cost": "$350-450",
    "bracket": "4-",
    "status": "brewing",
    "gameChangers": 3,
    "lastUpdatedSet": "The Hobbit",
    "archetypes": ["tokens-go-wide", "etb-flicker", "changeling-omnitype-tribal"],
    "wincon_style": "combat",
    "commanderRoles": {"primary": "engine", "secondary": "payoff"},
    "sources": [AI_SRC, EDHREC_SRC, SPELLBOOK_SRC, SCRYFALL_SRC],
    "guideContent": {
        "strategyOverview": (
            "Fíli the Pathfinder pays you twice for every nontoken Dwarf that enters: a 2/2 red Dwarf token, "
            "and progress toward storied — control 3+ artifacts, legendaries, or Sagas once and Fíli's +1/+1 "
            "anthem stays on for the rest of the game (14 legendaries plus the rock suite switch it on around "
            "turn 3-4). The deck stacks three multipliers on that trigger: 16 Dwarves whose ETBs do real work, "
            "a flicker suite that re-buys those ETBs, and token doublers (Mondrak, Anointed Procession) with "
            "trigger doublers (Panharmonicon, Roaming Throne naming Dwarf). Maskwood Nexus turns every nontoken "
            "creature into a Fíli trigger. Changelings count as Dwarves natively. The primary win is go-wide "
            "combat through Moonshaker Cavalry, Mirror Entity, Cathars' Crusade, and An Unexpected Party. The "
            "ceiling line is Felidar Guardian + Restoration Angel: infinite ETBs that Cathars' Crusade converts "
            "into an arbitrarily large board (the loop pieces are not Dwarves, so Fíli adds no tokens to the "
            "loop itself). Manabase is a 38-land plan: 36 real lands plus 3 pay-life modal MDFCs, 39 "
            "land-playable cards in total."
        ),
        "deckCategories": [
            {
                "name": "Dwarven Fuel",
                "description": "Nontoken Dwarves with jobs. Each one advances the board and leaves a 2/2 behind. Draw (Kíli, Tataru Taru, Priest of Ancient Lore), removal on bodies (Fairgrounds Warden, Deadeye Harpooner, Ori, Shattered Acolyte), protection (Bofur, Dáin), ramp (Stoic Farmer), recursion (Master Skald), and re-buy loops (Aviary Mechanic, Stockpiling Celebrant, Aethergeode Miner).",
                "cards": [N(n) for n, *_ in SPEC[:16]],
            },
            {
                "name": "Changelings",
                "description": "Every changeling is a nontoken Dwarf for Fíli and every creature type for the kindred payoffs. Mirror Entity doubles as a finisher with its {X} overrun activation.",
                "cards": [N("Mirror Entity"), N("Flock Impostor"), N("Bloodline Pretender"), N("Universal Automaton")],
            },
            {
                "name": "Blink Value & Combo Core",
                "description": "Creatures whose ETBs are worth re-buying. Felidar Guardian + Restoration Angel is the infinite-ETB core; both are strong value cards alone. Skyclave Apparition and Solemn Simulacrum are premium flicker targets; Esper Sentinel and Bennie Bracks keep cards flowing.",
                "cards": [N("Felidar Guardian"), N("Restoration Angel"), N("Skyclave Apparition"), N("Solemn Simulacrum"), N("Esper Sentinel"), N("Bennie Bracks, Zoologist")],
            },
            {
                "name": "Flicker Suite",
                "description": "Every flicker of a nontoken Dwarf repeats its ETB and makes another 2/2. Eerie Interlude and Semester's End double as board-wipe insurance that returns the team with a fresh wave of triggers.",
                "cards": [N("Ephemerate"), N("Eerie Interlude"), N("Semester's End"), N("Teleportation Circle"), N("Conjurer's Closet")],
            },
            {
                "name": "Multipliers & Glue",
                "description": "Panharmonicon and Roaming Throne (naming Dwarf) double the triggers; Mondrak and Anointed Procession double the tokens (multipliers stack multiplicatively). Maskwood Nexus makes every nontoken creature a Fíli trigger — with the documented anti-synergy that Restoration Angel cannot target our all-Angel board while Nexus is out.",
                "cards": [N("Panharmonicon"), N("Anointed Procession"), N("Mondrak, Glory Dominus"), N("Roaming Throne"), N("Maskwood Nexus")],
            },
            {
                "name": "Anthems & Finishers",
                "description": "Cathars' Crusade turns every token wave (and the combo) into lethal stats. An Unexpected Party names Dwarf and its adventure half makes X 2/2 Dwarves. Flowering of the White Tree pumps the whole board. Moonshaker Cavalry is the white Craterhoof. Emeria's Call adds a flood-mode Angel burst.",
                "cards": [N("Cathars' Crusade"), N("An Unexpected Party"), N("Flowering of the White Tree"), N("The Arkenstone"), N("Moonshaker Cavalry"), N("Emeria's Call")],
            },
            {
                "name": "Interaction",
                "description": "Six removal spells plus two token-army protectors. Winds of Abandon is one-sided mass exile. Clever Concealment phases the whole board out for {W}-ish with convoke (phased tokens survive — rules changed in 2017). Witch Enchanter and Razorgrass Ambush ride land slots.",
                "cards": [N("Swords to Plowshares"), N("Get Lost"), N("Generous Gift"), N("Winds of Abandon"), N("Austere Command"), N("Flawless Maneuver"), N("Clever Concealment"), N("Witch Enchanter"), N("Razorgrass Ambush")],
            },
            {
                "name": "Draw, Tutor & Ramp",
                "description": "The One Ring, Tocasia's Welcome (MV-based, so the anthem never breaks it), and Caretaker's Talent carry card advantage. Enlightened Tutor finds the best engine piece. The ramp package leans on Plains supply — Land Tax, Archaeomancer's Map, Stoic Farmer, and Deep Gnome Terramancer all fetch basics.",
                "cards": [N("The One Ring"), N("Tocasia's Welcome"), N("Caretaker's Talent"), N("Enlightened Tutor"), N("Sol Ring"), N("Arcane Signet"), N("Pearl Medallion"), N("Herald's Horn"), N("Smothering Tithe"), N("Land Tax"), N("Archaeomancer's Map"), N("Deep Gnome Terramancer")],
            },
        ],
    },
    "winConditions": [
        {
            "title": "Felidar Guardian + Restoration Angel",
            "kind": "combo",
            "pieces": [N("Felidar Guardian"), N("Restoration Angel")],
            "cards": [N("Felidar Guardian"), N("Restoration Angel"), N("Cathars' Crusade")],
            "description": "Felidar Guardian blinks any permanent; Restoration Angel blinks any non-Angel creature. Each points at the other for infinite enter-the-battlefield triggers. The loop needs a converter: Cathars' Crusade makes the whole board arbitrarily large, then any attack wins. The pieces are not Dwarves, so Fíli adds no tokens to the loop itself. Anti-synergy note: while Maskwood Nexus is out, every creature is an Angel and Restoration Angel has no legal target — blink Nexus away first.",
        },
        {
            "title": "Go-Wide Dwarf Combat",
            "kind": "combat",
            "cards": [N("Moonshaker Cavalry"), N("Mirror Entity"), N("An Unexpected Party"), N("Cathars' Crusade"), N("Flowering of the White Tree"), N("Mondrak, Glory Dominus"), N("Anointed Procession"), N("Windbrisk Heights")],
            "description": "The default win: 2-4 tokens per turn cycle before multipliers, pumped by Fíli's storied anthem and Flowering of the White Tree, then closed with Moonshaker Cavalry's flying overrun, Mirror Entity's {X} activation, or An Unexpected Party's X-token burst into Cathars' Crusade triggers.",
        },
    ],
    "synergies": [
        {
            "title": "Felidar Guardian + Restoration Angel",
            "cards": [N("Felidar Guardian"), N("Restoration Angel")],
            "description": "The two-card infinite ETB loop that sets the deck's bracket label. Each half is a playable value blink card on its own, which is why the deck runs them without tutoring pressure.",
            "sources": [SPELLBOOK_SRC],
        },
        {
            "title": "Fíli + Roaming Throne",
            "cards": [N("Fíli the Pathfinder"), N("Roaming Throne")],
            "description": "Throne names Dwarf and doubles Fíli's token trigger: every nontoken Dwarf entering now makes two 2/2s before token multipliers, and Throne is a legendary artifact creature for storied.",
            "sources": [EDHREC_SRC, AI_SRC],
        },
        {
            "title": "Fíli + Mondrak + Anointed Procession",
            "cards": [N("Fíli the Pathfinder"), N("Mondrak, Glory Dominus"), N("Anointed Procession")],
            "description": "Token multipliers stack multiplicatively (CR 616): one trigger through both doublers makes four tokens. Every other token producer in the deck (An Unexpected Party, Emeria's Call, Caretaker's Talent) scales the same way.",
            "sources": [AI_SRC],
        },
        {
            "title": "Panharmonicon + the Dwarf ETB corps",
            "cards": [N("Panharmonicon"), N("Priest of Ancient Lore"), N("Kíli the Resourceful"), N("Ori, Plate Stacker")],
            "description": "Panharmonicon doubles every creature and artifact ETB trigger the deck is built around — draw, removal, and Fíli's own token trigger all fire twice.",
            "sources": [EDHREC_SRC, AI_SRC],
        },
        {
            "title": "Maskwood Nexus + Fíli",
            "cards": [N("Maskwood Nexus"), N("Fíli the Pathfinder")],
            "description": "Nexus makes every nontoken creature a Dwarf, so off-tribe value creatures (Skyclave Apparition, Solemn Simulacrum, Esper Sentinel) stop costing us tokens. It also feeds storied as an artifact.",
            "sources": [EDHREC_SRC, AI_SRC],
        },
        {
            "title": "Cathars' Crusade + the token stream",
            "cards": [N("Cathars' Crusade"), N("Fíli the Pathfinder"), N("An Unexpected Party")],
            "description": "Every token wave puts a +1/+1 counter on the whole army. With multiple tokens entering at once, boards grow explosively — and it is the payoff that converts the infinite blink loop into a win.",
            "sources": [EDHREC_SRC, AI_SRC],
        },
        {
            "title": "Deadeye Harpooner + flicker",
            "cards": [N("Deadeye Harpooner"), N("Ephemerate"), N("Eerie Interlude")],
            "description": "Revolt is nearly always on in a flicker deck — the flicker itself makes a permanent leave the battlefield, so Harpooner's ETB kill clause turns on when you re-buy it.",
            "sources": [AI_SRC],
        },
        {
            "title": "Bennie Bracks + the token engine",
            "cards": [N("Bennie Bracks, Zoologist"), N("Fíli the Pathfinder")],
            "description": "Bennie draws on each end step where a token was created earlier that turn — most turns in this deck, and flash plays add opponent-turn draws. Note the intervening-if: a token made during the end step itself (for example by Teleportation Circle's blink) is too late for that turn's check.",
            "sources": [AI_SRC],
        },
    ],
    "highlights": [
        {
            "name": N("The One Ring"),
            "price": "$80-100",
            "isGameChanger": True,
            "reason": "The best colorless draw engine in the format: protection from everything on entry, then an escalating draw every turn. A legendary artifact that switches storied on by itself alongside any rock.",
            "sources": [AI_SRC],
        },
        {
            "name": N("Smothering Tithe"),
            "price": "$25-35",
            "isGameChanger": True,
            "reason": "Fires on every opponent draw (×3 per turn cycle minimum) and the Treasures are artifacts for storied. Funds Mirror Entity activations and double-spell turns.",
            "sources": [EDHREC_SRC, AI_SRC],
        },
        {
            "name": N("Enlightened Tutor"),
            "price": "$25-30",
            "isGameChanger": True,
            "reason": "One mana at instant speed for the best engine piece for the board state: Cathars' Crusade, Panharmonicon, Anointed Procession, Maskwood Nexus, or The Arkenstone.",
            "sources": [AI_SRC],
        },
        {
            "name": N("Roaming Throne"),
            "price": "$35-45",
            "isGameChanger": False,
            "reason": "Named on Dwarf it doubles Fíli's token trigger and every other Dwarf's triggered ability, on a ward-2 legendary artifact body that feeds storied.",
            "sources": [EDHREC_SRC, AI_SRC],
        },
        {
            "name": N("Mondrak, Glory Dominus"),
            "price": "$25-35",
            "isGameChanger": False,
            "reason": "Token doubler on a legendary body with built-in protection via its oil-counter activation. Stacks multiplicatively with Anointed Procession.",
            "sources": [AI_SRC],
        },
        {
            "name": N("Panharmonicon"),
            "price": "$8-15",
            "isGameChanger": False,
            "reason": "Doubles every creature and artifact ETB trigger in a deck built entirely around them — including Fíli's own token trigger.",
            "sources": [EDHREC_SRC, AI_SRC],
        },
        {
            "name": N("Cathars' Crusade"),
            "price": "$8-12",
            "isGameChanger": False,
            "reason": "The payoff that scales with token count and converts the Felidar Guardian + Restoration Angel loop into an arbitrarily large board.",
            "sources": [AI_SRC],
        },
        {
            "name": N("Maskwood Nexus"),
            "price": "$8-12",
            "isGameChanger": False,
            "reason": "Every nontoken creature becomes a Fíli trigger, changelings become everything, and the Rummage-token activation converts dead artifacts into blockers. Documented anti-synergy with Restoration Angel targeting.",
            "sources": [EDHREC_SRC, AI_SRC],
        },
        {
            "name": N("An Unexpected Party"),
            "price": "$3-6",
            "isGameChanger": False,
            "reason": "Anthem that names Dwarf, and the adventure half is an X-spell token burst that scales with Mondrak, Procession, and Cathars' Crusade.",
            "sources": [EDHREC_SRC, AI_SRC],
        },
        {
            "name": N("Moonshaker Cavalry"),
            "price": "$8-14",
            "isGameChanger": False,
            "reason": "The white Craterhoof: flying plus power-equal-to-creature-count pump on a flickerable ETB body. The cleanest closer for a 10+ token board.",
            "sources": [AI_SRC],
        },
    ],
    "decklist": decklist,
}

out = ROOT / "data/commanders/anvil-chorus/deck.json"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w") as f:
    json.dump(deck, f, indent=2, ensure_ascii=False)
    f.write("\n")

uniq = len(decklist) + 1
print(f"wrote {out}: {total} cards ({uniq} unique incl. commander)")
gc = [c["name"] for c in decklist if c["name"] in ("The One Ring", "Smothering Tithe", "Enlightened Tutor")]
print("GCs present:", gc)
