"""DEC-544: emit the definitive build spec for the amended 99 (A1-A5 applied).

Output: agents/ceo/analysis/dec544-build-spec.json — the single source the
Founding Engineer builds data/commanders/broodfire-hatchery/deck.json from.
Run from repo root: uv run python agents/ceo/analysis/dec544-emit-build-spec.py
"""
import json

# Same maps as dec544-final-metrics.py (kept in lockstep; both are one-shot artifacts)
ROLE = {
    "Mirror Entity": ("wincon", "combo"),
    "Seedborn Muse": ("engine", None),
    "Palani's Hatcher": ("engine", None),
    "Nesting Dragon": ("engine", None),
    "Mondrak, Glory Dominus": ("payoff", None),
    "Birds of Paradise": ("ramp", None),
    "Llanowar Elves": ("ramp", None),
    "Zacama, Primal Calamity": ("wincon", "combat"),
    "Etali, Primal Conqueror // Etali, Primal Sickness": ("wincon", "combat"),
    "Terror of the Peaks": ("payoff", None),
    "Purphoros, God of the Forge": ("wincon", "drain"),
    "Worldspine Wurm": ("threat", None),
    "Blightsteel Colossus": ("wincon", "combat"),
    "Vigor": ("protection", None),
    "Avacyn, Angel of Hope": ("protection", None),
    "Craterhoof Behemoth": ("wincon", "combat"),
    "Elesh Norn, Mother of Machines": ("payoff", None),
    "Titan of Industry": ("threat", None),
    "Apex Altisaur": ("removal-board", None),
    "Roaming Throne": ("payoff", None),
    "Sun Titan": ("recursion", None),
    "Vaultborn Tyrant": ("card-draw", None),
    "Sol Ring": ("ramp", None),
    "Arcane Signet": ("ramp", None),
    "Skullclamp": ("card-draw", None),
    "Ashnod's Altar": ("utility", None),
    "Phyrexian Altar": ("utility", None),
    "Thornbite Staff": ("engine", None),
    "Maskwood Nexus": ("utility", None),
    "Birthing Pod": ("tutor", None),
    "Idol of Oblivion": ("card-draw", None),
    "Goblin Bombardment": ("utility", None),
    "Impact Tremors": ("payoff", None),
    "Sylvan Library": ("card-draw", None),
    "Guardian Project": ("card-draw", None),
    "Garruk's Uprising": ("card-draw", None),
    "Aura Shards": ("removal-spot", None),
    "Smothering Tithe": ("ramp", None),
    "Warleader's Call": ("payoff", None),
    "Worldly Tutor": ("tutor", None),
    "Enlightened Tutor": ("tutor", None),
    "Eladamri's Call": ("tutor", None),
    "Gamble": ("tutor", None),
    "Natural Order": ("tutor", None),
    "Chord of Calling": ("tutor", None),
    "Deflecting Swat": ("protection", None),
    "Flawless Maneuver": ("protection", None),
    "Clever Concealment": ("protection", None),
    "Heroic Intervention": ("protection", None),
    "Swords to Plowshares": ("removal-spot", None),
    "Path to Exile": ("removal-spot", None),
    "Krosan Grip": ("removal-spot", None),
    "Force of Vigor": ("removal-spot", None),
    "Blasphemous Act": ("removal-board", None),
    "Nature's Lore": ("ramp", None),
    "Three Visits": ("ramp", None),
    "Farseek": ("ramp", None),
    "Utopia Sprawl": ("ramp", None),
    "Wild Growth": ("ramp", None),
    "Jeska's Will": ("ramp", None),
    "Rishkar's Expertise": ("card-draw", None),
    "Lightning Greaves": ("protection", None),
    "Beast Within": ("removal-spot", None),
}
ADDED_TYPES = {"Lightning Greaves": "Artifact — Equipment", "Beast Within": "Instant"}
BASIC_QTY = {"Forest": 9, "Plains": 5, "Mountain": 5}
SWAPS = {
    "Witty Roastmaster": ("Bountiful Promenade", "Land", "lands"),
    "Ojer Taq, Deepest Foundation // Temple of Civilization":
        ("Vaultborn Tyrant", "Creature — Dinosaur", "creatures"),
    "Teferi's Protection": ("Clever Concealment", "Instant", "protection"),
    "Angel of the Ruins": ("Idol of Oblivion", "Artifact", "artifacts"),
    "Congregation at Dawn": ("Clifftop Retreat", "Land", "lands"),
}

