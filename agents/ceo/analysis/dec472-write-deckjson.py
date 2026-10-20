"""DEC-472 — generate data/commanders/gandalf-party-guest/deck.json from the
board-approved 99 (dec472-rec99.json). Roles hand-authored by the CEO.
Run AFTER board acceptance (given 2026-08-15, interaction 1f2fd513)."""
import json

REC = json.load(open("agents/ceo/analysis/dec472-rec99.json"), strict=False)
TYPES = json.load(open("agents/ceo/analysis/dec472-typelines.json"), strict=False)

BASICS = {"Island": 8, "Mountain": 5, "Plains": 4}

# (primary_role, secondary_role, wincon_style) — secondary/style may be None
ROLES = {
    # legendary Wizards — cost reducers
    "Baral, Chief of Compliance": ("ramp", "engine", None),
    "Stenn, Paranoid Partisan": ("ramp", "engine", None),
    "Kaza, Roil Chaser": ("ramp", "engine", None),
    "Vadrik, Astral Archmage": ("ramp", "engine", None),
    "Mizzix of the Izmagnus": ("ramp", "engine", None),
    # legendary Wizards — engines / payoffs
    "Kitsa, Otterball Elite": ("engine", "payoff", None),
    "Raff, Weatherlight Stalwart": ("card-draw", "engine", None),
    "Vivi Ornitier": ("engine", "payoff", None),
    "Veyran, Voice of Duality": ("engine", None, None),
    "Adeliz, the Cinder Wind": ("payoff", "threat", None),
    "Balmor, Battlemage Captain": ("payoff", "threat", None),
    "Jori En, Ruin Diver": ("card-draw", None, None),
    "Hurkyl, Master Wizard": ("card-draw", None, None),
    "Vendilion Clique": ("utility", "threat", None),
    "Venser, Shaper Savant": ("removal-spot", "utility", None),
    "Kykar, Wind's Fury": ("engine", "ramp", None),
    "Naru Meha, Master Wizard": ("wincon", "engine", "combo"),
    "Gandalf the Grey": ("engine", "utility", None),
    "Deekah, Fractal Theorist": ("payoff", "wincon", "combo"),
    # support
    "Harmonic Prodigy": ("engine", None, None),
    "Wizard's Staff": ("engine", "utility", None),
    "Archmage Emeritus": ("card-draw", "payoff", None),
    "Storm-Kiln Artist": ("ramp", "payoff", None),
    "Dualcaster Mage": ("wincon", "payoff", "combo"),
    # free-cast payoffs
    "Jeskai Revelation": ("payoff", None, None),
    "Sublime Epiphany": ("counterspell", "wincon", "combo"),
    "Temporal Mastery": ("payoff", None, None),
    "Alrund's Epiphany": ("payoff", None, None),
    # combo spells
    "Fury Storm": ("wincon", "payoff", "combo"),
    "Ghostly Flicker": ("wincon", "utility", "combo"),
    "Displace": ("wincon", "utility", "combo"),
    "Twinflame": ("wincon", "payoff", "combo"),
    "Panoptic Mirror": ("wincon", "engine", "combo"),
    # tutors
    "Mystical Tutor": ("tutor", None, None),
    "Solve the Equation": ("tutor", None, None),
    "Merchant Scroll": ("tutor", None, None),
    "Step Through": ("tutor", "utility", None),
    "Muddle the Mixture": ("tutor", "counterspell", None),
    # draw
    "Dig Through Time": ("card-draw", None, None),
    # interaction
    "Counterspell": ("counterspell", None, None),
    "Wizard's Retort": ("counterspell", None, None),
    "Dovin's Veto": ("counterspell", None, None),
    "Mystic Confluence": ("counterspell", "card-draw", None),
    "Fierce Guardianship": ("counterspell", None, None),
    "Swords to Plowshares": ("removal-spot", None, None),
    "Generous Gift": ("removal-spot", None, None),
    "Chaos Warp": ("removal-spot", None, None),
    "Erode": ("removal-spot", None, None),
    "Prismari Command": ("removal-spot", "utility", None),
    "Wear // Tear": ("removal-spot", None, None),
    "Flame of Anor": ("removal-spot", "card-draw", None),
    "Olórin's Searing Light": ("removal-board", None, None),
    "Blasphemous Act": ("removal-board", None, None),
    "Raise the Palisade": ("removal-board", None, None),
    # protection
    "Unbreakable Formation": ("protection", None, None),
    "Clever Concealment": ("protection", None, None),
    # rocks
    "Sol Ring": ("ramp", None, None),
    "Arcane Signet": ("ramp", None, None),
    "Lotus Petal": ("ramp", None, None),
    "Izzet Signet": ("ramp", None, None),
    "Mox Amber": ("ramp", None, None),
    "Talisman of Creativity": ("ramp", None, None),
    "Talisman of Progress": ("ramp", None, None),
}

