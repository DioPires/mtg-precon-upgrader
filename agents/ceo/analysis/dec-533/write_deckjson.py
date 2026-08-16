#!/usr/bin/env python3
"""DEC-533: build the remade dark-dominion deck.json (Sauron amass + Ring-temptation).

Board-approved 2026-08-16 (comment af7c6063). Reads oracle data from
final99_oracle.json (verified via Scryfall this heartbeat), writes
data/commanders/dark-dominion/deck.json. tokens[] is left empty for
compute_tokens.py to fill.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ORACLE = json.load(open(os.path.join(HERE, "final99_oracle.json")))

EDHREC = {"type": "edhrec", "name": "EDHREC Sauron, the Dark Lord",
          "url": "https://edhrec.com/commanders/sauron-the-dark-lord"}
AI = {"type": "ai-inferred", "name": "DEC-533 remake analysis",
      "detail": "Amass + Ring-temptation engine analysis, board-approved 2026-08-16"}
SCRY = {"type": "scryfall", "name": "Tolkien-set pool sweep",
        "url": "https://scryfall.com/search?q=set%3Altr+OR+set%3Altc+OR+set%3Ahob+OR+set%3Ahoc",
        "detail": "463-card Grixis pool from LTR/LTC/HOB/HOC, fetched 2026-08-16"}

# name -> (primary_role, secondary_role or None, wincon_style or None)
ROLES = {
    # creatures
    "Orcish Bowmasters": ("engine", "removal-spot", None),
    "Gothmog, Morgul Lieutenant": ("utility", None, None),
    "Grishnákh, Brash Instigator": ("utility", "removal-spot", None),
    "Corsairs of Umbar": ("engine", None, None),
    "The Mouth of Sauron": ("payoff", None, None),
    "Moria Scavenger": ("engine", None, None),
    "Mauhúr, Uruk-hai Captain": ("payoff", None, None),
    "The Great Goblin": ("engine", "card-draw", None),
    "Great Goblin, Foul-Hearted": ("engine", None, None),
    "Saruman, the White Hand": ("engine", "protection", None),
    "Moria Marauder": ("card-draw", None, None),
    "Gorbag of Minas Morgul": ("card-draw", "ramp", None),
    "Witch-king of Angmar": ("protection", None, None),
    "Warg Rider": ("engine", "utility", None),
    "Sauron, Lord of the Rings": ("wincon", "recursion", "combat"),
    "Orcish Siegemaster": ("utility", "threat", None),
    "Nazgûl": ("engine", None, None),
    # ramp
    "Sol Ring": ("ramp", None, None),
    "Arcane Signet": ("ramp", None, None),
    "Mind Stone": ("ramp", "card-draw", None),
    "Thought Vessel": ("ramp", "utility", None),
    "Relic of Sauron": ("ramp", "card-draw", None),
    "Inherited Envelope": ("ramp", None, None),
    "Talisman of Dominance": ("ramp", None, None),
    "Talisman of Indulgence": ("ramp", None, None),
    # draw
    "The One Ring": ("card-draw", "protection", None),
    "Call of the Ring": ("card-draw", None, None),
    "Palantír of Orthanc": ("card-draw", None, None),
    "Rhystic Study": ("card-draw", None, None),
    "Night's Whisper": ("card-draw", None, None),
    "Sauron's Ransom": ("card-draw", None, None),
    # tutors
    "Demonic Tutor": ("tutor", None, None),
    "Diabolic Intent": ("tutor", None, None),
    "Ringsight": ("tutor", None, None),
    # amass package
    "March from the Black Gate": ("engine", None, None),
    "Book of Mazarbul": ("engine", None, None),
    "Treason of Isengard": ("engine", "recursion", None),
    "Summons of Saruman": ("payoff", None, None),
    "Swarming of Moria": ("payoff", "ramp", None),
    "Gathering of Darkness": ("recursion", "payoff", None),
    "Along the Crooked Way": ("engine", "recursion", None),
    "Assault on Osgiliath": ("wincon", None, "combat"),
    "Foray of Orcs": ("removal-spot", "payoff", None),
    "Orcish Medicine": ("protection", "payoff", None),
    "In the Darkness Bind Them": ("engine", None, None),
    "One Ring to Rule Them All": ("wincon", "removal-board", "drain"),
    # counterspells
    "Counterspell": ("counterspell", None, None),
    "Mana Drain": ("counterspell", "ramp", None),
    "Fierce Guardianship": ("counterspell", None, None),
    "Saruman's Trickery": ("counterspell", "payoff", None),
    "Swan Song": ("counterspell", None, None),
    # protection / removal / recursion
    "Soothing of Sméagol": ("protection", "removal-spot", None),
    "Feed the Swarm": ("removal-spot", None, None),
    "Claim the Precious": ("removal-spot", None, None),
    "Flame of Anor": ("removal-spot", "card-draw", None),
    "Deadly Rollick": ("removal-spot", None, None),
    "Cyclonic Rift": ("removal-board", None, None),
    "Toxic Deluge": ("removal-board", None, None),
    "Decree of Pain": ("removal-board", "card-draw", None),
    "Reanimate": ("recursion", None, None),
    "Lightning Greaves": ("protection", None, None),
}

LAND_SECONDARY = {
    "Bojuka Bog": "utility",
    "Rogue's Passage": "utility",
    "Barad-dûr": "engine",
    "Mount Doom": "utility",
    "The Black Gate": "utility",
    "Minas Morgul, Dark Fortress": "utility",
    "Goblin-town": "utility",
    "Urborg, Tomb of Yawgmoth": "mana-fixing",
}

LANDS = [
    "Command Tower", "Exotic Orchard", "Barad-dûr", "Mount Doom",
    "The Black Gate", "Minas Morgul, Dark Fortress", "Goblin-town",
    "Rogue's Passage", "Bojuka Bog", "Urborg, Tomb of Yawgmoth",
    "Watery Grave", "Blood Crypt", "Steam Vents", "Morphic Pool",
    "Luxury Suite", "Training Center", "Sunken Hollow", "Smoldering Marsh",
    "Drowned Catacomb", "Dragonskull Summit", "Sulfur Falls",
    "Darkslick Shores", "Blackcleave Cliffs", "Gloomlake Verge",
    "Underground River", "Sulfurous Springs", "Shivan Reef",
    "Bloodstained Mire", "Polluted Delta", "Takenuma, Abandoned Mire",
    "Otawara, Soaring City", "Stormcarved Coast", "Cascade Bluffs",
]
BASICS = [("Swamp", 2), ("Island", 1), ("Mountain", 2)]

BASIC_TYPES = {"Swamp": "Land", "Island": "Land", "Mountain": "Land"}


def simple_type(name):
    if name in BASIC_TYPES:
        return BASIC_TYPES[name]
    tl = ORACLE[name]["type_line"]
    for t in ("Planeswalker", "Creature", "Land", "Artifact", "Enchantment",
              "Sorcery", "Instant", "Battle"):
        if t in tl.split("//")[0]:
            return t
    raise SystemExit(f"no type for {name}: {tl}")


def entry(name, qty=None):
    e = {"name": name, "type": simple_type(name)}
    if name in ROLES:
        p, s, w = ROLES[name]
        e["primary_role"] = p
        if s:
            e["secondary_role"] = s
        if w:
            e["wincon_style"] = w
    else:
        e["primary_role"] = "land"
        if name in LAND_SECONDARY:
            e["secondary_role"] = LAND_SECONDARY[name]
    if qty:
        e["quantity"] = qty
    return e


decklist = [entry(n) for n in ROLES] + [entry(n) for n in LANDS] \
    + [entry(n, q) for n, q in BASICS]
count = sum(e.get("quantity", 1) for e in decklist)
assert count == 99, count

deck = {
    "id": "dark-dominion",
    "type": "commander",
    "name": "Dark Dominion",
    "subtitle": "The Eye of Mordor",
    "commander": "Sauron, the Dark Lord",
    "bracket": "4-",
    "gameChangers": 6,
    "lastUpdatedSet": "The Hobbit",
    "sources": [
        EDHREC | {"detail": "Top cards and closing diff, fetched 2026-08-16"},
        SCRY,
        {"type": "other", "name": "Board directive DEC-533",
         "detail": "Full Tolkien-theme remake: amass + Ring-temptation strategy, "
                   "board-approved 2026-08-16. 74 of 99 cards carry a Tolkien-set "
                   "printing; 25 imports kept as strictly-better staples."},
        {"type": "commanderspellbook", "name": "Commander Spellbook find-my-combos",
         "detail": "0 included combos on the final 99; all 15 near-misses need "
                   "off-theme cards and were rejected (no-combo direction)"},
    ],
    "guideContent": {
        "strategyOverview": (
            "Sauron, the Dark Lord turns the whole table into fuel: every spell an "
            "opponent casts amasses Orcs 1, so one Army creature grows all game "
            "without you spending a card. When that Army connects, the Ring tempts "
            "you, and each temptation lets Sauron discard your hand and draw four "
            "cards. The deck leans into both halves. Amass multipliers (Mauhúr, "
            "The Great Goblin) turn every counter batch into extra bodies of damage, "
            "and a dense Ring-temptation package (Call of the Ring, Nazgûl, In the "
            "Darkness Bind Them, Soothing of Sméagol) keeps the draw-four engine "
            "firing every turn. Discarding your hand is a resource, not a cost: "
            "Reanimate, Gathering of Darkness, Along the Crooked Way, and Treason "
            "of Isengard buy the best cards back from the graveyard. The deck wins "
            "through combat with one enormous evasive Army (trample, menace, "
            "deathtouch, unblockable), an Assault on Osgiliath double-strike burst, "
            "The Great Goblin converting counter batches into direct damage, or the "
            "One Ring to Rule Them All mill-and-drain. 74 of the 99 cards carry a "
            "printing from the four Tolkien sets (Tales of Middle-earth, its "
            "Commander decks, The Hobbit, and The Hobbit Eternal)."
        ),
        "deckCategories": [
            {
                "name": "Amass Engine",
                "description": "Repeatable amass sources that grow the Army every turn, on top of Sauron's opponent-cast trigger.",
                "cards": ["March from the Black Gate", "Warg Rider",
                          "Great Goblin, Foul-Hearted", "Saruman, the White Hand",
                          "Corsairs of Umbar", "Moria Scavenger", "Barad-dûr",
                          "Book of Mazarbul"],
            },
            {
                "name": "Amass Multipliers & Payoffs",
                "description": "Cards that make every +1/+1 counter batch worth more: Mauhúr adds one to each batch, The Great Goblin converts each batch into 2 damage.",
                "cards": ["Mauhúr, Uruk-hai Captain", "The Great Goblin",
                          "Gothmog, Morgul Lieutenant", "Orcish Siegemaster",
                          "Grishnákh, Brash Instigator", "The Mouth of Sauron",
                          "Foray of Orcs", "Summons of Saruman"],
            },
            {
                "name": "Ring-Temptation Package",
                "description": "Every temptation is a Sauron trigger: discard your hand, draw four. Call of the Ring alone makes it fire every upkeep.",
                "cards": ["Call of the Ring", "Nazgûl", "In the Darkness Bind Them",
                          "Soothing of Sméagol", "Sauron's Ransom",
                          "Claim the Precious", "Ringsight", "Inherited Envelope",
                          "One Ring to Rule Them All", "Witch-king of Angmar"],
            },
            {
                "name": "Graveyard Dividends",
                "description": "The tempt-discard fills the bin; these cards buy the best pieces back.",
                "cards": ["Reanimate", "Gathering of Darkness",
                          "Along the Crooked Way", "Treason of Isengard",
                          "Sauron, Lord of the Rings"],
            },
            {
                "name": "Interaction Suite",
                "description": "Six counterspells plus removal that covers creatures, artifacts, and enchantments, so resolved hosers have an answer.",
                "cards": ["Counterspell", "Mana Drain", "Fierce Guardianship",
                          "Saruman's Trickery", "Swan Song", "Feed the Swarm",
                          "Flame of Anor", "Deadly Rollick", "Cyclonic Rift",
                          "Toxic Deluge", "Decree of Pain"],
            },
            {
                "name": "Card Advantage",
                "description": "Backup draw engines that keep working when the commander is locked down.",
                "cards": ["The One Ring", "Palantír of Orthanc", "Rhystic Study",
                          "Night's Whisper", "Moria Marauder",
                          "Gorbag of Minas Morgul", "Relic of Sauron"],
            },
        ],
    },
    "categories": [
        {
            "name": "Amass Engine",
            "description": "Repeatable Army growth beyond the commander's own trigger.",
            "cards": ["March from the Black Gate", "Warg Rider",
                      "Great Goblin, Foul-Hearted", "Saruman, the White Hand",
                      "Corsairs of Umbar", "Moria Scavenger", "Barad-dûr",
                      "Book of Mazarbul", "Orcish Bowmasters"],
        },
        {
            "name": "Amass Multipliers & Payoffs",
            "description": "Every counter batch gets bigger (Mauhúr) and deals damage (The Great Goblin).",
            "cards": ["Mauhúr, Uruk-hai Captain", "The Great Goblin",
                      "Gothmog, Morgul Lieutenant", "Orcish Siegemaster",
                      "Grishnákh, Brash Instigator", "The Mouth of Sauron",
                      "Foray of Orcs", "Summons of Saruman", "Goblin-town"],
        },
        {
            "name": "Ring-Temptation Package",
            "description": "Each temptation triggers Sauron: discard your hand, draw four cards.",
            "cards": ["Call of the Ring", "Nazgûl", "In the Darkness Bind Them",
                      "Soothing of Sméagol", "Sauron's Ransom", "Claim the Precious",
                      "Ringsight", "Inherited Envelope", "One Ring to Rule Them All",
                      "Witch-king of Angmar"],
        },
        {
            "name": "Graveyard Dividends",
            "description": "Cards that turn the tempt-discard into a second hand.",
            "cards": ["Reanimate", "Gathering of Darkness", "Along the Crooked Way",
                      "Treason of Isengard", "Sauron, Lord of the Rings"],
        },
        {
            "name": "Evasion & Kill Turns",
            "description": "Getting the Army through: trample, menace, unblockable, double strike.",
            "cards": ["Great Goblin, Foul-Hearted", "Warg Rider",
                      "Orcish Siegemaster", "Corsairs of Umbar", "Rogue's Passage",
                      "The Black Gate", "Assault on Osgiliath", "Mount Doom"],
        },
    ],
    "winConditions": [
        {
            "title": "Army Alpha Strike (Primary)",
            "kind": "combat",
            "cards": ["Great Goblin, Foul-Hearted", "Warg Rider",
                      "Orcish Siegemaster", "Corsairs of Umbar", "Gothmog, Morgul Lieutenant",
                      "Rogue's Passage", "The Black Gate"],
            "description": (
                "Sauron amasses on every opponent spell (about 4-6 batches per turn "
                "cycle at a 4-player table), and Mauhúr adds a counter to each batch. "
                "The Army reaches 10+ power by the mid game. Trample (Great Goblin, "
                "Foul-Hearted / Orcish Siegemaster), menace (Warg Rider), deathtouch "
                "(Gothmog, so trample only needs to assign 1 per blocker), and "
                "unblockable (Corsairs of Umbar, Rogue's Passage, The Black Gate) "
                "push that one creature through for commander-damage-scale hits, and "
                "every connection tempts you into another draw-four."
            ),
            "sources": [AI],
        },
        {
            "title": "Assault on Osgiliath Burst",
            "kind": "burst",
            "cards": ["Assault on Osgiliath"],
            "description": (
                "With any Army on board, Assault on Osgiliath for X adds X counters "
                "and gives every Goblin and Orc double strike and haste. A 10-power "
                "Army with X=5 swings for 30 double-strike damage out of nowhere; "
                "Mauhúr makes it X+1."
            ),
            "sources": [AI],
        },
        {
            "title": "The Great Goblin Batch Pings",
            "kind": "drain",
            "cards": ["The Great Goblin", "Mauhúr, Uruk-hai Captain", "Mount Doom"],
            "description": (
                "The Great Goblin deals 2 damage to a target opponent every time a "
                "counter batch lands on your Goblins, Orcs, or Armies. With Sauron "
                "converting every opponent spell into a batch, that is 8-12 damage "
                "spread across a turn cycle without attacking. Mount Doom adds a "
                "repeatable 1 damage to each opponent as a mana sink."
            ),
            "sources": [AI],
        },
        {
            "title": "One Ring to Rule Them All Drain",
            "kind": "drain",
            "cards": ["One Ring to Rule Them All"],
            "description": (
                "Chapter I mills every player equal to your Ring-bearer's power — "
                "the Army, so often 8-15 cards each. Chapter II wipes nonlegendary "
                "creatures (the Army dies, but it rebuilds from Sauron's trigger "
                "within a turn cycle). Chapter III drains each opponent for every "
                "creature card in their graveyard, which chapter I just stocked. "
                "Against creature decks this closes from 25+ life."
            ),
            "sources": [AI, EDHREC],
        },
    ],
    "synergies": [
        {
            "title": "The Table Feeds the Army",
            "cards": ["Sauron, the Dark Lord", "Mauhúr, Uruk-hai Captain",
                      "The Great Goblin"],
            "description": (
                "Every opponent spell amasses Orcs 1 (about 4-6 per turn cycle at a "
                "4-player table). Mauhúr upgrades each batch to 2 counters, and The "
                "Great Goblin converts each batch into 2 damage at an opponent. "
                "Opponents deal 8-12 damage per turn cycle just by playing Magic."
            ),
            "sources": [AI, EDHREC],
        },
        {
            "title": "Temptation Draw Engine",
            "cards": ["Sauron, the Dark Lord", "Call of the Ring", "Nazgûl",
                      "In the Darkness Bind Them"],
            "description": (
                "Every 'the Ring tempts you' is a Sauron trigger: discard your hand, "
                "draw four. Call of the Ring makes it fire every upkeep, In the "
                "Darkness Bind Them fires on every chapter, and Nazgûl converts each "
                "temptation into Wraith counters on top."
            ),
            "sources": [AI, EDHREC],
        },
        {
            "title": "Discard Is a Second Hand",
            "cards": ["Reanimate", "Gathering of Darkness", "Along the Crooked Way",
                      "Treason of Isengard"],
            "description": (
                "Sauron's draw-four costs your hand, so big creatures and spells land "
                "in the graveyard for free. Reanimate and Gathering of Darkness buy "
                "creatures back, Treason of Isengard re-buys instants and sorceries, "
                "and Along the Crooked Way amasses Goblins 1 every time a creature "
                "card leaves your graveyard."
            ),
            "sources": [AI],
        },
        {
            "title": "Sauron, Lord of the Rings Loops the Bin",
            "cards": ["Sauron, Lord of the Rings", "Reanimate", "Moria Scavenger"],
            "description": (
                "The 8-drop Sauron amasses Orcs 5 on cast, mills five, and reanimates "
                "a creature immediately — often a creature the tempt-discard binned "
                "two turns earlier. Reanimate returning him costs 8 life and skips "
                "the mana cost entirely. Moria Scavenger loots creatures into the bin "
                "on purpose."
            ),
            "sources": [AI, EDHREC],
        },
        {
            "title": "Spells Become Counters",
            "cards": ["Saruman, the White Hand", "Saruman's Trickery",
                      "Summons of Saruman"],
            "description": (
                "Saruman amasses Orcs X for every noncreature spell you cast, where X "
                "is its mana value — a Cyclonic Rift overload is amass 7. The amass "
                "counterspell and the X-spell keep the Army growing while you "
                "interact."
            ),
            "sources": [AI],
        },
        {
            "title": "Unblockable Means Tempted",
            "cards": ["Corsairs of Umbar", "Rogue's Passage", "The Black Gate",
                      "Sauron, the Dark Lord"],
            "description": (
                "Sauron's temptation trigger needs an Army to connect. Corsairs of "
                "Umbar, Rogue's Passage, and The Black Gate guarantee the hit, which "
                "guarantees the draw-four — and Corsairs amasses Orcs 3 on connection "
                "for good measure."
            ),
            "sources": [AI],
        },
        {
            "title": "Wraith Duo Punishes Everything",
            "cards": ["Witch-king of Angmar", "Nazgûl"],
            "description": (
                "Witch-king forces attackers who damage you to be sacrificed and "
                "tempts you (another draw-four), while every temptation from any "
                "source puts +1/+1 counters on both Wraiths via Nazgûl. His "
                "discard-to-indestructible cost is nearly free in a deck that treats "
                "the graveyard as a resource."
            ),
            "sources": [AI, EDHREC],
        },
        {
            "title": "No Maximum Hand Size Matters",
            "cards": ["Thought Vessel", "Relic of Sauron", "The One Ring"],
            "description": (
                "Multiple draw-fours per turn cycle overflow a normal hand. Thought "
                "Vessel and Relic of Sauron (both on-theme mana rocks) remove the "
                "cap, and The One Ring accelerates toward it."
            ),
            "sources": [AI],
        },
        {
            "title": "Punisher Draw Stacks with Amass",
            "cards": ["Rhystic Study", "Orcish Bowmasters", "Sauron, the Dark Lord"],
            "description": (
                "Opponents face a tax matrix: casting spells feeds Sauron's amass, "
                "paying or not paying feeds Rhystic Study, and drawing extra cards "
                "feeds Orcish Bowmasters, which pings and amasses again."
            ),
            "sources": [EDHREC, AI],
        },
    ],
    "highlights": [
        {
            "name": "The One Ring",
            "isGameChanger": True,
            "reason": (
                "Protection from everything on entry buys a full turn cycle, then it "
                "draws an escalating 1/2/3+ cards per turn. The tempt-discard engine "
                "even resets burden-counter life loss by dumping dead cards first. "
                "Board-approved add 2026-08-16; our owned copy is committed to "
                "gandalf-party-guest, sourcing tracked in DEC-528."
            ),
            "sources": [EDHREC, AI],
        },
        {
            "name": "Great Goblin, Foul-Hearted",
            "isGameChanger": False,
            "reason": (
                "Amass Goblins 3 on entry and on every attack, and all Armies gain "
                "trample. The single strongest repeatable grower plus the evasion the "
                "one-big-Army plan needs, in one on-theme card. Board-approved $21 "
                "pickup (The Hobbit Eternal)."
            ),
            "sources": [SCRY, AI],
        },
        {
            "name": "Mauhúr, Uruk-hai Captain",
            "isGameChanger": False,
            "reason": (
                "A 2-mana replacement effect that adds a counter to every amass batch "
                "— with 4-6 batches per turn cycle from Sauron alone, Mauhúr is worth "
                "4-6 extra power per cycle, and he makes every The Great Goblin "
                "trigger happen on bigger batches."
            ),
            "sources": [SCRY, AI],
        },
        {
            "name": "The Great Goblin",
            "isGameChanger": False,
            "reason": (
                "Turns every counter batch into 2 damage at an opponent — a win "
                "condition that never attacks — and exiles a free card to play every "
                "time another Goblin, Orc, or Army dies."
            ),
            "sources": [SCRY, AI],
        },
        {
            "name": "Orcish Bowmasters",
            "isGameChanger": True,
            "reason": (
                "Punishes every opponent draw spell with a ping and an amass batch. "
                "In a deck where each batch also triggers Mauhúr and The Great "
                "Goblin, Bowmasters scales far past its usual staple rate."
            ),
            "sources": [EDHREC],
        },
        {
            "name": "Call of the Ring",
            "isGameChanger": False,
            "reason": (
                "A guaranteed temptation every upkeep means a guaranteed Sauron "
                "draw-four every turn, plus an optional pay-2-life draw on top. The "
                "single most important engine card after the commander."
            ),
            "sources": [EDHREC, AI],
        },
        {
            "name": "Saruman, the White Hand",
            "isGameChanger": False,
            "reason": (
                "Amasses Orcs X for every noncreature spell's full mana value and "
                "gives all Goblins and Orcs ward {2}. Keeps the Army growing even "
                "when the commander is locked down."
            ),
            "sources": [SCRY, AI],
        },
        {
            "name": "Sauron, Lord of the Rings",
            "isGameChanger": False,
            "reason": (
                "Amass 5, mill 5, immediate reanimation stapled to a 9/9 trample "
                "body. The premier top-end the tempt-discard engine reanimates for "
                "one mana."
            ),
            "sources": [EDHREC, SCRY],
        },
        {
            "name": "One Ring to Rule Them All",
            "isGameChanger": False,
            "reason": (
                "Mills every player by Army power, wipes nonlegendary boards (ours "
                "rebuilds in a turn cycle), then drains for every creature card in "
                "each opponent's graveyard. A 12-power Ring-bearer commonly converts "
                "to 20+ drain."
            ),
            "sources": [EDHREC, AI],
        },
        {
            "name": "Assault on Osgiliath",
            "isGameChanger": False,
            "reason": (
                "X counters plus double strike and haste for all Goblins and Orcs — "
                "the burst finisher that turns a 10-power board into 30+ damage from "
                "an empty-looking table."
            ),
            "sources": [SCRY, AI],
        },
        {
            "name": "Witch-king of Angmar",
            "isGameChanger": False,
            "reason": (
                "A crackback deterrent (attackers who damage you get sacrificed) that "
                "tempts you for another draw-four, with a discard-to-indestructible "
                "mode this deck pays for free."
            ),
            "sources": [EDHREC],
        },
        {
            "name": "Soothing of Sméagol",
            "isGameChanger": False,
            "reason": (
                "Two-mana instant that saves Sauron from targeted removal (or "
                "bounces a resolved hoser) and tempts you — commander protection "
                "that draws four cards."
            ),
            "sources": [SCRY, AI],
        },
        {
            "name": "Rhystic Study",
            "isGameChanger": True,
            "reason": (
                "The best backup draw engine in the colors, and every opponent "
                "spell it taxes is also a Sauron amass trigger."
            ),
            "sources": [EDHREC],
        },
        {
            "name": "Cyclonic Rift",
            "isGameChanger": True,
            "reason": (
                "One-sided mass bounce that answers artifact and enchantment hosers "
                "the deck otherwise struggles with, and clears blockers for the "
                "alpha strike. Overloading it under Saruman amasses Orcs 7."
            ),
            "sources": [EDHREC],
        },
        {
            "name": "Barad-dûr",
            "isGameChanger": False,
            "reason": (
                "A land that amasses X at instant speed whenever a creature died "
                "this turn — untapped in this deck almost always, and a mana sink "
                "that rebuilds the Army after a wipe."
            ),
            "sources": [SCRY, AI],
        },
        {
            "name": "Mount Doom",
            "isGameChanger": False,
            "reason": (
                "Painless-ish dual that pings each opponent as a mana sink and "
                "carries a sorcery-speed board wipe that spares two creatures — "
                "ours: the Army and a payoff."
            ),
            "sources": [SCRY, AI],
        },
    ],
    "decklist": decklist,
    "tokens": [],
    "archetypes": ["amass-orcs", "amass-armies", "tokens-go-wide"],
    "wincon_style": "combat",
    "commanderRoles": {"primary": "engine", "secondary": "card-draw"},
}

out = os.path.join(ROOT, "data", "commanders", "dark-dominion", "deck.json")
with open(out, "w") as f:
    json.dump(deck, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"wrote {out}: {count} cards, {len(deck['highlights'])} highlights, "
      f"{len(deck['synergies'])} synergies, {len(deck['winConditions'])} winConditions")