rows = json.load(open("agents/ceo/analysis/dec544-final-rows.json"))
decklist = []
for r in rows:
    if r["group"] == "commander":
        continue
    if r["name"] in SWAPS:
        name, tl, group = SWAPS[r["name"]]
    else:
        name, tl, group = r["name"], r.get("type") or ADDED_TYPES[r["name"]], r["group"]
    role, wstyle = ROLE.get(name, ("land", None))
    e = {"name": name, "type": tl, "primary_role": role, "group": group}
    if wstyle:
        e["wincon_style"] = wstyle
    if name in BASIC_QTY:
        e["quantity"] = BASIC_QTY[name]
    decklist.append(e)

spec = {
    "issue": "DEC-544",
    "deck_id": "broodfire-hatchery",
    "display_name": "Broodfire Hatchery",
    "subtitle": "Every Shell Hides a Titan",
    "commander": "Atla Palani, Nest Tender",
    "status": "brewing",
    "bracket": "4",
    "bracket_note": ("Sim is the acceptance gate: comboLethal >=50% at T6 keeps "
                     "bracket '4'; otherwise relabel '4-'. 8 GCs -> relabel floor "
                     "is '4-' (GC-gated, DEC-374)."),
    "gameChangers": 8,
    "game_changer_list": ["Aura Shards", "Enlightened Tutor", "Gamble",
                          "Jeska's Will", "Natural Order", "Seedborn Muse",
                          "Smothering Tithe", "Worldly Tutor"],
    "archetypes": ["ramp-big-mana", "aristocrats"],
    "commanderRoles": {"primary_role": "engine", "secondary_role": "tutor"},
    "deck_wincon_style": "combo",
    "winConditions": [
        {
            "title": "Nest Cascade",
            "kind": "combo",
            "pieces": ["Mirror Entity"],
            "cards": ["Mirror Entity", "Worldspine Wurm", "Vigor"],
            "description": ("With Atla out, activate Mirror Entity for X=0: every "
                            "creature you control becomes a 0/0 Egg and dies. Atla "
                            "hatches a nonegg creature from the library for each "
                            "death, flooding the board with bombs. Worldspine Wurm "
                            "and Vigor shuffle back from the graveyard, so repeat "
                            "activations keep finding fuel."),
        },
        {
            "title": "Thornbite Hatch Engine",
            "kind": "combo",
            "pieces": ["Thornbite Staff", "Ashnod's Altar"],
            "cards": ["Thornbite Staff", "Ashnod's Altar", "Phyrexian Altar",
                       "Goblin Bombardment"],
            "description": ("Equip Thornbite Staff to Atla. Pay {2},{T} for an Egg, "
                            "sacrifice it to Ashnod's Altar for {C}{C}, and the "
                            "death untaps Atla via the Staff. Each mana-neutral loop "
                            "hatches a creature off the top of the library."),
        },
        {
            "title": "Hatch-and-Burn",
            "kind": "drain",
            "cards": ["Purphoros, God of the Forge", "Impact Tremors",
                       "Terror of the Peaks", "Warleader's Call"],
            "description": ("Mass hatches convert directly to noncombat damage: "
                            "each hatched bomb triggers every ETB-damage payoff, "
                            "so a Mirror Entity cascade kills the table without "
                            "attacking."),
        },
        {
            "title": "Titan Combat",
            "kind": "combat",
            "cards": ["Craterhoof Behemoth", "Blightsteel Colossus",
                       "Etali, Primal Conqueror // Etali, Primal Sickness",
                       "Zacama, Primal Calamity"],
            "description": ("The fair plan: cheat 8-plus-mana bodies into play "
                            "early through egg deaths and swing."),
        },
    ],
    "spellbook_synergies": [
        {"cards": ["Atla Palani, Nest Tender", "Maskwood Nexus", "Ashnod's Altar"],
         "note": "Maskwood makes every creature an Egg; each sac hatches."},
        {"cards": ["Atla Palani, Nest Tender", "Maskwood Nexus", "Phyrexian Altar"],
         "note": "Same line on the colored-mana altar."},
        {"cards": ["Atla Palani, Nest Tender", "Maskwood Nexus", "Goblin Bombardment"],
         "note": "Same line converting each sac into 1 damage."},
        {"cards": ["Atla Palani, Nest Tender", "Thornbite Staff", "Ashnod's Altar"],
         "note": "Mana-neutral repeat hatches; see Thornbite Hatch Engine."},
        {"cards": ["Atla Palani, Nest Tender", "Mirror Entity", "Worldspine Wurm"],
         "note": "X=0 mass-Egg with graveyard-shuffle fuel."},
        {"cards": ["Atla Palani, Nest Tender", "Mirror Entity", "Vigor"],
         "note": "Second shuffle body for the Nest Cascade."},
    ],
    "decklist": decklist,
}

total = sum(c.get("quantity", 1) for c in decklist)
assert total == 99, total
out = "agents/ceo/analysis/dec544-build-spec.json"
json.dump(spec, open(out, "w"), indent=1, ensure_ascii=False)
print(f"wrote {out}: {total} cards, {len(decklist)} entries")