CSB = lambda cid, label: {
    "type": "commanderspellbook",
    "name": label,
    "url": f"https://commanderspellbook.com/combo/{cid}/",
    "detail": "Verified on the final 99, 2026-08-15",
}
CSB_NOURL = lambda label: {
    "type": "commanderspellbook",
    "name": label,
    "detail": "Confirmed via find-my-combos on the final 99, 2026-08-15",
}
AI = lambda detail: {"type": "ai-inferred", "name": detail}

decklist = []
seen = set()
for name in REC["decklist"]:
    if name in seen:
        continue
    seen.add(name)
    t = TYPES[name]["type_line"]
    entry = {"name": name, "type": t}
    if name in BASICS:
        entry["quantity"] = BASICS[name]
    if "Land" in t.split(" — ")[0] or t.startswith("Land") or t.startswith("Basic Land"):
        entry["primary_role"] = "land"
    else:
        pr, sec, ws = ROLES[name]
        entry["primary_role"] = pr
        if sec:
            entry["secondary_role"] = sec
        if ws:
            entry["wincon_style"] = ws
    decklist.append(entry)

total = sum(e.get("quantity", 1) for e in decklist)
assert total == 99, total
untyped = [e["name"] for e in decklist if "primary_role" not in e]
assert not untyped, untyped

deck = {
    "id": "gandalf-party-guest",
    "type": "commander",
    "status": "brewing",
    "name": "Arcane Convocation",
    "subtitle": "A Council of Legendary Wizards",
    "commander": "Gandalf, Party Guest",
    "bracket": "4-",
    "gameChangers": 4,
    "lastUpdatedSet": "The Hobbit Eternal",
    "archetypes": ["spellslinger"],
    "commanderRoles": {"primary": "engine", "secondary": "payoff"},
    "wincon_style": "combo",
    "sources": [
        AI("DEC-472 board-approved build 2026-08-15 — spell-lean hybrid (interaction c571acf7), power package + speed package accepted line-by-line (interactions 835dafc8/a816e09e answered via comments df22d8be/a8b7476a, 1f2fd513)"),
        {
            "type": "scryfall",
            "name": "Scryfall census — legendary Wizards in Jeskai identity",
            "detail": "136 legendary Wizard creatures in WUR identity; 64 at MV<=3 (mirror 2026-08-15). Deck runs 19 + commander.",
        },
        {
            "type": "commanderspellbook",
            "name": "Commander Spellbook — find-my-combos on the final 99",
            "url": "https://commanderspellbook.com/",
            "detail": "13 confirmed combos on the approved list, 2026-08-15",
        },
        {
            "type": "edhrec",
            "name": "EDHREC — Gandalf, Party Guest",
            "url": "https://edhrec.com/commanders/gandalf-party-guest",
            "detail": "Commander released 2026-08-14; page near-empty at build time. DEC-402 closing diff ran on thin data; census + first principles carried the build.",
        },
    ],
    "guideContent": {
        "strategyOverview": (
            "Gandalf, Party Guest free-casts an instant or sorcery from your hand at the start of "
            "each of your combats, with mana value up to twice your legendary Wizard count — and he "
            "counts himself. Nineteen cheap legendary Wizards keep that X climbing: two extra "
            "Wizards unlock a free Sublime Epiphany, three unlock Jeskai Revelation. Every free "
            "cast still counts as casting, so the magecraft shell (Storm-Kiln Artist, Archmage "
            "Emeritus, Deekah) and the prowess legends (Adeliz, Balmor) convert each spell into "
            "mana, cards, and damage. The deck closes with compact two-card combos — Dualcaster "
            "Mage + Twinflame makes infinite hasty attackers, Naru Meha loops any blink spell for "
            "infinite magecraft triggers — found by a five-tutor suite and protected by free "
            "counters. Five cost reducers keep the plan running honestly if Gandalf is locked down."
        ),
        "deckCategories": [
            {
                "name": "Commander Engine",
                "description": "Gandalf free-casts one instant or sorcery per combat at MV up to 2x your legendary Wizards. Wizard's Staff doubles his trigger; the free spell is cast, so every cast-trigger in the deck fires.",
                "cards": ["Gandalf, Party Guest", "Wizard's Staff", "Harmonic Prodigy", "Veyran, Voice of Duality"],
            },
            {
                "name": "The Wizard Council",
                "description": "Nineteen legendary Wizards, most at three mana or less, each raising Gandalf's X by two while doing real work: cost reduction (Baral, Stenn, Kaza, Vadrik, Mizzix), card flow (Raff, Jori En, Hurkyl), and pressure (Adeliz, Balmor, Vivi).",
                "cards": [
                    "Baral, Chief of Compliance", "Stenn, Paranoid Partisan", "Kaza, Roil Chaser",
                    "Kitsa, Otterball Elite", "Balmor, Battlemage Captain", "Raff, Weatherlight Stalwart",
                    "Vivi Ornitier", "Adeliz, the Cinder Wind", "Vadrik, Astral Archmage",
                    "Jori En, Ruin Diver", "Hurkyl, Master Wizard", "Vendilion Clique",
                    "Venser, Shaper Savant", "Mizzix of the Izmagnus", "Kykar, Wind's Fury",
                    "Gandalf the Grey",
                ],
            },
            {
                "name": "Free-Cast Payoffs",
                "description": "Marquee spells Gandalf casts for free once the council assembles: Jeskai Revelation at X=8, Sublime Epiphany at X=6, and extra-turn haymakers that untap the whole board.",
                "cards": ["Jeskai Revelation", "Sublime Epiphany", "Temporal Mastery", "Alrund's Epiphany"],
            },
            {
                "name": "Combo Package",
                "description": "Two-card kills and the loops behind them. Dualcaster + Twinflame swings the same turn; Naru Meha loops Ghostly Flicker or Displace for infinite magecraft; Fury Storm goes infinite with any magecraft payoff after one commander re-cast; Panoptic Mirror locks the turn cycle.",
                "cards": [
                    "Dualcaster Mage", "Twinflame", "Naru Meha, Master Wizard", "Ghostly Flicker",
                    "Displace", "Fury Storm", "Panoptic Mirror", "Storm-Kiln Artist",
                    "Archmage Emeritus", "Deekah, Fractal Theorist",
                ],
            },
            {
                "name": "Tutors & Selection",
                "description": "Five tutors find the kill: Mystical Tutor and Solve the Equation fetch Twinflame or any combo spell, Merchant Scroll finds the blue instants, Step Through wizardcycles for either combo starter, and Muddle the Mixture transmutes for Twinflame at MV 2.",
                "cards": ["Mystical Tutor", "Solve the Equation", "Merchant Scroll", "Step Through", "Muddle the Mixture", "Dig Through Time"],
            },
            {
                "name": "Interaction & Protection",
                "description": "Five counterspells (two free on the combo turn: Fierce Guardianship, and Muddle's counter mode), spot removal on every relevant permanent type — including the artifact/enchantment hosers that target this deck — and two free-cast board protectors.",
                "cards": [
                    "Counterspell", "Wizard's Retort", "Dovin's Veto", "Mystic Confluence",
                    "Fierce Guardianship", "Swords to Plowshares", "Generous Gift", "Chaos Warp",
                    "Erode", "Prismari Command", "Wear // Tear", "Flame of Anor",
                    "Olórin's Searing Light", "Blasphemous Act", "Raise the Palisade",
                    "Unbreakable Formation", "Clever Concealment",
                ],
            },
            {
                "name": "Mana Engine",
                "description": "Seven rocks headlined by Mox Amber (21 legends keep it live) and Ancient Tomb for explosive starts, on a 36-land base tuned to the 55U/23R/13W pip census.",
                "cards": ["Sol Ring", "Arcane Signet", "Lotus Petal", "Izzet Signet", "Mox Amber", "Talisman of Creativity", "Talisman of Progress", "Ancient Tomb"],
            },
        ],
    },
    "highlights": [
        {"name": "Vivi Ornitier", "type": TYPES["Vivi Ornitier"]["type_line"]},
        {"name": "Naru Meha, Master Wizard", "type": TYPES["Naru Meha, Master Wizard"]["type_line"]},
        {"name": "Dualcaster Mage", "type": TYPES["Dualcaster Mage"]["type_line"]},
        {"name": "Twinflame", "type": TYPES["Twinflame"]["type_line"]},
        {"name": "Jeskai Revelation", "type": TYPES["Jeskai Revelation"]["type_line"]},
        {"name": "Panoptic Mirror", "type": TYPES["Panoptic Mirror"]["type_line"]},
        {"name": "Mystical Tutor", "type": TYPES["Mystical Tutor"]["type_line"]},
        {"name": "Fierce Guardianship", "type": TYPES["Fierce Guardianship"]["type_line"]},
        {"name": "Mox Amber", "type": TYPES["Mox Amber"]["type_line"]},
        {"name": "Wizard's Staff", "type": TYPES["Wizard's Staff"]["type_line"]},
    ],
    "synergies": [
        {
            "title": "Gandalf's X — every legendary Wizard is +2 mana value",
            "cards": ["Gandalf, Party Guest", "Baral, Chief of Compliance", "Vivi Ornitier", "Adeliz, the Cinder Wind", "Mizzix of the Izmagnus"],
            "description": "Gandalf counts himself, so X starts at 2. Each cheap legend adds 2: with two others he free-casts Sublime Epiphany (MV 6); with three, Jeskai Revelation (MV 7). Nineteen legendary Wizards plus draw density keep the count climbing every turn.",
            "sources": [AI("DEC-472 census + hypergeometric draw model (comment e2794449)")],
        },
        {
            "title": "Wizard's Staff doubles Gandalf's free cast",
            "cards": ["Wizard's Staff", "Gandalf, Party Guest"],
            "description": "The Staff's second ability makes a triggered ability of the equipped creature trigger an additional time — on Gandalf that is two free instants or sorceries every combat. Equip Wizard costs a single generic mana.",
            "sources": [AI("Oracle-verified 2026-08-15")],
        },
        {
            "title": "Dualcaster + Twinflame — the 2-card, 5-mana kill",
            "cards": ["Twinflame", "Dualcaster Mage"],
            "description": "Cast Twinflame on any creature you control and flash in Dualcaster holding priority; its copy targets Dualcaster itself and each token repeats the loop. Infinite hasty 2/2 attackers that swing the same turn — no payoff needed, and only 3 mana when Gandalf free-casts Twinflame at combat.",
            "sources": [CSB("147-1235", "Commander Spellbook 147-1235")],
        },
        {
            "title": "Naru Meha loops any blink spell",
            "cards": ["Naru Meha, Master Wizard", "Ghostly Flicker", "Displace", "Sublime Epiphany", "Twinflame"],
            "description": "Flash Naru in response to your own spell; her enters trigger copies it. Flicker or Displace returns Naru's trigger every loop for infinite magecraft; Sublime Epiphany's bounce mode does the same. Hold Naru in hand — her trigger only fires on entry, so a pre-cast body cannot start the loop.",
            "sources": [CSB_NOURL("Commander Spellbook — Naru Meha lines"), AI("Zone requirement (hand) confirmed in DEC-472 review, comment 92844c53")],
        },
        {
            "title": "Fury Storm scales with commander casts",
            "cards": ["Fury Storm", "Storm-Kiln Artist", "Archmage Emeritus", "Deekah, Fractal Theorist"],
            "description": "After one Gandalf re-cast, Fury Storm copies itself, and each copy triggers every magecraft permanent: infinite Treasure with Storm-Kiln in the loop lines, deck-sized draw with Archmage, a Fractal army with Deekah.",
            "sources": [CSB_NOURL("Commander Spellbook — Fury Storm lines")],
        },
        {
            "title": "Panoptic Mirror locks the turn cycle",
            "cards": ["Panoptic Mirror", "Temporal Mastery", "Alrund's Epiphany"],
            "description": "Imprint either extra-turn spell and cast it free every upkeep: consecutive extra turns while the council attacks. Both spells are also honest one-shot free-casts off Gandalf before the Mirror lands.",
            "sources": [AI("DEC-472 power-package iteration (comment 92844c53)")],
        },
        {
            "title": "Trigger doublers multiply the spell engine",
            "cards": ["Veyran, Voice of Duality", "Harmonic Prodigy", "Storm-Kiln Artist", "Archmage Emeritus", "Adeliz, the Cinder Wind"],
            "description": "Veyran doubles your own cast-triggers; Harmonic Prodigy doubles every Wizard's triggered abilities, including Gandalf's combat trigger. Stacked with the magecraft shell, each spell pays out two Treasures, two cards, or two pumps.",
            "sources": [AI("Oracle-verified interactions, DEC-472 draft review")],
        },
        {
            "title": "Mox Amber is live off 21 legends",
            "cards": ["Mox Amber", "Gandalf, Party Guest", "Vivi Ornitier"],
            "description": "Twenty legendary creatures in the 99 plus the commander mean Amber is a 0-mana rock from the moment any legend resolves — usually turn 1-2 in a deck whose curve peaks at two.",
            "sources": [AI("DEC-472 power-package acceptance (comment df22d8be)")],
        },
    ],
    "winConditions": [
        {
            "title": "Dualcaster Mage + Twinflame",
            "kind": "combo",
            "pieces": ["Twinflame", "Dualcaster Mage"],
            "cards": ["Twinflame", "Dualcaster Mage"],
            "mana_cost": 5,
            "description": "Cast Twinflame targeting a creature you control; holding priority, flash in Dualcaster Mage. Its enters trigger copies Twinflame targeting Dualcaster; the hasty token copy re-copies the original. Infinite hasty 2/2 attackers swing the same turn — Dualcaster is not legendary, so the tokens all survive. Only 3 mana when Gandalf free-casts Twinflame at combat.",
            "sources": [CSB("147-1235", "Commander Spellbook 147-1235")],
        },
        {
            "title": "Naru Meha + Ghostly Flicker / Displace",
            "kind": "combo",
            "pieces": ["Naru Meha, Master Wizard", "Ghostly Flicker"],
            "cards": ["Naru Meha, Master Wizard", "Ghostly Flicker", "Displace", "Storm-Kiln Artist", "Archmage Emeritus", "Deekah, Fractal Theorist"],
            "mana_cost": 7,
            "description": "With Naru Meha in hand, cast Flicker or Displace on any two permanents, flash in Naru in response; her trigger copies the blink spell targeting Naru plus a land, restarting her trigger each loop. Infinite casts convert through any magecraft payoff: Storm-Kiln (infinite Treasure), Archmage (draw the deck), Deekah (infinite Fractals). Never pre-cast Naru — the trigger only fires on entry.",
            "sources": [CSB_NOURL("Commander Spellbook — Naru Meha + blink lines")],
        },
        {
            "title": "Naru Meha + Twinflame",
            "kind": "combo",
            "pieces": ["Naru Meha, Master Wizard", "Twinflame"],
            "cards": ["Naru Meha, Master Wizard", "Twinflame", "Storm-Kiln Artist", "Archmage Emeritus", "Deekah, Fractal Theorist"],
            "mana_cost": 6,
            "description": "Naru's copies of Twinflame make token Narus whose legend-rule deaths do not stop the loop of copy triggers. The legend rule kills the token bodies, so this line needs a magecraft payoff on board to convert the infinite copies.",
            "sources": [CSB("141-1235", "Commander Spellbook 141-1235")],
        },
        {
            "title": "Fury Storm + magecraft payoff",
            "kind": "combo",
            "pieces": ["Fury Storm", "Storm-Kiln Artist"],
            "cards": ["Fury Storm", "Storm-Kiln Artist", "Archmage Emeritus", "Deekah, Fractal Theorist"],
            "mana_cost": 4,
            "description": "With one prior commander re-cast, Fury Storm's cast trigger copies it; pointing copies at each other with Storm-Kiln out nets Treasure per iteration — infinite Treasure, then infinite draw or Fractals through the other payoffs.",
            "sources": [CSB_NOURL("Commander Spellbook — Fury Storm lines")],
        },
        {
            "title": "Panoptic Mirror extra-turn lock",
            "kind": "combo",
            "pieces": ["Panoptic Mirror", "Temporal Mastery"],
            "cards": ["Panoptic Mirror", "Temporal Mastery", "Alrund's Epiphany"],
            "mana_cost": 5,
            "description": "Imprint Temporal Mastery or Alrund's Epiphany on the Mirror and take every turn: the council plus Epiphany's birds attack each extra turn while opponents never untap. Wins through combat inside the lock.",
            "sources": [AI("DEC-472 power package, board-accepted (comment df22d8be)")],
        },
        {
            "title": "Council combat — prowess legends and Fractals",
            "kind": "combat",
            "cards": ["Adeliz, the Cinder Wind", "Balmor, Battlemage Captain", "Deekah, Fractal Theorist", "Kykar, Wind's Fury", "Vivi Ornitier"],
            "description": "The honest line: free spells every combat pump Adeliz and Balmor teams, Deekah manufactures X/X Fractals, Kykar makes Spirits per spell, and Vivi burns each opponent on every noncreature cast. Low B4 games this deck does not combo out, it closes with tempo damage.",
            "sources": [AI("DEC-472 spell-lean hybrid direction (interaction c571acf7)")],
        },
    ],
    "decklist": decklist,
}

path = "data/commanders/gandalf-party-guest/deck.json"
import os
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
    json.dump(deck, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("wrote", path, "— decklist entries:", len(decklist), "cards:", total)
