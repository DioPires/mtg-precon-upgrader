#!/usr/bin/env python3
"""Export mana simulation results as JSON for commander decks.

Imports each simulation module under a namespace (they share function names),
runs the simulations, and writes structured JSON to
data/commanders/{id}/simulation.json.
"""

import argparse
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
import traceback
from collections import Counter
from datetime import date
from pathlib import Path

# Add scripts dir to path for imports
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import mana_simulation_titan_convergence as sim_titan
import mana_simulation_eternal_agony as sim_rakdos
import mana_simulation_gathering_shadow as sim_grixis
import mana_simulation_eternal_harvest as sim_golgari
import mana_simulation_witherbloom_the_balancer as sim_witherbloom
import mana_simulation_the_white_forge as sim_mono_white
import mana_simulation_verdant_tide as sim_mono_green
import mana_simulation_creeping_corruption as sim_wubg_poison
import mana_simulation_grave_dividends as sim_grave_dividends
import mana_simulation_hoard_and_bleed as sim_hoard_and_bleed
import mana_simulation_hidden_legion as sim_hidden_legion
import mana_simulation_zada_hedron_grinder as sim_zada
import mana_simulation_exponential_growth as sim_exponential_growth
import mana_simulation_slivers as sim_slivers
import mana_simulation_stampede_acres as sim_stampede_acres
import mana_simulation_tidal_legion as sim_tidal_legion
import mana_simulation_armory_protocol as sim_armory_protocol
import mana_simulation_shield_doctrine as sim_shield_doctrine
import mana_simulation_gandalf_party_guest as sim_gandalf
import mana_simulation_broodfire_hatchery as sim_broodfire_hatchery
import mana_simulation_anvil_chorus as sim_anvil_chorus
import gate_tags_lib

PROJECT_ROOT = SCRIPTS_DIR.parent
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"

NUM_GAMES = 100_000
NUM_TURNS = 10
# The mana sims take the goldfish's scheme (DEC-363): run_parallel splits the
# games into MANA_SIM_CHUNKS fixed chunks whatever the CPU count, and each chunk
# seeds `random` with MANA_SIM_SEED + its index inside the worker. Two runs on
# one tree and one input then write equal files on any machine. (DEC-1115)
MANA_SIM_CHUNKS = 16
MANA_SIM_SEED = 0xDEC1115
GOLDFISH_GAMES = 10_000
GOLDFISH_MEANINGFUL_PRESSURE_FLOOR = 6
GOLDFISH_LETHAL_DAMAGE_PROXY = 40
# Fixed chunking + base seed make the Monte Carlo reproducible regardless of CPU
# count: the goldfish numbers (and the tutor-aware combo-assembly curves derived
# from them) stop wiggling on every regen. (DEC-363)
GOLDFISH_CHUNKS = 16
GOLDFISH_SEED = 0xDEC363

# DEC-365 — comboConsistency confidence multiplier keyed by deck-level
# `wincon_style`. Scales the assembly *bonus above the 50 floor* (never the 50
# floor itself, so declaring a combo still can't hurt — DEC-362 #1): a combo is
# the gameplan for combo decks (full weight) but only a backup line for
# value/aggro decks (reduced). Combo-less decks sit at 50 regardless, so this
# only moves decks that actually declared and can assemble a combo. The enum
# mirrors the `wincon_style` set keyed in compute_deck_metrics.py.
WINCON_COMBO_WEIGHT: dict[str | None, float] = {
    "combo":             1.00,  # combo IS the gameplan
    "value-incremental": 0.50,  # engine is the plan; combo a secondary line
    "drain":             0.50,
    "drain-x":           0.50,
    "mixed":             0.50,
    "combat":            0.25,  # creature-centric; combo incidental
    "discrete-threats":  0.25,
}
WINCON_COMBO_WEIGHT_DEFAULT = 0.50  # unset / unknown style

DRAW_PATTERNS = (
    r"\bdraws?\b",
    r"\binvestigate\b",
    r"\bsurveil\b",
    r"\block\b",
    r"\bconnive\b",
)

INTERACTION_PATTERNS = (
    r"\bcounter target\b",
    r"\bdestroy target\b",
    r"\bexile target\b",
    r"\breturn target\b",
    r"\bfight target\b",
    # Targeted burn / removal: catches "deals 3 damage to any target" (Lightning Bolt),
    # "to target creature/player/planeswalker", and X-damage variants. Requires a
    # "target" so table-wide pingers ("deals 1 damage to each opponent") stay excluded.
    r"\bdeals? (?:\d+|x) damage to (?:any )?target\b",
    # Board wipes count as interaction. Keyed on phrasings unique to sweepers so anthems
    # ("get +1/+1") and pingers ("to each opponent") don't match.
    r"\bdamage to each creature\b",
    r"\bcreatures? gets? -[\dx]",
    r"\bdestroy all (?:creatures|nonland|other)\b",
    r"\btarget player sacrifices\b",
    r"\beach opponent sacrifices\b",
    r"\bprevent all combat damage\b",
    r"\bcan\'t attack\b",
    r"\bcan\'t block\b",
)

THREAT_EXCLUDED_CATEGORY_TERMS = (
    "land", "mana", "ramp", "draw", "interaction", "removal", "tutor",
)

THREAT_TYPE_MARKERS = ("Creature", "Planeswalker", "Battle")
THREAT_ORACLE_PATTERNS = (
    r"\byou win the game\b",
    r"\bextra turn\b",
    r"\bdouble\b.*\btoken\b",
    r"\bwhenever .* loses life\b",
    r"\bwhenever .* create\b",
    r"\bproliferate\b",
)

COMMANDER_ENGINE_PATTERNS = (
    r"\bdraws?\b",
    r"\bcreate\b",
    r"\bproliferate\b",
    r"\badd\b",
    r"\bsacrifice\b",
    r"\breturn\b.*\bfrom your graveyard\b",
)

COLOR_SYMBOLS = "WUBRGC"
LAND_SUBTYPE_COLORS = {
    "Plains": "W",
    "Island": "U",
    "Swamp": "B",
    "Mountain": "R",
    "Forest": "G",
}
# The one word-to-number table: card counts ("two lands", "create two
# tokens", "seven or more lands").
COUNT_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
               "seven": 7}
COLOUR_WORDS = {"white": "W", "blue": "U", "black": "B", "red": "R", "green": "G"}
# A creature that is not one while a condition holds: "As long as <condition>,
# <name> isn't a creature." A Theros god's condition is its devotion.
NOT_CREATURE_WHILE = re.compile(r"As long as ([^.\n]*), [^.\n]* isn't a creature")
DEVOTION_BELOW = re.compile(r"your devotion to (\w+)(?: and (\w+))? is less than (\w+)")

# KEY_COMBOS slot schema (DEC-363): a combo is a list of *slots*; the combo is
# assembled when every slot is filled. A slot is a list of interchangeable cards
# — any one of them fills the slot — and a card may join a slot only if it
# *independently* completes that slot's function (e.g. any noncombat-damage
# doubler for Heartless Hidetsugu). No padding. Back-compat: a combo declared
# with a bare "pieces" list is read as one 1-card slot per piece. The commander,
# when named in a slot, fills it from the command zone automatically. A slot
# written {"members": [...], "noPriority": True} (owner decision 27,
# 2026-11-25, 6b) fills like any other, but its cards are not line members by
# it: no cast priority, paid-mulligan keep or imprint protection
# (build_goldfish_context).
KEY_COMBOS = {
    # gathering-shadow: Oracle Consultation removed in the DEC-533 remake — the
    # Thoracle/Consultation shell was cut with the strategy change. Commander
    # Spellbook finds zero included combos on the amass/Ring-temptation 99
    # (2026-08-16); the deck deliberately has NO entry (combat/attrition deck,
    # mirrors the exponential-growth precedent).
    "eternal-agony": [
        {
            "name": "Hidetsugu Lethal",
            "slots": [
                ["Heartless Hidetsugu"],
                [
                    "Solphim, Mayhem Dominus",
                    "Twinflame Tyrant",
                    "Bloodletter of Aclazotz",
                    "Wound Reflection",
                ],
            ],
            "requiresCommander": False,
            "description": "A doubler of damage or life loss to opponents makes a Heartless "
                           "Hidetsugu activation (half each player's life) lethal at even life "
                           "totals (Spellbook 3011-4847, 3011-6093, 3011-4475; Wound Reflection "
                           "makes each opponent lose the same life again at the end step); Fiery "
                           "Emancipation is not one: it triples the damage to you too.",
        }
    ],
    "eternal-harvest": [
        {
            "name": "Ballista Undying",
            "slots": [
                ["Walking Ballista"],
                ["Mikaeus, the Unhallowed"],
                # A drain payoff or a free outlet; added without cast priority
                # (owner decision 27, 6b).
                {
                    "members": [
                        "Blood Artist", "Zulaport Cutthroat", "Bastion of Remembrance",
                        "Sephiroth, Fabled SOLDIER", "Ashnod's Altar", "Phyrexian Altar",
                        "Altar of Dementia",
                    ],
                    "noPriority": True,
                },
            ],
            "requiresCommander": False,
            "description": "Walking Ballista and Mikaeus loop deaths without end (Spellbook "
                           "628-3693); a drain payoff, or a free outlet that lets each counter "
                           "ping an opponent, makes it a kill.",
        }
    ],
    "the-white-forge": [
        {
            "name": "Heliod Ballista",
            "pieces": ["Heliod, Sun-Crowned", "Walking Ballista"],
            "requiresCommander": False,
            "description": "Infinite damage via lifelink counter loop.",
        }
    ],
    "titan-convergence": [
        {
            # Owner decision 27 (2026-11-25, tick K4): rewritten from the
            # mana loop alone (Basalt Monolith with Rings of Brighthearth or
            # Forsaken Monument) to a line that names its finish.
            "name": "Basalt Rings Top Fleshraker",
            "slots": [
                ["Basalt Monolith"],
                ["Rings of Brighthearth"],
                ["Sensei's Divining Top"],
                ["Glaring Fleshraker"],
            ],
            "requiresCommander": False,
            "description": "Rings of Brighthearth copies Basalt Monolith's untap for unbounded "
                           "colorless mana (Spellbook 4131-4235) and Sensei's Divining Top's draw, "
                           "returning Top to hand; each recast makes a Spawn that Glaring Fleshraker "
                           "turns into 1 damage to each opponent. Needs {2} to start; one library "
                           "card per cycle.",
        }
    ],
    # creeping-corruption: Vorinclex + Vraska removed (owner decision 27,
    # 2026-11-25, tick K5): it kills only the targeted opponent, who must have
    # eight or fewer poison counters (Spellbook 1529-1887), not the table. The
    # deck has NO entry.
    "anvil-chorus": [
        {
            "name": "Blink Loop Lethal",
            # Felidar Guardian + Restoration Angel is infinite ETBs but not a
            # win by itself (the loop pieces are not Dwarves — Fíli adds no
            # tokens); Cathars' Crusade is the in-deck converter that makes the
            # board arbitrarily large. Lethal on the next combat.
            "pieces": ["Felidar Guardian", "Restoration Angel", "Cathars' Crusade"],
            "requiresCommander": False,
            "description": "Felidar Guardian and Restoration Angel blink each other for "
                           "infinite ETB triggers; Cathars' Crusade converts the loop into "
                           "an arbitrarily large board.",
        }
    ],
    # hidden-legion: Snoop+Kiki+Tremors combo cut in DEC-373 (1.4% assembly by T7 — phantom line).
    "grave-dividends": [
        {
            "name": "Recursive-ETB + Death-Return Aura + Free Outlet",
            "slots": [
                ["Sun Titan", "Angel of Indemnity"],
                ["Kaya's Ghostform", "Gift of Immortality", "Angelic Renewal", "Necrogen Communion"],
                ["Viscera Seer", "Carrion Feeder", "Ashnod's Altar", "Umbral Collar Zealot"],
                ["Blood Artist", "Zulaport Cutthroat", "Elas il-Kor, Sadistic Pilgrim",
                 "Bastion of Remembrance", "Marionette Apprentice"],
            ],
            "requiresCommander": False,
            "description": "Enchant a recursive-ETB creature with a cheap death-return aura it can "
                           "rebuy on enter; sac to a free outlet — the aura returns the body, the "
                           "body returns the aura. Infinite death + ETB; any drain payoff wins. "
                           "(Spellbook 2292-2730-3175.) Shepherd of the Cosmos is left out: it "
                           "returns mana value 2 or less, not Gift of Immortality.",
        },
        {
            "name": "Leonin Relic-Warder + Reanimation Aura",
            "slots": [
                ["Leonin Relic-Warder"],
                ["Animate Dead", "Necromancy"],
                ["Blood Artist", "Zulaport Cutthroat", "Elas il-Kor, Sadistic Pilgrim",
                 "Bastion of Remembrance", "Marionette Apprentice"],
            ],
            "requiresCommander": False,
            "description": "Reanimate Relic-Warder; its ETB exiles the aura, the aura leaving makes "
                           "Relic-Warder be sacrificed, returning the aura to reanimate it again. "
                           "Two-card infinite ETB/LTB — any drain payoff closes.",
        },
        {
            "name": "Plunderer + Ashnod's Altar + Reassembling Skeleton",
            "slots": [
                ["Pitiless Plunderer"],
                ["Ashnod's Altar"],
                ["Reassembling Skeleton"],
                ["Blood Artist", "Zulaport Cutthroat", "Bastion of Remembrance",
                 "Elas il-Kor, Sadistic Pilgrim", "Marionette Apprentice"],
            ],
            "requiresCommander": False,
            "description": "Sac Skeleton to Altar ({C}{C}) + Plunderer Treasure covers the "
                           "{1}{B} rebuy — infinite mana + infinite death triggers drain the table. "
                           "(Spellbook 1580-2034-4871.)",
        },
    ],
    # hoard-and-bleed (DEC-543): both lines are Commander Spellbook `included[]`
    # entries on the committed 99, with manaNeeded "". The payoff slots differ
    # between the two lines because the loops move different objects, so they are
    # NOT interchangeable — see each slot's note.
    "hoard-and-bleed": [
        {
            "name": "Plunderer + Ashnod's Altar + Reassembling Skeleton",
            "slots": [
                ["Pitiless Plunderer"],
                ["Ashnod's Altar"],
                ["Reassembling Skeleton"],
                # Each iteration sacrifices the Skeleton, creates a Treasure,
                # sacrifices that Treasure and returns the Skeleton. So every
                # payoff below fires: creature death, artifact-to-graveyard,
                # artifact entering, and token created/sacrificed all happen.
                # Exsanguinate qualifies because the loop nets {C} per iteration
                # (in {C}{C}{B}, out {1}{B}); it needs one black mana beyond the
                # last Treasure. Goblin Bombardment (owner decision 27, tick
                # K10) is a sacrifice outlet that alternates with the Altar.
                [
                    "Marionette Apprentice", "Marionette Master", "Mayhem Devil",
                    "Mirkwood Bats", "Reckless Fireweaver", "Weftstalker Ardent",
                    "The Sackville-Bagginses", "Exsanguinate", "Goblin Bombardment",
                ],
            ],
            "requiresCommander": False,
            "description": "Sacrifice Reassembling Skeleton to Ashnod's Altar for {C}{C}; "
                           "Pitiless Plunderer makes a Treasure, which pays part of the "
                           "{1}{B} rebuy. Nets {C} per loop, so infinite colorless mana plus "
                           "infinite death, sacrifice and artifact triggers. Goblin Bombardment "
                           "alternates with the Altar; Exsanguinate needs one black mana beyond "
                           "the last Treasure (Spellbook 1580-2034-4871).",
        },
        {
            "name": "Mycosynth Lattice free-loop",
            "slots": [
                ["Mycosynth Lattice"],
                # Under Lattice the Skeleton is an artifact, so Krark-Clan
                # Ironworks can eat it too; either outlet alone closes the loop.
                ["Ashnod's Altar", "Krark-Clan Ironworks"],
                ["Reassembling Skeleton"],
                # No Treasure and no token in this loop, and it nets zero mana:
                # {C}{C} in, {2} out (Lattice lets the {B} be paid with anything).
                # So Mirkwood Bats, The Sackville-Bagginses and Exsanguinate are
                # deliberately absent from this slot.
                [
                    "Marionette Apprentice", "Marionette Master", "Mayhem Devil",
                    "Reckless Fireweaver", "Weftstalker Ardent",
                ],
            ],
            "requiresCommander": False,
            "description": "Mycosynth Lattice makes the Skeleton an artifact and lets any mana "
                           "pay its {1}{B}. Sacrifice it to either free outlet for {C}{C} and "
                           "rebuy for {2} — a net-zero, infinitely repeatable death loop.",
        },
    ],
    # hoard-and-bleed deliberately omits two other Spellbook `included[]` lines.
    # Mycosynth Lattice + Hellkite Tyrant wins at upkeep but is combat-gated —
    # Spellbook itself lists "An opponent cannot block Hellkite Tyrant" as a
    # prerequisite, which a solitaire model cannot check. Mycosynth Lattice +
    # Vandalblast is mass land denial, not a win, so it does not belong in a
    # combo-assembly tracker.
    # zada-hedron-grinder: Reiterate with Mana Geyser or Jeska's Will removed
    # (owner decision 27, 2026-11-25, tick K12): its included records need an
    # opponent's state the goldfish does not have (six or more tapped lands,
    # six or more cards in hand).
    "zada-hedron-grinder": [
        {
            "name": "Reiterate Seething Song",
            "slots": [
                ["Reiterate"],
                ["Seething Song", "Blazing Firesinger // Seething Song"],
                ["Birgi, God of Storytelling // Harnfel, Horn of Bounty",
                 "Storm-Kiln Artist", "Ruby Medallion", "Bonus Round", "Spinerock Tyrant"],
                ["Grapeshot"],
            ],
            "requiresCommander": False,
            "description": "Reiterate with buyback copying Seething Song is mana-neutral with "
                           "Birgi or Ruby Medallion and gains with Storm-Kiln Artist or Bonus "
                           "Round or Spinerock Tyrant; storm grows and Grapeshot closes, given "
                           "the start mana for Song and Reiterate with buyback (Spellbook "
                           "3368-4036-5195 and siblings).",
        },
        {
            # Kiki-Jiki has no slot (tick K14): Recruiter stacks it from the
            # library, which is not tracked, so a game where it was drawn is
            # also counted (the line fails there).
            "name": "Snoop Kiki Tokens",
            "slots": [
                ["Conspicuous Snoop"],
                ["Goblin Recruiter"],
                ["Impact Tremors", "Goblin Bombardment", "General Kreat, the Boltbringer",
                 "Boggart Shenanigans", "Pashalik Mons"],
            ],
            "requiresCommander": False,
            "description": "Recruiter stacks Kiki-Jiki on top (it must still be in the library); "
                           "Snoop gains Kiki's ability and copies itself without end; any of five "
                           "payoffs turns the tokens into damage (mechanism of Spellbook "
                           "618-1827-2240).",
        },
    ],
    # broodfire-hatchery (DEC-544/DEC-550): slot spec authored by the CEO. Atla
    # Palani is the commander (command zone) — she is never a slot, but all three
    # loops need her on the battlefield, so each line is requiresCommander.
    "broodfire-hatchery": [
        {
            "name": "Maskwood Nexus Hatch Loop",
            # Maskwood Nexus makes every creature an Egg; any free repeatable
            # sac outlet then hatches the library. All three outlets
            # independently complete the outlet slot.
            "slots": [
                ["Maskwood Nexus"],
                ["Ashnod's Altar", "Phyrexian Altar", "Goblin Bombardment"],
            ],
            "requiresCommander": True,
            "description": "Maskwood Nexus makes every creature you control an Egg, so "
                           "Atla Palani's dies trigger fires off any creature. A free "
                           "repeatable sacrifice outlet — Ashnod's Altar, Phyrexian Altar "
                           "or Goblin Bombardment — converts the board into creature cards "
                           "revealed off the top of the library, over and over.",
        },
        {
            "name": "Thornbite Hatch Engine",
            # Thornbite Staff equipped to Atla + Ashnod's Altar — mana-neutral
            # hatch loop.
            "slots": [
                ["Thornbite Staff"],
                ["Ashnod's Altar"],
            ],
            "requiresCommander": True,
            "description": "Equip Thornbite Staff to Atla. Pay {2},{T} for a 0/1 Egg, "
                           "sacrifice it to Ashnod's Altar for {C}{C}, and the Staff's "
                           "\"whenever a creature dies, untap this creature\" resets Atla "
                           "— each mana-neutral loop hatches a creature off the top of the "
                           "library.",
        },
        # DEC-935 (2026-09-30): the Mirror Entity X=0 mass-hatch line was removed
        # with the combat remake (Mirror Entity cut, board verdict card 5e9a7eeb).
    ],
    "shield-doctrine": [
        {
            "name": "Feast and Famine Assault",
            "pieces": ["Sword of Feast and Famine", "Aggravated Assault"],
            "requiresCommander": False,
            "description": "Sword of Feast and Famine untaps all lands on combat damage; "
                           "Aggravated Assault converts {3}{R}{R} into an extra combat — "
                           "every connect pays for the next attack step.",
        }
    ],
    "stampede-acres": [
        {
            "name": "Scurry Rosie Squirrels",
            "slots": [
                ["Scurry Oak"],
                ["Rosie Cotton of South Lane"],
                # Added without cast priority (owner decision 27, 6b). A payoff
                # fills the slot without the commander, so the line is not
                # requiresCommander.
                {
                    "members": [
                        "Baylen, the Haymaker", "Impact Tremors", "Purphoros, God of the Forge",
                        "Warleader's Call",
                    ],
                    "noPriority": True,
                },
            ],
            "requiresCommander": False,
            "description": "Rosie Cotton and Scurry Oak make Squirrels without end once started "
                           "(the Oak out before Rosie, or a later token or counter; Spellbook "
                           "2433-4186); Impact Tremors, Purphoros or Warleader's Call already out "
                           "kills, and Baylen draws to Halo Fountain or to a payoff, which needs "
                           "token creation restarted after it is cast.",
        }
    ],
    "witherbloom-the-balancer": [
        {
            "name": "Sprout Swarm Buyback",
            "slots": [
                ["Witherbloom, the Balancer"],
                ["Sprout Swarm"],
                # Added without cast priority (owner decision 27, 6b).
                {
                    "members": ["Witherbloom Apprentice", "Exsanguinate", "Torment of Hailfire"],
                    "noPriority": True,
                },
            ],
            "requiresCommander": True,
            "description": "Witherbloom's affinity lets Sprout Swarm with buyback recast itself "
                           "once about four creatures and green mana are out: unbounded Saprolings "
                           "and storm (Spellbook 3209-7496). Witherbloom Apprentice drains each "
                           "opponent per cast; Exsanguinate or Torment of Hailfire, X paid by "
                           "affinity and {B}{B} from outside the loop, kills.",
        },
        {
            "name": "Altar Skeleton Loop",
            "slots": [
                ["Ashnod's Altar"],
                ["Pitiless Plunderer"],
                ["Reassembling Skeleton"],
                ["Blood Artist", "Zulaport Cutthroat", "Bastion of Remembrance",
                 "Cauldron of Essence", "Arnyn, Deathbloom Botanist"],
            ],
            "requiresCommander": False,
            "description": "Ashnod's Altar, Pitiless Plunderer and Reassembling Skeleton loop "
                           "deaths and mana without end (Spellbook 1580-2034-4871); a drain "
                           "payoff kills.",
        },
        {
            "name": "Altar Sprout Doubling",
            "slots": [
                ["Sprout Swarm"],
                ["Ashnod's Altar"],
                ["Parallel Lives"],
                # Added without cast priority (owner decision 27, 6b).
                {
                    "members": [
                        "Witherbloom Apprentice", "Blood Artist", "Zulaport Cutthroat",
                        "Bastion of Remembrance", "Cauldron of Essence",
                        "Arnyn, Deathbloom Botanist", "Exsanguinate", "Torment of Hailfire",
                    ],
                    "noPriority": True,
                },
            ],
            "requiresCommander": False,
            "description": "Sprout Swarm, Ashnod's Altar and Parallel Lives make unbounded "
                           "Saprolings and colorless mana once started (up to {7}{G}, Spellbook "
                           "2034-2557-3209); a drain payoff, or Exsanguinate or Torment of "
                           "Hailfire with {B}{B} from outside the loop, kills.",
        }
    ],
    "gandalf-party-guest": [
        {
            # Fury Storm copies itself once per prior commander cast from the
            # command zone — with zero casts it makes no copies, so the line is
            # commander-gated. requiresCommander flags commander dependency
            # (resilience component); it does not delay the assembly-turn
            # measurement.
            "name": "Fury Storm Magecraft",
            "slots": [
                ["Fury Storm"],
                ["Storm-Kiln Artist"],
                # Added without cast priority (owner decision 27, 6b).
                {"members": ["Twinflame"], "noPriority": True},
            ],
            "requiresCommander": True,
            "description": "After Gandalf has been cast from the command zone, Fury Storm's "
                           "copies make Treasures through Storm-Kiln Artist without end "
                           "(Spellbook 2655-5195); Fury Storm's copies also copy Twinflame onto "
                           "the Artist: three hasty Artists, one per opponent, before attackers "
                           "are declared.",
        }
    ],
    # DEC-370 note: exponential-growth was audited and deliberately has NO entry —
    # Commander Spellbook finds zero included combos (Simic Ascendancy is a
    # non-deterministic engine payoff, not an assembly combo). Its 50-floor
    # comboConsistency is accurate, not measurement debt.
}

# DEC-385 — commander-granted cascade. The goldfish scores one spell per cast,
# so commanders like Zhulodok, Void Gorger (colorless 7+ MV spells cast from
# hand gain "Cascade, cascade") turn every qualifying cast into ~3 spells the
# sim never saw — lethalProxy/typical-win-turn systematically under-scored the
# deck (DEC-369/DEC-371 misread T9 as the ceiling; it was a floor). Model: when
# the commander is on the battlefield and a qualifying spell is cast from hand,
# resolve `triggers` cascade digs — each exiles from the top of the library
# until a nonland card with lesser mana value is hit, free-casts it (crediting
# its pressure/ramp/draw exactly like a paid cast), and bottoms the rest.
# Config keys:
#   minValue      — qualifying mana-value threshold (Zhulodok: 7)
#   triggers      — cascade instances per qualifying cast (Zhulodok: 2)
#   colorlessOnly — restrict qualifying spells to colorless (Zhulodok: True)
#   fromHandOnly  — True: cascade free-casts (from library) never re-trigger,
#                   matching "cast from your hand" grants. False: qualifying
#                   free-casts recurse (bounded — each hit costs strictly less).
# Trigger doubling (e.g. Echoes of Eternity) can be layered later by scaling
# `triggers` per deck.
COMMANDER_CASCADE = {
    "titan-convergence": {
        "minValue": 7,
        "triggers": 2,
        "colorlessOnly": True,
        "fromHandOnly": True,
    },
}

# DEC-393 — commander copy-trigger engines (sequel to DEC-385's cascade).
# The goldfish credits one resolution per cast, so copy-trigger commanders read
# artificially slow: Zada, Hedron Grinder copies each instant/sorcery that
# targets only her once for every other creature she controls (the deck's whole
# velocity engine), and Aziza, Mage Tower Captain copies any instant/sorcery
# when three untapped creatures are tapped. Model: on a qualifying paid cast
# with the commander on the battlefield, resolve N extra copies through
# resolve_cast_effects — each copy re-credits draw and land-ramp exactly like
# the original. Copies are NOT cast (CR 707.10): they never re-trigger the
# engine, cascade, or any other cast-gated model. Board-state dependence is
# real: creature counts come from creature permanents on the battlefield plus a
# stat-less ledger of creature tokens made by resolved spells (fixed
# "create N ... creature token" clauses only — X-spells and storm copies credit
# 0, so counts are floors; the ledger adds no combat/pressure/threat, it only
# feeds these gates).
# Config keys:
#   mode    — "per_other_creature": copies = creatures you control minus the
#             commander, gated on the spell targeting only a single creature
#             (Zada's "targets only Zada" read).
#             "tap_gate": one copy per cast while `tapCost` untapped creatures
#             remain; each use taps `tapCost` creatures for the turn.
#   tapCost — creatures tapped per tap_gate use (Aziza: 3).
COMMANDER_COPY_ENGINE = {
    "zada-hedron-grinder": {"mode": "per_other_creature"},
}

# DEC-404 — commander token-swarm engines (sequel to DEC-385/DEC-393). The
# goldfish's combat pressure counts only creature *cards* on the battlefield,
# so a commander whose primary clock is a growing token army reads near-zero:
# Namor the Sub-Mariner creates one 1/1 Merfolk per blue pip on each
# noncreature spell cast, and his own power equals the Merfolk count. Model:
# on each qualifying paid cast with the commander on the battlefield, mint
# `manaCost[pipColor]` tokens into a per-game ledger. Tokens attack from the
# turn after they were minted (summoning sickness): each contributes
# tokenPower + (count of battlefield anthem permanents) to per-turn combat
# damage, and the commander adds commanderPowerPerToken per ready token once
# he can attack (his */4 power scales with the swarm). A copy of a spell
# made on the stack is not cast (CR 707.10) and never mints. A card that lets
# its controller cast a copy (Harmonized Trio, prepared) does cast it, and a
# free cast is a cast too: either would trigger him (his trigger is on
# casting, paid or not), but the engine is credited only on the cast loop's
# casts from the hand, so neither mints: a limit of the model, which reads
# too little. Floors, not ceilings: X pips
# credit only printed symbols, anthems don't pump nontoken creature cards
# (their cmc-based combat already counts), and token draw engines (Curiosity
# Crafter/Bident) are not modeled.
# Config keys:
#   pipColor              — mana symbol counted per qualifying cast ("U")
#   nonCreatureOnly       — True: creature spells don't trigger
#   tokenPower            — base power per token (1)
#   anthemNames           — battlefield permanents granting the tokens +1/+1
#   commanderPowerPerToken — commander damage added per ready token (Namor: 1)
COMMANDER_TOKEN_ENGINE = {
    "tidal-legion": {
        "pipColor": "U",
        "nonCreatureOnly": True,
        "tokenPower": 1,
        # Verified +1/+1 Merfolk lords only (Scryfall, DEC-404): Svyelun is
        # ward-only, Kopala is a targeting tax, Master of Waves anthems
        # Elementals — none of those pump the Merfolk tokens.
        "anthemNames": {
            "Lord of Atlantis", "Master of the Pearl Trident",
            "Merrow Reejerey", "Vodalian Hexcatcher", "Merfolk Sovereign",
            # v1.2 (DEC-401): Attuma is a 7th +1/+1 lord; Patchwork Banner
            # (naming Merfolk) is an anthem artifact that pumps Namor too —
            # the commander pump is unmodeled (floors, not ceilings).
            "Attuma, Atlantean Warlord", "Patchwork Banner",
            # Roaming Throne (v1.3) doubles Namor's token trigger itself —
            # left unmodeled in the goldfish (floors, not ceilings).
        },
        "commanderPowerPerToken": 1,
    },
}

# DEC-405 — commander transform/free-deploy engine (sequel to DEC-385/393/404).
# Tony Stark casts at {1}{U} but the deck's engine is the BACK face: pay
# {4}{U}{R} ({2}{U}{R} with Training Grounds — activated abilities of creatures
# cost {2} less) to transform into a 5/5 flying haste body that, at the
# beginning of each of your combats, puts one artifact card from your hand onto
# the battlefield free — Equipment attach directly to him. The stock goldfish
# is blind to all of it. Model: (1) the transform is attempted each turn once
# the commander is in play, affordability-checked against the turn pool like
# any other cast; (2) once transformed, one artifact from hand, never a card
# reserved for the combo checks (reservedPieces, left in the hand), is
# deployed free at each combat via resolve_cast_effects (deployed creatures are
# summoning-sick; the record's combatReadyTurn handles that); (3) every
# deployed Equipment counts as attached, adding its configured power bonus (0
# when the table does not list it), and the commander swings each turn from
# the transform turn (haste) for
# (transformedPower + attached bonuses), doubled while an Equipment listed
# in doubleStrikeNames is attached. Configured kill-piece Equipment are held in hand as
# deploy fuel (mirrors the DEC-393 fuel-hold): the sim has no equip-cost path,
# so hard-casting them would strand them. Floors, not ceilings: the front-face
# {1},{T} artifact dig, Nexus of Becoming's second deploy stream, backup
# attachers (Armory Automaton / Kazuul's Toll Collector / Shuri), and paying
# equip costs for extra attachments are all unmodeled.
# Config keys:
#   transformCost / reducedTransformCost — activation pips; reduced applies
#       while `reducerName` is on the battlefield
#   transformedPower — back-face power (5/5 flying haste)
#   equipmentPower — Equipment name -> commander damage added while attached.
#       Values re-derived clause-by-clause from Scryfall oracle text
#       (2026-07-06): Excalibur +10/+0; Colossus Hammer +10/+10 (loses flying
#       — irrelevant in a blocker-less goldfish); Kaldra Compleat +5/+5;
#       Aettir and Priwen sets base P/T to your life total — modeled as a
#       conservative flat +15 (assumes ~20 life mid-game replacing the 5/5
#       base) because the goldfish tracks no life; Embercleave / The Reaver
#       Cleaver / Sword of the Animist +1/+1; Iron Man Armor +2/+1.
#       Mjölnir, Hammer of Thor at 0 (2026-11-25): "Double all damage equipped
#       creature would deal." is not credited (a question for the owner); it
#       is listed so the goldfish holds it for the free deploy, as the old
#       interaction classifier did by its "deals 2 damage to each creature"
#       text, instead of hard-casting it where it never attaches.
#   doubleStrikeNames — Equipment granting double strike (Fireshrieker,
#       Embercleave): doubles the commander's combat damage while attached.
COMMANDER_DEPLOY_ENGINE = {
    "armory-protocol": {
        "transformCost": {"generic": 4, "U": 1, "R": 1},
        "reducedTransformCost": {"generic": 2, "U": 1, "R": 1},
        "reducerName": "Training Grounds",
        "transformedPower": 5,
        "equipmentPower": {
            "Excalibur, Sword of Eden": 10,
            "Colossus Hammer": 10,
            "Kaldra Compleat": 5,
            "Aettir and Priwen": 15,
            "Embercleave": 1,
            "The Reaver Cleaver": 1,
            "Sword of the Animist": 1,
            "Iron Man Armor": 2,
            "Mjölnir, Hammer of Thor": 0,
        },
        "doubleStrikeNames": {"Fireshrieker", "Embercleave"},
    },
}

# DEC-472 — opponent-independent activated draw engines. The goldfish credits
# draw only on cast resolution (immediateDraw), so a repeatable tap engine like
# The One Ring reads as a one-shot cantrip: CAST_TURN_ACTIVATION_DRAW credits
# the cast-turn activation (draw 1) and nothing after. Model: each turn a
# configured permanent is on the battlefield, activate it once — the counter
# total grows by one and that many cards are drawn (activation n draws n).
# The cast-turn activation stays on the immediateDraw path, so per-turn
# escalation starts at 2 the following turn. `maxActivations` is the honest
# stopping rule for The One Ring's upkeep life loss (the goldfish tracks no
# life total): after n activations the pilot loses n life per upkeep, so a
# real pilot stops tapping around 4 — activations 1+2+3+4 = 10 cards, then 0.
# Floors, not ceilings: the on-cast protection turn and opponent-dependent
# engines (Rhystic Study / Mystic Remora taxes) are not modeled.
# Recurring draw triggers on opponents' turns (owner-approved 2026-11-17).
# The Theorist, Jace Beleren draws a card at the beginning of each opponent's
# draw step: 3 cards per turn cycle in the vanilla 4-player model (DEC-477).
# The goldfish has no opponent turns, so those cards are drawn at the start of
# each of your turns, from the turn after the permanent is cast (the first
# opponent draw steps come after your cast turn). No stopping rule: all three
# opponents stay in the game and the permanent survives (nothing attacks it
# in a goldfish).
# Config keys (per card name):
#   maxActivations — total activations including the cast turn (One Ring: 4)
#   drawsPerTurn — cards drawn at the start of each later turn (Jace: 3)
PERMANENT_DRAW_ENGINE = {
    "gandalf-party-guest": {
        "The One Ring": {"maxActivations": 4},
    },
    # DEC-533: same One Ring stopping rule as gandalf-party-guest.
    "gathering-shadow": {
        "The One Ring": {"maxActivations": 4},
        "The Theorist, Jace Beleren": {"drawsPerTurn": 3},
    },
    "tidal-legion": {
        "The Theorist, Jace Beleren": {"drawsPerTurn": 3},
    },
}

# Cards whose draw ability is activated the turn they are cast, credited as
# their immediateDraw (immediate_draw_count skips activated abilities). The One
# Ring: its first activation, per DEC-472 (the PERMANENT_DRAW_ENGINE loop still
# seeds at 1). Azami, Lady of Scrolls: her cost is "Tap an untapped Wizard you
# control", with no {T} symbol, so she pays with herself the turn she enters.
# Floor: every other activated draw counts 0 on the cast turn.
CAST_TURN_ACTIVATION_DRAW = {
    "The One Ring": 1,
    "Azami, Lady of Scrolls": 1,
}

# X spells (owner-approved 2026-11-18): a card with {X} in its front-face mana
# cost keeps its place in the cast order, and when the cast loop reaches it, X
# is the largest value the mana left at that point pays after the coloured
# pips and the DEC-944 holds ({X}{X} costs two per X). Below X_SPELL_MIN_X the
# card stays in hand and the next candidate is tried. An X spell is never a
# mana source (build_goldfish_profile). Combo-line pieces and KEY_COMBOS
# assembly members with {X} are not under this rule: they are reserved, never
# cast from the hand (owner-approved 2026-11-23, decision C,
# build_goldfish_context), and the combo gate reads them from the hand at
# X = 0, except a piece its line's minX names, priced at that X
# (owner-approved 2026-11-19, extract_combo_lines). A commander with {X} named
# in a combo line's pieces (winConditions[]) is cast from the command zone at
# X = 0 with the line pieces; any other commander with {X}, one named only in
# a KEY_COMBOS slot included (the slot fills itself from the command zone and
# lists no member), falls under this rule and its holds (no commander in the
# fleet has {X}); to be decided when a deck has one. Effects at the paid X, and nothing
# else: a creature's combat and impact read mana value + X (x_cast_profile), the
# draws below, AMASS_ARMY_ENGINE's amassXNames and TOKEN_MAKER_ENGINE's perX
# token spells. Other token, life-loss, damage, tutor, pump and proliferate X
# spells are only re-timed. Floors: convoke,
# improvise and cost reducers (Zimone's discount) are not modelled.
# Over-credit: a free put (cascade, hatch, deploy) resolves the printed
# profile, so an X creature scores its printed mana value and an X draw spell
# its printed-text draw (Kinetic Ooze 1), where by the rules X is 0 there.
X_SPELL_MIN_X = 1

# Cards an X spell draws as it is cast or enters: (the count in words, the
# count from the paid X and the number of times the commander was cast from
# the command zone; the goldfish casts it at most once). Oracle text from
# data/card-metadata.json, 2026-11-18. A cast with X paid uses these in place
# of immediateDraw; the methodology names each deck's own entries in words.
X_SPELL_DRAW = {
    # "you gain half X life and draw half X cards. Round down each time."
    # (cast trigger)
    "Hydroid Krasis": ("half X rounded down", lambda x, commander_casts: x // 2),
    # "When Wan Shi Tong enters, put X +1/+1 counters on him. Then draw half
    # X cards, rounded down."
    "Wan Shi Tong, Librarian": ("half X rounded down",
                                lambda x, commander_casts: x // 2),
    # "Draw X cards. Then you may put a permanent card with mana value X or
    # less from your hand onto the battlefield tapped." (the put is not
    # modelled)
    "Mind into Matter": ("X", lambda x, commander_casts: x),
    # "Draw X cards, then discard a card." (the discard is not modelled)
    "Pull from Tomorrow": ("X", lambda x, commander_casts: x),
    # "Draw X cards." (convoke is not modelled)
    "Transcendent Message": ("X", lambda x, commander_casts: x),
    # "Target player draws X cards plus an additional card for each time
    # they've cast a commander from the command zone this game."
    "Commander's Insight": ("X plus one per commander cast",
                            lambda x, commander_casts: x + commander_casts),
    # "Target player draws 2ˣ cards."
    "Mathemagics": ("2^X", lambda x, commander_casts: 2 ** x),
    # "If X is 5 or more, you draw a card." (enters trigger)
    "Kinetic Ooze": ("one card only at X 5 or more",
                     lambda x, commander_casts: 1 if x >= 5 else 0),
}

# DEC-533 — commander amass-Army engine (sequel to DEC-385/393/404/405).
# Sauron, the Dark Lord: "Whenever an opponent casts a spell, amass Orcs 1."
# The goldfish is a solitaire — it can see neither opponent casts nor the
# single growing Army token, so the deck's primary clock reads zero. Model:
# one Army creature tracked as a counter total.
#  * Opponent casts: credit a floor of one spell per opponent per turn cycle
#    (3 batches/turn, vanilla 4-player model per DEC-477) while the commander
#    is on the battlefield.
#  * amassOnResolve: one-shot amass credited when the named card is cast
#    (Book of Mazarbul's chapter I+II credited once on cast). Foray of Orcs is
#    a removal-spot sorcery in gathering-shadow, held back as interaction
#    (goldfish_holds_back), so its amass is never credited.
#  * amassXNames: amass X spells, credited with the X paid for them (see
#    X_SPELL_MIN_X above).
#  * amassPerTurn: repeatable attack/begin-of-combat/connect triggers, credited
#    each turn starting the turn AFTER the permanent lands (no haste). March
#    from the Black Gate additionally requires a combat-ready Army (its
#    trigger is "whenever an Army you control attacks").
#  * batchBonusName (Mauhur): replacement effect, +1 counter per batch.
#  * batchDamageName (The Great Goblin): 2 noncombat damage per batch while
#    on the battlefield.
#  * The Army swings every turn from the turn after it was created (amass
#    onto an existing Army never resets readiness); combat damage = counter
#    total. An Army created by the opponent-cast amass credited at the start
#    of your turn already existed before that turn began (the opponents cast
#    those spells on their turns), so it swings that same turn.
#  * Ring-temptation draw: each tempt with Sauron out may discard the hand
#    and draw four. Floor: only Call of the Ring's guaranteed upkeep tempt
#    plus one Army-connect tempt per attacking turn are converted, and only
#    when hand size <= temptDrawHandMax (net +2 or better); discarded cards
#    are simply lost (no graveyard re-buy credit).
# Floors, not ceilings: Saruman's ward, Nazgul/In the Darkness Bind Them/
# Soothing of Smeagol tempts, Witch-king sacrifice punisher, Gorbag/Moria
# Marauder connect draws, Barad-dur activations, Orcish Bowmasters' ping and
# amass ("When this creature enters and whenever an opponent draws a card
# except the first one they draw in each of their draw steps, this creature
# deals 1 damage to any target. Then amass Orcs 1."), and all graveyard
# re-buys (Reanimate/Gathering of Darkness/Along the Crooked Way) are
# unmodeled.
AMASS_ARMY_ENGINE = {
    "gathering-shadow": {
        "opponentCastsPerTurn": 3,
        "amassOnResolve": {
            "Gothmog, Morgul Lieutenant": 1,
            "Grishn\u00e1kh, Brash Instigator": 2,
            "The Mouth of Sauron": 2,
            "Great Goblin, Foul-Hearted": 3,
            "Sauron, Lord of the Rings": 5,
            "March from the Black Gate": 1,
            "Book of Mazarbul": 3,
            "Treason of Isengard": 2,
            "Swarming of Moria": 2,
            "Gathering of Darkness": 3,
            "Foray of Orcs": 2,
            "Orcish Medicine": 1,
        },
        # "Amass Orcs X" (Summons of Saruman; Assault on Osgiliath).
        "amassXNames": {"Summons of Saruman", "Assault on Osgiliath"},
        "amassPerTurn": {
            "March from the Black Gate": 1,
            "Warg Rider": 2,
            "Great Goblin, Foul-Hearted": 3,
            "Corsairs of Umbar": 3,
        },
        # Saruman, the White Hand: amass Orcs X per own noncreature cast (X =
        # that spell's mana value, which on the stack counts the X paid)
        "perNoncreatureCastMV": "Saruman, the White Hand",
        "batchBonusName": "Mauh\u00far, Uruk-hai Captain",
        "batchDamageName": "The Great Goblin",
        "batchDamage": 2,
        "temptPermanents": ["Call of the Ring"],
        "temptDrawHandMax": 2,
    },
}

# DEC-938 — commander hatch engines (sequel to DEC-385/393/404/405/533).
# Creatures only ever reach the goldfish battlefield by being cast from hand, so
# a commander whose whole plan is "sacrifice a token, put the top creature card
# onto the battlefield" reads as zero. Atla Palani, Nest Tender: "{2}, {T}:
# Create a 0/1 green Egg creature token with defender. Whenever an Egg you
# control dies, reveal cards from the top of your library until you reveal a
# creature card. Put that card onto the battlefield and the rest on the bottom."
# Model: Eggs are a counter, Egg deaths are gated on a real sacrifice outlet,
# and each death runs `hatch_from_library` — the DEC-385 cascade dig without the
# mana-value filter, resolving through the DEC-405 free put-onto-battlefield
# path so a hatch credits impact/combat/draw exactly like a cast but never
# re-triggers a cast-gated model (CR 707.10 reasoning; a put is not a cast).
#
# Config keys:
#   activationCost        — pips per commander activation ({2})
#   maxEggsPerTurn        — own-turn activation cap before token doublers (4)
#   maxHatchesPerTurn     — hard cap on hatches per turn; the Thornbite infinite
#                           is scored by the combo systems, not here (8)
#   instantOutletNames    — free, unlimited instant-speed sacrifice outlets
#   limitedOutletNames    — instant-speed outlets usable once per untap
#   sorceryOutletName/Cost/Draw — Skullclamp: own-turn Eggs only, {1} per Egg,
#                           credits its two-card draw (equip is sorcery-speed,
#                           so it never serves opponent-turn Eggs)
#   combatOutletNames     — free sacrifice of one Egg at your combat
#                           (Palani's Hatcher)
#   tokenDoublerNames     — each doubles every Egg created (Mondrak/Elspeth: x4)
#   extraHatchNames       — each adds one hatch per Egg death (Annie Joins Up
#                           doubles Atla's legendary trigger; Roaming Throne
#                           naming Shaman doubles it again — three with both)
#   untapperName/untapperRequiresName — Thornbite Staff untaps the commander as
#                           an Egg dies to any outlet; a further activation that
#                           turn only while Ashnod's Altar is out (its {C}{C}
#                           pays it); and only if the Staff was already on the
#                           battlefield when the
#                           commander entered (the sim has no equip path, so the
#                           free "whenever a Shaman enters, attach" is the only
#                           way it lands; its Equip {4} is a floor: a Staff cast
#                           after her never attaches)
#   untapStepName/untapStepActivations — Seedborn Muse: three extra activations
#                           on opponents' untap steps, free (lands untap too);
#                           those hatches are ready next turn regardless of haste
#   entryEggNames/entryEggDoublerName — Eggs made on entry (Palani's Hatcher's
#                           two, doubled again by Elesh Norn's ETB doubling)
#   landfallEggNames      — one Egg per land drop from the turn after entry
#                           (Nesting Dragon)
#   combatHatchNames/legendaryTriggerDoublerName — Raph & Mikey, Troublemakers
#                           hatch once per combat while combat-ready, and that
#                           creature attacks the same combat; Annie doubles it
# Floors, not ceilings: no blockers and no opponents; Eggs left unsacrificed
# carry over but never block or trade; Palani's Hatcher's 3/3 Dinosaur token and
# Nesting Dragon's 2/2 Dragon token are not credited; Maskwood Nexus making
# every creature an Egg, Zopandrel's and Mondrak's paid sacrifice outlets,
# Elesh Norn doubling Nesting Dragon's landfall trigger, extra land drops from
# ramp spells, and hatching on opponents' end steps beyond Seedborn are all
# unmodelled.
COMMANDER_HATCH_ENGINE = {
    "broodfire-hatchery": {
        "activationCost": {"generic": 2},
        "maxEggsPerTurn": 4,
        "maxHatchesPerTurn": 8,
        "instantOutletNames": {"Ashnod's Altar", "Phyrexian Altar",
                               "Goblin Bombardment"},
        "limitedOutletNames": {"High Market"},
        "sorceryOutletName": "Skullclamp",
        "sorceryOutletCost": {"generic": 1},
        "sorceryOutletDraw": 2,
        "combatOutletNames": {"Palani's Hatcher"},
        "tokenDoublerNames": {"Mondrak, Glory Dominus", "Elspeth, Storm Slayer"},
        "extraHatchNames": {"Annie Joins Up", "Roaming Throne"},
        "untapperName": "Thornbite Staff",
        "untapperRequiresName": "Ashnod's Altar",
        "untapStepName": "Seedborn Muse",
        "untapStepActivations": 3,
        "entryEggNames": {"Palani's Hatcher": 2},
        "entryEggDoublerName": "Elesh Norn, Mother of Machines",
        "landfallEggNames": {"Nesting Dragon"},
        "combatHatchNames": {"Raph & Mikey, Troublemakers"},
        "legendaryTriggerDoublerName": "Annie Joins Up",
    },
}

# Token makers (owner-approved 2026-11-18; sequel to DEC-404). The goldfish's
# combat counts creature cards only, so a deck whose army is mostly tokens
# reads as if its token makers did nothing. Model: the makers below mint into
# the DEC-404 token ledger (swarm_tokens_new / swarm_tokens_ready in
# simulate_goldfish_game) and its combat convention applies unchanged: each
# creature token attacks every turn from the turn after it is made for
# tokenPower plus one per anthem on the battlefield, and tokens made tapped
# and attacking deal damage the turn they are made. Every creature token able
# to attack attacks; no token is ever removed, sacrificed or spent. Food
# counts only for the commander draw below.
# Each resolution, trigger or activation is one creation event: Peregrin Took
# adds one Food to it, then each doubler on the battlefield doubles every
# token of it. The controller orders replacement effects (CR 616.1), and this
# order makes the most. Peregrin Took's ruling: the Food gets whatever the
# effect specifies for its tokens, so a Food made with tokens that enter
# tapped and attacking enters tapped.
# Commander draw. Baylen, the Haymaker: "Tap three untapped tokens you
# control: Draw a card." The cost has no {T} symbol, so it works the turn he
# is cast and summoning-sick tokens can pay; a token that attacked stays
# tapped until your next untap step and cannot. So at the last opponent's end
# step before each of your turns, while the commander is on the battlefield,
# he draws one card per commanderDrawTokens untapped tokens: every Food
# except any that entered tapped on your last turn, and the creature tokens
# made on your last turn, which could not attack yet. Those tokens untap in
# your untap step, and the cards arrive with the opponents'-turn draws,
# before your upkeep.
# Config keys (oracle text from data/card-metadata.json, 2026-11-18):
#   onResolve — (creature tokens, Food) a card makes as it resolves or enters
#   perX — creature tokens per X paid (the X spell rule, X_SPELL_MIN_X)
#   attackMakers — "whenever you attack": creature tokens made tapped and
#       attacking each attack, from the turn after the maker was cast
#   growingAttackMakers — the same, with a +1/+1 counter first and then one
#       token per counter (1, 2, 3 ...)
#   landfallMakers — one creature token per natural land drop while on the
#       battlefield; the drop comes before the turn's casts, so from the turn
#       after the maker was cast
#   activatedMakers — one creature token for this cost (without the
#       maker's own {T}), at most once per turn, paid after combat out of the
#       mana the turn's casts left, in name order. The maker must be untapped
#       and is tapped for it; a land maker's own mana leaves the pool.
#   needsTappedCreature — activated makers whose cost untaps a tapped
#       creature you control: only while a creature is tapped (it attacked
#       or was tapped for mana), which the cost then untaps
#   doublerNames / extraFoodName — the replacements above
#   artifactTokensReplacedBy — a permanent that turns artifact tokens into
#       creatures the engine does not credit: while it is on the battlefield
#       no new Food is credited
#   tokenPower / anthemNames — the DEC-404 combat convention
#   commanderDrawTokens — untapped tokens the commander taps per card
#   excluded — (reason, cards) for every other card in the deck that makes
#       or replaces tokens; a test fails when a deck card that does is in
#       neither this config nor this list
#   notCredited / notModeled — the deck's other floors, for the methodology
# The commander's own mana ability is not modelled under this engine
# (build_goldfish_context).
TOKEN_MAKER_ENGINE = {
    "stampede-acres": {
        "onResolve": {
            # "Choose one — • Create two 1/1 red Goblin creature tokens. •
            # Target creature gets +X/+X ..." (the token mode)
            "Frontline Rush": (2, 0),
            # "When this enchantment enters, create two 1/1 green and white
            # Citizen creature tokens." Its "Tap three untapped creatures you
            # control: Create a Treasure token." is not modelled.
            "Prosperous Partnership": (2, 0),
            # "When this artifact enters, create a 1/1 white Spirit creature
            # token with flying."
            "Staff of the Storyteller": (1, 0),
            # "When Rosie Cotton enters, create a Food token."
            "Rosie Cotton of South Lane": (0, 1),
        },
        "perX": {
            # "Create X 1/1 white Warrior creature tokens."
            "Secure the Wastes": 1,
            # "Create X 1/1 green and white Citizen creature tokens. ..."
            "Grand Crescendo": 1,
            # "Create X 1/1 white Soldier creature tokens with lifelink."
            "March of the Multitudes": 1,
            # "... Create twice X 1/1 black and green Pest creature tokens ..."
            "Pest Infestation": 2,
        },
        # "Whenever you attack, for each opponent, create a 1/1 white Human
        # creature token that's tapped and attacking that player ..."
        # (three opponents)
        "attackMakers": {"Adeline, Resplendent Cathar": 3},
        # "Whenever you attack with one or more non-Gnome creatures, put a
        # +1/+1 counter on Anim Pakal, then create X 1/1 colorless Gnome
        # artifact creature tokens that are tapped and attacking, where X is
        # the number of +1/+1 counters on Anim Pakal." (he attacks himself)
        "growingAttackMakers": {"Anim Pakal, Thousandth Moon"},
        "landfallMakers": {
            # "Landfall — Whenever a land you control enters, create a 1/1
            # green Insect creature token. If you control six or more lands,
            # create a token that's a copy of this creature instead." One
            # token either way; the copies' own landfall is not modelled.
            "Scute Swarm",
            # "Landfall — ... If you didn't create a token this way, create a
            # 1/1 green Insect creature token." (cast as a creature, not
            # bestowed)
            "Springheart Nantuko",
        },
        "activatedMakers": {
            # "{W}, {T}, Untap a tapped creature you control: Create a 1/1
            # green and white Citizen creature token."
            "Halo Fountain": {"W": 1},
            # "{2}{W}{W}, {T}: Create a 1/1 white Human creature token." Its
            # own {T}: the Castle must be untapped and is tapped for it.
            "Castle Ardenvale": {"generic": 2, "W": 2},
        },
        "needsTappedCreature": {"Halo Fountain"},
        # "If an effect would create one or more tokens under your control,
        # it creates twice that many of those tokens instead." and, Mondrak
        # and Elspeth, "If one or more tokens would be created under your
        # control, twice that many of those tokens are created instead."
        # Elspeth's +1 Soldier is not credited (notCredited).
        "doublerNames": {"Anointed Procession", "Mondrak, Glory Dominus", "Elspeth, Storm Slayer"},
        # "If one or more tokens would be created under your control, those
        # tokens plus an additional Food token are created instead."
        "extraFoodName": "Peregrin Took",
        # "If one or more artifact tokens would be created under your control,
        # that many 5/5 red Dragon creature tokens with flying are created
        # instead." Its ruling: anything else the effect specifies (tapped,
        # attacking) still applies. The Dragons are not credited (it is in
        # `excluded`), so while it is on the battlefield no new Food is
        # credited either; Anim Pakal's Gnomes (artifact creature tokens) stay
        # 1/1 attackers where they would be 5/5 flying ones.
        "artifactTokensReplacedBy": "Draconic Visitor",
        "tokenPower": 1,
        # "Creatures you control get +1/+1." The only static anthem credited
        # (Caretaker's Talent's level 3 is in notModeled).
        "anthemNames": {"Warleader's Call"},
        "commanderDrawTokens": 3,
        "excluded": (
            # Tithe's opponent may pay {2}; the Queen recruits on an
            # opponent's first noncreature spell.
            ("their tokens depend on opponents' choices",
             ("Smothering Tithe", "The Queen of Dale")),
            # "Whenever an opponent draws their second card each turn, you
            # create a Treasure token. / {2}{W}: Two target players each draw
            # a card." The second draw can come on any turn, its own
            # activations included.
            ("its Treasure needs an opponent's second draw in a turn: the "
             "goldfish models no opponent draws and never activates its {2}{W}",
             ("Gleaming Splendor",)),
            # A removal-spot instant and a removal-board sorcery:
            # goldfish_holds_back.
            ("never cast: held back as interaction",
             ("Artifact Mutation", "The Battle of Bywater")),
            # "Mobilize 2 (Whenever this creature attacks, create two tapped
            # and attacking 1/1 red Warrior creature tokens. Sacrifice them at
            # the beginning of the next end step.)"
            ("its Warriors are sacrificed at the end of the turn they attack, "
             "and the token ledger never removes a token", ("Voice of Victory",)),
            # Flurry: "Whenever you cast your second spell each turn, ..."
            ("tokens only on the second spell in a turn",
             ("Aligned Heart", "Cori-Steel Cutter")),
            # Level 2's copy of a token; the {8} sacrifice for an Eldrazi.
            ("one-shot activations", ("Caretaker's Talent", "Idol of Oblivion")),
            # "Whenever one or more +1/+1 counters are put on this creature,
            # you may create a 1/1 green Squirrel creature token."
            ("Squirrels from +1/+1 counters: with Rosie Cotton of South Lane "
             "they are the infinite the combo gate scores", ("Scurry Oak",)),
            # See artifactTokensReplacedBy above.
            ("its 5/5 flying Dragons are not credited: while it is on the "
             "battlefield no new Food is credited, and Anim Pakal's Gnomes "
             "count as 1/1s", ("Draconic Visitor",)),
        ),
        # The rest of this deck's floors, as the methodology states them.
        "notCredited": (
            "token copies' own landfall",
            "landfall from lands a fetch land or ramp spell puts onto the "
            "battlefield",
            "the makers' other abilities (Prosperous Partnership's Treasure)",
            "Elspeth, Storm Slayer's +1 Soldier token",
            "an attack maker's trigger on the turn it is cast (another creature "
            "attacking would trigger it)",
        ),
        "notModeled": (
            "the commander's mana and +1/+1 counter abilities",
            "Halo Fountain's draw and win abilities",
            "Treasure and Food being spent",
            "untaps on opponents' turns (Seedborn Muse, Drumbellower)",
            "Caretaker's Talent's level 3 anthem (\"Creature tokens you control "
            "get +2/+2.\")",
            "noncombat token payoffs (Impact Tremors, Purphoros, Warleader's "
            "Call's ping)",
            "token-draw payoffs (Caretaker's Talent, Bennie Bracks, Belladonna "
            "Took, Staff of the Storyteller's story counters, Idol of Oblivion, "
            "Peregrin Took's Foods)",
        ),
    },
}

# DEC-938 — team-haste rule. The goldfish profile scores combat from mana value
# plus a keyword list and ignores printed Haste fleet-wide, so a deck whose
# whole point is "the fatty that just entered attacks now" is measured a full
# turn slow on every body. Generic opt-in mechanism, one deck configured today:
# a creature that enters — cast or hatched — while any source is on the
# battlefield is combat-ready the turn it entered, and `printedHasteNames`
# creatures are ready on entry regardless.
#
# Sources split by how they behave for a creature that is ALREADY on the
# battlefield when the source lands (DEC-938 review):
#   staticNames / staticPairs — continuous grants ("Creatures you control have
#       haste"). They cover creatures already out, so a permanent that needs to
#       be untapped-and-unsick this turn can check them live.
#   entryGatedNames — replacement effects that only apply as a creature enters
#       (Rhythm of the Wild's riot). They never haste a creature that was
#       already on the battlefield, so they only count through the entry-time
#       record written when that creature entered.
# Lightning Greaves is deliberately absent: single target, and the sim has no
# equip path.
COMMANDER_HASTE_SOURCES = {
    "broodfire-hatchery": {
        # Rising of the Day left at DEC-935 round 6 (Fecund Greenshell took the
        # slot; its Egg-side card advantage is not modelled — a floor).
        "staticNames": set(),
        # Palani's Hatcher grants haste to other Dinosaurs; Maskwood Nexus makes
        # every creature you control every creature type.
        "staticPairs": [("Palani's Hatcher", "Maskwood Nexus")],
        # Surrak and Goreclaw: haste on each other nontoken creature as it
        # enters (DEC-935 round 5) — entry-time only, like riot.
        "entryGatedNames": {"Rhythm of the Wild", "Surrak and Goreclaw"},
        "printedHasteNames": {"Raph & Mikey, Troublemakers"},
    },
}

# DEC-940 (DEC-935 Phase 2) — combat modifiers: extra combat phases and power
# multipliers. The goldfish credits each ready creature `min(8, MV)` (+1 per
# listed keyword; MV + X for an X creature cast with X paid, X_SPELL_MIN_X)
# exactly once per turn, so a deck whose plan is "swing three times with
# doubled power" is measured as a single unmodified combat. Generic opt-in
# mechanism, one deck configured today (broodfire-hatchery).
#
# THE BASE COMBAT PROXY IS UNCHANGED. Every deck's per-creature combat value is
# still `min(8, MV)` + keyword bonus (MV + X for an X creature cast with X
# paid), so lethalProxy stays comparable across the
# fleet; a deck with no COMBAT_MODIFIERS entry runs exactly one unmodified combat
# phase, as before. Printed power (`profile["printedPower"]`, DEC-940 metadata)
# is read only by the power gates below, never by the damage sum.
#
# Per combat phase, in this order (the controller's own trigger order, chosen to
# stack the multipliers the way a real pilot would):
#   1. teamDoublerNames (Zopandrel, Hunger Dominus) — "at the beginning of each
#      combat, double the power and toughness of each creature you control until
#      end of turn". Until-end-of-turn doubling compounds across the turn's
#      combat phases, so a creature present for n beginning-of-combat triggers
#      is scaled 2**n (30 -> 60 -> 120).
#   2. largestDoublerNames (Xenagos, God of Revels) — "another target creature
#      you control ... gets +X/+X where X is that creature's power": the single
#      largest other ready attacker is doubled. A creature that entered during
#      this combat phase was not on the battlefield when the trigger went on the
#      stack, so it cannot be targeted this phase (it can from the next one).
#   3. doubleStrikeGrantNames (Raphael, the Nightwatcher) — "attacking creatures
#      you control have double strike": the whole phase's damage doubles.
#
# Extra combat phases, each re-running the sum above:
#   extraCombatAttackerNames (Aurelia, the Warleader) — "whenever Aurelia attacks
#       for the first time each turn": one extra combat, from the first combat
#       only, while she is combat-ready.
#   exertCombatNames (Combat Celebrant) — exert as it attacks for one extra
#       combat; it untaps all *other* creatures, so the Celebrant itself is out
#       of the rest of the turn's combats, and an exerted creature does not untap
#       during the next untap step, so it is available every other turn.
#   powerGatedCombatNames (Tifa, Martial Artist) — one extra combat from the
#       first combat only, gated on at least one ready attacker with printed
#       power >= powerGateThreshold (7).
#   paidCombatName (Aggravated Assault) — after any combat, pay paidCombatCost
#       ({3}{R}{R}) out of the mana the turn's casts and activations left and
#       take another combat; repeats while the pool allows.
#   legendaryTriggerDoublerName (Annie Joins Up) — "if a triggered ability of a
#       legendary creature you control triggers, that ability triggers an
#       additional time": the Aurelia and Tifa triggers each add two combats.
#       Combat Celebrant is not legendary, and Aggravated Assault is an activated
#       ability on an enchantment, so neither is doubled.
#   maxCombatPhases — hard cap on combat phases per turn, base combat included.
#
# Per-combat hooks into the DEC-938 hatch engine fire again at each extra
# combat's beginning of combat: combatOutletNames (Palani's Hatcher sacrifices
# one Egg) and combatHatchNames (Raph & Mikey hatch, entering tapped and
# attacking so they count in that combat).
#
# Floors, not ceilings: no blockers, no opponents, no fogs, so every phase
# connects. Annie Joins Up also doubles Zopandrel's beginning-of-combat trigger
# (x4 per phase, not x2) and Roaming Throne naming the relevant creature type
# under Maskwood Nexus doubles the combat triggers again — both left unmodelled.
# Ghalta and Mavren's attack token, Combat Celebrant untapping again off a later
# untap-all effect, and the DEC-404/405/533 ledgers (token swarm, free-deploy
# commander, amass Army — none of which this deck runs) are unmodified by the
# multipliers.
#
# Decks that carry these effects and could opt in later, each with its own
# review and a calibration re-run: shield-doctrine (Aggravated Assault, double
# strike), armory-protocol (Genji Glove), hidden-legion, gathering-shadow,
# anvil-chorus and eternal-agony (double strike or damage doublers).
COMBAT_MODIFIERS = {
    "broodfire-hatchery": {
        "maxCombatPhases": 4,
        "teamDoublerNames": {"Zopandrel, Hunger Dominus"},
        "largestDoublerNames": {"Xenagos, God of Revels"},
        "doubleStrikeGrantNames": {"Raphael, the Nightwatcher"},
        "extraCombatAttackerNames": {"Aurelia, the Warleader"},
        # Combat Celebrant left at DEC-935 round 5; Moraug, Fury of Akoum
        # (landfall extra combat) replaced it and is not modelled — a floor.
        "exertCombatNames": set(),
        "powerGatedCombatNames": {"Tifa, Martial Artist"},
        "powerGateThreshold": 7,
        "paidCombatName": "Aggravated Assault",
        "paidCombatCost": {"generic": 3, "R": 2},
        "legendaryTriggerDoublerName": "Annie Joins Up",
    },
}


def ready_attackers(permanents: list[dict], turn: int) -> list[dict]:
    """Permanent records that attack this turn (DEC-940).

    The same predicate ``metrics_from_board`` sums for the reported ``combat``
    field: a positive combat proxy and combat readiness reached.
    """
    return [
        permanent for permanent in permanents
        if permanent["combat"] > 0 and permanent["combatReadyTurn"] <= turn
    ]


def combat_phase_damage(attackers: list[dict], modifiers: dict | None,
                        board: set[str], phase_index: int) -> float:
    """Damage one combat phase deals, with the DEC-940 multipliers applied.

    ``phase_index`` is 0 for the turn's first combat. With no modifiers config
    (or none of the configured permanents on the battlefield) this is exactly
    the unmodified sum the goldfish has always credited.
    """
    values = [float(permanent["combat"]) for permanent in attackers]
    if modifiers is None or not values:
        return sum(values)

    # Zopandrel: one doubling per beginning-of-combat trigger the creature was
    # present for. `combatEntryPhase` is the phase a creature entered during
    # (absent = already on the battlefield before combat, i.e. -1).
    if modifiers["teamDoublerNames"] & board:
        for idx, permanent in enumerate(attackers):
            entry_phase = permanent.get("combatEntryPhase", -1)
            values[idx] *= 2 ** max(0, phase_index - entry_phase)

    # Xenagos: +X/+X where X is that creature's power, on another target
    # creature — the biggest attacker that was already on the battlefield when
    # the beginning-of-combat trigger went on the stack.
    if modifiers["largestDoublerNames"] & board:
        targetable = [
            idx for idx, permanent in enumerate(attackers)
            if permanent["name"] not in modifiers["largestDoublerNames"]
            and permanent.get("combatEntryPhase", -1) < phase_index
        ]
        if targetable:
            best = max(targetable, key=lambda idx: values[idx])
            values[best] *= 2

    total = sum(values)
    # Raphael: attacking creatures you control have double strike.
    if modifiers["doubleStrikeGrantNames"] & board:
        total *= 2
    return total


def combo_slot_lists(combo: dict) -> list[list[str]]:
    """Return a combo's slots as lists of interchangeable member card names.

    Slot schema: ``combo["slots"]`` is a list of slots, each a list of names
    or ``{"members": [names], "noPriority": True}`` (build_combo_assembly_lines
    refuses any other slot). Back-compat: a combo declared with a bare
    ``combo["pieces"]`` list is read as one 1-card slot per piece.
    """
    if combo.get("slots"):
        return [list(slot["members"]) if isinstance(slot, dict) else list(slot) for slot in combo["slots"]]
    return [[piece] for piece in combo.get("pieces", [])]


def build_combo_assembly_lines(deck_id: str, decklist: list[str],
                               commander_name: str) -> list[dict]:
    """Per-combo slot spec for the goldfish assembly tracker.

    Each line: ``{name, pieces, slots, requiresCommander, description}`` where
    every slot is ``{members: [names present in deck], isCommander: bool,
    noPriority: bool}``. A slot is valid if it names the commander (auto-filled
    from the command zone) or holds >=1 member present in the decklist; a
    combo whose every slot is valid is included. Combos with a
    missing-from-deck slot are dropped (the deck cannot assemble them) —
    mirrors the old closed-form behaviour.

    A slot is a non-empty list of card names, or ``{"members": [card names],
    "noPriority": True}`` with a non-empty list, a slot added without cast
    priority (owner decision 27, 6b: its cards are not line members by it,
    build_goldfish_context); any other slot, a combo with no slot (no
    slots and no pieces) or one with both slots and pieces raises ValueError. A card listed in two slots of one combo
    raises ValueError: assembly (assembly_tutor_cost) reads each slot as filled
    by any of its drawn members, so one card would fill both, and two slots
    could keep the same card from paying an extra cost. With every member in
    one slot only, one card fills at most one slot.
    """
    deck_cards = set(decklist)
    lines = []
    for combo in KEY_COMBOS.get(deck_id, []):
        if "slots" in combo and "pieces" in combo:
            raise ValueError(f"KEY_COMBOS {deck_id} {combo.get('name')!r}: both slots and pieces (give one)")
        raw_slots = combo.get("slots") or (
            [[piece] for piece in combo["pieces"]] if isinstance(combo.get("pieces"), list) else [])
        if not raw_slots:
            raise ValueError(f"KEY_COMBOS {deck_id} {combo.get('name')!r}: no slot")
        for slot in raw_slots:
            members = (slot["members"] if isinstance(slot, dict) and set(slot) == {"members", "noPriority"}
                       and slot["noPriority"] is True else slot)
            if not (isinstance(members, list) and members and all(isinstance(member, str) for member in members)):
                raise ValueError(f"KEY_COMBOS {deck_id} {combo.get('name')!r}: slot {slot!r} is not a non-empty "
                                 "list of card names or {\"members\": [card names], \"noPriority\": true}")
        listed = [member for members in combo_slot_lists(combo) for member in members]
        repeated = sorted({member for member in listed if listed.count(member) > 1})
        if repeated:
            raise ValueError(f"KEY_COMBOS {deck_id} {combo.get('name')!r}: {repeated} listed in two slots")
        slots = []
        complete = True
        for raw, members in zip(raw_slots, combo_slot_lists(combo)):
            is_commander = commander_name in members
            present = [m for m in members if m != commander_name and m in deck_cards]
            no_priority = isinstance(raw, dict)
            if is_commander:
                slots.append({"members": present, "isCommander": True, "noPriority": no_priority})
            elif present:
                slots.append({"members": present, "isCommander": False, "noPriority": no_priority})
            else:
                complete = False
                break
        if not complete:
            continue
        pieces = combo.get("pieces") or [m for slot in combo_slot_lists(combo) for m in slot]
        lines.append({
            "name": combo["name"],
            "pieces": list(pieces),
            "slots": slots,
            "requiresCommander": combo.get("requiresCommander", False),
            "description": combo.get("description", ""),
        })
    return lines


# --- Helpers ---


def pct(count: int, total: int) -> float:
    """Percentage rounded to 1 decimal."""
    return round(count / total * 100, 1) if total > 0 else 0.0


def r1(val: float) -> float:
    """Round to 1 decimal."""
    return round(val, 1)


def compute_avg_cmc(decklist: list[str], metadata: dict) -> float:
    """Average CMC of non-land cards."""
    cmcs = []
    for name in decklist:
        meta = metadata.get(name, {})
        if "Land" not in meta.get("type_line", ""):
            cmc = meta.get("cmc", 0)
            if isinstance(cmc, (int, float)):
                cmcs.append(cmc)
    return statistics.mean(cmcs) if cmcs else 0.0


def mana_stats(data: list) -> dict:
    """Compute median/p25/p75/mean from a list of values."""
    if not data:
        return {"median": 0.0, "p25": 0.0, "p75": 0.0, "mean": 0.0}
    q = statistics.quantiles(data, n=4)
    return {
        "median": r1(statistics.median(data)),
        "p25": r1(q[0]),
        "p75": r1(q[2]),
        "mean": r1(statistics.mean(data)),
    }


def cumulative_pct(values: list, threshold: int, total: int) -> float:
    """Percentage of values <= threshold."""
    count = sum(1 for v in values if v <= threshold)
    return pct(count, total)


def median_or_null(values: list):
    """Median of a list, or None if empty."""
    if not values:
        return None
    return r1(statistics.median(values))


def median_turn_from_cumulative(by_turn: dict) -> int | None:
    """First turn where cumulative castable % >= 50."""
    for t in range(1, NUM_TURNS + 1):
        if by_turn.get(str(t), 0) >= 50.0:
            return t
    return None


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp numeric score into [low, high]."""
    return max(low, min(high, value))


def weighted_average(weighted_values: list[tuple[float, float]]) -> float:
    """Weighted average helper."""
    total_weight = sum(weight for _, weight in weighted_values)
    if total_weight <= 0:
        return 0.0
    return sum(value * weight for value, weight in weighted_values) / total_weight


def pct_to_score(value: float) -> float:
    """Normalize percentage-like values into score space."""
    return clamp(value)


def paid_mulligan_pct(mulligan_attempts: Counter, total: int) -> float:
    """Percentage of games that took any non-free mulligan."""
    return pct(sum(count for attempt, count in mulligan_attempts.items() if attempt >= 2), total)


def cards_seen_by_turn(turn: int) -> int:
    """Cards seen by the end of `turn`: the opening seven and one draw a turn
    from turn 1. The simulators model a four-player free-for-all Commander
    game, in which no player skips the draw step of their first turn (CR
    103.8c)."""
    return min(99, 7 + turn)


def hypergeom_at_least(deck_size: int, hits_in_deck: int, cards_seen: int,
                       hits_needed: int) -> float:
    """Probability of seeing at least hits_needed successes in cards_seen draws."""
    if hits_needed <= 0:
        return 1.0
    if hits_in_deck < hits_needed or cards_seen <= 0:
        return 0.0

    max_hits = min(hits_in_deck, cards_seen)
    total = math.comb(deck_size, cards_seen)
    success = 0
    for hits in range(hits_needed, max_hits + 1):
        miss_count = cards_seen - hits
        if deck_size - hits_in_deck < miss_count:
            continue
        success += math.comb(hits_in_deck, hits) * math.comb(deck_size - hits_in_deck, miss_count)
    return success / total if total else 0.0


def parse_generic_mana_cost(mana_cost: str) -> dict:
    """Parse WUBRG mana costs from Scryfall-style mana_cost strings.

    ``X`` counts the {X} symbols of the front face; ``total`` is the cost at
    X = 0 (x_spell_cost adds the X paid).
    """
    result = {
        "generic": 0,
        "W": 0,
        "U": 0,
        "B": 0,
        "R": 0,
        "G": 0,
        "C": 0,
        "total": 0,
        "X": 0,
    }
    if not mana_cost:
        return result
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    for symbol in re.findall(r"\{([^}]+)\}", mana_cost):
        if symbol == "X":
            result["X"] += 1
        elif symbol.isdigit():
            result["generic"] += int(symbol)
        elif symbol in COLOR_SYMBOLS:
            result[symbol] += 1
    result["total"] = result["generic"] + sum(result[color] for color in COLOR_SYMBOLS)
    return result


def ordered_unique(cards: list[str]) -> list[str]:
    """Keep first-seen order while removing duplicates."""
    seen = set()
    ordered = []
    for card in cards:
        if card in seen:
            continue
        seen.add(card)
        ordered.append(card)
    return ordered


def build_card_category_lookup(deck_data: dict) -> dict[str, set[str]]:
    """Map card name to guide category names for deck-guided threat inference."""
    lookup: dict[str, set[str]] = {}
    guide = deck_data.get("guideContent", {})
    for category in guide.get("deckCategories", []):
        for card in category.get("cards", []):
            lookup.setdefault(card, set()).add(category.get("name", ""))
    return lookup


def text_matches(text: str, patterns: tuple[str, ...]) -> bool:
    """Regex convenience helper."""
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def is_draw_card(meta: dict) -> bool:
    """Heuristic card-draw classifier based on Scryfall oracle text."""
    oracle = meta.get("oracle_text", "")
    return text_matches(oracle, DRAW_PATTERNS)


def is_health_interaction_card(meta: dict, category_names: set[str]) -> bool:
    """The interaction count of interactionAvailability and the health
    score's interactionDensity (classify_functional_cards): a guide category
    name with an interaction word, or removal, stack interaction or combat
    denial text. The goldfish does not read it: it holds cards back by role
    and type (goldfish_holds_back)."""
    oracle = meta.get("oracle_text", "")
    category_blob = " ".join(category_names).lower()
    if any(term in category_blob for term in ("interaction", "removal", "counter", "stax", "disruption", "lock")):
        return True
    if "Board wipe" in oracle:
        return True
    return text_matches(oracle, INTERACTION_PATTERNS)


def is_threat_card(name: str, meta: dict, category_names: set[str]) -> bool:
    """Threat classifier leaning on curated guide categories first, text second."""
    if category_names:
        if not any(term in cat.lower() for cat in category_names for term in THREAT_EXCLUDED_CATEGORY_TERMS):
            return True

    type_line = meta.get("type_line", "")
    cmc = meta.get("cmc", 0) or 0
    oracle = meta.get("oracle_text", "")

    if any(marker in type_line for marker in THREAT_TYPE_MARKERS) and cmc >= 3:
        return True

    if any(marker in type_line for marker in ("Artifact", "Enchantment")) and cmc >= 4:
        return text_matches(oracle, THREAT_ORACLE_PATTERNS)

    return False


def classify_functional_cards(decklist: list[str], deck_data: dict, metadata: dict) -> dict:
    """Classify threats, draw, and interaction cards from deck data + metadata."""
    category_lookup = build_card_category_lookup(deck_data)
    threats = []
    draw = []
    interaction = []

    for name in decklist:
        meta = metadata.get(name, {})
        if not meta or "Land" in meta.get("type_line", ""):
            continue

        category_names = category_lookup.get(name, set())
        if is_threat_card(name, meta, category_names):
            threats.append(name)
        if is_draw_card(meta):
            draw.append(name)
        if is_health_interaction_card(meta, category_names):
            interaction.append(name)

    return {
        "threats": threats,
        "draw": draw,
        "interaction": interaction,
    }


def is_permanent_card(meta: dict) -> bool:
    """Return True for cards that remain on battlefield after resolution."""
    type_line = meta.get("type_line", "")
    return any(marker in type_line for marker in ("Land", "Artifact", "Creature", "Enchantment", "Planeswalker", "Battle"))


# The decklist roles (docs/role-taxonomy.md) whose instants and sorceries the
# goldfish holds back (owner-approved 2026-11-23): an answer to an opponent's
# card or spell, or a save for the pilot's own permanents against one, and the
# goldfish has no opponents' cards or spells.
GOLDFISH_HELD_ROLES = frozenset({"removal-spot", "removal-board", "counterspell", "protection"})


def goldfish_holds_back(primary_role: str | None, meta: dict) -> bool:
    """Whether the goldfish holds a card back as interaction (owner-approved
    2026-11-23): its primary role in the deck is one of GOLDFISH_HELD_ROLES
    and it is an instant or sorcery, with no permanent type on its type line
    (both faces', is_permanent_card). A permanent with one of those roles (a
    creature, an Aura, an Adventure creature, a card with a land face) is not
    held. Its secondary role, its guide categories and its text are not read;
    the commander is never held (build_goldfish_profile). A held card is never
    cast from the hand (goldfish_never_casts). Outside the cards a paid
    mulligan keeps, it is bottomed before the other spells; one the mulligan
    keeps (Muddle the Mixture, also a tutor) goes with the kept spells, the
    dearest first; from a seven with five or more playable lands a land goes
    first (goldfish_bottom_cards). An imprint that can exile it exiles it
    first, ranked with an alternative a combo line or a table slot keeps in
    the hand and no line names plainly (imprint_choice: the most colours,
    then the highest mana value, then the name latest in the alphabet; never a kept card or another
    reserved card); a cascade declines it."""
    return primary_role in GOLDFISH_HELD_ROLES and not is_permanent_card(meta)


def type_words(type_line: str) -> frozenset:
    """The words of one face's type line: supertypes, card types and subtypes."""
    return frozenset(re.findall(r"[\w'-]+", type_line))


def extract_land_subtypes(type_line: str) -> set[str]:
    """Basic land types on one face's type line."""
    return {word for word in type_words(type_line) if word in LAND_SUBTYPE_COLORS}


def battlefield_face(meta: dict) -> tuple[str, str]:
    """The type line and oracle text of the face a card is on the battlefield as.

    The metadata holds the front face's text and the joined type line
    ("A // B"). A modal DFC whose front is not a land but whose back is
    (``back_face``) is on the battlefield as its land face (played as a land,
    unless the goldfish keeps it in the hand as a combo-line or assembly
    piece: handOnlyPieces); any other card is its front face, so a transform
    card with a land back (Growing Rites of Itlimoc) is cast as its front.
    """
    front_type = meta.get("type_line", "").split(" // ")[0]
    back = meta.get("back_face")
    if back and "Land" not in front_type:
        return back["type_line"], back["oracle_text"]
    return front_type, meta.get("oracle_text", "")


def strip_reminder_text(text: str) -> str:
    return re.sub(r"\([^)]*\)", "", text)


# The subject of a quoted ability a card grants, matched in full (M1): the
# card itself receives it when it has the type named beside the subject
# ("Creatures you control have" on a creature, "All Slivers have" on a
# Sliver, "This Saga gains" on itself).
SELF_GRANT_SUBJECTS = {
    "creatures you control have": "Creature",
    "all slivers have": "Sliver",
    "sliver creatures you control have": "Sliver",
    "this saga gains": "",
}
# Subjects whose grant reaches only other permanents (a named floor): tokens,
# Treasures, a target, and lands (read as colours every land makes,
# ``landGrant``, read on the battlefield by land_grant).
OTHER_GRANT_SUBJECTS = (
    r"other [\w ]+ you control have",
    r"creature tokens you control have", r"treasures you control have",
    r"lands you control have", r".*\btarget land gains", r".*\btokens? with",
    r".*\. it has", r".*\bbecomes a treasure artifact with",
    r"enchanted permanent is a colorless land with",
)
# A line a card's mana is read from (M2): "add", "adds" or "produces".
MANA_WORDS = r"\b(?:adds?|produces?)\b"


def quoted_grants(text: str) -> list[tuple[str, str, str]]:
    """Each quoted ability with mana in a card's text, as (subject, ability,
    reading): "self" for a subject in SELF_GRANT_SUBJECTS, "other" for one in
    OTHER_GRANT_SUBJECTS, "unread" for any other subject."""
    out = []
    for line in strip_reminder_text(text).split("\n"):
        for subject, quoted in re.findall(r'([^"]*)"([^"]*)"', line):
            if not re.search(MANA_WORDS, quoted, re.I):
                continue
            subject = re.sub(r"^(?:[IVX]+, )*[IVX]+ — ", "", subject.strip()).strip().lower()
            reading = ("self" if subject in SELF_GRANT_SUBJECTS
                       else "other" if any(re.fullmatch(p, subject) for p in OTHER_GRANT_SUBJECTS)
                       else "unread")
            out.append((subject, quoted, reading))
    return out


def own_ability_lines(text: str, words: frozenset) -> list[str]:
    """A permanent's own ability lines: reminder and quoted text removed, and a
    quoted ability granted to a group the card belongs to added as a line of
    its own (M1). The subject must match a SELF_GRANT_SUBJECTS entry in full:
    "Other creatures you control have" grants nothing to the card itself."""
    lines = []
    for line in strip_reminder_text(text).split("\n"):
        for subject, quoted in re.findall(r'([^"]*)"([^"]*)"', line):
            subject = re.sub(r"^(?:[IVX]+, )*[IVX]+ — ", "", subject.strip()).strip().lower()
            word = SELF_GRANT_SUBJECTS.get(subject)
            if word is not None and (not word or word in words):
                lines.append(quoted)
        line = re.sub(r'"[^"]*"', '""', line).strip()
        if line:
            lines.append(line)
    return lines


MANA_SYMBOL = r"\{([WUBRGC])\}"
# Card types and supertypes: a changeling is every creature type, never these.
CARD_TYPE_WORDS = frozenset({"Artifact", "Basic", "Battle", "Creature", "Enchantment",
                             "Kindred", "Land", "Legendary", "Planeswalker", "Snow"})
# CR 205.3i, for "This land is every nonbasic land type" (Planar Nexus).
NONBASIC_LAND_TYPES = frozenset({"Cave", "Cloud", "Desert", "Gate", "Lair", "Locus", "Mine",
                                 "Planet", "Power-Plant", "Sphere", "Tower", "Town", "Urza's"})
# Sentences beside a mana ability that change nothing the goldfish counts.
MANA_RIDERS = (
    r"deals \d+ damage to you", r"^you gain \d+ life", r"^until end of turn, you don't lose",
    r"^if you spend this mana to cast", r"^when that mana is spent", r"^if any of that mana is spent",
    r"^when you do,", r"^choose a color\.$", r"^activate only during your turn",
    r"^activate only once each turn",
)
# Mana verdicts that credit nothing because the mana needs something the
# goldfish does not see (M2, M5, M9): named floors.
MANA_FLOORS = ("condition floor", "graveyard floor", "chosen type floor")


def mana_condition(text: str):
    """A condition the goldfish evaluates on its own battlefield (M5); None
    when it needs anything else (graveyard, hand, opponents, a counter put by
    another card): that ability then counts at its unconditional floor;
    "unread" for wording no rule covers, which the fleet guard rejects."""
    lower = text.lower().strip().rstrip(".")
    types = re.fullmatch(r"you control an? (\w+)(?: or an? (\w+))?", lower)
    if types and all(t is None or t.capitalize() in LAND_SUBTYPE_COLORS for t in types.groups()):
        return ("anyType", frozenset(t.capitalize() for t in types.groups() if t))
    if lower == "you control an artifact":
        return ("atLeast", "Artifact", 1)
    count = re.fullmatch(r"you control (\w+) or more (artifacts|lands)", lower)
    if count and count.group(1) in COUNT_WORDS:
        return ("atLeast", count.group(2)[:-1].capitalize(), COUNT_WORDS[count.group(1)])
    tron = re.fullmatch(r"you control an urza's ([\w-]+) and an urza's ([\w-]+)", lower)
    if tron:
        return ("landTypes", frozenset(t.title() for t in tron.groups()))
    if lower == "a card is exiled with this land":
        return ("imprinted",)  # read as the land enters (imprint_from_hand)
    if any(phrase in lower for phrase in ("opponent", "graveyard", "luck counter")):
        return None
    return "unread"


def parse_mana_cost(cost: str, name: str) -> tuple[str, int]:
    """(kind, mana paid) of an activated or loyalty cost (M3).

    kind: "free" ({T}, mana, life, a plus or zero loyalty cost), "once" (the
    cost names the permanent itself: "Sacrifice this artifact", "Sacrifice
    Lotus Petal"), "minus" (a minus loyalty cost), "tapArtifact" ("Tap an
    untapped artifact you control": board_term_atoms counts the artifacts
    that lose nothing by it), "resource" (anything else: another permanent,
    "a" or "an" permanent of a type even when the card is of that type, since
    a pilot feeds Krark-Clan Ironworks, Skirk Prospector or Ashnod's Altar
    with other permanents; a card from hand or graveyard; exert), "unread"
    (wording no rule covers, and removing counters from the permanent: what
    the counters allow is not read).
    """
    cost = cost.strip()
    if re.fullmatch(r"\+?\d+", cost):
        return "free", 0
    if re.fullmatch(r"[−-]\d+", cost):
        return "minus", 0
    kind, mana = "free", 0
    short_name = name.split(" // ")[0].split(",")[0].lower()
    for part in (part.strip() for part in cost.split(",")):
        low = part.lower()
        if re.fullmatch(r"(\{[^}]+\})+", part):
            mana += sum(int(sym) if sym.isdigit() else 1
                        for sym in re.findall(r"\{([^}]+)\}", part) if sym not in ("T", "X"))
        elif re.fullmatch(r"pay \d+ life", low):
            continue
        elif low.startswith("sacrifice this ") or low == f"sacrifice {short_name}":
            kind = "once"
        elif low == "tap an untapped artifact you control":
            kind = "tapArtifact"
        elif low.startswith("remove ") and "counter" in low:
            return "unread", mana
        elif low.startswith(("sacrifice ", "tap ", "exert ", "exile ", "discard ", "remove ")):
            return "resource", mana
        else:
            return "unread", mana
    return kind, mana


def parse_mana_effect(effect: str, own_colors: frozenset, power: int,
                      commander_colors: list[str]) -> dict:
    """The mana one ability's effect makes (M1-M5).

    ``atoms``: one per mana, at the floor with the card alone on the
    battlefield; ``board``: a term the goldfish evaluates each turn on its own
    battlefield; ``gate``: an "Activate only if" condition it evaluates;
    ``restricted``: "Spend this mana only ..." (counted in full, owner
    decision); ``imprint``: the mana an imprinted card gives (atoms
    "instead", or "colors" of the exiled card); ``oneColour``: all of the
    ability's mana is one colour chosen as it is made ("three mana of any one
    color", "Choose a color. Add ... of that color"); ``verdict``: how the
    ability was read ("unread" when no rule covers a sentence). A condition
    inside the ability ("If you control a Dragon, add ...") is read as a gate
    when the goldfish sees it, a floor when it needs anything else, and
    "unread" otherwise.
    """
    cmd = frozenset(commander_colors)
    out = {"atoms": [], "board": None, "gate": None, "restricted": False,
           "imprint": None, "oneColour": False, "verdict": "credited"}
    sentences = [s for s in re.split(r"(?<=\.)\s+", effect.strip()) if s]
    main = next(s for s in sentences if re.search(r"\badds?\b", s, re.I))
    out["oneColour"] = bool(re.search(r"mana of any one color|^choose a color\.$", effect.strip(), re.I)
                            or any(s.lower() == "choose a color." for s in sentences))
    for sentence in sentences:
        lower = sentence.lower()
        if sentence is main or any(re.search(rider, lower) for rider in MANA_RIDERS):
            continue
        conditional = re.fullmatch(r"if (.*?), (?:instead )?add (.*?)(?: instead)?\.", sentence, re.I)
        if lower.startswith("spend this mana only"):
            out["restricted"] = True
        elif lower.startswith("activate only if"):
            out["gate"] = mana_condition(lower[len("activate only if "):])
            if out["gate"] is None:
                out["verdict"] = "condition floor"
        elif conditional:
            # "If <condition>, add <more> instead": evaluated when the goldfish
            # sees the condition (Tron, an imprinted card), else the
            # unconditional floor.
            gate = mana_condition(conditional.group(1))
            if gate == "unread":
                out["verdict"] = "unread"
            elif gate is not None:
                alt = parse_mana_effect("Add " + conditional.group(2) + ".", own_colors, power,
                                        commander_colors)
                if gate == ("imprinted",):
                    out["imprint"] = tuple(alt["atoms"])
                else:
                    out["board"] = ("gate", gate, tuple(alt["atoms"]))
        else:
            out["verdict"] = "unread"
    before, _, after = re.split(r"\b(adds?)\b", main, maxsplit=1, flags=re.I)
    after = after.strip().rstrip(".")
    low = after.lower()
    symbols = re.findall(MANA_SYMBOL, after)
    each = re.fullmatch(r"(\{[wubrgc]\}) for each ([\w' ]+?)(?: you control| on the battlefield)?", low)
    lead = before.strip().rstrip(",").strip().lower()
    if lead and lead != "for each color among permanents you control":
        # A condition inside the ability: "If you control a Dragon, add ...".
        condition = re.fullmatch(r"if (.*)", lead)
        gate = mana_condition(condition.group(1)) if condition else "unread"
        if gate == "unread":
            out["verdict"] = "unread"
            return out
        if gate is None:
            out["verdict"] = "condition floor"
            return out
        out["gate"] = gate
    if lead == "for each color among permanents you control":
        out["atoms"] = [frozenset({color}) for color in "WUBRG" if color in own_colors]
        out["board"] = ("vivid",)
    elif re.fullmatch(r"(an additional )?(\{[WUBRGC]\})+", after):
        out["atoms"] = [frozenset({symbol}) for symbol in symbols]
    elif re.fullmatch(r"(\{[WUBRGC]\})+(, (\{[WUBRGC]\})+)*,? or (\{[WUBRGC]\})+", after):
        size = max(len(re.findall(MANA_SYMBOL, group))
                   for group in re.split(r",? or |, ", after))
        out["atoms"] = [frozenset(symbols)] * size
    elif re.fullmatch(r"(\w+) mana in any combination of (colors|(\{[wubrgc]\})+(, (\{[wubrgc]\})+)*,? "
                      r"and/or (\{[wubrgc]\})+)", low) and low.split()[0] in COUNT_WORDS:
        # "of colors": each mana any colour (the commander's colours, as for
        # "one mana of any color"); else the colours named. The amount from
        # the count-word table (Cascading Cataracts' five).
        out["atoms"] = [frozenset(symbols) or cmd] * COUNT_WORDS[low.split()[0]]
    elif re.fullmatch(r"(two|three) mana of any one color", low):
        out["atoms"] = [cmd] * COUNT_WORDS[low.split()[0]]
    elif low.startswith("one mana of any color among legendary"):
        if "graveyard" in low:
            out["verdict"] = "graveyard floor"
        else:
            kinds = ("Creature", "Planeswalker") if "creatures and planeswalkers" in low else ()
            out["board"] = ("legendColors", kinds)
    elif low == "one mana of any of the exiled card's colors":
        out["imprint"] = "colors"
    elif low == "one mana of any type that a land you control could produce":
        # Reflecting Pool: the colours the other lands on the battlefield
        # could make, read each turn; nothing with no other land.
        out["board"] = ("landColors",)
    elif low in ("one mana of any color", "one mana of any color in your commander's color identity",
                 "one mana of any color that a land an opponent controls could produce"):
        # Colours of opponents' lands (Exotic Orchard, Fellwar Stone) count as
        # the commander's colours: opponents are not modelled (judgement).
        out["atoms"] = [cmd]
    elif re.fullmatch(r"x mana (of any one color|in any combination of .*), where x is .*'s power"
                      r"|an amount of \{[wubrgc]\} equal to .*'s power", low):
        # Variable amount: what the card alone guarantees, its printed power.
        out["atoms"] = [frozenset(symbols) or cmd] * power
        out["verdict"] = "printed power"
    elif re.fullmatch(r"x mana of any one color, where x is the number of elves on the battlefield", low):
        out["board"] = ("count", ("type", "Elf"), cmd)
    elif low == "an amount of mana of that color equal to your devotion to that color":
        out["board"] = ("count", ("devotion",), cmd)
    elif low == ("an amount of mana of that color equal to the number of creatures you control "
                 "of the chosen type"):
        out["verdict"] = "chosen type floor"
    elif each:
        noun = each.group(2)
        word = {"elf": "Elf", "creature": "Creature", "swamp": "Swamp", "urza's land": "Urza's"}.get(
            noun if noun == "urza's land" else noun.rstrip("s").replace("elve", "elf"))
        if "graveyard" in noun:
            out["verdict"] = "graveyard floor"
        elif word is None:
            out["verdict"] = "unread"
        else:
            out["board"] = ("count", ("type", word), frozenset(symbols))
    else:
        out["verdict"] = "unread"
    return out


# Triggered mana whose event the goldfish does not model (named floors),
# matched in full: a sacrifice it feeds with other permanents (Crime
# Novelist), a land the goldfish never exiles to it (Extraplanar Lens). Any
# other wording (Rose, Cutthroat Raider's Junk) is not read.
TRIGGER_FLOORS = (
    r"whenever you sacrifice an artifact, put a \+1/\+1 counter on this creature and add \{[wubrg]\}\.",
    r"whenever a land with the same name as the exiled card is tapped for mana, its controller adds "
    r"one mana of any type that land produced\.",
)
# A card that gives up one of its controller's lands as part of what it does
# (Harrow, Crop Rotation, Roiling Regrowth, Mox Diamond's discard): no rule
# reads what that costs the goldfish.
GIVES_UP_LAND = (r"\b(?:sacrifice|sacrifices|discard|discards|return|returns) "
                 r"(?:an?|one|two|three|four|five|six|seven|x|another|any number of|up to \w+)? ?"
                 r"(?:untapped |tapped |basic |nonbasic |snow )*"
                 r"(?:lands?|land cards?|plains|islands?|swamps?|mountains?|forests?)\b")


def gives_up_land(text: str) -> bool:
    """Whether a card gives up one of its lands as part of what it does
    (GIVES_UP_LAND): in its spell text, a cost, a replacement as it enters or
    its own abilities, not in a separate "Whenever" or "At the beginning"
    trigger (Sutina, Speaker of the Tajuru's return on attack)."""
    return any(re.search(GIVES_UP_LAND, line, re.I)
               for line in strip_reminder_text(text).split("\n")
               if not re.match(r"(Whenever|At the beginning) ", line.strip()))


# A permanent that changes the land types of lands: granting types (Prismatic
# Omen, Dryad of the Ilysian Grove; Urborg's "Each land is a Swamp" on a land
# is read, eachLandIs) or setting them ("Nonbasic lands are Islands").
LAND_TYPE_CHANGE = (r"\b(?:each land|lands you control|all lands|nonbasic lands|lands)\b[^.\"]*\b(?:is|are)\b"
                    r"[^.\"]*\b(?:land types?|the chosen type|plains|islands?|swamps?|mountains?|forests?)\b")


def mana_trigger(line: str):
    """A triggered "add" ability the goldfish evaluates (M2): an on-cast term
    or a board term; None for a named floor (TRIGGER_FLOORS); "unread" for any
    other trigger (a landfall "add" included)."""
    lower = line.lower()
    cast = re.match(r"whenever you cast a spell, add \{([wubrgc])\}\.", lower)
    if cast:
        return ("onCast", frozenset({cast.group(1).upper()}))
    tapped = re.fullmatch(r"whenever you tap an? (swamp|creature|permanent) for (mana|\{c\}), "
                          r"add an additional \{([wubrgc])\}\.", lower)
    if tapped:
        source = {"swamp": "swampsTapped", "creature": "creatureSources",
                  "permanent": "colorlessSources"}[tapped.group(1)]
        return ("extra", source, frozenset({tapped.group(3).upper()}), 0)
    if any(re.fullmatch(pattern, lower) for pattern in TRIGGER_FLOORS):
        return None
    return "unread"


def parse_land_search(text: str) -> dict | None:
    """Lands a "search your library for ... land" effect moves (M8), or None.

    count: lands put onto the battlefield; toHand: lands put into the hand;
    perType: one land of each named type ("a Forest card and a Plains card");
    sharedType: the lands share a basic land type. A put that depends on
    opponents ("If an opponent controls more lands than you") counts as its
    other branch. The whole clause up to its first comma is read: "unread"
    for a land search whose count or filter no rule places ("up to X",
    "four", "that many", "a snow land card", a qualification after "card":
    "with different names", "that each have a basic land type", "of each
    basic land type", "or Planet card").
    """
    lower = text.lower()
    found = re.search(r"search your library for (up to )?(a|an|one|two|three) "
                      r"((?:basic )?[\w,' ]*?)cards?\b", lower)
    if not found:
        clause = re.search(r"search your library for ([^.]*?)\bcards?\b", lower)
        if clause and re.search(r"\b(?:lands?|plains|islands?|swamps?|mountains?|forests?)\b", clause.group(1)):
            return "unread"
        return None
    count = COUNT_WORDS[found.group(2)]
    kinds = found.group(3).strip()
    if not set(re.findall(r"[a-z']+", kinds)) <= {"basic", "land", "plains", "island", "swamp", "mountain",
                                                   "forest", "or", "and"}:
        if re.search(r"\b(?:lands?|plains|islands?|swamps?|mountains?|forests?)\b", kinds):
            return "unread"
        return None
    # The rest of the clause after "card": nothing, a shared land type, a
    # second named type ("a Forest card and a Plains card"; Yasharn's "a
    # basic Forest card and a basic Plains card"), or the verb that follows.
    tail = re.match(r"[^,.;\n]*", lower[found.end():]).group(0).strip()
    second = re.fullmatch(r"and an? (?:basic )?(\w+) card", tail)
    per_type = []
    if second:
        first = kinds.replace("basic", "").strip().capitalize()
        if first not in LAND_SUBTYPE_COLORS or second.group(1).capitalize() not in LAND_SUBTYPE_COLORS:
            return "unread"
        per_type = [first, second.group(1).capitalize()]
        count = len(per_type)
    allowed = {t for t in LAND_SUBTYPE_COLORS if t.lower() in kinds} | set(per_type)
    if not allowed and "land" not in kinds:
        return None  # not a land search (Ringsight's "a card that shares a color")
    if not second and tail and tail != "that share a land type" and not re.match(r"and (?:put|reveal)\b", tail):
        return "unread"
    if not second and re.match(r",? (?:and )?an? \w+ card", lower[found.end():]):
        return "unread"  # a list of cards, one clause each (Shard Convergence)
    # A condition before the land search in its sentence: one that reads
    # opponents is a floor (None), any other is not read.
    lead = re.split(r"[.:\n]", lower[:found.start()])[-1]
    if re.search(r"\bif\b", lead):
        return None if "opponent" in lead else "unread"
    after = lower[found.end():]
    # Each destination the text names is read, or the search is refused:
    # a split between the battlefield and the hand only in these words, and
    # no later "instead" (Embermouth Sentinel) unless it depends on opponents
    # (the floor above).
    split = re.search(r"put (one|two) (?:of them )?onto the battlefield tapped and the (other|rest) into your hand",
                      after)
    opponents = "if an opponent controls more lands than you" in after
    if split:
        # Cultivate, Nissa's Pilgrimage, Viewpoint Synchronization.
        on_battlefield = COUNT_WORDS[split.group(1)]
        to_hand = 1 if split.group(2) == "other" else count - on_battlefield
    elif re.search(r"\binstead\b", after) and not opponents:
        return "unread"
    elif "onto the battlefield" in after and "into your hand" in after and not opponents:
        return "unread"
    elif opponents or re.search(r"put (them|it|that card) into your hand", after):
        on_battlefield, to_hand = 0, count
    elif "onto the battlefield" in after:
        on_battlefield, to_hand = count, 0
    else:
        return None
    return {
        "count": on_battlefield,
        "toHand": to_hand,
        "basicOnly": "basic" in kinds,
        "allowedSubtypes": allowed,
        "perType": per_type,
        "sharedType": "share a land type" in after,
        "entersTapped": "onto the battlefield tapped" in after,
    }


def parse_land_entry(text: str) -> tuple | str:
    """How a land enters (M6, M7), as a rule land_enters_tapped evaluates on
    the battlefield (and the hand) as the land is played; "unread" for wording
    no rule covers.

    Opponents follow the vanilla four-player model of the per-deck mana
    simulations: "unless you have two or more opponents" is always met, and
    "unless your opponents control eight or more lands" is met from your
    fourth land drop (DEC-688 / DEC-929: mana_simulation_gathering_shadow.py
    114-120, mana_simulation_eternal_agony.py 180-186,
    mana_simulation_hoard_and_bleed.py 223-229).
    """
    lower = strip_reminder_text(text).lower()
    if "you may pay 2 life" in lower or "you may pay 3 life" in lower:
        return ("untapped",)
    # A fetch land's own text about the land it puts onto the battlefield
    # (landCrack) is not about how the fetch land enters.
    lower = re.sub(r"search your library.*", "", lower, flags=re.S)
    reveal =re.search(r"you may reveal an? (\w+) or (\w+) card from your hand\. if you don't, "
                       r"this land enters tapped", lower)
    if reveal:
        return ("reveal", frozenset(t.capitalize() for t in reveal.groups()))
    unless = re.search(r"enters tapped unless (.*?)\.", lower)
    if unless:
        condition = unless.group(1)
        types = re.fullmatch(r"you control an? (\w+)(?: or an? (\w+))?", condition)
        other = re.fullmatch(r"you control (two|three) or (fewer|more) other lands", condition)
        basics = re.fullmatch(r"you control (a|two) (?:or more )?basic lands?", condition)
        typed = re.fullmatch(r"you control three or more other (islands|swamps)", condition)
        if condition == "you have two or more opponents":
            return ("untapped",)
        if condition == "your opponents control eight or more lands":
            return ("otherLandsAtLeast", 3)
        if types and all(t is None or t.capitalize() in LAND_SUBTYPE_COLORS for t in types.groups()):
            return ("anyType", frozenset(t.capitalize() for t in types.groups() if t))
        if condition == "you control a legendary creature":
            return ("legendaryCreature",)
        if other:
            return ("otherLandsAtMost" if other.group(2) == "fewer" else "otherLandsAtLeast",
                    COUNT_WORDS[other.group(1)])
        if basics:
            return ("basicsAtLeast", COUNT_WORDS[basics.group(1)])
        if typed:
            return ("otherTypeAtLeast", typed.group(1)[:-1].capitalize(), 3)
        return "unread"
    if "if you control two or more other lands, this land enters tapped" in lower:
        return ("otherLandsAtMost", 1)
    if "enters tapped" in lower:
        return ("tapped",)
    return ("untapped",)


def card_mana_model(name: str, meta: dict, commander_colors: list[str]) -> dict:
    """The mana a permanent gives the goldfish (owner-approved 2026-11-19).

    A permanent gives the mana its own text gives a pilot on a normal turn,
    using only itself and what the goldfish has on its own battlefield; mana
    that needs anything else is not credited (a named floor):
    M1 the face on the battlefield, without reminder or quoted text; basic
       land types make their colour (Urborg is itself a Swamp); an ability a
       card grants counts for itself when it is one of the permanents granted
       (the grant's subject matched in full, SELF_GRANT_SUBJECTS); a grant to
       lands is read as colours every land can make (``landGrant``).
    M2 activated and plus or zero loyalty abilities make mana ("add", "adds",
       "produces"); a triggered "add" counts only where the goldfish evaluates
       it (mana_trigger).
    M3 free costs: {T}, life, a plus or zero loyalty cost; mana in the cost
       nets produced minus paid; a cost that names the permanent itself
       ("Sacrifice this artifact") or a permanent that does not untap gives
       the mana once, held until a turn spends it ("{N}: Untap this" re-arms
       it, ``onceRearm``); tapping an untapped artifact counts the artifacts
       that lose nothing by it (Urza); any other resource gives nothing;
       removing the permanent's own counters is not read.
    M4 a permanent taps once: its best single ability; at one mana, the union
       of the colours of the abilities it could use instead.
    M5 conditions on its own battlefield are evaluated each turn
       (``manaBoard``); other conditions count at the floor; restricted mana
       counts in full; variable amounts count what the card alone guarantees.
       An imprint from the hand is made as the card enters (``imprint``).
    M6 land faces, fetch lands (cracked for a land of the library as they
       are played, ``landCrack``), entry rules, lands given up as it enters
       (``landEntryCost``).
    M7 a creature whose mana ability uses {T}, or a permanent that enters
       tapped, makes mana from the next turn; a costed non-land ability
       (Signets) also from the next turn, a floor: using it the turn the
       permanent is cast needs a spare mana the goldfish does not plan for.

    Returns ``manaAtoms`` (one mana a turn per atom, the floor with the card
    alone), ``manaOnce`` (one-shot atoms) and ``onceLeaves`` (spending them
    sacrifices it), ``manaBoard`` (terms evaluated each turn), ``manaOnCast``
    (atoms per spell cast while it is out), ``manaSourceDelay`` (0 this turn,
    1 from the next, None when it gives nothing), ``manaTapsSelf`` (an
    ability it is tapped for mana by has {T}: a creature then does not
    attack), ``manaOneColour`` (all of one activation's mana is one colour),
    ``manaTurns`` (a Saga's turns of mana), ``imprint``, the land fields and
    ``verdicts``: each mana line with how it was read; build_goldfish_profile
    refuses a card with an "unread" verdict.
    """
    type_line, text = battlefield_face(meta)
    words = type_words(type_line)
    is_land = "Land" in words
    model = {"isLand": is_land, "manaAtoms": [], "manaOnce": [], "onceLeaves": False,
             "onceRearm": None, "manaOneColour": False,
             "manaBoard": [], "manaOnCast": [], "manaSourceDelay": None, "manaTapsSelf": False,
             "manaTurns": None, "imprint": None, "landEntry": None, "landEntryCost": None,
             "landFaces": None, "landFetch": None, "landCrack": None, "landTypes": frozenset(),
             "eachLandIs": None, "landGrant": None, "landOutputs": [], "entersTapped": False,
             "verdicts": []}
    if not is_land and not ({"Artifact", "Creature", "Enchantment", "Planeswalker"} & words):
        return model  # an instant or sorcery: not a permanent's mana (floor)
    try:
        power = max(0, int(meta.get("power") or 0))
    except ValueError:
        power = 0
    # A land face is colourless; Dryad Arbor, a land creature, has its colour.
    own_colors = (frozenset(meta.get("colors") or []) if not is_land or "Creature" in words
                  else frozenset())
    stripped = strip_reminder_text(text)
    for subject, quoted, reading in quoted_grants(text):
        if reading == "unread":
            model["verdicts"].append((f'{subject} "{quoted}"', "unread"))
        elif reading == "other" or SELF_GRANT_SUBJECTS[subject] not in words | {""}:
            if subject == "lands you control have":
                # A grant to every land (Chromatic Lantern): its colours, read
                # only for exactly "{T}: Add" one mana with nothing else in
                # the grant or after it (Resonating Lute's two restricted mana
                # is not read).
                cost, _, effect = quoted.partition(":")
                read = parse_mana_effect(effect, own_colors, power, commander_colors)
                whole = re.search(rf'^Lands you control have "{re.escape(quoted)}"\.?$', stripped, re.M)
                plain = (cost.strip() == "{T}" and len(read["atoms"]) == 1 and whole is not None
                         and read["verdict"] == "credited" and not read["restricted"]
                         and read["gate"] is None and read["board"] is None)
                model["landGrant"] = frozenset(read["atoms"][0]) if plain else None
                model["verdicts"].append((quoted, "land grant" if plain else "unread"))
            else:
                model["verdicts"].append((quoted, "grant floor"))
    lines = own_ability_lines(text, words)
    lasting, once = [], []
    costed = False
    level = False
    for line in lines:
        if re.fullmatch(r"(\{[^}]+\})+: Level \d+|LEVEL \d+(-\d+|\+)?", line):
            level = True  # the abilities below belong to a level not gained
            continue
        if not re.search(MANA_WORDS, line, re.I):
            continue
        if level:
            model["verdicts"].append((line, "unread"))
            continue
        if line.startswith("Max speed — "):
            model["verdicts"].append((line, "condition floor"))  # speed counts opponents' life
            continue
        if line.startswith("Exhaust — "):
            model["verdicts"].append((line, "unread"))  # once a game: no rule reads it
            continue
        body = re.sub(r"^(?!(?:[IVX]+, )*[IVX]+ —)[A-Z][\w' ]* — ", "", line)
        if re.match(r"(When|Whenever|At) ", body):
            term = mana_trigger(body)
            if term is None or term == "unread":
                model["verdicts"].append((line, "trigger floor" if term is None else "unread"))
            elif term[0] == "onCast":
                model["manaOnCast"].append(term[1])
                model["verdicts"].append((line, "on cast"))
            else:
                if "earthbend" in stripped.lower():
                    term = term[:3] + (1,)  # its earthbent land is a creature tapped for mana
                model["manaBoard"].append(term)
                model["verdicts"].append((line, "board extra"))
            continue
        cost, sep, effect = body.partition(":")
        if not sep or not re.search(r"\badds?\b", effect, re.I):
            model["verdicts"].append((line, "unread"))
            continue
        if is_land:
            # What the ability's effect makes, before its cost is netted and
            # whatever the cost or condition (Reflecting Pool reads it,
            # land_could_produce): a fixed output, or a board term evaluated
            # on the battlefield (Cabal Coffers' Swamps).
            printed = parse_mana_effect(effect, own_colors, power, commander_colors)
            if printed["verdict"] != "unread" and printed["board"] is not None:
                model["landOutputs"].append(("board", printed["board"]))
            elif printed["verdict"] != "unread" and printed["atoms"]:
                model["landOutputs"].append(("fixed", frozenset().union(*printed["atoms"])))
        kind, paid = parse_mana_cost(cost, name)
        if kind not in ("free", "once", "tapArtifact"):
            model["verdicts"].append((line, {"resource": "needs another resource",
                                             "minus": "minus loyalty"}.get(kind, kind)))
            continue
        read = parse_mana_effect(effect, own_colors, power, commander_colors)
        if "unread" in (read["verdict"], read["gate"]):
            model["verdicts"].append((line, "unread"))
            continue
        if read["verdict"] in MANA_FLOORS:
            model["verdicts"].append((line, read["verdict"]))
            continue
        # Whatever this ability credits below, using it taps the permanent
        # when its cost has {T} (a count or gated creature included).
        taps = "{T}" in cost
        net = len(read["atoms"]) - paid
        colours = frozenset().union(*read["atoms"]) if read["atoms"] else frozenset()
        if kind == "tapArtifact":
            # Each untapped artifact that loses nothing by it (no mana of its
            # own, not a creature) pays it; a token artifact it makes as it
            # enters is one (Urza's Construct).
            own = 1 if re.search(r"When \w+ enters, create [^.]*artifact[^.]*token", stripped) else 0
            model["manaBoard"].append(("count", ("idleArtifacts", own), colours, 0, None))
            model["verdicts"].append((line, "board"))
            continue
        if read["imprint"] is not None:
            model["imprint"] = {"atoms": None if read["imprint"] == "colors" else read["imprint"]}
            model["verdicts"].append((line, "imprint"))
            model["manaTapsSelf"] |= taps
            if read["imprint"] == "colors":
                continue
        board = read["board"]
        if board is not None and board[0] == "count":
            model["manaBoard"].append(("count", board[1], board[2], paid, read["gate"]))
            model["verdicts"].append((line, "board"))
            model["manaTapsSelf"] |= taps
            model["manaOneColour"] |= read["oneColour"]
            continue
        if board is not None:
            model["manaBoard"].append(board)
            model["manaTapsSelf"] |= taps
        if read["gate"] is not None:
            if net > 0:
                model["manaBoard"].append(("gate", read["gate"], tuple([colours] * net)))
                model["manaTapsSelf"] |= taps
            model["verdicts"].append((line, "gated" if net > 0 else "filter"))
            continue
        if net <= 0:
            model["verdicts"].append((line, "board" if board else read["verdict"]
                                      if read["verdict"] == "printed power" else "filter"))
            continue
        atoms = list(read["atoms"]) if not paid else [colours] * net
        model["manaTapsSelf"] |= taps
        model["manaOneColour"] |= read["oneColour"] and len(atoms) > 1
        if kind == "once":
            once.append(atoms)
            model["onceLeaves"] = True
            model["verdicts"].append((line, "once"))
            continue
        lasting.append(atoms)
        costed = costed or bool(paid)
        model["verdicts"].append((line, "restricted, in full" if read["restricted"]
                                  else read["verdict"]))
    imprint = re.search(r"Imprint — When this \w+ enters, you may exile an? ([\w, ]+?) card"
                        r"(?: with mana value (\d+) or greater)? from your hand", stripped)
    if model["imprint"] is not None and imprint:
        kinds = imprint.group(1)
        model["imprint"].update(colorless="colorless" in kinds, nonartifact="nonartifact" in kinds,
                                nonland="nonland" in kinds,
                                minValue=int(imprint.group(2) or 0))
    elif model["imprint"] is not None:
        model["verdicts"].append(("imprint", "unread"))
    if is_land:
        intrinsic = frozenset(LAND_SUBTYPE_COLORS[t] for t in words if t in LAND_SUBTYPE_COLORS)
        each_land = re.search(r"Each land is an? (\w+) in addition", stripped)
        if each_land:
            model["eachLandIs"] = each_land.group(1)
            intrinsic |= {LAND_SUBTYPE_COLORS[each_land.group(1)]}
            model["landGrant"] = frozenset({LAND_SUBTYPE_COLORS[each_land.group(1)]})
        if intrinsic:
            lasting.append([intrinsic])
            model["manaTapsSelf"] = True
            model["landOutputs"].append(("fixed", intrinsic))
        model["landTypes"] = (NONBASIC_LAND_TYPES if "This land is every nonbasic land type" in stripped
                              else frozenset(w for w in words if w not in CARD_TYPE_WORDS))
        fetch_cost = re.search(r"^(.*?): Search your library", stripped, re.M)
        search = parse_land_search(stripped)
        if search == "unread":
            model["verdicts"].append(("search", "unread"))
        elif search and fetch_cost and "Sacrifice this land" not in fetch_cost.group(1):
            # A search behind a cost that keeps the land (Thawing Glaciers,
            # back to the hand at the cleanup step): not read.
            model["verdicts"].append((fetch_cost.group(0), "unread"))
        elif search and fetch_cost and "Sacrifice this land" in fetch_cost.group(1):
            _, fetch_paid = parse_mana_cost(fetch_cost.group(1), name)
            tail = stripped.lower()[stripped.lower().index("search your library"):]
            if fetch_paid == 0:
                # A fetch land (M6): cracked as it is played for a land of the
                # library that it can find; it makes no mana of its own.
                untap = (("landsAtLeast", 4) if "four or more lands, untap" in tail
                         else ("elf",) if "behold an elf" in tail else None)
                model["landCrack"] = dict(search, untapIf=untap)
                model["verdicts"].append((fetch_cost.group(0), "crack"))
            else:
                model["landFetch"] = dict(search, tapsSelf="{T}" in fetch_cost.group(1),
                                          cost=parse_generic_mana_cost(
                                              "".join(re.findall(r"\{[^}T]+\}", fetch_cost.group(1)))))
                model["verdicts"].append((fetch_cost.group(0), "land fetch"))
        # A land creature (Dryad Arbor) enters by its own rule and is summoning
        # sick: untapped, its mana from the next turn (put_land_onto_battlefield).
        model["landEntry"] = parse_land_entry(text)
        if model["landCrack"] and model["landEntry"] != ("untapped",):
            # A fetch land with an entry rule of its own (Grasslands enters
            # tapped): cracking it as it is played is not read.
            model["verdicts"].append(("a fetch land's own entry rule", "unread"))
        short_name = re.escape(name.split(" // ")[0].split(",")[0])
        for line in stripped.split("\n"):
            if (re.match(r"(When|Whenever|At) ", line) and "you may" not in line
                    and re.search(rf"(?:sacrifice|return|exile) (?:this land|{short_name})\b", line)):
                # It sacrifices, returns or exiles itself (City of Traitors):
                # not read.
                model["verdicts"].append((line, "unread"))
        if re.search(r"choose a basic land type|as a copy of", stripped, re.I):
            # Its land type, or the land it copies, is chosen as it enters
            # (Multiversal Passage, Thran Portal, Vesuva): not read.
            model["verdicts"].append(("a type or copy chosen as it enters", "unread"))
        given_up = re.search(r"(if this land would enter, )?sacrifice (two)(?: untapped)? lands"
                             r"|return (a) land you control to its owner's hand", stripped.lower())
        if given_up:
            # Lands it takes as it enters (M6): sacrificed "instead" of entering
            # (gone before they are tapped), or by an entering trigger (tapped
            # in response first) and returned to the hand or sacrificed.
            model["landEntryCost"] = {
                "count": COUNT_WORDS[given_up.group(2) or given_up.group(3)],
                "now": bool(given_up.group(1)), "toHand": bool(given_up.group(3))}
        elif re.search(r"(?:enters|would enter)[^.]*\b(?:sacrifice|return)\b", stripped.lower()):
            # Any other sacrifice or return as it enters: of lands in other
            # words (Coral Atoll's "an untapped Island"), or of itself (Brokers
            # Hideout).
            model["verdicts"].append(("lands taken as it enters", "unread"))
        back = meta.get("back_face")
        if back and "Land" in meta.get("type_line", "").split(" // ")[0]:
            # Two land faces (Pathways): the face is chosen as it is played.
            model["landFaces"] = [
                card_mana_model(name, {"type_line": face["type_line"], "oracle_text": face["oracle_text"]},
                                commander_colors)["manaAtoms"]
                for face in ({"type_line": type_line, "oracle_text": text}, back)]
    else:
        for line in lines:
            cost, sep, effect = line.partition(":")
            found = parse_land_search(effect) if sep and "Search your library" in effect else None
            if found == "unread":
                model["verdicts"].append((line, "unread"))
                continue
            kind, paid = parse_mana_cost(cost, name) if found else ("", 0)
            if found and kind == "once" and found["count"]:
                model["landFetch"] = dict(found, tapsSelf="{T}" in cost, cost=parse_generic_mana_cost(
                    "".join(re.findall(r"\{[^}T]+\}", cost))))
                model["verdicts"].append((line, "land fetch"))
            elif found and found["count"] and kind in ("free", "unread", "tapArtifact"):
                # A land search the permanent keeps after (no self-sacrifice):
                # repeatable, not read. Another permanent sacrificed for it
                # (Elvish Reclaimer's land) nets nothing: not credited.
                model["verdicts"].append((line, "unread"))
    if once and lasting and model["onceLeaves"]:
        # A sacrifice-for-mana ability beside its lasting mana (Crystal Vein:
        # {C}, or sacrifice it for {C}{C}): alternatives, not both; not read.
        model["verdicts"].append(("lasting mana or sacrificing it for more", "unread"))
    each_land = re.search(r"Each land is an? \w+ in addition to its other land types", stripped)
    for line in stripped.split("\n"):
        if not re.search(LAND_TYPE_CHANGE, line, re.I) or (is_land and each_land
                                                            and each_land.group(0) in line):
            continue
        set_to = re.fullmatch(r"Nonbasic lands are (Plains|Island|Swamp|Mountain|Forest)s?\.", line)
        if set_to and sorted(commander_colors) == [LAND_SUBTYPE_COLORS[set_to.group(1)]]:
            # Setting the type of every nonbasic land to the type of the
            # commander's only colour (Harbinger of the Seas in a mono-blue
            # deck): not applied to the goldfish's own lands, a named floor
            # (owner-accepted, review round 3). In any other deck (Blood Moon,
            # Magus of the Moon beside other colours) it is not read.
            model["verdicts"].append((line, "land types set, not applied"))
        else:
            # Granting land types (Prismatic Omen, Dryad of the Ilysian
            # Grove): every land's mana changes; no rule reads it.
            model["verdicts"].append((line, "unread"))
    # M4: one activation a turn, its best free ability; at one mana the union
    # of the colours of the abilities it could use instead.
    if lasting:
        best = max(len(atoms) for atoms in lasting)
        model["manaAtoms"] = ([frozenset().union(*(atoms[0] for atoms in lasting))] if best == 1
                              else list(next(atoms for atoms in lasting if len(atoms) == best)))
    # A count term's value with the card alone on the battlefield is its floor.
    for term in model["manaBoard"]:
        if term[0] == "count" and term[1][0] in ("type", "idleArtifacts") and term[4] is None:
            if term[1][0] == "idleArtifacts":
                alone = term[1][1]
            else:
                alone = 1 if term[1][1] in words or (term[1][1] not in CARD_TYPE_WORDS
                                                     and "Changeling" in stripped) else 0
            if alone - term[3] > len(model["manaAtoms"]):
                model["manaAtoms"] = [term[2]] * (alone - term[3])
    if "doesn't untap during your untap step" in stripped and model["manaAtoms"]:
        once.append(model["manaAtoms"])
        model["manaAtoms"] = []
        rearm = re.search(r"^(\{\d+\}): Untap this \w+\.$", stripped, re.M)
        if rearm:
            model["onceRearm"] = parse_generic_mana_cost(rearm.group(1))
    if once:
        model["manaOnce"] = max(once, key=len)
    if (not is_land and gives_up_land(stripped)
            and (model["manaAtoms"] or model["manaOnce"] or model["manaBoard"] or model["manaOnCast"]
                 or model["landFetch"] or model["imprint"])):
        # Mana from a card that gives up a land to enter or as it acts (Mox
        # Diamond's discard): what that costs the goldfish is not read.
        model["verdicts"].append(("gives up a land", "unread"))
    chapters = re.findall(r"^([IVX]+)(?:, [IVX]+)* —", stripped, re.M)
    if chapters and (model["manaAtoms"] or model["manaOnce"] or model["manaBoard"]):
        # A Saga is sacrificed after its last chapter resolves, on the turn
        # (chapters - 1) after it enters; it is tapped for mana first, so its
        # mana lasts as many turns as it has chapters.
        model["manaTurns"] = max(("I", "II", "III", "IV", "V").index(c) + 1 for c in chapters)
    if not is_land:
        # A non-land permanent that enters tapped, a rider after it included
        # (Nevinyrral's Disk; Noble's Purse "enters tapped and with three coin
        # counters"), is tapped until the next untap step, for every reader
        # (Urza's grant), and its mana comes from the next turn.
        short = re.escape(name.split(" // ")[0].split(",")[0])
        model["entersTapped"] = bool(re.search(rf"^(?:This \w+|{short}) enters tapped(?:\.| and\b)",
                                               stripped, re.M))
    if is_land:
        model["manaSourceDelay"] = 0
    elif (model["manaAtoms"] or model["manaOnce"] or model["manaBoard"] or model["manaOnCast"]
          or model["imprint"]):
        # A creature's mana comes the turn it enters only from an activated
        # ability without {T} (Urza taps another artifact); a {T} ability is
        # summoning sick, and a triggered extra (Crypt Ghast) is read from the
        # next turn's pool, as every board term is.
        costs = [line.partition(":")[0] for line in lines
                 if ":" in line and re.search(MANA_WORDS, line, re.I)]
        sick = "Creature" in words and (any("{T}" in cost for cost in costs) or not costs)
        model["manaSourceDelay"] = 1 if (sick or costed or model["entersTapped"]) else 0
    return model


def is_mana_source(profile: dict) -> bool:
    """A permanent with lasting mana (at least one every turn), a spell that
    puts a land onto the battlefield, or a permanent with a land-fetching
    ability the goldfish activates (M7, M8): the cast order's ramp tier, the
    mulligan's cheap ramp, the ramp count and the DEC-944 hold exemption.
    A permanent whose mana an imprint sets (Chrome Mox) is one too. One-shot
    sources and cards with no credited mana are not."""
    return (bool(profile["manaAtoms"]) or bool(profile["landRamp"] and profile["landRamp"]["count"])
            or bool(profile["landFetch"]) or bool(profile["imprint"]))


def parse_land_ramp_profile(meta: dict, name: str = "") -> dict | str | None:
    """Lands a spell, or a permanent's entering trigger ("When this creature
    enters" or "When <its short name> enters"), moves as it resolves (M8).
    Refused, as the reason no rule reads it: "unread" for a search no rule
    places (a condition before it, its count or filter: parse_land_search),
    "gives up a land" for a card that sacrifices, discards or returns a land
    as it resolves or as a cost (Harrow, Crop Rotation, Roiling Regrowth)."""
    type_line, text = battlefield_face(meta)
    words = type_words(type_line)
    if "Land" in words:
        return None
    spell = bool({"Instant", "Sorcery"} & words)
    short = re.escape(name.split(" // ")[0].split(",")[0]) if name else r"this \w+"
    for line in own_ability_lines(text, words):
        if spell or re.match(rf"When (?:this \w+|{short}) enters, ", line):
            found = parse_land_search(line)
            if found == "unread":
                return found
            if found and (found["count"] or found["toHand"]):
                if gives_up_land(text):
                    return "gives up a land"
                return found
    return None


def immediate_draw_count(name: str, meta: dict) -> int:
    """Cards drawn as the card is cast or enters, from its oracle text.

    Reminder text in parentheses is removed, then each oracle line is kept or
    skipped. Skipped: an activated ability, minus loyalty included (a colon
    before the line's first "draw", unless it is a plus or zero loyalty
    ability); a saga chapter line without chapter I; a trigger ("Whenever",
    "At the beginning", "When ") other than the card's own entering (first
    sentence: "this <word>" or the card's name, optionally " or ..." up to
    the next comma, then "enter" or "enters") or own casting ("When you cast
    this spell"). A "•" mode line follows the line that introduces it. In a
    kept line the first sentence with "draw N cards", "draw a card" or
    "target player draws N cards" counts. A sentence naming a trigger
    (whenever, at the beginning, attacks, dies, combat damage, or "when"
    without "enters") is passed over; in the first sentence of the card's
    own entering or casting trigger only "at the beginning" (a delayed draw)
    is. "Draws" with any other subject ("target opponent draws") counts 0.

    Floors (counts less): an affordable minus ability (the metadata carries
    no loyalty); activated draws on the cast turn (CAST_TURN_ACTIVATION_DRAW
    names the exceptions); a draw only in reminder text (connive, recruit);
    an own name containing a period; "each player draws" (the pilot is one
    of them); an own entering trigger behind an ability word ("Constellation
    — Whenever this creature ... enters, draw a card"); in a later sentence
    of an own trigger, a same-resolution draw worded with "dies" or
    "attacks", or after a reflexive "When you do"; spelled-out counts above
    five ("draw 6 cards" counts 6), and variable counts, which count 0 or 1
    (X_SPELL_DRAW sets an X draw spell's count when it is cast with X paid).
    Over-credits (counts more): a conditional draw counts as if the
    condition held, a modal spell its draw mode, "target player draws" as if
    the pilot targets themself, "draw" after another subject ("target
    opponent may draw a card") as the pilot's, a static "If you would draw a
    card ..." as a draw, a later sentence of a trigger behind an ability word
    ("Landfall — Whenever ...") as spell text, a draw inside a quoted granted
    ability in an own trigger's first sentence, and a cast trigger's draw
    also when a path puts the card onto the battlefield without casting it;
    discards, put-backs and sacrifice costs are not modelled.
    """
    oracle = re.sub(r"\([^)]*\)", "", meta.get("oracle_text", ""))
    own_subjects = [r"this \w+"]
    for face in name.lower().split(" // "):
        own_subjects += [re.escape(face), re.escape(face.split(",", 1)[0])]
    # The subject, then optionally " or <another subject>", then enter(s):
    # "this creature or another creature you control ... enters" is its own
    # entering; "this creature attacks or another creature ... enters" is not.
    own_entering = re.compile(
        rf"(when|whenever) ({'|'.join(own_subjects)})(?: or [^,]*)? enters?\b")
    skip_line = False
    for line in oracle.split("\n"):
        line = line.strip()
        lower = line.lower()
        own_trigger = False
        if not line.startswith("\u2022"):
            first = lower.split(".", 1)[0]
            chapter = re.match(r"([IVX]+(?:, [IVX]+)*) \u2014 ", line)
            trigger = first.startswith(("whenever", "at the beginning", "when "))
            own_trigger = trigger and bool(
                own_entering.match(first)
                or first.startswith("when you cast this spell"))
            skip_line = bool(
                (":" in lower.split("draw", 1)[0]
                 and not re.match(r"(\+(\d+|X)|0):", line))
                or (chapter and "I" not in chapter.group(1).split(", "))
                or (trigger and not own_trigger)
            )
        if skip_line:
            continue
        for index, sentence in enumerate(line.split(".")):
            lower = sentence.strip().lower()
            if "draw" not in lower:
                continue
            # "At the beginning" marks a delayed or recurring draw anywhere. In
            # the first sentence of the card's own entering or casting trigger
            # the other trigger words are that trigger itself; any other
            # sentence naming a trigger is treated as a later, recurring draw.
            if "at the beginning" in lower:
                continue
            if not (own_trigger and index == 0):
                if "whenever" in lower or "attacks" in lower:
                    continue
                if "dies" in lower or "deals combat damage" in lower:
                    continue
                if "enters" not in lower and lower.startswith("when "):
                    continue

            # "Target player draws": the pilot targets themself.
            match = re.search(
                r"(?:draw|target player draws) (a|an|one|two|three|four|five|\d+) cards?",
                lower)
            if match:
                token = match.group(1)
                if token.isdigit():
                    return int(token)
                return {
                    "a": 1,
                    "an": 1,
                    "one": 1,
                    "two": 2,
                    "three": 3,
                    "four": 4,
                    "five": 5,
                }.get(token, 1)
            if "draw a card" in lower:
                return 1
    return 0


def targets_only_creatures(meta: dict) -> bool:
    """True when every target the spell takes is a single creature (DEC-393).

    Zada's trigger needs a spell that "targets only Zada": accept oracle text
    where the word target/targets is always immediately followed by "creature"
    (e.g. "target creature gains haste") and appears at least once. Plural
    "target creatures" and reminder text stay disqualifying on purpose —
    storm/copy reminders mention "new targets" and those spells can't target
    only the commander.
    """
    lowered = (meta.get("oracle_text") or "").lower()
    if not re.search(r"\btarget creature\b", lowered):
        return False
    return not re.search(r"\btargets?\b(?!\s+creature\b)", lowered)


def creature_token_count(meta: dict) -> int:
    """Fixed creature-token count a card makes on resolution (DEC-393).

    Feeds the copy-engine creature ledger only. A sentence is skipped when it
    names a trigger (whenever, at the beginning, attacks, dies, combat damage,
    or "when" without "enters"), has a colon before "create" (an activated or
    loyalty ability) or counts "for each", so recurring triggers don't count;
    granted-ability quotes are stripped so a token's own "Whenever ..." text
    doesn't hide the create clause. X-counts and storm copies parse as 0 —
    the ledger is a floor.
    """
    oracle = re.sub(r'"[^"]*"', "", meta.get("oracle_text", ""))
    total = 0
    for sentence in re.split(r"[\n.]", oracle):
        lower = sentence.strip().lower()
        if "create" not in lower:
            continue
        if "whenever" in lower or "at the beginning" in lower or "attacks" in lower:
            continue
        if "dies" in lower or "deals combat damage" in lower:
            continue
        if "enters" not in lower and lower.startswith("when "):
            continue
        # A colon before "create" marks an activated/loyalty ability — not an
        # on-resolution effect; "for each" counts are variable (floor: 0).
        if ":" in lower.split("create", 1)[0]:
            continue
        if "for each" in lower:
            continue
        for count_token in re.findall(r"\bcreate (a|an|one|two|three|four|five|\d+)\b[^.]*?\bcreature tokens?\b", lower):
            total += int(count_token) if count_token.isdigit() else COUNT_WORDS.get(count_token, 1)
    return total


def land_types_on_battlefield(battlefield_lands: list[dict], profiles: dict) -> list[frozenset]:
    """Each land's land types, with a type another land gives every land
    ("Each land is a Swamp": Urborg)."""
    granted = {profiles[land["name"]]["eachLandIs"] for land in battlefield_lands} - {None}
    return [profiles[land["name"]]["landTypes"] | granted for land in battlefield_lands]


def has_creature_type(profile: dict, word: str) -> bool:
    """A permanent's creature type, a changeling having every one."""
    return word in profile["typeWords"] or (profile["changeling"] and word not in CARD_TYPE_WORDS)


def land_enters_tapped(rule: tuple, battlefield_lands: list[dict], permanents: list[dict],
                       profiles: dict, hand: list[str]) -> bool:
    """Whether a land enters tapped under its entry rule (parse_land_entry),
    read against the lands and permanents already on the battlefield and the
    rest of the hand (a Snarl's reveal, Elven Passage's behold)."""
    kind = rule[0]
    if kind == "reveal":
        return not any(profiles[card]["subtypes"] & rule[1] for card in hand)
    if kind in ("untapped", "tapped"):
        return kind == "tapped"
    if kind == "otherLandsAtMost":
        return len(battlefield_lands) > rule[1]
    if kind == "otherLandsAtLeast":
        return len(battlefield_lands) < rule[1]
    if kind == "basicsAtLeast":
        return sum(1 for land in battlefield_lands if land["isBasic"]) < rule[1]
    land_types = land_types_on_battlefield(battlefield_lands, profiles)
    if kind == "anyType":
        return not any(rule[1] & types for types in land_types)
    if kind == "otherTypeAtLeast":
        return sum(1 for types in land_types if rule[1] in types) < rule[2]
    others = [profiles[permanent["name"]] for permanent in permanents]
    if kind == "legendaryCreature":
        return not any({"Legendary", "Creature"} <= profile["typeWords"] for profile in others)
    if kind == "elf":
        # Behold an Elf you control or an Elf card in the hand.
        return not any("Creature" in profile["typeWords"] and has_creature_type(profile, "Elf")
                       for profile in others + [profiles[card] for card in hand])
    raise ValueError(f"unknown land entry rule {rule!r}")


def land_colors(profile: dict, played: bool = True) -> set[str]:
    """Every colour a land can make: its atoms, its board terms and, for a
    land played from the hand, both faces (a Pathway's face is chosen as it
    is played); a land put onto the battlefield (a search) enters front face
    up, so only that face counts."""
    faces = (profile["landFaces"] or []) if played else (profile["landFaces"] or [])[:1]
    atoms = list(profile["manaAtoms"]) + [atom for face in faces for atom in face]
    for term in profile["manaBoard"]:
        if term[0] == "gate":
            atoms += list(term[2])
        elif term[0] == "count":
            atoms.append(term[2])
    return set().union(*atoms) if atoms else set()


def usable_this_turn(profile: dict, tapped: bool) -> bool:
    """Whether a land's mana can be spent the turn it enters, for choosing a
    land to play and a land a search finds alike: it does not enter tapped
    and is not a land creature (summoning sick: Dryad Arbor)."""
    return not tapped and "Creature" not in profile["typeWords"]


def choose_best_land_index(library: list[str], profiles: dict, commander_colors: list[str],
                           battlefield_lands: list[dict], permanents: list[dict],
                           candidate_indices: list[int], tapped_test=None, *,
                           to_hand: bool) -> int | None:
    """Choose best land target from library for ramp/fetch effects.

    ``tapped_test(name)`` says whether the land would enter tapped; by
    default its own entry rule, with a hand that reveals and beholds nothing.
    ``to_hand``: the search puts the land into the hand, to be played later
    (either face of a Pathway counts); otherwise it puts it onto the
    battlefield, front face up, and only that face counts (land_colors).
    """
    if not candidate_indices:
        return None

    present_colors = set()
    for land in battlefield_lands:
        present_colors.update(land.get("colors", set()))

    best_index = None
    best_score = None
    for idx in candidate_indices:
        profile = profiles[library[idx]]
        colors = land_colors(profile, played=to_hand)
        tapped = (tapped_test(library[idx]) if tapped_test is not None
                  else land_enters_tapped(profile["landEntry"], battlefield_lands, permanents,
                                          profiles, []))
        untapped_bonus = 10 if usable_this_turn(profile, tapped) else 0
        new_colors = len((set(colors) & set(commander_colors)) - present_colors)
        score = (
            untapped_bonus,
            new_colors,
            len(set(colors) & set(commander_colors)),
            len(colors),
            library[idx],
        )
        if best_score is None or score > best_score:
            best_score = score
            best_index = idx
    return best_index


def select_ramp_targets(library: list[str], profiles: dict, commander_colors: list[str],
                        battlefield_lands: list[dict], permanents: list[dict],
                        ramp_profile: dict, count: int, tapped_test=None, *,
                        to_hand: bool) -> list[str]:
    """Take from the library the land cards a land search finds (M8), at
    most `count`: one per named type for "a Forest card and a Plains card";
    for "share a land type" the most lands of one basic land type (a legal
    set), the type whose best land scores best on a tie. Land types are the
    printed ones of the card's front face, what it is in the library (a card
    there has no granted type, and a modal DFC whose front is a spell is not
    a land card). ``to_hand``: where the search puts the lands, which decides
    the face they are scored by (choose_best_land_index); ``tapped_test``
    whether each would enter tapped."""
    if count <= 0:
        return []

    def fits(name: str, types: set) -> bool:
        profile = profiles[name]
        if not profile["libraryLand"] or (ramp_profile["basicOnly"] and not profile["libraryBasic"]):
            return False
        return not types or bool(profile["librarySubtypes"] & types)

    def take(types: set) -> str | None:
        candidates = [idx for idx, name in enumerate(library) if fits(name, types)]
        best_idx = choose_best_land_index(library, profiles, commander_colors, battlefield_lands,
                                          permanents, candidates, tapped_test, to_hand=to_hand)
        return None if best_idx is None else library.pop(best_idx)

    if ramp_profile["sharedType"]:
        sizes = {land_type: min(count, sum(1 for name in library if fits(name, {land_type})))
                 for land_type in LAND_SUBTYPE_COLORS}
        size = max(sizes.values())
        if size == 0:
            return []
        tied = [land_type for land_type, n in sizes.items() if n == size]
        leaders = {choose_best_land_index(
            library, profiles, commander_colors, battlefield_lands, permanents,
            [idx for idx, name in enumerate(library) if fits(name, {land_type})], tapped_test,
            to_hand=to_hand): land_type
            for land_type in tied}
        land_type = leaders[choose_best_land_index(library, profiles, commander_colors,
                                                   battlefield_lands, permanents, sorted(leaders),
                                                   tapped_test, to_hand=to_hand)]
        return [take({land_type}) for _ in range(size)]
    wanted = ([{land_type} for land_type in ramp_profile["perType"]][:count]
              if ramp_profile["perType"] else [ramp_profile["allowedSubtypes"]] * count)
    return [name for name in (take(types) for types in wanted) if name is not None]


def mana_value_combat(mana_value: int) -> int:
    """A creature's combat proxy before its keyword bonus: min(8, MV), at least 1."""
    return max(1, min(8, mana_value))


def mana_value_impact(mana_value: int) -> int:
    """A threat's impact term: min(8, MV), at least 2."""
    return max(2, min(8, mana_value))


def creature_condition(face_text: str) -> tuple[bool, tuple | None]:
    """(whether the face is a creature only while a condition holds, the
    devotion that makes it one). A Theros god: "As long as your devotion to
    black and red is less than seven, Mogis isn't a creature" is
    (True, ({B, R}, 7)). A condition that is not a devotion the goldfish reads
    is (True, None): never read as a creature (extra_cost_objects)."""
    found = NOT_CREATURE_WHILE.search(strip_reminder_text(face_text))
    if found is None:
        return False, None
    devotion = DEVOTION_BELOW.fullmatch(found.group(1))
    if devotion is None:
        return True, None
    first, second, count = devotion.groups()
    words = [word for word in (first, second) if word]
    if count not in COUNT_WORDS or not all(word in COLOUR_WORDS for word in words):
        return True, None
    return True, (frozenset(COLOUR_WORDS[word] for word in words), COUNT_WORDS[count])


def devotion_symbols(mana_cost: str) -> tuple:
    """The coloured mana symbols of a front face's mana cost, each as the set
    of its colours, for devotion (CR 700.5): {R/G} is red and green, {2/W},
    {C/W} and {W/P} white; {C}, {X} and generic symbols count for none. A
    Room counts its first door's cost: only unlocked doors contribute mana
    symbols to devotion, and the goldfish casts that door and never unlocks
    the other (reads devotion too low)."""
    return tuple(colours for colours in (frozenset(symbol.split("/")) & frozenset("WUBRG")
                                         for symbol in re.findall(r"\{([^}]+)\}", mana_cost.split("//")[0]))
                 if colours)


def devotion_to(colours, permanents: list[dict], profiles: dict) -> int:
    """Devotion to ``colours`` (CR 700.5): the mana symbols in the mana costs
    of the non-land permanents (a land, an MDFC's land face too, has none)
    that are one of those colours, each symbol once (a hybrid {R/G} once
    toward red and green). Nykthos reads each colour alone (board_term_atoms);
    a Theros god its own colours (extra_cost_objects)."""
    return sum(1 for record in permanents if record["kind"] != "land"
               for symbol in profiles[record["name"]]["devotionSymbols"] if symbol & colours)


def build_goldfish_profile(name: str, meta: dict, category_names: set[str], primary_role: str | None,
                           commander_colors: list[str], commander_name: str) -> dict:
    """Compile per-card goldfish heuristics from metadata.

    ``category_names`` (the card's guide categories) feed the threat flag;
    ``primary_role`` (its decklist entry's, None for a card with none) the
    interaction flag (goldfish_holds_back; the commander is never held).

    Raises ValueError for a card whose mana text no rule reads (an "unread"
    verdict, entry rule or land search): nothing is read by accident.
    """
    mana_cost = parse_generic_mana_cost(meta.get("mana_cost", ""))
    type_line = meta.get("type_line", "")
    oracle = meta.get("oracle_text", "")
    mana = card_mana_model(name, meta, commander_colors)
    is_land = mana["isLand"]
    face_type, face_text = battlefield_face(meta)
    conditional_creature, creature_devotion = creature_condition(face_text)
    is_threat = is_threat_card(name, meta, category_names) or name == commander_name
    is_draw = is_draw_card(meta)
    is_interaction = name != commander_name and goldfish_holds_back(primary_role, meta)
    land_ramp = None if is_land else parse_land_ramp_profile(meta, name)
    unread = [line for line, verdict in mana["verdicts"] if verdict == "unread"]
    if mana["landEntry"] == "unread":
        unread.append("how it enters")
    if land_ramp == "unread":
        unread.append("its land search (a condition before it, its count or its filter)")
    if land_ramp == "gives up a land":
        unread.append("the land it gives up as it resolves or as its cost")
    if not is_land and not (meta.get("mana_cost") or "").strip():
        # No mana cost: it cannot be cast for mana (suspend, an alternative
        # cost); read as free it would be cast at once.
        unread.append("how it is cast (no mana cost)")
    if unread:
        raise ValueError(f"{name}: no rule reads {unread}; extend card_mana_model")
    # An X spell is not a mana source in the goldfish: it is cast under the X
    # rule (X_SPELL_MIN_X) with the mana left at its place in the cast order,
    # so it neither sorts first as ramp, skips the DEC-944 holds, counts as
    # the mulligan's cheap ramp nor as a ramp permanent. No castable X card in
    # the fleet has a mana ability of its own (Springleaf Parade grants one to
    # its creature tokens, which the goldfish does not model). Lands are
    # outside the X rule: an MDFC whose front has {X} (Agadeem's Awakening) is
    # played as its land, unless it is a combo-line or assembly piece the
    # goldfish keeps in the hand (handOnlyPieces).
    if mana_cost["X"] and not is_land:
        land_ramp = None
        mana = dict(mana, manaAtoms=[], manaOnce=[], manaBoard=[], manaOnCast=[],
                    manaSourceDelay=None, landFetch=None)

    impact = 0
    if is_threat:
        impact += mana_value_impact(int(meta.get("cmc", 0) or mana_cost["total"] or 2))
        if "Planeswalker" in type_line or "Battle" in type_line:
            impact += 1
    if is_draw:
        impact += 1
    if "create" in oracle.lower() and "token" in oracle.lower():
        impact += 1
    if text_matches(oracle, THREAT_ORACLE_PATTERNS):
        impact += 1

    combat = 0
    if "Creature" in type_line:
        combat = mana_value_combat(int(meta.get("cmc", 0) or mana_cost["total"] or 1))
        if any(keyword in oracle for keyword in ("Flying", "Trample", "Menace", "Double strike", "First strike")):
            combat += 1

    # DEC-940 — printed front-face power, for the combat modifiers' power gates
    # only (Tifa's "power 7 or greater"). It never feeds the combat proxy above,
    # which stays min(8, MV) + keyword bonus fleet-wide (MV + X for an X
    # creature cast with X paid, x_cast_profile). `*`-style printed power has
    # no fixed value, so it reads as 0 rather than guessing.
    printed_power = meta.get("power")
    try:
        printed_power = int(printed_power)
    except (TypeError, ValueError):
        printed_power = 0

    return {
        "name": name,
        "cmc": int(meta.get("cmc", 0) or mana_cost["total"] or 0),
        "manaCost": mana_cost,
        "typeLine": type_line,
        "printedPower": printed_power,
        "isColorless": not meta.get("colors"),
        "isLand": is_land,
        "isPermanent": is_permanent_card(meta),
        "isThreat": is_threat,
        "isDraw": is_draw,
        "isInteraction": is_interaction,
        **{key: mana[key] for key in (
            "manaAtoms", "manaOnce", "onceLeaves", "onceRearm", "manaBoard", "manaOnCast",
            "manaSourceDelay", "manaTapsSelf", "manaOneColour", "manaTurns", "imprint",
            "landEntry", "landEntryCost", "landFaces", "landFetch", "landCrack", "landTypes",
            "eachLandIs", "landGrant", "landOutputs", "entersTapped")},
        # An activated ability of its own with {T} in its cost (Isochron
        # Scepter): a line that names it needs it untapped (urzaKeep).
        "tapAbility": any("{T}" in line.partition(":")[0]
                          for line in own_ability_lines(face_text, type_words(face_type)) if ":" in line),
        # A draw ability whose cost has {T} (The One Ring): activating it taps
        # the permanent (CAST_TURN_ACTIVATION_DRAW, PERMANENT_DRAW_ENGINE).
        "drawTapsSelf": bool(re.search(r"^[^:\n]*\{T\}[^:\n]*:[^\n]*\bdraw", strip_reminder_text(face_text),
                                       re.M | re.I)),
        # How each mana line was read (card_mana_model), for the methodology.
        "manaVerdicts": tuple(mana["verdicts"]),
        # A creature with vigilance attacks untapped, so it can still be
        # tapped for mana after combat (spend_order).
        "vigilance": bool(re.search(r"(^|\n|, )vigilance\b", strip_reminder_text(face_text).lower())),
        "landRamp": land_ramp,
        "immediateDraw": CAST_TURN_ACTIVATION_DRAW.get(name, immediate_draw_count(name, meta)),
        "targetsOnlyCreature": targets_only_creatures(meta),
        "tokenCreatures": creature_token_count(meta),
        "impact": impact,
        "combat": combat,
        # The face on the battlefield, for the board terms and entry rules.
        "typeWords": type_words(face_type),
        # A land face is colourless; Dryad Arbor, a land creature, has its colour.
        "colors": (frozenset(meta.get("colors") or [])
                   if not is_land or "Creature" in type_words(face_type) else frozenset()),
        "changeling": "Changeling" in face_text,
        # A creature only while a condition holds, and the devotion that
        # makes it one (creature_condition): a Theros god is a creature to
        # sacrifice once its devotion is met (extra_cost_objects).
        "conditionalCreature": conditional_creature,
        "creatureDevotion": creature_devotion,
        # The coloured symbols of its mana cost, for devotion (devotion_to).
        "devotionSymbols": devotion_symbols(meta.get("mana_cost") or ""),
        # Printed basic land types, read in the hand (a Snarl's reveal) and
        # the library (searches); a type granted on the battlefield (Urborg)
        # is read there only (land_types_on_battlefield).
        "subtypes": extract_land_subtypes(face_type),
        "isBasic": "Basic" in type_words(face_type),
        # What the card is in the library, for land searches: its front face
        # (a modal DFC whose front is a spell is not a land card there:
        # Hagra Mauling).
        "libraryLand": "Land" in type_words(type_line.split(" // ")[0]),
        "librarySubtypes": extract_land_subtypes(type_line.split(" // ")[0]),
        "libraryBasic": "Basic" in type_words(type_line.split(" // ")[0]),
        # The front face's type words, colours and Changeling, which the combo
        # checks' tutor and recursion tags are read against (substitute_allows),
        # with the printed mana value (``cmc``).
        "libraryTypeWords": type_words(type_line.split(" // ")[0]),
        "libraryColors": frozenset(meta.get("colors") or []),
        "libraryChangeling": "Changeling" in oracle,
    }


class GoldfishManaPool:
    """The turn's mana (ManaAtom, one per mana) and the sources it has used.

    ``tapped``: the ids of the sources the turn's spending has used: their
    other mana is already made (floating) and costs nothing more.
    ``tapping``: the ids of the sources whose own {T} a payment used (settle
    taps them). ``added``: every mana that entered the turn's pool, kept
    through spending (the turn's availableMana). ``post_combat``: after combat
    no creature attacks again, so a creature's mana costs what a land's does.
    ``turn``: the turn the pool belongs to; ``board_key``: the board its
    unspent mana was last read from (refresh_pool); ``lasting_only``: the end
    of the turn's pool, which holds no one-shot mana. The pool answers questions
    (can_cast) and builds the pool a payment leaves (pay); mana leaves the
    turn's pool only through spend_mana.

    The spend preference, in one place (GoldfishManaPool.rank, lower first):
      0    floating mana: more mana of a source the turn has already used
           (Sol Ring's second {C}), and mana with no source (a cast trigger,
           a Saga tapped as it leaves, lands tapped before they were given up);
      1    lands, noncreature permanents, creatures whose mana does not tap
           them, that could not attack anyway (summoning sick, no combat) or
           that attack anyway (vigilance: the pilot attacks first and casts
           after combat), and after combat every creature;
      1.5  a permanent whose own {T} ability the turn uses later
           (``manaReserve``: Castle Ardenvale, Myriad Landscape, High Market);
      2    one-shot mana (Lotus Petal, Mana Vault, Basalt Monolith);
      3+   a creature that could still attack: 3 plus its combat.
    The preferred payment takes the fewest of those creatures, then the
    least combat, then the fewest one-shot sources; then the lowest ranks,
    the narrowest colours first. A one-colour activation (Lotus Field,
    Nykthos) that pays is activated for one colour: its other mana is that
    colour, and mana it makes only for another colour is not made.

    With requirements to keep (pay) a payment is exact: one is found
    whenever the cost and every requirement can be paid together, never
    otherwise, and it is the most preferred payment that keeps them.
    """

    def __init__(self, sources=None, tapped=None, added=None, post_combat=False, turn=None,
                 tapping=None, board_key=None, lasting_only=False, records=None):
        self.sources = list(sources or [])
        self.tapped = set(tapped or ())
        self.tapping = set(tapping or ())
        self.added = len(self.sources) if added is None else added
        self.post_combat = post_combat
        self.turn = turn
        self.board_key = board_key
        self.lasting_only = lasting_only
        # The records whose ids ``tapped``, ``tapping`` and ``board_key``
        # hold, kept alive for the turn: a record that leaves mid-turn (a
        # sacrificed Lotus Petal) is not freed, so its id is never reused by
        # a permanent that enters later.
        self.records = {} if records is None else records

    @property
    def total(self) -> int:
        return len(self.sources)

    def add(self, atoms) -> None:
        """Mana that comes online during the turn with no source to read it
        from again: a cast trigger's, mana tapped before its source left."""
        atoms = list(atoms)
        self.sources.extend(atoms)
        self.added += len(atoms)

    def _derived(self, sources, tapped=None, tapping=None, post_combat=None) -> "GoldfishManaPool":
        return GoldfishManaPool(sources, self.tapped if tapped is None else tapped,
                                self.added, self.post_combat if post_combat is None else post_combat,
                                self.turn, self.tapping if tapping is None else tapping, self.board_key,
                                self.lasting_only, self.records)

    def without(self, keep) -> "GoldfishManaPool":
        """The pool with only the mana ``keep(atom)`` accepts (an attacker's
        mana leaves with it); the rest of its state carries over."""
        return self._derived([atom for atom in self.sources if keep(atom)])

    def after_combat(self) -> "GoldfishManaPool":
        """The same pool once combat is over (``post_combat``)."""
        return self._derived(self.sources, post_combat=True)

    def lasting(self) -> "GoldfishManaPool":
        """The end of the turn's pool: its lasting mana (one-shot mana not
        spent is kept for a later turn)."""
        pool = self._derived([atom for atom in self.sources if not getattr(atom, "once", False)])
        pool.lasting_only = True
        return pool

    def rank(self, atom) -> float:
        """The spend preference of one mana (the class docstring)."""
        sid = atom_source_id(atom)
        if sid is None or sid in self.tapped:
            return 0
        order = getattr(atom, "order", 0)
        if order >= 2:
            return 1 if self.post_combat else order + 1
        if order == 1:
            return 2
        return 1.5 if getattr(atom, "reserve", False) else 1

    def can_cast(self, pips: dict) -> bool:
        return self._allocate(pips) is not None

    def pay(self, pips: dict, keep=()) -> "GoldfishManaPool | None":
        """The pool a payment of ``pips`` leaves, or None when none can pay.

        ``keep``: requirements the pool left must still pay, each a list of
        costs any one of which keeps it (a held activation, a gate with each
        of its lines). The payment and the requirements are checked jointly:
        the preferred payment when it keeps them, else the most preferred of
        every payment (_payments) that keeps them all; None when none does.
        """
        payment = self._allocate(pips)
        if payment is None:
            return None
        first = self._after(*payment)
        if self._keeps(first, keep):
            return first
        # A requirement paid together with the payment from this pool: a
        # payment that keeps it exists only if both can be paid at once.
        if not all(any(self.can_cast(combine_mana_costs([pips, cost])) for cost in costs)
                   for costs in keep):
            return None
        for used, pinned in self._payments(pips):
            option = self._after(used, pinned)
            if self._keeps(option, keep):
                return option
        return None

    @staticmethod
    def _keeps(pool: "GoldfishManaPool", keep) -> bool:
        return all(any(pool.can_cast(cost) for cost in costs) for costs in keep)

    def _after(self, used: set, pinned: dict) -> "GoldfishManaPool":
        """The pool a payment (the mana at ``used``, the one-colour
        activations it made in ``pinned``) leaves."""
        atoms = self.sources
        sids = {atom_source_id(atoms[i]) for i in used} - {None}
        tapping = {atom_source_id(atoms[i]) for i in used if getattr(atoms[i], "taps", False)} - {None}
        return self._derived(self._left(used, pinned), self.tapped | sids, self.tapping | tapping)

    def _groups(self, indices) -> dict:
        """The one-colour activations among ``indices`` that could make more
        than one colour: {group: the colours its mana could be}."""
        groups: dict = {}
        for i in indices:
            group = getattr(self.sources[i], "group", None)
            if group is not None:
                groups.setdefault(group, set()).update(self.sources[i])
        return {group: union for group, union in groups.items() if len(union) > 1}

    def _allocate(self, pips: dict):
        """The preferred exact payment of ``pips``: (mana indices used,
        {one-colour activation: its colour}) or None. A payment is found
        whenever one exists (pips matched to mana by augmenting paths, each
        one-colour activation tried unused and at each colour). Creatures
        that could attack are allowed only when needed: the fewest, then the
        least combat, then the fewest one-shot sources; one-shot sources
        likewise."""
        colours = [colour for colour in COLOR_SYMBOLS for _ in range(pips.get(colour, 0))]
        need = len(colours) + pips.get("generic", 0)
        if self.total < need:
            return None
        if need == 0:
            return set(), {}
        by_source: dict = {}
        for index, atom in enumerate(self.sources):
            by_source.setdefault(atom_source_id(atom), []).append(index)
        free, once, creatures = [], [], []
        for sid, indices in by_source.items():
            rank = self.rank(self.sources[indices[0]])
            (free if rank < 2 else once if rank == 2 else creatures).append(sid)
        if self._payment(colours, need, by_source, list(by_source)) is None:
            return None
        combat = {sid: self.rank(self.sources[by_source[sid][0]]) for sid in creatures}

        def fewest_once(chosen):
            for count in range(len(once) + 1):
                for picked in itertools.combinations(once, count):
                    payment = self._payment(colours, need, by_source, free + list(picked) + list(chosen))
                    if payment is not None:
                        return count, payment
            return None

        for size in range(len(creatures) + 1):
            best = None
            ordered = sorted(itertools.combinations(sorted(creatures, key=lambda s: combat[s]), size),
                             key=lambda c: sum(combat[s] for s in c))
            for chosen in ordered:
                key = sum(combat[s] for s in chosen)
                if best is not None and key > best[0]:
                    break
                if self._payment(colours, need, by_source, free + once + list(chosen)) is None:
                    continue
                count, payment = fewest_once(chosen)
                # Equal combat given up: the fewest one-shot sources.
                if best is None or count < best[1]:
                    best = (key, count, payment)
            if best is not None:
                return best[2]
        return None

    def _left(self, used: set, pinned: dict) -> list:
        """The mana a payment leaves. A one-colour activation that paid is
        that colour; its mana that colour does not make is not made
        (Nykthos: each colour its own devotion)."""
        left = []
        for i, atom in enumerate(self.sources):
            if i in used:
                continue
            group = getattr(atom, "group", None)
            if group in pinned:
                if pinned[group] not in atom:
                    continue
                if len(atom) > 1:
                    atom = retag(atom, frozenset({pinned[group]}))
            left.append(atom)
        return left

    def _payment(self, colours: list[str], need: int, by_source: dict, allowed: list):
        """(mana indices, {one-colour activation: colour}) paying ``colours``
        and the generic rest from the sources in ``allowed``, or None."""
        return self._match(colours, need, [i for sid in allowed for i in by_source[sid]])

    def _match(self, colours: list[str], need: int, indices: list):
        """The cheapest payment of ``colours`` and ``need`` mana in all from
        the mana at ``indices``: (mana indices, {one-colour activation: the
        colour it is made as}), or None. Each one-colour activation is tried
        unused first, then at each colour, the one that makes the most first
        (then the colour the rest of the mana makes least)."""
        atoms = self.sources
        if len(indices) < need:
            return None
        groups = self._groups(indices)

        def colour_order(group):
            members = [i for i in indices if getattr(atoms[i], "group", None) == group]
            others = [i for i in indices if getattr(atoms[i], "group", None) != group]
            return [None] + sorted(groups[group], key=lambda c: (
                -sum(1 for i in members if c in atoms[i]), sum(1 for i in others if c in atoms[i]), c))

        group_ids = list(groups)
        for choice in itertools.product(*[colour_order(g) for g in group_ids]):
            chosen = dict(zip(group_ids, choice))

            def colours_of(i, chosen=chosen):
                group = getattr(atoms[i], "group", None)
                if group in chosen:
                    return frozenset({chosen[group]})
                return atoms[i]

            def cost(i):
                one_colour = getattr(atoms[i], "group", None) in chosen
                return (self.rank(atoms[i]), 1 if one_colour else len(atoms[i]), i)

            # An unused activation makes nothing here; one made as a colour
            # makes the mana that colour makes.
            usable = [i for i in indices
                      if getattr(atoms[i], "group", None) not in chosen
                      or (chosen[getattr(atoms[i], "group", None)] is not None
                          and chosen[getattr(atoms[i], "group", None)] in atoms[i])]
            if len(usable) < need:
                continue
            order = sorted(usable, key=cost)
            pips = sorted(colours, key=lambda c: sum(1 for i in usable if c in colours_of(i)))
            match: dict = {}

            def augment(p, seen):
                for i in order:
                    if pips[p] in colours_of(i) and i not in seen:
                        seen.add(i)
                        if i not in match or augment(match[i], seen):
                            match[i] = p
                            return True
                return False

            if not all(augment(p, set()) for p in range(len(pips))):
                continue
            used = set(match)
            # Generic: mana of sources this payment already uses first, then
            # the cheapest.
            using = {atom_source_id(atoms[i]) for i in used}
            rest = sorted((i for i in usable if i not in used),
                          key=lambda i: (atom_source_id(atoms[i]) not in using, cost(i)))
            generic = need - len(pips)
            if len(rest) < generic:
                continue
            used |= set(rest[:generic])
            touched = {getattr(atoms[i], "group", None) for i in used}
            pinned = {group: colour for group, colour in chosen.items()
                      if colour is not None and group in touched}
            if any(colour is not None and group not in touched for group, colour in chosen.items()):
                continue  # made as a colour but not used: the unused trial covers it
            return used, pinned
        return None

    def _payments(self, pips: dict):
        """Every payment of ``pips`` that leaves a different pool, most
        preferred first (fewest creatures that could attack, least combat,
        fewest one-shot sources, lowest ranks, narrowest colours): mana of one
        rank and colours is interchangeable (a source's mana together), and
        each one-colour activation is unused or made as each colour it can
        make, paying any number of the mana it makes."""
        colours = [colour for colour in COLOR_SYMBOLS for _ in range(pips.get(colour, 0))]
        need = len(colours) + pips.get("generic", 0)
        atoms = self.sources
        groups = self._groups(range(len(atoms)))
        kinds: dict = {}
        members: dict = {}
        for i, atom in enumerate(atoms):
            group = getattr(atom, "group", None)
            if group in groups:
                members.setdefault(group, []).append(i)
                continue
            rank = self.rank(atom)
            own = atom_source_id(atom) if rank >= 2 else None  # counted per source
            kinds.setdefault((rank, tuple(sorted(atom)), own), []).append(i)
        for key in kinds:
            sizes = Counter(atom_source_id(atoms[i]) for i in kinds[key])
            kinds[key].sort(key=lambda i: (atom_source_id(atoms[i]) not in self.tapped,
                                           getattr(atoms[i], "taps", False),
                                           -sizes[atom_source_id(atoms[i])], i))
        items = [("kind", key, len(kinds[key])) for key in sorted(kinds, key=lambda k: (k[0], len(k[1]), k[1]))]
        for group in groups:
            made = {c: [i for i in members[group] if c in atoms[i]] for c in sorted(groups[group])}
            items.append(("group", group, made))
        room = []
        for item in items:
            room.append(item[2] if item[0] == "kind" else max(len(v) for v in item[2].values()))
        room = [sum(room[pos:]) for pos in range(len(items))] + [0]
        found = []

        def walk(pos: int, left: int, picks: list) -> None:
            if left == 0:
                found.append(list(picks))
                return
            if pos == len(items) or room[pos] < left:
                return
            item = items[pos]
            if item[0] == "kind":
                for n in range(min(item[2], left), -1, -1):
                    walk(pos + 1, left - n, picks + ([(item, n)] if n else []))
            else:
                walk(pos + 1, left, picks)
                for colour, made in item[2].items():
                    for n in range(1, min(len(made), left) + 1):
                        walk(pos + 1, left - n, picks + [(item, (colour, n))])

        walk(0, need, [])
        candidates = []
        for picks in found:
            used, pinned, mana = set(), {}, []
            for item, pick in picks:
                if item[0] == "kind":
                    chosen = kinds[item[1]][:pick]
                    used.update(chosen)
                    mana += [atoms[i] for i in chosen]
                else:
                    colour, n = pick
                    chosen = item[2][colour][:n]
                    used.update(chosen)
                    pinned[item[1]] = colour
                    mana += [frozenset({colour})] * n
            candidates.append((self._preference(used), len(candidates), used, pinned, mana))
        candidates.sort(key=lambda c: c[:2])
        for _, _, used, pinned, mana in candidates:
            if _plain_payable(mana, colours):
                yield used, pinned

    def _preference(self, used) -> tuple:
        """The order of preference of a payment (the class docstring)."""
        ranks: dict = {}
        for i in used:
            sid = atom_source_id(self.sources[i])
            if sid is not None and sid not in self.tapped:
                ranks[sid] = max(ranks.get(sid, 0), self.rank(self.sources[i]))
        creatures = [rank for rank in ranks.values() if rank > 2]
        return (len(creatures), sum(creatures), sum(1 for rank in ranks.values() if rank == 2),
                sum(self.rank(self.sources[i]) for i in used),
                sum(1 if getattr(self.sources[i], "group", None) is not None else len(self.sources[i])
                    for i in used))


def _plain_payable(mana: list, colours: list[str]) -> bool:
    """Whether these mana (each paying one of its colours) pay ``colours``,
    the rest generic: augmenting-path matching."""
    match: dict = {}

    def augment(p, seen):
        for j, colour_set in enumerate(mana):
            if colours[p] in colour_set and j not in seen:
                seen.add(j)
                if j not in match or augment(match[j], seen):
                    match[j] = p
                    return True
        return False

    return len(mana) >= len(colours) and all(augment(p, set()) for p in range(len(colours)))


def atom_source_id(atom):
    """The id of the permanent record a mana comes from (None for mana with no
    source: floating mana, and mana in tests)."""
    source = getattr(atom, "source", None)
    return None if source is None else id(source)


def retag(atom, colours: frozenset):
    """The same mana (source, order, one-shot, group, reserve, taps) with
    other colours."""
    mana = ManaAtom(colours)
    for key in ("source", "order", "once", "group", "reserve", "taps"):
        setattr(mana, key, getattr(atom, key, getattr(ManaAtom, key)))
    return mana


def floated(atom):
    """Mana already made before the turn's pool is built (a Saga tapped as
    it leaves, lands tapped before an entering land takes them): it has no
    source left to tap, so it is floating mana (GoldfishManaPool.rank 0)."""
    mana = retag(atom, frozenset(atom))
    mana.source = None
    return mana


def combine_mana_costs(costs: list[dict]) -> dict:
    """Sum a list of pip-cost dicts into one combined cost.

    Used to build a synthetic mana cost for casting multiple combo pieces in one turn.
    Drops the X count: an X piece comes in already priced (extract_combo_lines:
    at its line's minX, else at X = 0).
    """
    combined = {
        "generic": 0, "W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0, "total": 0, "X": 0,
    }
    for cost in costs:
        for key in ("generic", "W", "U", "B", "R", "G", "C", "total"):
            combined[key] += cost.get(key, 0)
    return combined


def x_spell_cost(cost: dict, x: int) -> dict:
    """An X spell's cost with X paid: each {X} adds x generic mana."""
    paid = dict(cost)
    paid["generic"] += x * cost["X"]
    paid["total"] += x * cost["X"]
    return paid


def x_cast_profile(profile: dict, x: int, commander_casts: int) -> dict:
    """The goldfish profile of an X spell cast with X paid.

    The mana cost is the paid one, so a spell's mana value on the stack
    (Saruman, the White Hand's amass) counts the X. A creature's combat and
    impact read mana value + X where build_goldfish_profile reads mana value
    (same cap of 8, same keyword bonus). X_SPELL_DRAW sets the cards drawn.
    Nothing else changes: the sort keys, cascade and the DEC-404 pip count
    still read the printed card.
    """
    cast = dict(profile)
    cast["manaCost"] = x_spell_cost(profile["manaCost"], x)
    if "Creature" in profile["typeLine"]:
        mana_value = profile["cmc"] + x
        cast["combat"] += (mana_value_combat(mana_value)
                           - mana_value_combat(profile["cmc"]))
        if profile["isThreat"]:
            cast["impact"] += (mana_value_impact(mana_value)
                               - mana_value_impact(profile["cmc"]))
    if profile["name"] in X_SPELL_DRAW:
        _, draw = X_SPELL_DRAW[profile["name"]]
        cast["immediateDraw"] = draw(x, commander_casts)
    return cast


def extract_combo_lines(deck_data: dict, profiles: dict) -> list[dict]:
    """Parse winConditions[] entries with kind=='combo' into combo-line specs.

    Each combo line: {pieces: [name], costs: [pip_dict], startPiece: name | None,
    minX: {name: int}, alternatives: [name], readyPieces: [name], readyHaste:
    {static: [name], equip: {name: pip_dict}, instant: {name: pip_dict}},
    castFromHand: [name], needsCreature: int, extraCost: pip_dict | None};
    build_goldfish_context adds ``deliveries`` (combo_deliveries). The deck's
    winConditions are checked by gate_tags_lib.win_conditions_errors
    (validate_deck_json.py reports the same errors): the value and each
    entry's type, its keys (a closed list) and its combo-line fields, against
    the cards in ``profiles`` (gate_tags_lib.combo_line_cards: the decklist and
    the commander) with their front faces' type lines; a partner is refused by
    name. Any error raises ``ValueError`` naming the entry.

    A list in ``pieces`` (owner decision 27, 2026-11-25, decision 6) is a choice
    of one of its cards: the entry gives one line per choice
    (itertools.product over its list entries), each with the cards it chose
    from lists as ``alternatives``. An alternative is not a line member by that
    line (decision 6b, build_goldfish_context).

    The combo-line corrections' fields (decisions 1, 1b, 2 and 7), read by
    combo_line_costs and combo_deliveries: ``readyPieces``, pieces that count
    only once they have been on the battlefield since the turn began, else with
    one of the line's ``readyHaste`` sources; ``castFromHand``, pieces that
    count only when cast during the combo (never from the battlefield) and that
    the goldfish keeps in the hand (handOnlyPieces); ``needsCreature``, the
    number of other creatures the line needs on the battlefield to target
    (0: none); ``extraCost``, a mana cost added to the line's cost each time it
    is counted. A commander named as a piece is never supplied by a tutor or
    recursion card (combo_deliveries).

    ``startPiece`` is the optional piece the loop starts by casting (e.g. Sensei's
    Divining Top recast through Mystic Forge). In ``combo_line_costs`` it is free
    only if it was the last of the line's pieces to enter this turn; if it has been on
    the battlefield since an earlier turn its cost is paid again; if it entered this
    turn before a partner, or could only be put onto the battlefield (a tutor or
    recursion card that puts it there), the line is not ready that turn. A
    ``startPiece`` that is not one of the line's ``pieces`` named outside a list
    raises ``ValueError``.

    ``minX`` (owner-approved 2026-11-19, built 2026-11-21) maps a piece with {X} in its
    cost to the X it is priced at: the cheapest direct cast with which the line's listed
    pieces work (Walking Ballista beside Heliod, Sun-Crowned: 2; beside Mikaeus, the
    Unhallowed: 1). Its cost in ``costs`` is priced at that X (x_spell_cost: {X}{X} at
    X = 2 is 4 mana), and ``combo_line_costs`` takes the piece only from the hand, or
    through a card that puts it into the hand or lets it be cast from the graveyard
    (decision 5, 2026-11-24), cast at that X; never through one that puts it onto the
    battlefield or a bargained free cast (combo_deliveries). ``minX`` must be a mapping
    whose keys are cards the line's pieces name (in a list or not) exactly as the deck
    lists them (a face name is not the card's name) with {X} in their mana cost, and
    whose values are positive integers; a line priced from a list entry carries the
    minX of the card it chose only.
    """
    lines = []
    cards = {name: profile["typeLine"].split(" // ")[0] for name, profile in profiles.items()}
    x_cards = {name for name, profile in profiles.items() if profile["manaCost"]["X"]}
    win_conditions = deck_data.get("winConditions", [])
    errors = gate_tags_lib.win_conditions_errors(win_conditions, cards, x_cards, deck_data.get("partner"))
    if errors:
        messages = []
        for index, error in errors:
            wincon = None if index is None else win_conditions[index]
            title = f" {wincon.get('title')!r}" if isinstance(wincon, dict) else ""
            messages.append(f"winConditions{'' if index is None else f'[{index}]'}{title}: {error}")
        raise ValueError("; ".join(messages))
    for wincon in win_conditions:
        if wincon.get("kind") != "combo":
            continue
        haste = wincon.get("readyHaste", {})
        ready_haste = {"static": list(haste.get("static", [])),
                       **{kind: {name: parse_generic_mana_cost(cost) for name, cost in haste.get(kind, {}).items()}
                          for kind in ("equip", "instant")}}
        entries = wincon["pieces"]
        for chosen in itertools.product(*(entry if isinstance(entry, list) else [entry] for entry in entries)):
            min_x = {piece: x for piece, x in wincon.get("minX", {}).items() if piece in chosen}
            lines.append({
                "pieces": list(chosen),
                "costs": [x_spell_cost(profiles[p]["manaCost"], min_x.get(p, 0)) for p in chosen],
                "startPiece": wincon.get("startPiece"),
                "minX": min_x,
                "alternatives": [piece for entry, piece in zip(entries, chosen) if isinstance(entry, list)],
                "readyPieces": list(wincon.get("readyPieces", [])),
                "readyHaste": ready_haste,
                "castFromHand": list(wincon.get("castFromHand", [])),
                "needsCreature": wincon.get("needsCreature", {}).get("count", 0),
                "extraCost": parse_generic_mana_cost(wincon["extraCost"]) if "extraCost" in wincon else None,
            })
    return lines


# --- The combo checks' substitutes (owner-approved plan "combo checks, step 1",
# 2026-11-24) ---
#
# A substitute is a tutor or recursion card in hand that a combo check lets
# stand in for a missing piece. What it may supply, and what that costs, is
# read from the tags of its decklist entry (gate_tags_lib holds the
# vocabulary): rules B1-B10 of the plan. The graveyard is not tracked (step
# 3): combo lethal assumes a piece a recursion card could return is in the
# graveyard, and a tutor's target in the library. In a deck with a combo or
# KEY_COMBOS line the goldfish never casts a tutor or recursion card from the
# hand (step 2, reservedPieces; a cascade can free-cast a permanent one), and
# the combo checks read substitutes only from the hand, so a use that needs
# the card on the battlefield before this turn supplies nothing, even when a
# cascade put it there on an earlier turn.

# The modes that supply a piece this turn; every other mode supplies nothing
# (to_top: decision 1a; to_graveyard: while the graveyard is assumed, a
# recursion card alone covers the piece; self, on_death, none: no credit).
TUTOR_CREDIT_MODES = frozenset({"to_hand", "split_hand_graveyard", "to_battlefield"})
RECURSION_CREDIT_MODES = frozenset({"to_battlefield", "to_hand", "cast_from_graveyard"})
# Beseech the Mirror, bargained, casts the card it finds free at mana value 4 or less.
BARGAIN_FREE_MV = 4
COST_KEYS = ("generic", "W", "U", "B", "R", "G", "C")


def is_front_permanent(profile: dict) -> bool:
    """Whether a card's front face is a permanent (what it is in the hand,
    library and graveyard)."""
    return bool(profile["libraryTypeWords"] & gate_tags_lib.PERMANENT_TYPE_WORDS)


def substitute_use(entry: dict, role: str, profile: dict) -> dict:
    """One role ("tutor" or "recursion") of a decklist entry, as the combo
    checks read it (gate_tags_lib.entry_errors has checked its tags).

    ``useCost`` is what using the card costs (rule B4): its printed cost; with
    a ``*_cost`` tag, a card whose front face is a permanent pays its printed
    cost and that cost (it is cast, then used: Wishclaw Talisman {1}{B} + {1}),
    and any other card that cost instead (Step Through's wizardcycling {2}).
    ``abilityCost`` is the ``*_cost`` tag alone (a piece cast from the hand
    pays only it for its second use, rule B6). ``xCount`` is the {X} in the
    cost paid: each is paid as the piece's mana value. ``credits`` is false
    for a card that supplies nothing this turn: a land in hand (B2), a use
    that is ``later`` (decision 2a), and the modes outside
    TUTOR_CREDIT_MODES / RECURSION_CREDIT_MODES.
    """
    printed = profile["manaCost"]
    ability = entry.get(f"{role}_cost")
    ability_cost = parse_generic_mana_cost(ability or "")
    front_permanent = is_front_permanent(profile)
    if ability is None:
        use_cost, x_count = printed, printed["X"]
    elif front_permanent:
        use_cost, x_count = combine_mana_costs([printed, ability_cost]), printed["X"] + ability_cost["X"]
    else:
        use_cost, x_count = ability_cost, ability_cost["X"]
    mv_cap = entry.get(f"{role}_mv_cap")
    targets = entry.get(f"{role}_targets")
    mode = entry.get(f"{role}_mode", "to_hand" if role == "tutor" else None)
    credit_modes = TUTOR_CREDIT_MODES if role == "tutor" else RECURSION_CREDIT_MODES
    return {
        "mode": mode,
        "targets": None if not targets or "any" in targets else frozenset(targets),
        "subtypes": frozenset(entry[f"{role}_subtypes"]) if f"{role}_subtypes" in entry else None,
        "colors": frozenset(entry[f"{role}_colors"]) if f"{role}_colors" in entry else None,
        "mvCap": mv_cap if type(mv_cap) is int else None,
        "mvExact": entry.get(f"{role}_mv_exact"),
        "mvOdd": bool(entry.get(f"{role}_mv_odd")),
        "extra": entry.get(f"{role}_extra_cost"),
        "bargain": role == "tutor" and bool(entry.get("tutor_free_cast_via_bargain")),
        "useCost": combine_mana_costs([use_cost]),
        "abilityCost": combine_mana_costs([ability_cost]),
        "xCount": x_count,
        "frontPermanent": front_permanent,
        "credits": (not profile["libraryLand"] and entry.get(f"{role}_timing") != "later"
                    and mode in credit_modes),
    }


def substitute_tables(deck_data: dict, profiles: dict, metadata: dict, deck_id: str = "") -> tuple[dict, dict]:
    """(tutors, recursion cards): name -> substitute_use, for every decklist
    entry with the ``tutor`` or ``recursion`` role whose card has a profile.

    Every entry's tags and roles are checked in every deck by
    gate_tags_lib.entry_errors, the check validate_deck_json.py also runs: an
    unknown field or a value outside its set, a role that is not a string or
    not one of gate_tags_lib.ROLES, a missing ``primary_role`` on a card whose
    front face is not a land (or not known), a tag without its role, a
    missing ``recursion_mode`` on a recursion entry whose front face is known
    and is not a land, in a deck with a
    ``kind: "combo"`` win condition (rule B9), or an "X" cap on a card that
    pays no {X}, raises ValueError naming the deck and the card.
    """
    has_combo_line = any(wincon.get("kind") == "combo" for wincon in deck_data.get("winConditions") or [])
    tutors, recursion = {}, {}
    for entry in deck_data.get("decklist", []) or []:
        name = entry.get("name")
        meta = metadata.get(name)
        front = None if meta is None else ((meta.get("type_line") or "").split(" // ")[0],
                                           (meta.get("mana_cost") or "").split("//")[0].strip())
        errors = gate_tags_lib.entry_errors(entry, has_combo_line, front)
        if errors:
            raise ValueError(f"{deck_id}: {name}: " + "; ".join(errors))
        if name not in profiles:
            continue
        roles = {entry.get("primary_role"), entry.get("secondary_role")}
        if "tutor" in roles:
            tutors[name] = substitute_use(entry, "tutor", profiles[name])
        if "recursion" in roles:
            recursion[name] = substitute_use(entry, "recursion", profiles[name])
    return tutors, recursion


def role_names(deck_data: dict, role: str) -> set[str]:
    """The decklist cards with ``role`` as their primary or secondary role."""
    return {entry["name"] for entry in deck_data.get("decklist", []) or []
            if entry.get("name") and role in (entry.get("primary_role"), entry.get("secondary_role"))}


def substitute_allows(use: dict, piece: dict) -> bool:
    """Whether a substitute's tags allow it to find or return ``piece`` (rule
    B1): its card types, subtypes (a Changeling card has every creature
    subtype) and colours (C: colourless) on the piece's front face, and its
    mana value caps on the printed mana value (``cmc``; X caps nothing)."""
    words = piece["libraryTypeWords"]
    if use["targets"] is not None and not any(target.capitalize() in words for target in use["targets"]):
        return False
    mana_value = piece["cmc"]
    if use["mvCap"] is not None and mana_value > use["mvCap"]:
        return False
    if use["mvExact"] is not None and mana_value != use["mvExact"]:
        return False
    if use["mvOdd"] and mana_value % 2 == 0:
        return False
    colors = piece["libraryColors"]
    if use["colors"] is not None and not any(
            (not colors) if color == "C" else color in colors for color in use["colors"]):
        return False
    if use["subtypes"] is not None and not any(
            subtype in words or (piece["libraryChangeling"] and subtype in gate_tags_lib.CREATURE_SUBTYPES)
            for subtype in use["subtypes"]):
        return False
    return True


def x_paid(use: dict, piece: dict) -> dict:
    """The X a substitute with {X} in the cost it pays spends: the piece's
    printed mana value per {X} (Whir of Invention, Agadeem's Awakening). It is
    not the piece's minX."""
    paid = piece["cmc"] * use["xCount"]
    return dict(combine_mana_costs([]), generic=paid, total=paid)


def combo_deliveries(line: dict, profiles: dict, tutor_meta: dict, recursion_meta: dict,
                     commander_name: str = "") -> dict:
    """For each piece of a combo line, every way a substitute can supply it
    when it is missing (rule B3), as dicts: ``card``, ``use``
    (substitute_use), ``route``, ``parts`` (the costs paid on top of the use:
    the X paid, and the piece when it is cast), ``kinds`` (extra-cost
    objects).

    - into the hand (a tutor, or Final Parting's hand half), or back to the
      hand or castable from the graveyard (a recursion card, decision 5): the
      piece is cast and paid, at its line's minX;
    - onto the battlefield (a tutor or a recursion card): only a permanent
      piece that is neither a minX piece, the line's startPiece nor one of its
      castFromHand pieces, not paid;
    - Beseech the Mirror bargained (``tutor_free_cast_via_bargain``): a piece
      of mana value 4 or less that is neither a minX piece nor a castFromHand
      piece, cast free, with one bargain object; its other route is the paid
      route to the hand.

    The commander, named as a piece, is never supplied (owner decision 27,
    decision 1): it counts only on the battlefield.
    """
    deliveries = {}
    for piece, piece_cost in zip(line["pieces"], line["costs"]):
        profile = profiles[piece]
        start = piece == line["startPiece"]
        min_x = piece in line["minX"]
        cast_only = piece in line["castFromHand"]
        options = []
        for card, use in itertools.chain(tutor_meta.items(), recursion_meta.items()):
            if piece == commander_name or not use["credits"] or not substitute_allows(use, profile):
                continue
            kinds = (use["extra"],) if use["extra"] else ()
            x_cost = x_paid(use, profile)
            if use["mode"] == "to_battlefield":
                if is_front_permanent(profile) and not start and not min_x and not cast_only:
                    options.append({"card": card, "use": use, "route": "battlefield", "parts": [x_cost],
                                    "kinds": kinds})
                continue
            options.append({"card": card, "use": use, "route": "hand", "parts": [x_cost, piece_cost],
                            "kinds": kinds})
            if use["bargain"] and profile["cmc"] <= BARGAIN_FREE_MV and not min_x and not cast_only:
                options.append({"card": card, "use": use, "route": "bargain", "parts": [],
                                "kinds": kinds + ("bargain",)})
        deliveries[piece] = options
    return deliveries


def assembly_fetches(line: dict, profiles: dict, tutor_meta: dict) -> list[list[dict]]:
    """For each slot of an assembly line, every (tutor, member) fetch: a
    tutor that supplies a piece this turn and whose tags allow the member
    (onto the battlefield: a permanent member), as dicts: ``card``, ``use``,
    ``member``, ``cost`` (the tutor's use and the X paid; assembly never pays
    for the piece; Beseech the Mirror by its route to the hand), ``kinds``.
    A commander slot fills itself and fetches nothing."""
    fetches = []
    for slot in line["slots"]:
        options = []
        for member in [] if slot["isCommander"] else slot["members"]:
            profile = profiles[member]
            for card, use in tutor_meta.items():
                if not use["credits"] or not substitute_allows(use, profile):
                    continue
                if use["mode"] == "to_battlefield" and not is_front_permanent(profile):
                    continue
                options.append({"card": card, "use": use, "member": member,
                                "cost": combine_mana_costs([use["useCost"], x_paid(use, profile)]),
                                "kinds": (use["extra"],) if use["extra"] else ()})
        fetches.append(options)
    return fetches


def build_goldfish_context(decklist: list[str], deck_data: dict, metadata: dict,
                           commander_name: str, commander_colors: list[str],
                           deck_id: str = "") -> dict:
    """Precompute per-card profiles for goldfish simulation."""
    category_lookup = build_card_category_lookup(deck_data)
    # Each card's primary role, from its first decklist entry: the
    # interaction flag reads it (goldfish_holds_back). A role that is not a
    # string is read as none here; substitute_tables below refuses the deck
    # and names it.
    primary_roles = {}
    for entry in deck_data.get("decklist", []) or []:
        role = entry.get("primary_role")
        primary_roles.setdefault(entry.get("name"), role if isinstance(role, str) else None)
    profiles = {}
    # The deck's cards: the decklist and the commander, the definition the
    # combo-line check reads as the cards a line may name (no partner: the
    # goldfish models none).
    for name in gate_tags_lib.combo_line_cards(commander_name, decklist):
        profiles[name] = build_goldfish_profile(
            name=name,
            meta=metadata.get(name, {}),
            category_names=category_lookup.get(name, set()),
            primary_role=primary_roles.get(name),
            commander_colors=commander_colors,
            commander_name=commander_name,
        )
    combo_lines = extract_combo_lines(deck_data, profiles)
    assembly_lines = build_combo_assembly_lines(deck_id, decklist, commander_name)
    # The substitute tables (every deck's tags are checked against the
    # vocabulary here) drive both the winConditions combo check and the
    # KEY_COMBOS assembly check; each line carries what may supply each of
    # its pieces (combo_deliveries) or slots (assembly_fetches).
    needs_substitution = bool(combo_lines or assembly_lines)
    tutor_meta, recursion_meta = substitute_tables(deck_data, profiles, metadata, deck_id)
    if not needs_substitution:
        tutor_meta, recursion_meta = {}, {}
    for line in combo_lines:
        line["deliveries"] = combo_deliveries(line, profiles, tutor_meta, recursion_meta, commander_name)
    for line in assembly_lines:
        line["fetches"] = assembly_fetches(line, profiles, tutor_meta)
    # DEC-944 — every card the deck's two gates name: combo-gate pieces
    # (winConditions[] kind:'combo') plus KEY_COMBOS assembly slot members.
    # These are cast ahead of filler and are never held back by either hold
    # in the cast loop, because casting a piece advances the line instead of
    # spending it; an X piece or a non-permanent one among them is kept in the
    # hand instead (handOnlyPieces, below). Not a member by a line (owner
    # decision 27, 6b): a card it names only in a list entry of its pieces (an
    # alternative) or in a KEY_COMBOS slot flagged noPriority; such a card is
    # a member when another line names it plainly.
    line_members = frozenset(
        {piece for line in combo_lines for piece in line["pieces"] if piece not in line["alternatives"]}
        | {member
           for line in assembly_lines
           for slot in line["slots"] if not slot["noPriority"]
           for member in slot["members"]}
    )
    alternatives = frozenset(
        {piece for line in combo_lines for piece in line["alternatives"]}
        | {member for line in assembly_lines for slot in line["slots"] if slot["noPriority"]
           for member in slot["members"]})
    # The combo-line and assembly cards the goldfish keeps in the hand
    # (handOnlyPieces), where the combo checks read them: a member or an
    # alternative whose front face is not a permanent (Demonic Consultation;
    # an instant or sorcery slot member is not spent before its slot counts as
    # filled; a modal DFC whose front is a spell is not played as its land),
    # or with {X} in its cost whatever its type (owner-approved 2026-11-23,
    # decision C: the combo gate prices it at its line's minX, else at X = 0;
    # cast at X = 0, a 0/0 Walking Ballista would die), and every
    # castFromHand piece (owner decision 27, decision 2: it counts only cast
    # during the combo). The goldfish never casts one from the hand, plays one
    # as its land (choose_land_to_play), deploys one free (the DEC-405 deploy
    # engine) or casts one from a cascade (resolve_cascade_triggers). Other
    # permanent pieces (Thassa's Oracle) are cast proactively and stay
    # available to the checks on the battlefield.
    hand_only_pieces = frozenset(
        {member for member in line_members | alternatives
         if not is_front_permanent(profiles[member]) or profiles[member]["manaCost"]["X"]}
        | {piece for line in combo_lines for piece in line["castFromHand"]})
    # Reserved from filler casting and from the DEC-405 deploy engine's free
    # deploy, which leaves them in the hand: those pieces, and the tutor and
    # recursion cards the checks read as substitutes (none in a deck with no
    # combo or KEY_COMBOS line: the tables are emptied above).
    reserved_pieces = hand_only_pieces | set(tutor_meta) | set(recursion_meta)
    # Cards an imprint never exiles, in every deck whether or not it has a
    # gate: tutor and recursion cards by their roles, and every combo-line
    # and assembly-line member (imprint_from_hand).
    imprint_keep = (frozenset(role_names(deck_data, "tutor")) | role_names(deck_data, "recursion")
                    | line_members)
    # The alternatives kept in the hand that are no member of any line
    # (decision 6b): reserved like a line piece, but an imprint may exile
    # them, as it may a card held back as interaction (imprint_choice).
    held_alternatives = (alternatives - line_members) & hand_only_pieces
    # The spells a paid mulligan bottoms last of the spells (goldfish_bottom_cards): those
    # the goldfish takes from the hand without casting them as filler. Every
    # combo-line and assembly-line member; the tutor and recursion cards whose
    # tags can supply some piece of one of the deck's lines from the hand
    # (decision 6: a combo_deliveries or assembly_fetches entry; not a land,
    # a top-of-library or ``later`` card, a to-graveyard tutor, a no-credit
    # mode, or a card that matches no piece); and the deploy engine's
    # Equipment, never cast and deployed free from the hand
    # (deploy_engine_choice). A deck with no gate and no deploy engine keeps
    # nothing. Unlike imprintKeep, which an imprint never exiles in any deck,
    # it holds no tutor or recursion card the checks cannot use.
    deploy_engine = COMMANDER_DEPLOY_ENGINE.get(deck_id)
    gate_substitutes = frozenset(
        {option["card"] for line in combo_lines for options in line["deliveries"].values()
         for option in options}
        | {option["card"] for line in assembly_lines for options in line["fetches"] for option in options})
    mulligan_keep = line_members | gate_substitutes
    if deploy_engine is not None:
        mulligan_keep |= frozenset(deploy_engine["equipmentPower"]) | deploy_engine["doubleStrikeNames"]
    # Permanents with a {T} ability the turn uses after its casts: an
    # activated token maker (Castle Ardenvale), a once-per-untap hatch outlet
    # (High Market), a land fetch with {T} (Myriad Landscape) whose search can
    # net a land in this deck (activate_land_fetches; Urza's Cave in a deck
    # whose lands it would only swap one for one is not). Their mana is spent
    # last among the lands (GoldfishManaPool.rank), so the ability is left to
    # them when other mana pays.
    token_makers = TOKEN_MAKER_ENGINE.get(deck_id)
    hatch_engine = COMMANDER_HATCH_ENGINE.get(deck_id)

    def fetch_nets_a_land(name: str) -> bool:
        search = profiles[name]["landFetch"]
        found = len(select_ramp_targets([card for card in decklist if card != name], profiles,
                                        commander_colors, [], [], search, search["count"], to_hand=False))
        return found - (1 if profiles[name]["isLand"] else 0) >= 1

    reserve = ((set(token_makers["activatedMakers"]) if token_makers else set())
               | (set(hatch_engine["limitedOutletNames"]) if hatch_engine else set())
               | {name for name, profile in profiles.items()
                  if profile["landFetch"] and profile["landFetch"]["tapsSelf"] and fetch_nets_a_land(name)})
    for name in reserve & set(profiles):
        profiles[name] = dict(profiles[name], manaReserve=True)
    # Combo-line and assembly-line members Urza never taps for {U}
    # (urza_eligible): those whose line needs them untapped, a member with an
    # activated ability of its own with {T} in its cost (Isochron Scepter).
    # Another member (an Equipment such as Sword of Feast and Famine) can be
    # tapped for {U}.
    for name in line_members & set(profiles):
        if profiles[name]["tapAbility"]:
            profiles[name] = dict(profiles[name], urzaKeep=True)
    return {
        "profiles": profiles,
        "imprintKeep": imprint_keep,
        "mulliganKeep": mulligan_keep,
        "commanderName": commander_name,
        "commanderColors": commander_colors,
        "comboLines": combo_lines,
        "assemblyLines": assembly_lines,
        "reservedPieces": reserved_pieces,
        "handOnlyPieces": hand_only_pieces,
        "heldAlternatives": held_alternatives,
        "lineMembers": line_members,
        "cascade": COMMANDER_CASCADE.get(deck_id),
        "copyEngine": COMMANDER_COPY_ENGINE.get(deck_id),
        "tokenEngine": COMMANDER_TOKEN_ENGINE.get(deck_id),
        "deployEngine": COMMANDER_DEPLOY_ENGINE.get(deck_id),
        "drawEngines": PERMANENT_DRAW_ENGINE.get(deck_id),
        "amassEngine": AMASS_ARMY_ENGINE.get(deck_id),
        "hatchEngine": COMMANDER_HATCH_ENGINE.get(deck_id),
        "tokenMakers": TOKEN_MAKER_ENGINE.get(deck_id),
        "hasteSources": COMMANDER_HASTE_SOURCES.get(deck_id),
        "combatModifiers": COMBAT_MODIFIERS.get(deck_id),
    }


def goldfish_never_casts(name: str, profile: dict, context: dict) -> bool:
    """Cards the goldfish cast loop never casts from hand.

    Lands and modal cards with a land back (isLand: played as lands, except
    a line piece kept in the hand, which is neither cast nor played),
    interaction (goldfish_holds_back: a removal,
    counterspell or protection instant or sorcery, which has nothing to answer
    or save), the reserved cards (reservedPieces, only in a deck with a combo
    or KEY_COMBOS line: the line pieces kept in the hand, an X piece among
    them, decision C, and the tutor and recursion cards), and the DEC-405
    deploy engine's configured Equipment: the sim has no equip-cost path, so a
    hard-cast copy would sit on the battlefield unattached forever, and a real
    pilot holds them for the back face's free attach. The cast loop and the
    X-spell methodology read this one rule.
    """
    if profile["isLand"] or profile["isInteraction"]:
        return True
    if name in context["reservedPieces"]:
        return True
    deploy_engine = context.get("deployEngine")
    return (deploy_engine is not None
            and (name in deploy_engine["equipmentPower"]
                 or name in deploy_engine["doubleStrikeNames"]))


def should_goldfish_mulligan(hand: list[str], profiles: dict, hand_only: frozenset) -> bool:
    """Simple Commander goldfish mulligan heuristic. A card in ``hand_only``
    (the deck's handOnlyPieces, the combo-line and assembly pieces the
    goldfish keeps in the hand: one with a land face, Agadeem's Awakening, is
    never played as a land) is not a land here."""
    lands = sum(1 for name in hand if profiles[name]["isLand"] and name not in hand_only)
    cheap_ramp = sum(
        1 for name in hand
        if not profiles[name]["isLand"]
        and is_mana_source(profiles[name])
        and profiles[name]["cmc"] <= 2
    )
    return lands <= 1 or lands >= 6 or (lands == 2 and cheap_ramp == 0)


def goldfish_bottom_cards(hand: list[str], count: int, profiles: dict,
                          commander_colors: list[str], library: list[str],
                          keep: frozenset, hand_only: frozenset) -> list[str]:
    """The ``count`` cards of the seven-card ``hand`` a paid mulligan puts on
    the bottom, in order.

    Spells go first: those outside ``keep`` before those in it. Outside it,
    interaction first (held back, goldfish_holds_back: the goldfish never
    casts it, so never uses it), the most expensive first, then the other
    spells, the most expensive first, keeping the cheap ones a six-card hand
    casts early; inside it, the most expensive first, interaction or not (a
    kept card is one the combo checks read from the hand: Muddle the Mixture,
    a counterspell and a transmute tutor); lands last. ``keep`` is the deck's mulliganKeep
    (build_goldfish_context): the cards the goldfish takes from the hand
    without casting them as filler: every combo-line and assembly-line
    member; the tutor and recursion cards whose tags can supply some piece
    of one of the deck's lines from the hand (decision 6, 2026-11-24); and
    the deploy engine's configured Equipment, deployed free from the hand. A card the
    goldfish never casts, such as a spell held back as interaction whose
    secondary role is recursion, is not a card it never uses. A deck with no gate and no
    deploy engine keeps nothing.

    Exception: a hand of five or more lands it can play (a card in
    ``hand_only`` is not one) bottoms lands first, as a pilot
    does not keep a flood by bottoming a spell; five lands of seven leave
    four in six. The land bottomed is the one the land
    drop ranks lowest on the empty opening battlefield (land_play_score:
    one that enters tapped, then the fewest commander colours), the fetch
    lands scored against ``library``. Ties go by name.

    A card in ``hand_only`` (handOnlyPieces, the combo-line and assembly
    pieces kept in the hand: one with a land face is never played as a land)
    is a kept spell here, not a land.
    """
    land_names = [name for name in hand if profiles[name]["isLand"] and name not in hand_only]
    spells = sorted((name for name in hand if name not in land_names),
                    key=lambda name: (name in keep, name in keep or not profiles[name]["isInteraction"],
                                      -profiles[name]["cmc"], name))
    lands = sorted(land_names,
                   key=lambda name: land_play_score(name, hand, profiles, [], [],
                                                    commander_colors, library))
    return (lands + spells if len(lands) >= 5 else spells + lands)[:count]


def commander_mulligan_goldfish(decklist: list[str], profiles: dict, commander_colors: list[str],
                                keep: frozenset, hand_only: frozenset) -> tuple[list[str], list[str]]:
    """Run the Commander mulligan and return library + kept hand.

    The first mulligan is free (a new seven); the second is paid: the third
    seven is kept and one card goes to the bottom (goldfish_bottom_cards,
    ``keep`` the deck's mulliganKeep; ``hand_only`` its handOnlyPieces,
    never counted as lands). Draws pop the library's end, so the
    card goes in at index 0: ordinary draws leave it under the rest of the
    library, but a land search can still take it and a cascade or hatch dig
    can reach it (the goldfish does not shuffle after a search, as a real
    game would).
    """
    attempt = 0
    while True:
        library = list(decklist)
        random.shuffle(library)
        hand = [library.pop() for _ in range(7)]
        if should_goldfish_mulligan(hand, profiles, hand_only) and attempt < 2:
            attempt += 1
            continue
        break

    if attempt >= 2:
        for card in goldfish_bottom_cards(hand, attempt - 1, profiles, commander_colors, library, keep,
                                          hand_only):
            hand.remove(card)
            library.insert(0, card)
    return library, hand


def crack_target_tapped(crack: dict, target: str, battlefield_lands: list[dict],
                        permanents: list[dict], profiles: dict, hand: list[str]) -> bool:
    """Whether the land a fetch land finds enters tapped (M6): by its own
    entry rule when the search puts it onto the battlefield untapped; when the
    search puts it tapped, untapped only by the search's own rule ("if you
    control four or more lands, untap that land", "behold an Elf").
    ``battlefield_lands`` is the battlefield without the fetch land."""
    if not crack["entersTapped"]:
        return land_enters_tapped(profiles[target]["landEntry"], battlefield_lands, permanents,
                                  profiles, hand)
    rule = crack["untapIf"]
    if rule is None:
        return True
    if rule[0] == "landsAtLeast":
        return len(battlefield_lands) + 1 < rule[1]
    return land_enters_tapped(rule, battlefield_lands, permanents, profiles, hand)


def crack_target(name: str, library: list[str], profiles: dict, commander_colors: list[str],
                 battlefield_lands: list[dict], permanents: list[dict], hand: list[str],
                 take: bool) -> tuple[str | None, bool]:
    """The land fetch land ``name`` finds in the library (the best legal
    target) and whether it enters tapped; with ``take`` it is removed from the
    library. (None, True) when nothing legal is left."""
    crack = profiles[name]["landCrack"]
    search_in = library if take else list(library)
    test = lambda target: crack_target_tapped(crack, target, battlefield_lands, permanents,  # noqa: E731
                                              profiles, hand)
    found = select_ramp_targets(search_in, profiles, commander_colors, battlefield_lands,
                                permanents, crack, 1, tapped_test=test, to_hand=False)
    if not found:
        return None, True
    return found[0], test(found[0])


def choose_land_to_play(hand: list[str], profiles: dict, battlefield_lands: list[dict],
                        permanents: list[dict], commander_colors: list[str],
                        library: list[str] = (), keep: frozenset = frozenset()) -> str | None:
    """Pick the land in hand that land_play_score ranks highest on this board.

    A land that sacrifices or returns N lands as it enters (Scorched Ruins,
    Lotus Field, Simic Growth Chamber) is played only with N other lands out.
    A card in ``keep`` (the deck's handOnlyPieces: a combo-line or assembly
    piece with a land face, Agadeem's Awakening) stays in the hand for the
    combo checks.
    """
    land_names = [name for name in hand if profiles[name]["isLand"] and name not in keep
                  and (profiles[name]["landEntryCost"] or {"count": 0})["count"]
                  <= len(battlefield_lands)]
    if not land_names:
        return None

    return max(land_names, key=lambda name: land_play_score(
        name, hand, profiles, battlefield_lands, permanents, commander_colors, library))


def land_play_score(name: str, hand: list[str], profiles: dict, battlefield_lands: list[dict],
                    permanents: list[dict], commander_colors: list[str],
                    library: list[str] = ()) -> tuple:
    """What the goldfish gets from playing land ``name`` from ``hand`` now,
    higher first: usable this turn, then the commander colours it adds that
    the lands out lack, its commander colours, its colours, then its name. A
    fetch land scores as the land it would find in ``library`` (none: it makes
    nothing). The land drop plays the highest (choose_land_to_play); a paid
    mulligan that bottoms a land bottoms the lowest (goldfish_bottom_cards)."""
    present_colors = set()
    for land in battlefield_lands:
        present_colors.update(land.get("colors", set()))
    profile = profiles[name]
    rest_of_hand = list(hand)
    rest_of_hand.remove(name)
    if profile["landCrack"]:
        target, tapped = crack_target(name, list(library), profiles, commander_colors,
                                      battlefield_lands, permanents, rest_of_hand, take=False)
        colors = land_colors(profiles[target], played=False) if target else set()
    else:
        colors = land_colors(profile)
        tapped = land_enters_tapped(profile["landEntry"], battlefield_lands, permanents,
                                    profiles, rest_of_hand)
    untapped_bonus = 10 if usable_this_turn(profiles[target] if profile["landCrack"] and target
                                            else profile, tapped) else 0
    return (
        untapped_bonus,
        len((colors & set(commander_colors)) - present_colors),
        len(colors & set(commander_colors)),
        len(colors),
        name,
    )


def proactive_cast_priority(name: str, profile: dict, commander_name: str,
                            commander_cast: bool,
                            line_members: frozenset = frozenset()) -> tuple:
    """Sort order for proactive solitaire decisions.

    DEC-944 — ``line_members`` are the cards named by the deck's combo gate
    (``winConditions[] kind:'combo'``) and KEY_COMBOS assembly slots, not a
    card named only in a list entry of a line's pieces or in a slot flagged
    noPriority (owner decision 27, build_goldfish_context). A piece
    outranks the generic threat/draw/filler tiers because it is the cast that
    advances the turn's line. The order: mana sources first (they are mana
    positive across the turn and the line needs the mana), then the commander
    (most of the fleet's engines gate on the commander being on the
    battlefield), then the line's pieces, then threats, draw, other
    permanents and the rest; interaction last. For a deck with no combo
    configuration ``line_members`` is empty and the relative order is exactly
    as before.
    """
    if profile["isInteraction"]:
        return (99, 99, 99, name)
    if is_mana_source(profile):
        ramp_value = (len(profile["manaAtoms"])
                      + (profile["landRamp"]["count"] if profile["landRamp"] else 0)
                      + (profile["landFetch"]["count"] if profile["landFetch"] else 0))
        return (0, profile["cmc"], -ramp_value, name)
    if name == commander_name and not commander_cast:
        return (1, 0, -profile["impact"], name)
    if name in line_members:
        return (2, profile["cmc"], -profile["impact"], name)
    if profile["isThreat"]:
        return (3, -profile["impact"], -profile["cmc"], name)
    if profile["isDraw"]:
        return (4, profile["cmc"], -profile["immediateDraw"], name)
    if profile["isPermanent"]:
        return (5, -profile["impact"], -profile["cmc"], name)
    return (6, profile["cmc"], 0, name)


def board_has_type(permanent: dict, word: str, profiles: dict, granted: set) -> bool:
    """Whether a permanent on the goldfish battlefield has a type word: a land
    its land types (with a type another land gives every land), any card its
    type line (a changeling every creature type)."""
    profile = profiles[permanent["name"]]
    if permanent["kind"] == "land" and (word in profile["landTypes"] or word in granted):
        return True
    return word in profile["typeWords"] or (
        permanent["kind"] != "land" and profile["changeling"] and word not in CARD_TYPE_WORDS
        and word not in LAND_SUBTYPE_COLORS)


def board_condition(test: tuple, permanents: list[dict], profiles: dict, granted: set) -> bool:
    """A mana condition (mana_condition) read on the goldfish battlefield."""
    if test[0] == "anyType":
        return any(board_has_type(p, word, profiles, granted)
                   for p in permanents if p["kind"] == "land" for word in test[1])
    if test[0] == "atLeast":
        return sum(1 for p in permanents if board_has_type(p, test[1], profiles, granted)) >= test[2]
    # "landTypes": every one of these land types is on the battlefield (Tron).
    return all(any(p["kind"] == "land" and board_has_type(p, word, profiles, granted)
                   for p in permanents) for word in test[1])


def land_grant(permanents: list[dict], profiles: dict) -> frozenset:
    """Colours every land can make from a permanent on the battlefield (F2):
    Urborg ("Each land is a Swamp": {B}), Chromatic Lantern ("Lands you
    control have "{T}: Add one mana of any color."")."""
    return frozenset().union(*(profiles[p["name"]]["landGrant"] or frozenset() for p in permanents))


def with_grant(atoms: list, grant: frozenset) -> list:
    """A land's mana with a granted mana ability: a land still taps once, so
    at one mana (or none) the granted colours join its own (M4); a land that
    makes more keeps its own."""
    if not grant or len(atoms) > 1:
        return atoms
    return [(atoms[0] if atoms else frozenset()) | grant]


def land_could_produce(land: dict, permanents: list[dict], profiles: dict, turn: int) -> frozenset:
    """The colours a land on the battlefield could produce (Reflecting Pool,
    G4): its mana as played (a Pathway's face, whose other face is not
    read), what each of its mana abilities' effects would make on this
    board, read before the ability's cost is netted and whatever its
    activation condition or cost (``landOutputs``: The Mycosynth Gardens'
    "{1}, {T}: any color", Spire of Industry's any colour with no artifact
    out; Cabal Coffers makes black only with a Swamp out), and a grant to
    every land."""
    profile = profiles[land["name"]]
    colours = set().union(*land["manaAtoms"]) if land["manaAtoms"] else set()
    for kind, output in ([] if profile["landFaces"] else profile.get("landOutputs", ())):
        if kind == "fixed":
            colours |= output
        elif output[0] == "count":
            colours.update(*board_term_atoms(("count", output[1], output[2], 0, None), [], permanents,
                                             profiles, turn, land))
        elif output[0] != "landColors":  # another Reflecting Pool copies nothing
            colours.update(*board_term_atoms(output, [], permanents, profiles, turn, land))
    for atom in record_atoms(land, permanents, profiles, turn):
        colours |= atom
    return frozenset(colours)


def board_term_atoms(term: tuple, atoms: list[frozenset], permanents: list[dict],
                     profiles: dict, turn: int, owner: dict | None = None) -> list[frozenset]:
    """A permanent's mana this turn: ``atoms`` with one board term read on the
    goldfish's own battlefield (M5). A term that makes more mana replaces the
    floor; one of equal size, one mana, joins its colours (M4). ``owner`` is
    the permanent the term belongs to (Reflecting Pool reads the other
    lands)."""
    granted = {profiles[p["name"]]["eachLandIs"] for p in permanents if p["kind"] == "land"} - {None}
    kind = term[0]
    if kind == "gate":
        if not board_condition(term[1], permanents, profiles, granted):
            return atoms
        candidate = list(term[2])
    elif kind == "count":
        _, key, colours, cost, gate = term
        if gate is not None and not board_condition(gate, permanents, profiles, granted):
            return atoms
        if key[0] == "devotion":
            # Each colour with its own devotion (devotion_to). The k-th mana
            # is every colour with devotion k or more past the cost; the
            # activation is one colour (manaOneColour), so a colour pays only
            # the mana it makes (GoldfishManaPool._left).
            devotion = {colour: devotion_to(frozenset(colour), permanents, profiles)
                        for colour in "WUBRG" if colour in colours}
            top = max(devotion.values(), default=0) - cost
            candidate = [frozenset(c for c, n in devotion.items() if n - cost >= k)
                         for k in range(1, top + 1)]
            if len(candidate) > len(atoms):
                return candidate
            if len(candidate) == len(atoms) == 1:
                return [atoms[0] | candidate[0]]
            return atoms
        if key[0] == "idleArtifacts":
            # Its own artifact token (Urza's Construct): his own mana. Each
            # other eligible artifact taps for its own {U} (board_mana,
            # urza_eligible): it is the permanent that gets tapped (G5).
            count = key[1]
        else:
            count = sum(1 for p in permanents if board_has_type(p, key[1], profiles, granted))
        candidate = [colours] * (count - cost)
    elif kind == "vivid":
        colours = frozenset().union(*(profiles[p["name"]]["colors"] for p in permanents))
        candidate = [frozenset({colour}) for colour in "WUBRG" if colour in colours]
    elif kind == "landColors":
        # Reflecting Pool: what the other lands could produce (land_could_produce:
        # the face a Pathway was played as, every colour their mana abilities
        # make whatever their activation conditions, a grant to every land);
        # another Pool makes nothing of its own to copy.
        colours = frozenset().union(*(
            land_could_produce(p, permanents, profiles, turn) for p in permanents
            if p["kind"] == "land" and p is not owner
            and not any(t[0] == "landColors" for t in profiles[p["name"]]["manaBoard"])))
        candidate = [colours] if colours else []
    else:  # legendColors: colours among legendary permanents (of these types)
        colours = frozenset().union(*(
            profiles[p["name"]]["colors"] for p in permanents
            if "Legendary" in profiles[p["name"]]["typeWords"]
            and (not term[1] or set(term[1]) & profiles[p["name"]]["typeWords"])))
        candidate = [colours] if colours else []
    if len(candidate) > len(atoms):
        return candidate
    if len(candidate) == len(atoms) == 1:
        return [atoms[0] | candidate[0]]
    return atoms


class ManaAtom(frozenset):
    """One mana from one permanent: its colours, the permanent's record
    (``source``), whether it is one-shot mana (``once``), its spend order
    (``order``, spend_order), whether its permanent has a {T} ability the
    turn uses later (``reserve``), whether spending it taps that permanent
    (``taps``: an ability with {T}, an extra a {T} ability fires) and, for
    mana that is all one colour as it is made (Lotus Field, Nykthos, a
    source that makes {C} or a colour beside Forsaken Monument), its
    activation (``group``). GoldfishManaPool.rank reads them: a turn taps a
    creature for mana only when its spending needs it."""
    source = None
    order = 0
    once = False
    group = None
    reserve = False
    taps = False


def tag_atoms(atoms, source: dict, order: int, once: bool = False, group=None,
              reserve: bool = False, taps: bool = False) -> list:
    """Tag a permanent's mana atoms for the turn's pool (ManaAtom)."""
    tagged = []
    for atom in atoms:
        mana = ManaAtom(atom)
        mana.source, mana.order, mana.once, mana.group = source, order, once, group
        mana.reserve, mana.taps = reserve, taps
        tagged.append(mana)
    return tagged


def spend_order(record: dict, profiles: dict, turn: int) -> int:
    """When the goldfish spends a permanent's mana (GoldfishManaPool.rank): 0
    for lands, noncreature permanents and every creature whose mana does not
    tap it, that could not attack anyway (summoning sick, no combat) or that
    attacks anyway (vigilance, M9: the pilot attacks first and taps it for
    mana after combat); 2 plus its combat for a creature that taps for mana
    instead of attacking, so the least combat is given up first. One-shot
    mana is at least 1 (permanent_mana)."""
    profile = profiles[record["name"]]
    if ("Creature" not in profile["typeWords"] or not profile["manaTapsSelf"] or profile["vigilance"]
            or record["combat"] <= 0 or record["combatReadyTurn"] > turn):
        return 0
    return 2 + record["combat"]


def record_atoms(permanent: dict, permanents: list[dict], profiles: dict, turn: int) -> list:
    """A permanent's lasting mana this turn: its floor with its board terms
    read (board_term_atoms) and, for a land, the colours a permanent grants
    every land (with_grant)."""
    atoms = permanent["manaAtoms"]
    for term in permanent.get("manaBoard", ()):
        if term[0] != "extra":
            atoms = board_term_atoms(term, atoms, permanents, profiles, turn, permanent)
    if permanent["kind"] == "land":
        atoms = with_grant(atoms, land_grant(permanents, profiles))
    return atoms


def urza_grant(present: list[dict]) -> frozenset:
    """The colours Urza, Lord High Artificer's "Tap an untapped artifact you
    control: Add {U}" gives each eligible artifact (an ``idleArtifacts``
    count term on a permanent whose mana is online)."""
    return frozenset().union(*(term[2] for p in present for term in p.get("manaBoard", ())
                               if term[0] == "count" and term[1][0] == "idleArtifacts"))


def urza_eligible(permanent: dict, profiles: dict) -> bool:
    """An artifact Urza taps for {U}: noncreature, with no mana of its own
    (tapping it loses nothing), and not one the goldfish needs untapped for
    something else: a combo-line or assembly-line member whose line needs it
    untapped, one with an activated ability of its own with {T} in its cost
    (``urzaKeep``, build_goldfish_context: Isochron Scepter; an Equipment
    such as Sword of Feast and Famine is tapped). One whose own {T} ability was
    used (The One Ring's draw) is tapped, so it offers nothing (board_mana)."""
    profile = profiles[permanent["name"]]
    words = profile["typeWords"]
    return (permanent["kind"] != "land" and "Artifact" in words and "Creature" not in words
            and not profile.get("urzaKeep") and not own_mana(permanent))


def own_mana(permanent: dict) -> bool:
    """Whether a permanent has mana of its own (lasting, one-shot or read on
    the battlefield), as opposed to mana only a grant gives it."""
    return bool(permanent["manaAtoms"] or permanent.get("manaOnce") or permanent.get("manaBoard"))


def mana_taps_it(permanent: dict, profiles: dict) -> bool:
    """Whether using the permanent's own mana taps it: an ability with {T},
    or a land's mana from a grant to every land when it has none of its own
    (Maze of Ith beside Urborg: the granted ability is "{T}: Add")."""
    return bool(profiles[permanent["name"]]["manaTapsSelf"]) or (
        permanent["kind"] == "land" and not own_mana(permanent))


def extra_fires(term: tuple, permanent: dict, atoms: list, profiles: dict, granted: set) -> str | None:
    """Whether a triggered "add an additional" term (mana_trigger) fires for
    one activation of ``permanent`` making ``atoms``: "always", "colourless"
    (Forsaken Monument on an activation that makes {C} or a colour: only when
    it makes {C}) or None."""
    source = term[1]
    profile = profiles[permanent["name"]]
    if not atoms:
        return None
    if source == "swampsTapped":
        return "always" if (permanent["kind"] == "land"
                            and board_has_type(permanent, "Swamp", profiles, granted)) else None
    if not profile["manaTapsSelf"]:
        return None
    if source == "creatureSources":
        return "always" if "Creature" in profile["typeWords"] else None
    # colorlessSources: "Whenever you tap a permanent for {C}".
    if any(atom == frozenset({"C"}) for atom in atoms):
        return "always"
    if len(atoms) == 1 and "C" in atoms[0]:
        return "colourless"
    return None


def permanent_mana(permanent: dict, permanents: list[dict], profiles: dict, turn: int,
                   extras: list, urza: frozenset, granted: set) -> list:
    """One untapped permanent's mana for the pool, tagged: its lasting mana
    (record_atoms; one activation's mana shares a group when it is all one
    colour), its one-shot mana unless spent, the {U} Urza gives it, and the
    extras the active triggers add for it (``extras``: (term, owner)). An
    extra that fires only on the colourless choice of an activation joins
    that activation's group, so it is made only when the activation makes
    {C}."""
    profile = profiles[permanent["name"]]
    order = spend_order(permanent, profiles, turn)
    reserve = bool(profile.get("manaReserve"))
    taps = mana_taps_it(permanent, profiles)
    group = id(permanent) if profile["manaOneColour"] else None
    lasting = list(record_atoms(permanent, permanents, profiles, turn))
    once = [] if permanent.get("onceSpent") else list(permanent.get("manaOnce", ()))
    once_group = group
    lasting_extra, once_extra = [], []
    for term, _owner in extras:
        fires = extra_fires(term, permanent, lasting, profiles, granted)
        if fires:
            lasting_extra.append(term[2])
            if fires == "colourless":
                group = group or id(permanent)
        # Monument also fires on one-shot {C} (Basalt Monolith): that extra
        # is one-shot too.
        fires_once = (extra_fires(term, permanent, once, profiles, granted)
                      if term[1] == "colorlessSources" else None)
        if fires_once:
            once_extra.append(term[2])
            if fires_once == "colourless":
                once_group = once_group or id(permanent)
    tagged = tag_atoms(lasting + lasting_extra, permanent, order, group=group, reserve=reserve, taps=taps)
    tagged += tag_atoms(once + once_extra, permanent, max(order, 1), once=True, group=once_group,
                        taps=taps)
    if permanent.get("tapped"):
        # Tapped (it attacked, or a {T} ability of its own was used): only a
        # permanent whose mana does not tap it gets here (board_mana: Urza's
        # own {U}, which taps his Construct), and Urza taps only untapped
        # artifacts.
        return tagged
    if urza and urza_eligible(permanent, profiles):
        tagged += tag_atoms([urza], permanent, 0, reserve=reserve, taps=True)
    return tagged


def board_mana(permanents: list[dict], turn: int, profiles: dict, used=frozenset()) -> list:
    """The mana the goldfish battlefield offers now, tagged (ManaAtom): each
    permanent whose mana is online (a Saga's only while it lasts) and not yet
    used this turn (``used``: GoldfishManaPool.tapped), untapped or with mana
    that does not tap it (Urza's own {U}, after he attacked), with the extras
    the active triggers add for it (Crypt Ghast, Badgermole Cub, Forsaken
    Monument; the Cub's earthbent land as a source of its own), the {U}
    Urza gives each untapped eligible artifact, and a grant to every land on
    a land with no mana of its own (Maze of Ith beside Urborg or Chromatic
    Lantern; a fetch land left with nothing to find). GoldfishManaPool's
    unspent mana is always this plus mana already floating (refresh_pool)."""
    present = [p for p in permanents
               if p["manaActiveTurn"] <= turn and p.get("manaLastTurn", turn) >= turn]
    extras = [(term, owner) for owner in present for term in owner.get("manaBoard", ())
              if term[0] == "extra"]
    urza = urza_grant(present)
    grant = land_grant(permanents, profiles)
    sources = [p for p in present
               if id(p) not in used
               and (not p.get("tapped") or not mana_taps_it(p, profiles))
               and (own_mana(p) or (urza and urza_eligible(p, profiles))
                    or (grant and p["kind"] == "land"))]
    granted = ({profiles[p["name"]]["eachLandIs"] for p in permanents if p["kind"] == "land"} - {None}
               if sources else set())
    out = []
    for permanent in sources:
        out += permanent_mana(permanent, permanents, profiles, turn, extras, urza, granted)
    for term, owner in extras:
        if term[3]:
            # The earthbent land: a land creature, tapped for mana, that the
            # goldfish does not keep a record of.
            land = owner.setdefault("earthbentLand", {"name": f"{owner['name']} (earthbent land)"})
            if id(land) not in used:
                out += tag_atoms([term[2]] * term[3], land, 0, taps=True)
    return out


def board_key(permanents: list[dict], used) -> tuple:
    """What board_mana reads that can change during a turn: which permanents
    are on the battlefield, which are tapped or spent other than by this
    turn's spending, their imprinted mana, readiness, combat and online
    turn."""
    return tuple((id(p), bool(p.get("tapped")) and id(p) not in used,
                  bool(p.get("onceSpent")) and id(p) not in used, id(p["manaAtoms"]),
                  p.get("combatReadyTurn"), p.get("combat"), p["manaActiveTurn"]) for p in permanents)


def refresh_pool(pool: "GoldfishManaPool", permanents: list[dict], profiles: dict,
                 turn: int) -> "GoldfishManaPool":
    """Read the pool's unspent mana from the board again (invariant I1): it is
    the mana already floating (no source, or a source this turn has used)
    plus board_mana for every permanent not yet used. Called after every
    resolution (a cast, a land put onto the battlefield, a permanent leaving,
    a trigger or grant source entering); mana new to the pool counts as
    added (availableMana). Returns the pool, changed in place."""
    if pool.turn is None:
        pool.turn = turn
    key = board_key(permanents, pool.tapped)
    if key == pool.board_key:
        return pool
    floating, fresh_before = [], Counter()
    for atom in pool.sources:
        sid = atom_source_id(atom)
        if sid is None or sid in pool.tapped:
            floating.append(atom)
        else:
            fresh_before[sid] += 1
    fresh = [atom for atom in board_mana(permanents, turn, profiles, pool.tapped)
             if not (pool.lasting_only and atom.once)]
    fresh_after = Counter(atom_source_id(atom) for atom in fresh)
    pool.added += sum(max(0, n - fresh_before[sid]) for sid, n in fresh_after.items())
    pool.sources = floating + fresh
    pool.board_key = key
    # Every record the pool has read stays alive for the turn (records): the
    # ids board_key, tapped and tapping hold stay unique, a source that
    # sacrificed itself included.
    pool.records.update((id(p), p) for p in permanents)
    return pool


def cost_vector(cost: dict) -> tuple:
    """A cost's mana, one count per kind (generic, then W, U, B, R, G, C)."""
    return tuple(cost.get(key, 0) for key in COST_KEYS)


def payable_assignments(fixed: list[dict], options: list[list[dict]], leaf_ok) -> list[dict]:
    """The costs of every way to fill each entry of ``options`` with a
    different choice (rule B7), keeping only the cheapest (Pareto-minimal:
    no other cost is at most as much in every kind of mana).

    ``options[i]`` lists the ways to supply the i-th missing piece or open
    slot, each a dict with ``uses`` (the cards it takes; no two choices of
    one assignment share one) and
    ``cost``. ``fixed`` is paid by every assignment. ``leaf_ok(chosen)``
    decides whether a full assignment's extra costs find their objects. A
    check is ready when any returned cost is payable, so the cost a dearer
    assignment would add is never needed.
    """
    frontier: list[tuple[tuple, dict]] = []

    def covered(vector: tuple) -> bool:
        return any(all(a <= b for a, b in zip(other, vector)) for other, _ in frontier)

    def search(index: int, used: frozenset, parts: list[dict], chosen: list[dict]) -> None:
        cost = combine_mana_costs(fixed + parts)
        vector = cost_vector(cost)
        if covered(vector):
            return  # every completion costs at least as much as a cost already kept
        if index == len(options):
            if leaf_ok(chosen):
                frontier[:] = [(other, kept) for other, kept in frontier
                               if not all(a <= b for a, b in zip(vector, other))]
                frontier.append((vector, cost))
            return
        for option in options[index]:
            if option["uses"] & used:
                continue
            search(index + 1, used | option["uses"], parts + [option["cost"]], chosen + [option])

    search(0, frozenset(), [], [])
    return [cost for _, cost in frontier]


def creature_now(profile: dict, permanents: list[dict], profiles: dict) -> bool:
    """Whether a permanent on the goldfish battlefield is a creature: its
    battlefield face's type line says so, and one that is a creature only
    while a condition holds (``conditionalCreature``) is one only when that
    condition is a devotion (``creatureDevotion``) met on ``permanents``
    (devotion_to, its own mana cost included)."""
    devotion = profile["creatureDevotion"]
    return "Creature" in profile["typeWords"] and (not profile["conditionalCreature"] or (
        devotion is not None and devotion_to(devotion[0], permanents, profiles) >= devotion[1]))


def extra_cost_objects(permanents: list[dict], hand: list[str], profiles: dict, commander_name: str,
                       excluded: set[str]) -> list[tuple]:
    """The objects that can pay an extra cost (rule B5), as (key, card name,
    the kinds it pays): a non-land permanent to sacrifice (a creature, a
    green creature, an artifact) or as the bargain object (an artifact or an
    enchantment), read on its battlefield face; a creature card in hand to
    discard (its front face). Never the commander, a card named in
    ``excluded``, or a permanent whose mana comes from sacrificing it (Lotus
    Petal: its mana is already in the pool). A land permanent and a token
    never pay one: the goldfish keeps tokens as counts, not objects. A
    creature only while a condition holds (``conditionalCreature``) is a
    creature to sacrifice only when that condition is a devotion
    (``creatureDevotion``) met on this battlefield, the god's own mana cost
    included (devotion_to): Mogis, God of Slaughter at devotion to black and
    red of seven or more. Below it, it is still the bargain object as an
    enchantment, and in the hand a creature card to discard. The devotion is
    read once, from ``permanents`` as the check starts: a cast that would add
    to it this turn is not counted (reads too little), nor a sacrifice that
    would lower it (reads too much: two gods whose creature status depends on
    devotion, both at their thresholds, both count, though sacrificing one
    could turn the other off; no deck holds two such gods)."""
    objects = []
    for index, record in enumerate(permanents):
        name = record["name"]
        if record["kind"] == "land" or name == commander_name or name in excluded:
            continue
        profile = profiles[name]
        if profile["onceLeaves"]:
            continue
        words = profile["typeWords"]
        kinds = set()
        if creature_now(profile, permanents, profiles):
            kinds.add("sacrifice-creature")
            if "G" in profile["colors"]:
                kinds.add("sacrifice-green-creature")
        if "Artifact" in words:
            kinds |= {"sacrifice-artifact", "bargain"}
        if "Enchantment" in words:
            kinds.add("bargain")
        if kinds:
            objects.append((("battlefield", index), name, frozenset(kinds)))
    for index, name in enumerate(hand):
        if name != commander_name and name not in excluded and "Creature" in profiles[name]["libraryTypeWords"]:
            objects.append((("hand", index), name, frozenset({"discard-creature"})))
    return objects


def objects_found(kinds: list[str], objects: list[tuple], used_names: set[str],
                  keeps=lambda taken: True) -> bool:
    """Whether every extra cost in ``kinds`` takes its own object (one object
    per cost) that is not a card the assignment uses, such that
    ``keeps(the keys taken)`` holds."""
    candidates = [[obj for obj in objects if kind in obj[2] and obj[1] not in used_names] for kind in kinds]

    def search(index: int, taken: frozenset) -> bool:
        if index == len(kinds):
            return keeps(taken)
        return any(search(index + 1, taken | {obj[0]}) for obj in candidates[index] if obj[0] not in taken)

    return search(0, frozenset())


def combo_ready_this_turn(turn: int, hand: list[str], permanents: list[dict],
                          combo_lines: list[dict], profiles: dict,
                          pool: "GoldfishManaPool", commander_name: str = "") -> bool:
    """Whether any combo line is fully assembled and payable this turn: one of
    combo_line_costs is payable from ``pool``, the mana still unspent this
    turn after the main-phase casts (DEC-937), not a fresh turn pool."""
    return any(pool.can_cast(cost) for cost in combo_line_costs(
        turn, hand, permanents, combo_lines, profiles, commander_name))


def combo_line_costs(turn: int, hand: list[str], permanents: list[dict],
                     combo_lines: list[dict], profiles: dict, commander_name: str = "") -> list[dict]:
    """The costs that put each combo line together this turn, the cheapest
    (payable_assignments) of every way to supply its missing pieces: the
    costs a spend keeps the combo gate by keeping one of payable.

    A piece on the non-land battlefield costs nothing; one in hand costs its
    cost (a ``minX`` piece at its line's minX: Walking Ballista beside
    Heliod, Sun-Crowned is priced at X = 2). A missing piece is supplied by a
    substitute in hand, as the line's ``deliveries`` (combo_deliveries) say:
    a tutor or recursion card whose tags allow the piece, paying its use and,
    when the piece goes to the hand or is cast from the graveyard, the piece;
    onto the battlefield it is not paid and never supplies a minX piece, the
    startPiece or a castFromHand piece; bargained Beseech the Mirror casts a
    piece of mana value 4 or less free (not a minX or castFromHand piece);
    nothing supplies the commander. Every assignment of the missing pieces to different cards
    is tried (rule B7). One use per card (B6): a card that is a piece in hand
    supplies another piece only if it is a permanent, paying only its
    ``*_cost`` on top of the cast already counted (Sun Titan cast as a piece
    returns Kaya's Ghostform); an instant or sorcery piece is never also a
    substitute. Each extra cost takes its own object (extra_cost_objects),
    never a piece of the line.

    A line's ``startPiece`` is the piece its loop starts by casting (Sensei's
    Divining Top tapped onto the library and recast through Mystic Forge, or
    redrawn and cast with Echoes of Eternity). On the battlefield it is free
    only if it was the last of the line's pieces to enter, this turn (its
    record has ``enteredTurn == turn`` and every other piece's record comes
    before it in ``permanents``); out since an earlier turn its cost is paid
    again (a minX piece at its minX); entered this turn before a partner, the
    line is not ready this turn. Missing, it is supplied only by a route that
    casts it. A line whose loop recasts the piece from the battlefield
    (Mystic Forge) pays its cost again, a one-mana restart; a line that needs
    it cast from the hand (Echoes of Eternity) also lists it in castFromHand,
    so on the battlefield it never counts there. The goldfish does not plan its casts
    around the start piece: it casts line pieces cheapest first, so a start
    piece cast in the same turn as its last partner lands first and the line
    waits a turn.

    A minX piece already on the battlefield counts whatever X it entered
    with. Walking Ballista, the only such piece in the fleet, is reserved as
    a line piece with {X} (decision C, build_goldfish_context), so the cast
    loop never casts it, a cascade declines it and a deploy never takes it;
    the hatch, the other free put the goldfish models, is in no deck that
    holds it.

    The combo-line corrections' fields (owner decision 27, 2026-11-25;
    extract_combo_lines):

    - ``needsCreature``: the line is ready only with that many creatures on
      the battlefield that are not its pieces (creature_now: a land creature
      counts, a Theros god at its devotion), and an extra cost never takes
      one of them below that many; tokens are not objects here, so they are
      not seen.
    - ``castFromHand``: such a piece counts in the hand (its cost paid) or
      supplied by a route that casts it (combo_deliveries); on the
      battlefield the line is not ready.
    - ``readyPieces``: such a piece counts once its record shows it entered
      on an earlier turn (whether it is untapped is not checked). One that
      entered this turn, is in the hand or is supplied takes one of the
      line's ``readyHaste`` sources, chosen with the rest of the assignment,
      so the cheapest payable is kept: a static grant on the battlefield,
      free, for any number of pieces; an Equipment on the battlefield, its
      equip added, or an instant in the hand, its cost added, each for one
      piece. A source an assignment relies on is never an extra cost's
      object. With no source the line is not ready.
    - ``extraCost`` is added to the line's cost each time it is counted.
    """
    costs = []
    if not combo_lines:
        return costs
    battlefield_names = {permanent["name"] for permanent in permanents if permanent["kind"] != "land"}
    hand_names = set(hand)
    # The latest record of each non-land permanent, for the readyPieces rule.
    records = {permanent["name"]: permanent for permanent in permanents if permanent["kind"] != "land"}
    # Entry position of each non-land permanent (latest copy), for the startPiece rule.
    entry_index = (
        {p["name"]: idx for idx, p in enumerate(permanents) if p["kind"] != "land"}
        if any(line["startPiece"] for line in combo_lines) else {}
    )
    for line in combo_lines:
        # The creatures the line may target (needsCreature), by their keys in
        # extra_cost_objects: those on the battlefield, a land creature
        # included, that are not its pieces. No extra cost may take them below
        # the count (leaf_ok).
        targets = frozenset(("battlefield", index) for index, permanent in enumerate(permanents)
                            if permanent["name"] not in line["pieces"]
                            and creature_now(profiles[permanent["name"]], permanents, profiles)
                            ) if line["needsCreature"] else frozenset()
        if len(targets) < line["needsCreature"]:
            continue  # no creature to target
        start_piece = line["startPiece"]
        start_recast = False
        if start_piece in entry_index:
            start_idx = entry_index[start_piece]
            if permanents[start_idx].get("enteredTurn") != turn:
                start_recast = True  # out since an earlier turn: cast it again
            elif not all(other in entry_index and entry_index[other] < start_idx
                         for other in line["pieces"] if other != start_piece):
                continue  # entered this turn before a partner: no restart this turn
        fixed, missing, ready = [], [], True
        for piece, piece_cost in zip(line["pieces"], line["costs"]):
            if piece in battlefield_names:
                if piece in line["castFromHand"]:
                    ready = False  # on the battlefield it is not cast during the combo
                    break
                if piece == start_piece and start_recast:
                    fixed.append(piece_cost)
                continue
            if piece in hand_names:
                fixed.append(piece_cost)
                continue
            missing.append(piece)
        # Each ready piece not out since the turn began takes one of the line's
        # haste sources, chosen with the rest of the assignment (the cheapest
        # payable is kept): a static grant on the battlefield, free and for any
        # number of pieces; an Equipment on the battlefield at its equip, or an
        # instant in the hand at its cost, one piece each. A source an option
        # relies on is no object for an extra cost (leaf_ok: it is a card the
        # assignment uses).
        haste = line["readyHaste"]
        options = []
        for piece in line["readyPieces"] if ready else ():
            if piece in records and records[piece].get("enteredTurn", turn) < turn:
                continue  # on the battlefield since the turn began
            grants = ([{"uses": frozenset(), "card": name, "kinds": (), "cost": combine_mana_costs([])}
                       for name in haste["static"] if name in battlefield_names]
                      + [{"uses": frozenset({name}), "card": name, "kinds": (), "cost": cost}
                         for name, cost in haste["equip"].items() if name in battlefield_names]
                      + [{"uses": frozenset({name}), "card": name, "kinds": (), "cost": cost}
                         for name, cost in haste["instant"].items() if name in hand_names])
            if not grants:
                ready = False  # a piece not ready and nothing to haste it
                break
            options.append(sorted(grants, key=lambda option: option["cost"]["total"]))
        if not ready:
            continue
        if line["extraCost"] is not None:
            fixed.append(line["extraCost"])
        hand_pieces = {piece for piece in line["pieces"]
                       if piece in hand_names and piece not in battlefield_names}
        supplied = []
        for piece in missing:
            piece_options = []
            for delivery in line["deliveries"][piece]:
                card, use = delivery["card"], delivery["use"]
                if card not in hand_names:
                    continue
                if card in hand_pieces:
                    if not use["frontPermanent"]:
                        continue  # an instant or sorcery piece is not also a substitute
                    base = use["abilityCost"]  # its cast is already paid as the piece
                else:
                    base = use["useCost"]
                piece_options.append({"uses": frozenset({card}), "card": card, "kinds": delivery["kinds"],
                                      "cost": combine_mana_costs([base] + delivery["parts"])})
            if not piece_options:
                break
            supplied.append(sorted(piece_options, key=lambda option: option["cost"]["total"]))
        if len(supplied) < len(missing):
            continue
        options += supplied
        if not options:
            costs.append(combine_mana_costs(fixed))
            continue
        line_objects = []

        def leaf_ok(chosen: list[dict], pieces=frozenset(line["pieces"]), line_objects=line_objects,
                    targets=targets, need=line["needsCreature"]) -> bool:
            kinds = [kind for option in chosen for kind in option["kinds"]]
            if not kinds:
                return True
            if not line_objects:
                line_objects.append(extra_cost_objects(permanents, hand, profiles, commander_name, set(pieces)))
            return objects_found(kinds, line_objects[0], {option["card"] for option in chosen},
                                 lambda taken: len(targets - taken) >= need)

        costs.extend(payable_assignments(fixed, options, leaf_ok))
    return costs


def combo_assembled_this_turn(turn: int, hand: list[str], permanents: list[dict],
                              library: list[str], assembly_line: dict, profiles: dict,
                              pool: "GoldfishManaPool", commander_name: str = "") -> bool:
    """Whether every slot of one combo can be filled this turn (DEC-363): one
    of assembly_tutor_cost is payable from ``pool``, the mana still unspent
    this turn after the main-phase casts (DEC-937)."""
    return any(pool.can_cast(cost) for cost in assembly_tutor_cost(
        hand, permanents, library, assembly_line, profiles, commander_name))


def assembly_tutor_cost(hand: list[str], permanents: list[dict], library: list[str],
                        assembly_line: dict, profiles: dict, commander_name: str = "") -> list[dict]:
    """The costs of the tutors that fill a combo's open slots, the cheapest
    of every way to fill them (payable_assignments): ``[nothing]`` when every
    slot is filled, ``[]`` when the slots cannot be filled this turn whatever
    the mana.

    A slot is filled by a drawn member (in hand or on the battlefield, lands
    included); the commander slot fills itself from the command zone. An
    open slot is filled by a tutor in hand, as the line's ``fetches``
    (assembly_fetches) say: one whose tags allow a member still in the
    library, paying the tutor's use and the X paid, never the piece; each
    tutor fills one slot (and each member belongs to one slot only,
    build_combo_assembly_lines). Recursion cards fill none. Extra
    costs each take their own object (extra_cost_objects), and every filled
    slot keeps one drawn member that pays nothing: a member may be sacrificed,
    discarded or bargained, or, as a tutor that is an instant or sorcery,
    cast, only if another drawn member of its slot is left. A member that is
    a permanent tutor stays when cast (B6: it pays its cast).
    """
    slots = assembly_line["slots"]
    drawn = {permanent["name"] for permanent in permanents} | set(hand)
    open_slots = [index for index, slot in enumerate(slots)
                  if not slot["isCommander"] and not any(member in drawn for member in slot["members"])]
    if not open_slots:
        return [combine_mana_costs([])]
    hand_names, library_set = set(hand), set(library)
    options = []
    for index in open_slots:
        slot_options = [{"uses": frozenset({fetch["card"]}), "card": fetch["card"],
                         "use": fetch["use"], "kinds": fetch["kinds"], "cost": fetch["cost"]}
                        for fetch in assembly_line["fetches"][index]
                        if fetch["card"] in hand_names and fetch["member"] in library_set]
        if not slot_options:
            return []
        options.append(sorted(slot_options, key=lambda option: option["cost"]["total"]))
    # The drawn members of each filled slot, as object keys.
    filled = [{("battlefield", i) for i, permanent in enumerate(permanents) if permanent["name"] in slot["members"]}
              | {("hand", i) for i, card in enumerate(hand) if card in slot["members"]}
              for index, slot in enumerate(slots) if not slot["isCommander"] and index not in open_slots]
    line_objects = []

    def leaf_ok(chosen: list[dict]) -> bool:
        spent = {("hand", hand.index(option["card"])) for option in chosen if not option["use"]["frontPermanent"]}
        kinds = [kind for option in chosen for kind in option["kinds"]]
        if kinds and not line_objects:
            line_objects.append(extra_cost_objects(permanents, hand, profiles, commander_name, set()))
        return objects_found(kinds, line_objects[0] if kinds else [], {option["card"] for option in chosen},
                             lambda taken: all(keys - taken - spent for keys in filled))

    return payable_assignments([], options, leaf_ok)


def metrics_from_board(turn: int, permanents: list[dict], profiles: dict, commander_name: str,
                       commander_in_play: bool, cumulative_damage: float,
                       meaningful_threshold: int, combo_ready_ever: bool,
                       extra_combat: float = 0.0, available_mana: int = 0) -> dict:
    """Summarize goldfish board state at end of turn.

    ``extra_combat`` carries damage from sources outside the permanent list
    (the DEC-404 token ledger, which the token makers also feed).
    ``available_mana`` is the mana the pilot could have spent this turn: the
    turn's pool as it was built plus every mana added during the turn
    (GoldfishManaPool.added: cast triggers, sources and lands that came online
    untapped, mana of lands given up or a Saga leaving after it was tapped).
    The board counts (lands, ramp, threats, pressure) are read after the
    turn's end-of-turn actions (land fetches, a Saga leaving).
    """
    lands = sum(1 for permanent in permanents if permanent["kind"] == "land")
    ramp = sum(1 for permanent in permanents if permanent["kind"] == "ramp")
    threats = sum(1 for permanent in permanents if permanent["isThreat"])
    pressure = sum(permanent["impact"] for permanent in permanents if permanent["kind"] != "land")
    combat = extra_combat + sum(
        permanent["combat"] for permanent in permanents
        if permanent["combat"] > 0 and permanent["combatReadyTurn"] <= turn
    )
    meaningful = pressure >= meaningful_threshold or threats >= 2 or (commander_in_play and pressure >= meaningful_threshold - 1)
    return {
        "lands": lands,
        "ramp": ramp,
        "threats": threats,
        "availableMana": available_mana,
        "pressure": pressure,
        "combat": combat,
        "cumulativeDamage": cumulative_damage,
        "commanderCast": 1 if commander_in_play else 0,
        "firstThreat": 1 if threats > 0 else 0,
        "meaningfulBoard": 1 if meaningful else 0,
        "lethalProxy": 1 if cumulative_damage >= GOLDFISH_LETHAL_DAMAGE_PROXY else 0,
        "comboLethal": 1 if combo_ready_ever else 0,
    }


def put_land_onto_battlefield(land_name: str, turn: int, tapped: bool, permanents: list[dict],
                              battlefield_lands: list[dict], profiles: dict,
                              commander_colors: list[str], played: bool = True) -> dict:
    """Record a land entering the goldfish battlefield and return its record.

    A card with two land faces (a Pathway) played from the hand enters as the
    face that adds a commander colour not yet among the lands, the front on a
    tie (M6); put onto the battlefield (``played=False``: a land search, a
    fetch land's crack) it enters front face up. A
    Saga's mana lasts its ``manaTurns``; then it leaves (leave_battlefield).
    A land that enters tapped is tapped until the next untap step (one
    state for every own-{T} check). The record carries the land's one-shot
    and on-cast mana too.
    """
    profile = profiles[land_name]
    atoms = profile["manaAtoms"]
    if profile["landFaces"] and not played:
        atoms = profile["landFaces"][0]
    elif profile["landFaces"]:
        present = set().union(*(land["colors"] for land in battlefield_lands))
        front = profile["landFaces"][0]
        atoms = max(profile["landFaces"], key=lambda face: (
            len((set().union(*face) & set(commander_colors)) - present), face is front))
    record = {
        "name": land_name,
        "kind": "land",
        "manaAtoms": atoms,
        "manaOnce": profile["manaOnce"],
        "manaBoard": profile["manaBoard"],
        "manaOnCast": profile["manaOnCast"],
        # A land creature (Dryad Arbor) is summoning sick: untapped, but its
        # {T} mana comes from the next turn.
        "manaActiveTurn": turn + (1 if tapped or "Creature" in profile["typeWords"] else 0),
        "combatReadyTurn": 99,
        "impact": 0,
        "combat": 0,
        "isThreat": False,
        "tapped": tapped,
    }
    if profile["manaTurns"] is not None:
        record["manaLastTurn"] = turn + profile["manaTurns"] - 1
    permanents.append(record)
    battlefield_lands.append({
        "name": land_name,
        "colors": set().union(*atoms) if profile["landFaces"] else land_colors(profile),
        "isBasic": profile["isBasic"],
    })
    return record


def leave_battlefield(record: dict, permanents: list[dict], battlefield_lands: list[dict]) -> None:
    """A permanent leaves the battlefield: its record and, for a land, its
    entry in ``battlefield_lands``, so every later reading of the turn (land
    counts, conditions, board terms) no longer sees it."""
    permanents[:] = [p for p in permanents if p is not record]
    if record["kind"] == "land":
        battlefield_lands.pop(next(i for i, land in enumerate(battlefield_lands)
                                   if land["name"] == record["name"]))


def fetch_lands(search: dict, count: int, turn: int, pool: "GoldfishManaPool",
                library: list[str], hand: list[str], permanents: list[dict], battlefield_lands: list[dict],
                profiles: dict, commander_colors: list[str]) -> int:
    """Put `count` lands a land search finds onto the battlefield (M8); a land
    enters tapped when the search or the land's own text says so, read
    against the cards in ``hand`` (a Snarl's reveal), and front face up (a
    Pathway); the lands are chosen by that state and that face. Each gives
    up the lands its entry takes as a land that is played does (Simic Growth
    Chamber returns one to ``hand``; give_up_lands: the mana of a land tapped
    first and not yet used this turn floats). The pool is read from the
    board again (refresh_pool: an untapped land's mana joins this turn's
    pool, with the extras and grants already out). Returns how many
    entered."""
    def enters_tapped(land_name: str) -> bool:
        return search["entersTapped"] or land_enters_tapped(
            profiles[land_name]["landEntry"], battlefield_lands, permanents, profiles, hand)

    fetched = select_ramp_targets(library, profiles, commander_colors, battlefield_lands,
                                  permanents, search, count, tapped_test=enters_tapped, to_hand=False)
    for land_name in fetched:
        if profiles[land_name]["landEntryCost"]:
            # Their unused mana is already in the pool (and in availableMana):
            # it stays, floating, as they leave.
            pool.sources.extend(floated(atom) for atom in give_up_lands(
                profiles[land_name]["landEntryCost"], turn, hand, permanents, battlefield_lands, profiles)
                if atom_source_id(atom) not in pool.tapped)
        put_land_onto_battlefield(land_name, turn, enters_tapped(land_name), permanents, battlefield_lands,
                                  profiles, commander_colors, played=False)
    refresh_pool(pool, permanents, profiles, turn)
    return len(fetched)


def crack_fetch_land(name: str, turn: int, library: list[str], hand: list[str],
                     permanents: list[dict], battlefield_lands: list[dict], profiles: dict,
                     commander_colors: list[str]) -> dict:
    """Play a fetch land and crack it at once (M6): the legal land it finds
    leaves the library and enters with its own types, colours and entry rule
    (crack_target_tapped); the fetch land is sacrificed. With nothing legal
    left in the library the fetch land stays on the battlefield and makes
    nothing. Returns the record of the land now on the battlefield."""
    target, tapped = crack_target(name, library, profiles, commander_colors, battlefield_lands,
                                  permanents, hand, take=True)
    if target is None:
        return put_land_onto_battlefield(name, turn, False, permanents, battlefield_lands, profiles,
                                         commander_colors)
    return put_land_onto_battlefield(target, turn, tapped, permanents, battlefield_lands, profiles,
                                     commander_colors, played=False)


def resolve_cast_effects(name: str, profile: dict, turn: int, pool: "GoldfishManaPool",
                         library: list[str], hand: list[str], permanents: list[dict],
                         battlefield_lands: list[dict], profiles: dict,
                         commander_colors: list[str]) -> None:
    """Apply the on-resolution effects of a cast spell (ramp fetch, board record, draw).

    Shared by the paid main-phase cast path and the cascade free-cast path (DEC-385)
    so both credit identical board impact.
    """
    if profile["landRamp"]:
        ramp = profile["landRamp"]
        fetch_lands(ramp, ramp["count"], turn, pool, library, hand, permanents, battlefield_lands,
                    profiles, commander_colors)
        # Lands put into the hand are played later: either face counts.
        hand.extend(select_ramp_targets(library, profiles, commander_colors, battlefield_lands,
                                        permanents, ramp, ramp["toHand"], to_hand=True))

    if profile["isPermanent"]:
        record = {
            "name": name,
            "kind": "ramp" if is_mana_source(profile) else "spell",
            "manaAtoms": profile["manaAtoms"],
            "manaOnce": profile["manaOnce"],
            "manaBoard": profile["manaBoard"],
            "manaOnCast": profile["manaOnCast"],
            "manaActiveTurn": turn + (profile["manaSourceDelay"] or 0),
            "combatReadyTurn": turn + (1 if profile["combat"] > 0 else 99),
            "impact": profile["impact"],
            "combat": profile["combat"],
            "isThreat": profile["isThreat"],
            "enteredTurn": turn,
            # Tapped until the next untap step: it enters tapped (Nevinyrral's
            # Disk), or its {T} draw is activated the turn it enters (The One
            # Ring, CAST_TURN_ACTIVATION_DRAW).
            "tapped": bool(profile.get("entersTapped")
                           or (profile.get("drawTapsSelf") and CAST_TURN_ACTIVATION_DRAW.get(name))),
        }
        if profile["manaTurns"] is not None:
            record["manaLastTurn"] = turn + profile["manaTurns"] - 1
        permanents.append(record)

    for _ in range(profile["immediateDraw"]):
        if library:
            hand.append(library.pop())
    # The pool is read from the board again (refresh_pool, invariant I1): a
    # permanent whose mana comes online this turn adds it, as its text gives
    # it on the battlefield it enters (Urza: his Construct, and a {U} for each
    # idle artifact), with the extras and grants already out; a grant or
    # trigger source entering changes the untapped sources' mana.
    refresh_pool(pool, permanents, profiles, turn)


def count_creature_permanents(permanents: list[dict], profiles: dict) -> int:
    """Creature cards on the goldfish battlefield (commander included)."""
    return sum(1 for permanent in permanents if "Creature" in profiles[permanent["name"]]["typeLine"])


def copy_engine_copy_count(copy_engine: dict, profile: dict, creature_count: int,
                           gate_uses: int) -> int:
    """Copies the commander's copy-trigger engine produces for one cast (DEC-393).

    ``creature_count`` is battlefield creatures + the token ledger at trigger
    time (before the spell itself resolves — a token-maker can't feed its own
    trigger). tap_gate uses tap ``tapCost`` creatures for the rest of the turn,
    so ``gate_uses`` throttles repeat casts; summoning sickness doesn't block
    the gate (tapping via an effect is not a {T} cost).
    """
    if copy_engine["mode"] == "per_other_creature":
        if not profile["targetsOnlyCreature"]:
            return 0
        return max(0, creature_count - 1)
    if copy_engine["mode"] == "tap_gate":
        untapped = creature_count - copy_engine["tapCost"] * gate_uses
        return 1 if untapped >= copy_engine["tapCost"] else 0
    return 0


def deploy_engine_choice(deploy_engine: dict, hand: list[str], profiles: dict,
                         attached: set[str]) -> str | None:
    """Pick the artifact to free-deploy at combat (DEC-405).

    Scores each artifact in hand: an Equipment by its attach bonus in the
    table (0 when the table does not list it; one listed in the table's
    doubleStrikeNames, while none of those is attached, adds the commander's
    whole current swing to its bonus, since it doubles it; an Equipment that
    grants double strike but is not listed there, such as Genji Glove, scores
    0 and loses to The Reaver Cleaver's 1), an
    artifact creature by its combat score, another artifact by its impact
    (pressure) score, which adds no combat damage: Nexus of Becoming (8) is
    chosen over Kaldra Compleat (bonus 5), though Kaldra would add 5 to the
    commander's damage. The highest score wins; ties
    go to the higher mana value, so the deploy leans toward the biggest mana
    cheat, then to the name later in alphabetical order. An Equipment's own
    pressure score plays no part in the choice; it applies once the
    Equipment is on the battlefield.

    The caller passes the hand without the reserved cards (reservedPieces,
    in a deck with a combo or KEY_COMBOS line: the line pieces kept in the
    hand, a Walking Ballista, and the tutor and recursion cards), which stay
    in the hand, where the combo checks read the ones that can supply a
    piece (Wishclaw Talisman).
    """
    equipment_power = deploy_engine["equipmentPower"]
    ds_names = deploy_engine["doubleStrikeNames"]
    has_ds = bool(attached & ds_names)
    attach_sum = sum(equipment_power.get(n, 0) for n in attached)
    best_name = None
    best_score = None
    for name in ordered_unique(hand):
        profile = profiles[name]
        if profile["isLand"] or "Artifact" not in profile["typeLine"]:
            continue
        if "Equipment" in profile["typeLine"]:
            gain = equipment_power.get(name, 0)
            if name in ds_names and not has_ds:
                gain += deploy_engine["transformedPower"] + attach_sum
        elif "Creature" in profile["typeLine"]:
            gain = profile["combat"]
        else:
            gain = profile["impact"]
        score = (gain, profile["cmc"], name)
        if best_score is None or score > best_score:
            best_score = score
            best_name = name
    return best_name


def spell_qualifies_for_cascade(profile: dict, cascade: dict) -> bool:
    """Whether a cast spell triggers the commander-granted cascade model (DEC-385)."""
    if profile["cmc"] < cascade["minValue"]:
        return False
    if cascade.get("colorlessOnly") and not profile["isColorless"]:
        return False
    return True


def resolve_cascade_triggers(spell_profile: dict, cascade: dict, turn: int,
                             pool: "GoldfishManaPool", library: list[str], hand: list[str],
                             permanents: list[dict], battlefield_lands: list[dict],
                             profiles: dict, commander_colors: list[str],
                             reserved_pieces: set[str], context: dict | None = None,
                             commander_in_play: bool = True) -> None:
    """Resolve commander-granted cascade off a qualifying cast (DEC-385).

    Each trigger digs the library top-down: the first nonland card with lesser
    mana value, read as the card is in the library (its front face: a modal
    DFC whose front is a spell is a nonland card there), is free-cast via
    ``resolve_cast_effects``; the cards dug past it go to the bottom (library
    order is already random, so no reshuffle needed). "May cast" is declined
    for a card held back as interaction (goldfish_holds_back), for a
    combo-line or assembly piece the goldfish keeps in the hand
    (handOnlyPieces: one whose front face is not a permanent, or one with {X}
    in its cost, decision C: a free cast pays X = 0), for a reserved tutor or
    recursion card whose front face is not a permanent, for a card the
    goldfish plays as its land face (it does not cast the spell face) and for
    a Chrome Mox with no card in hand to imprint (can_imprint_from_hand) —
    those are bottomed instead; a cascaded Mox imprints as a paid one does
    (imprint_on_entry).
    With ``fromHandOnly`` (Zhulodok-style grants) free-casts never re-trigger;
    without it, qualifying free-casts recurse, bounded because every hit costs
    strictly less than its parent.
    """
    for _ in range(cascade["triggers"]):
        exiled = []
        hit = None
        while library:
            card = library.pop()
            if not profiles[card]["libraryLand"] and profiles[card]["cmc"] < spell_profile["cmc"]:
                hit = card
                break
            exiled.append(card)
        library[:0] = exiled
        if hit is None:
            return
        hit_profile = profiles[hit]
        imprints = context is not None and hit_profile["imprint"] and not hit_profile["isLand"]
        hand_only = context["handOnlyPieces"] if context is not None else frozenset()
        if (hit_profile["isInteraction"] or hit in hand_only or hit_profile["isLand"]
                or (hit in reserved_pieces and not is_front_permanent(hit_profile))
                or (imprints and not can_imprint_from_hand(hit, hit_profile, hand, profiles, context,
                                                           commander_in_play))):
            library.insert(0, hit)
            continue
        resolve_cast_effects(hit, hit_profile, turn, pool, library, hand, permanents,
                             battlefield_lands, profiles, commander_colors)
        if imprints:
            imprint_on_entry(hit, hit_profile, turn, pool, hand, permanents, profiles, context,
                             commander_in_play)
        if not cascade.get("fromHandOnly") and spell_qualifies_for_cascade(hit_profile, cascade):
            resolve_cascade_triggers(hit_profile, cascade, turn, pool, library, hand,
                                     permanents, battlefield_lands, profiles,
                                     commander_colors, reserved_pieces, context, commander_in_play)


def set_entry_ready_turn(permanents: list[dict], name: str, ready_turn: int) -> None:
    """Pull a just-entered creature's combat readiness forward (DEC-938).

    Finds the most recently appended record with this name and lowers its
    ``combatReadyTurn``; non-combat permanents (``combat`` 0) are left alone.
    """
    for permanent in reversed(permanents):
        if permanent["name"] != name:
            continue
        if permanent["combat"] > 0:
            permanent["combatReadyTurn"] = min(permanent["combatReadyTurn"], ready_turn)
        return


def static_haste_active(haste_sources: dict, permanents: list[dict]) -> bool:
    """Whether a continuous team-haste grant is on the battlefield (DEC-938).

    Static grants ("Creatures you control have haste") also cover creatures that
    were already on the battlefield when the source landed, so a permanent that
    needs to be unsick *this* turn can read them live.
    """
    names = {permanent["name"] for permanent in permanents}
    if haste_sources["staticNames"] & names:
        return True
    return any(set(pair) <= names for pair in haste_sources["staticPairs"])


def team_haste_active(haste_sources: dict, permanents: list[dict]) -> bool:
    """Whether any team-haste source covers a creature entering now (DEC-938).

    Entry-gated sources (Rhythm of the Wild's riot) count here but not in
    ``static_haste_active`` — riot applies only as the creature enters.
    """
    if static_haste_active(haste_sources, permanents):
        return True
    names = {permanent["name"] for permanent in permanents}
    return bool(haste_sources["entryGatedNames"] & names)


def hatch_from_library(turn: int, pool: "GoldfishManaPool", library: list[str],
                       hand: list[str], permanents: list[dict],
                       battlefield_lands: list[dict], profiles: dict,
                       commander_colors: list[str],
                       ready_turn: int | None = None) -> str | None:
    """Put the top creature card of the library onto the battlefield free (DEC-938).

    The DEC-385 cascade dig without the mana-value filter: reveal from the top
    until a creature card is found, resolve it through the DEC-405 free
    put-onto-battlefield path (``resolve_cast_effects``, so it credits impact,
    combat and draw exactly like a cast) and bottom the cards revealed past it.
    A put is not a cast, so it never re-triggers a cast-gated model. Returns the
    hatched card name, or ``None`` when the library holds no creature card.

    Deliberately free of deck-specific names so other reveal-and-put engines
    (e.g. Eladamri, Korvecdal) can reuse it from their own config block.
    """
    passed = []
    hit = None
    while library:
        card = library.pop()
        if "Creature" in profiles[card]["typeLine"]:
            hit = card
            break
        passed.append(card)
    library[:0] = passed
    if hit is None:
        return None
    resolve_cast_effects(hit, profiles[hit], turn, pool, library, hand, permanents,
                         battlefield_lands, profiles, commander_colors)
    if ready_turn is not None:
        set_entry_ready_turn(permanents, hit, ready_turn)
    return hit


def hatch_egg_multiplier(hatch_engine: dict, permanents: list[dict]) -> int:
    """Token-doubling multiplier applied to every Egg created (DEC-938)."""
    names = {permanent["name"] for permanent in permanents}
    return 2 ** len(hatch_engine["tokenDoublerNames"] & names)


def hatch_entry_eggs(hatch_engine: dict, name: str, permanents: list[dict]) -> int:
    """Eggs a just-entered permanent creates (DEC-938).

    Palani's Hatcher's "create two Egg tokens" ETB; Elesh Norn doubles the
    trigger itself (two triggers, two Eggs each) and the token doublers then
    multiply the tokens.
    """
    base = hatch_engine["entryEggNames"].get(name, 0)
    if not base:
        return 0
    names = {permanent["name"] for permanent in permanents}
    if hatch_engine["entryEggDoublerName"] in names:
        base *= 2
    return base * hatch_egg_multiplier(hatch_engine, permanents)


def settle_tapped(pool: "GoldfishManaPool", before: "GoldfishManaPool", permanents: list[dict],
                  battlefield_lands: list[dict], profiles: dict) -> "GoldfishManaPool":
    """Record on each permanent what one payment did (R1: one tapped state
    per permanent per turn), reading only the sources it newly used (the
    payment's pool less ``before``, the pool it was made from): a source
    whose own {T} paid (``tapping``: a {T} mana ability, an artifact Urza
    tapped for {U}; not Urza himself) is tapped, except a vigilant creature
    (M9: it attacks first and taps for mana after combat); a one-shot source
    (Mana Vault, Basalt Monolith, Lotus Petal) is spent, and one that
    sacrifices itself for its mana leaves the battlefield at once (its mana
    stays in the pool). Returns the pool."""
    newly_used = pool.tapped - before.tapped
    newly_tapping = pool.tapping - before.tapping
    for record in list(permanents):
        if id(record) in newly_tapping:
            profile = profiles[record["name"]]
            if not (profile["vigilance"] and "Creature" in profile["typeWords"]):
                record["tapped"] = True
        if id(record) not in newly_used:
            continue
        if record.get("manaOnce") and not record["manaAtoms"] and not record.get("onceSpent"):
            record["onceSpent"] = True
            if profiles[record["name"]]["onceLeaves"]:
                leave_battlefield(record, permanents, battlefield_lands)
    return pool


def find_payment(pool: "GoldfishManaPool", cost: dict, keep=(), strict: bool = True,
                 taps: dict | None = None) -> "GoldfishManaPool | None":
    """The pool a payment of ``cost`` leaves (GoldfishManaPool.pay), or None.

    ``keep``: the requirements the payment must leave payable (the turn's
    held activation and reachable gates, checked jointly with it); with
    ``strict`` False a cast that is never held back (the commander, a line
    piece, a mana source) takes the preferred payment when none keeps them.
    ``taps``: the permanent whose own {T} is part of the cost (Castle
    Ardenvale, Myriad Landscape, High Market, the hatch commander): it must
    be untapped, and its own mana cannot pay (it is tapped for the
    ability)."""
    if taps is not None:
        if taps.get("tapped"):
            return None
        pool = pool.without(lambda atom: getattr(atom, "source", None) is not taps)
    paid = pool.pay(cost, keep)
    if paid is None and keep and not strict:
        paid = pool.pay(cost)
    return paid


def spend_mana(pool: "GoldfishManaPool", cost: dict, permanents: list[dict],
               battlefield_lands: list[dict], profiles: dict, keep=(), strict: bool = True,
               taps: dict | None = None,
               paid: "GoldfishManaPool | None" = None) -> "GoldfishManaPool | None":
    """Every spend of the turn's mana (casts, X, activations, the end of the
    turn's untaps and land fetches): finds the payment (find_payment, or
    ``paid``, the payment find_payment already found for this same cost),
    commits that same payment and settles it before the next one
    (settle_tapped: exactly the permanents whose own {T} paid are tapped;
    ``taps`` is tapped for its ability). Returns the pool left, or None
    (nothing changes) when the cost cannot be paid."""
    if paid is None:
        paid = find_payment(pool, cost, keep, strict, taps)
    if paid is None:
        return None
    settle_tapped(paid, pool, permanents, battlefield_lands, profiles)
    if taps is not None:
        taps["tapped"] = True
    return paid


def rearm_once_sources(permanents: list[dict], pool: "GoldfishManaPool", battlefield_lands: list[dict],
                       profiles: dict) -> "GoldfishManaPool":
    """A spent one-shot source with its own "{N}: Untap this" (Basalt
    Monolith), spent this turn or an earlier one, is untapped at the end of
    the turn with N of the lasting mana the turn left (M3), each payment
    settled before the next (spend_mana). Returns the pool left."""
    for permanent in list(permanents):
        cost = profiles[permanent["name"]]["onceRearm"]
        if cost is None or not permanent.get("onceSpent"):
            continue
        left = spend_mana(pool, cost, permanents, battlefield_lands, profiles)
        if left is not None:
            pool = left
            permanent["onceSpent"] = False
            permanent["tapped"] = False
    return pool


def give_up_lands(cost: dict, turn: int, hand: list[str], permanents: list[dict],
                  battlefield_lands: list[dict], profiles: dict) -> list:
    """Give up the lands a land takes as it enters (``landEntryCost``, M6):
    the least mana first. They leave at once, so every condition the land
    reads as it enters, and every later one, counts fewer lands. Lands
    sacrificed "instead" of entering (Scorched Ruins) go untapped; lands an
    entering trigger takes (Lotus Field, Simic Growth Chamber) are tapped in
    response first, and that mana is returned for this turn's pool. A land
    returned to the hand (Growth Chamber) can be played again."""
    lands = [p for p in permanents if p["kind"] == "land" and p["manaActiveTurn"] <= turn]
    chosen = sorted(lands, key=lambda p: (
        len(p["manaAtoms"]) + len(p.get("manaBoard", ())),
        len(frozenset().union(*p["manaAtoms"])) if p["manaAtoms"] else 0, p["name"]))[:cost["count"]]
    gone = {id(p) for p in chosen}
    floating = [] if cost["now"] else [
        atom for atom in board_mana(permanents, turn, profiles)
        if id(atom.source) in gone and not atom.once]
    for record in chosen:
        leave_battlefield(record, permanents, battlefield_lands)
        if cost["toHand"]:
            hand.append(record["name"])
    return floating


def imprint_choice(profile: dict, hand: list[str], profiles: dict, context: dict,
                   commander_in_play: bool) -> str | None:
    """The card an imprint would exile from ``hand`` (imprint_from_hand), or
    None when no card can be exiled for it."""
    rule = profile["imprint"]

    def eligible(card: str) -> bool:
        card_profile = profiles[card]
        front = card_profile["typeLine"].split(" // ")[0]
        return not (card_profile["isLand"] or "Land" in front or card in context["imprintKeep"]
                    or (rule.get("colorless") and not card_profile["isColorless"])
                    or (rule.get("nonartifact") and "Artifact" in front)
                    or card_profile["cmc"] < rule.get("minValue", 0)
                    or (rule["atoms"] is None and not card_profile["colors"]))

    cards = [card for card in ordered_unique(hand) if eligible(card)]
    # Never cast from the hand, so exiled first, ranked together: a card held
    # back as interaction, and an alternative a combo line or a table slot
    # keeps in the hand and no line names plainly (heldAlternatives, decision
    # 6b: no imprint protection).
    idle = [card for card in cards if (profiles[card]["isInteraction"] and card not in context["reservedPieces"])
            or card in context["heldAlternatives"]]
    castable = [card for card in cards if not goldfish_never_casts(card, profiles[card], context)]
    if idle:
        return max(idle, key=lambda c: (len(profiles[c]["colors"]), profiles[c]["cmc"], c))
    if castable:
        return max(castable, key=lambda c: (
            proactive_cast_priority(c, profiles[c], context["commanderName"], commander_in_play,
                                    context["lineMembers"])[:-1], profiles[c]["cmc"], c))
    return None


def imprint_from_hand(record: dict, profile: dict, hand: list[str], profiles: dict,
                      context: dict, commander_in_play: bool) -> str | None:
    """Imprint as the permanent enters (owner-approved 2026-11-19): exile the
    eligible card from the hand that the goldfish gets least from and set the
    permanent's mana. Ugin's Labyrinth: a colourless card with mana value 7
    or greater, then {C}{C} instead of {C}. Chrome Mox: a nonartifact,
    nonland card, then one mana of its colours (a colourless one gives
    nothing, so it is never chosen); with no such card the Mox gives nothing.

    The card chosen is one held back as interaction (goldfish_holds_back) or
    an alternative a combo line or a table slot keeps in the hand and no line
    names plainly (``heldAlternatives``, owner decision 27, 6b), ranked
    together ahead of the castable cards (both are never cast; the most
    colours, then the highest mana value, then the name latest in the alphabet, goes first), if the
    hand has any, else the castable card last in its own cast order (ties:
    the higher mana value). Never exiled, in every deck: tutor and
    recursion cards (by their roles), every combo-line and assembly-line
    member (``imprintKeep``), the other reserved combo pieces and the deploy
    engine's Equipment; nor a land (a Pathway included) or a modal card with a spell
    front and a land back, played as its land or kept in the hand as a line
    piece (handOnlyPieces). A transforming card with a land back (Growing
    Rites of Itlimoc, an enchantment on its front) can be exiled. Returns the
    card exiled, or None.
    """
    card = imprint_choice(profile, hand, profiles, context, commander_in_play)
    if card is None:
        return None
    hand.remove(card)
    rule = profile["imprint"]
    record["manaAtoms"] = (list(rule["atoms"]) if rule["atoms"] is not None
                           else [frozenset(profiles[card]["colors"])])
    return card


def can_imprint_from_hand(name: str, profile: dict, hand: list[str], profiles: dict, context: dict,
                          commander_in_play: bool) -> bool:
    """Whether a cast of a non-land permanent whose mana an imprint sets
    (Chrome Mox: nothing without one) has a card in hand to exile, besides
    the card itself: the paid cast and a cascade's free cast are declined
    without one."""
    if not profile["imprint"] or profile["isLand"] or profile["imprint"]["atoms"] is not None:
        return True
    rest = list(hand)
    if name in rest:
        rest.remove(name)
    return imprint_choice(profile, rest, profiles, context, commander_in_play) is not None


def imprint_on_entry(name: str, profile: dict, turn: int, pool: "GoldfishManaPool", hand: list[str],
                     permanents: list[dict], profiles: dict, context: dict,
                     commander_in_play: bool) -> None:
    """A cast non-land imprint permanent (Chrome Mox) as it enters, paid or
    cascaded: the card it exiles from the hand sets its mana, usable at once
    (it is an artifact). A put that is not a cast (a hatch, the deploy
    engine) imprints nothing: a floor."""
    if not profile["imprint"] or profile["isLand"]:
        return
    record = next(p for p in reversed(permanents) if p["name"] == name)
    imprint_from_hand(record, profile, hand, profiles, context, commander_in_play)
    refresh_pool(pool, permanents, profiles, turn)


def land_fetch_payment(permanent: dict, turn: int, pool: "GoldfishManaPool", library: list[str],
                       permanents: list[dict], battlefield_lands: list[dict], profiles: dict,
                       commander_colors: list[str], keep=()) -> "GoldfishManaPool | None":
    """The payment of a land-fetching permanent's activation out of ``pool``
    (find_payment, leaving ``keep`` payable), or None when it cannot be
    activated: a creature's own {T} ability is summoning sick the turn it
    enters (Embodiment of Spring; a fetch without {T} is not: Sakura-Tribe
    Elder), the search must put more lands onto the battlefield than it takes
    away, and with {T} in the cost the permanent must be untapped and its own
    mana cannot pay. activate_land_fetches pays it; the attack declaration
    keeps a fetch creature home by the same test (fetches_instead)."""
    search = profiles[permanent["name"]]["landFetch"]
    if (search["tapsSelf"] and "Creature" in profiles[permanent["name"]]["typeWords"]
            and permanent.get("enteredTurn") == turn):
        return None
    found = len(select_ramp_targets(list(library), profiles, commander_colors, battlefield_lands,
                                    permanents, search, search["count"], to_hand=False))
    if found - (1 if permanent["kind"] == "land" else 0) < 1:
        return None
    return find_payment(pool, search["cost"], keep, taps=permanent if search["tapsSelf"] else None)


def activate_land_fetches(turn: int, pool: "GoldfishManaPool", library: list[str], hand: list[str],
                          permanents: list[dict], battlefield_lands: list[dict], profiles: dict,
                          commander_colors: list[str]) -> "GoldfishManaPool":
    """Land-fetching permanents (M8): Wayfarer's Bauble, Sakura-Tribe Elder,
    Myriad Landscape. Each is sacrificed at the end of the turn when ``pool``
    (the mana the turn left) pays its cost and it puts more lands onto the
    battlefield than it takes away; one whose cost has {T} must be untapped
    (a creature also not summoning sick), and its own mana cannot pay
    (spend_mana ``taps``). Each payment is settled before the next: a land
    that paid the Bauble is tapped and cannot pay its own {T}. The lands
    enter as the search says. Returns the pool left."""
    for permanent in list(permanents):
        search = profiles[permanent["name"]]["landFetch"]
        if search is None or not any(p is permanent for p in permanents):
            continue
        refresh_pool(pool, permanents, profiles, turn)
        paid = land_fetch_payment(permanent, turn, pool, library, permanents, battlefield_lands, profiles,
                                  commander_colors)
        if paid is None:
            continue
        pool = spend_mana(pool, search["cost"], permanents, battlefield_lands, profiles,
                          taps=permanent if search["tapsSelf"] else None, paid=paid)
        leave_battlefield(permanent, permanents, battlefield_lands)
        fetch_lands(search, search["count"], turn, pool, library, hand, permanents, battlefield_lands,
                    profiles, commander_colors)
    return pool


def simulate_goldfish_game(decklist: list[str], context: dict,
                           meaningful_threshold: int) -> dict:
    """Simulate one solitaire game with heuristic sequencing."""
    profiles = context["profiles"]
    commander_name = context["commanderName"]
    commander_colors = context["commanderColors"]
    combo_lines = context.get("comboLines", [])
    assembly_lines = context.get("assemblyLines", [])

    cascade = context.get("cascade")
    copy_engine = context.get("copyEngine")
    token_engine = context.get("tokenEngine")
    deploy_engine = context.get("deployEngine")
    draw_engines = context.get("drawEngines")
    amass_engine = context.get("amassEngine")
    hatch_engine = context.get("hatchEngine")
    token_makers = context.get("tokenMakers")
    haste_sources = context.get("hasteSources")
    combat_modifiers = context.get("combatModifiers")
    # DEC-472 activated-draw bookkeeping: activations so far per engine name.
    # The cast-turn activation is credited by immediateDraw, so it seeds at 1.
    draw_engine_activations: dict[str, int] = {}
    library, hand = commander_mulligan_goldfish(decklist, profiles, commander_colors, context["mulliganKeep"],
                                                context["handOnlyPieces"])
    permanents = []
    battlefield_lands = []
    commander_in_play = False
    commander_play_turn = None
    cumulative_damage = 0.0
    # DEC-393 copy-engine bookkeeping: stat-less creature-token ledger (feeds
    # engine gates only) and per-turn tap_gate usage.
    token_creatures = 0
    copy_gate_uses = 0
    # DEC-404 token-swarm ledger: tokens minted this turn are summoning-sick;
    # they migrate to the ready pool at the start of the next turn.
    swarm_tokens_ready = 0
    swarm_tokens_new = 0
    # TOKEN_MAKER_ENGINE bookkeeping beside that ledger: the Food on the
    # battlefield, the Food that entered tapped this turn, and the +1/+1
    # counters on each growing attack maker.
    food_tokens = 0
    food_entered_tapped = 0
    attack_maker_counters: dict[str, int] = {}

    def make_tokens(creatures: int, food: int, attacking: bool = False) -> None:
        """One TOKEN_MAKER_ENGINE creation event of creature tokens and Food.

        extraFoodName adds one Food; under artifactTokensReplacedBy the Food
        would be creatures the engine does not credit, so none is credited;
        then each doubler doubles every token. Tokens made tapped and
        attacking join the ready pool (they deal damage this turn); the Food
        made with them enters tapped.
        """
        nonlocal swarm_tokens_ready, swarm_tokens_new, food_tokens, food_entered_tapped
        if token_makers is None or creatures + food <= 0:
            return
        board = {permanent["name"] for permanent in permanents}
        if token_makers["extraFoodName"] in board:
            food += 1
        if token_makers["artifactTokensReplacedBy"] in board:
            food = 0
        multiplier = 2 ** len(token_makers["doublerNames"] & board)
        creatures *= multiplier
        food *= multiplier
        if attacking:
            swarm_tokens_ready += creatures
            food_entered_tapped += food
        else:
            swarm_tokens_new += creatures
        food_tokens += food
    # DEC-533 amass-Army ledger: one Army creature as a counter total. The
    # Army is combat-ready the turn after it was first created (the same turn
    # when the start-of-turn opponent-cast amass created it); amassing onto
    # an existing Army never resets readiness. amass_perm_entry records when a
    # repeatable amass permanent landed (its trigger starts the next turn).
    army_counters = 0
    army_ready_turn = None
    amass_perm_entry: dict[str, int] = {}
    amass_ping_damage = 0.0

    def apply_amass(n: int, current_turn: int, ready_turn: int | None = None) -> None:
        """Credit one amass batch of n counters (Mauhur adds 1 per batch).

        An Army this batch creates can attack from `ready_turn`, by default
        the turn after `current_turn` (summoning sickness).
        """
        nonlocal army_counters, army_ready_turn, amass_ping_damage
        if amass_engine is None or n <= 0:
            return
        names_on_board = {permanent["name"] for permanent in permanents}
        if amass_engine["batchBonusName"] in names_on_board:
            n += 1
        if army_ready_turn is None:
            army_ready_turn = current_turn + 1 if ready_turn is None else ready_turn
        army_counters += n
        if amass_engine["batchDamageName"] in names_on_board:
            amass_ping_damage += amass_engine["batchDamage"]
    # DEC-938 hatch-engine bookkeeping: Eggs are a counter (they have no power
    # and never block in a goldfish), carried across turns until an outlet eats
    # them. Two counters, because Skullclamp's +1/-1 only kills the 0/1 Eggs the
    # commander and Palani's Hatcher make — Nesting Dragon's Dragon Egg is 0/2
    # and survives the equip as a 1/1, so those sit in `tough_eggs_on_board` and
    # only the free/limited sacrifice outlets eat them. `landfall_entry` records
    # when a per-land-drop Egg maker landed (its trigger starts the next turn)
    # and `untapper_attached` locks in whether the Staff was already on the
    # battlefield when the commander entered.
    eggs_on_board = 0
    tough_eggs_on_board = 0
    landfall_entry: dict[str, int] = {}
    untapper_attached = False

    def on_permanent_entered(name: str, current_turn: int) -> None:
        """Post-entry bookkeeping for the hatch engine and team-haste rule."""
        nonlocal eggs_on_board
        if haste_sources is not None:
            if (name in haste_sources["printedHasteNames"]
                    or team_haste_active(haste_sources, permanents)):
                set_entry_ready_turn(permanents, name, current_turn)
        if hatch_engine is None:
            return
        eggs_on_board += hatch_entry_eggs(hatch_engine, name, permanents)
        if name in hatch_engine["landfallEggNames"]:
            landfall_entry.setdefault(name, current_turn)
    # DEC-940 — hatch budget and the hatch runner live at turn scope so the
    # combat-phase loop can fire the per-combat hatch triggers again at each
    # extra combat. Reset at the top of each turn's hatch block.
    hatches_left = 0

    def mark_combat_entry(name: str, phase_index: int) -> None:
        """Record which combat phase a creature entered during (DEC-940).

        Xenagos cannot target a creature that was not on the battlefield when
        its beginning-of-combat trigger went on the stack, and Zopandrel's
        doubling only compounds over the triggers a creature was present for.
        """
        for permanent in reversed(permanents):
            if permanent["name"] == name:
                permanent["combatEntryPhase"] = phase_index
                return

    def run_hatches(count: int, ready_turn: int | None,
                    combat_phase: int | None = None) -> None:
        """Resolve `count` hatches (capped), applying entry bookkeeping."""
        nonlocal hatches_left
        for _ in range(count):
            if hatches_left <= 0:
                return
            hatched = hatch_from_library(
                turn, pool, library, hand, permanents, battlefield_lands,
                profiles, commander_colors, ready_turn=ready_turn)
            hatches_left -= 1
            if hatched is None:
                return
            on_permanent_entered(hatched, turn)
            if combat_phase is not None:
                mark_combat_entry(hatched, combat_phase)

    def run_combat_phase_hatches(phase_index: int) -> None:
        """Per-combat hatch triggers at an extra combat's beginning of combat.

        Palani's Hatcher sacrifices one Egg for free at the beginning of combat
        on your turn, and Raph & Mikey hatch whenever they attack — both fire
        again in every extra combat phase. Their first-combat instances are
        already credited by the DEC-938 block above. The Hatcher keeps DEC-938's
        gate: it adds capacity but never opens the engine on its own, so an
        altar or High Market still has to be on the battlefield.
        """
        nonlocal eggs_on_board, tough_eggs_on_board
        if hatch_engine is None:
            return
        board = {permanent["name"] for permanent in permanents}
        outlet_online = bool((hatch_engine["instantOutletNames"]
                              | hatch_engine["limitedOutletNames"]) & board)
        hatches_per_egg = 1 + len(hatch_engine["extraHatchNames"] & board)
        if (hatch_engine["combatOutletNames"] & board
                and commander_in_play and outlet_online
                and eggs_on_board + tough_eggs_on_board > 0):
            if tough_eggs_on_board > 0:
                tough_eggs_on_board -= 1
            else:
                eggs_on_board -= 1
            run_hatches(hatches_per_egg, turn, combat_phase=phase_index)
        for name in sorted(hatch_engine["combatHatchNames"] & board):
            record = next((permanent for permanent in permanents
                           if permanent["name"] == name), None)
            if record is None or record["combatReadyTurn"] > turn:
                continue
            triggers = 1 + (1 if hatch_engine["legendaryTriggerDoublerName"]
                            in board else 0)
            run_hatches(triggers, turn, combat_phase=phase_index)
    # DEC-405 transform/free-deploy bookkeeping: the back face comes online
    # when the transform activation is paid; every engine-deployed Equipment
    # counts as attached from then on, adding its configured bonus (0 when
    # unlisted).
    commander_transformed = False
    attached_equipment: set[str] = set()
    # DEC-940 — the turn Combat Celebrant last exerted. It does not untap during
    # the next untap step, so it can attack (and exert) only every other turn.
    celebrant_exert_turn: int | None = None
    combo_ready_ever = False
    assembly_turn = [None] * len(assembly_lines)
    reserved_combo_pieces = context["reservedPieces"]
    line_members = context["lineMembers"]
    has_gates = bool(combo_lines or assembly_lines)

    def hatch_engine_state() -> dict:
        """Is the DEC-938 Egg engine online right now, and on which outlets?

        Single source of truth for the hatch block below and for the DEC-944
        activation hold, so the mana the pilot keeps and the mana the engine
        actually spends are decided by the same predicate. The commander's
        {2},{T} needs her unsick *now*, which is a different question from
        "does a creature entering now get haste": a static grant covers her
        retroactively, Rhythm's riot only if it was already out when she
        entered (recorded on her own permanent by `on_permanent_entered`).
        """
        board = {permanent["name"] for permanent in permanents}
        commander_record = next(
            (permanent for permanent in permanents
             if permanent["name"] == commander_name), None)
        commander_hasted_on_entry = (
            commander_record is not None
            and commander_record["combat"] > 0
            and commander_record["combatReadyTurn"] <= turn)
        commander_ready = (
            commander_in_play and commander_play_turn is not None
            and commander_record is not None and not commander_record.get("tapped")
            and (commander_play_turn < turn
                 or commander_hasted_on_entry
                 or (haste_sources is not None
                     and static_haste_active(haste_sources, permanents))))
        instant_outlet = bool(hatch_engine["instantOutletNames"] & board)
        limited_outlet = bool(hatch_engine["limitedOutletNames"] & board)
        return {
            "board": board,
            "commander": commander_record,
            "instantOutlet": instant_outlet,
            "limitedOutlet": limited_outlet,
            "outletOnline": instant_outlet or limited_outlet,
            "online": commander_ready and (instant_outlet or limited_outlet),
        }

    def engine_hold_cost() -> dict | None:
        """Mana to keep back for this deck's configured paid activations (DEC-944).

        One commander Egg activation (DEC-938) while the hatch engine is online,
        and one Aggravated Assault combat (DEC-940) while the enchantment is on
        the battlefield and something can attack. One of each: a real pilot
        protects the activation that converts a turn, not an open-ended budget,
        and holding for more than the deck can convert would starve development.
        """
        costs = []
        if hatch_engine is not None and hatch_engine_state()["online"]:
            costs.append(hatch_engine["activationCost"])
        if combat_modifiers is not None:
            board = {permanent["name"] for permanent in permanents}
            if (combat_modifiers["paidCombatName"] in board
                    and ready_attackers(permanents, turn)):
                costs.append(combat_modifiers["paidCombatCost"])
        return combine_mana_costs(costs) if costs else None

    def assault_hold(current_pool: "GoldfishManaPool") -> dict | None:
        """The held Aggravated Assault (DEC-940) the hatch engine's payments
        keep (the Egg activation, Skullclamp, High Market's {T}): its cost
        while it is on the battlefield with an attacker and the pool can pay
        it, else None."""
        if combat_modifiers is None:
            return None
        board = {permanent["name"] for permanent in permanents}
        cost = combat_modifiers["paidCombatCost"]
        if (combat_modifiers["paidCombatName"] in board and ready_attackers(permanents, turn)
                and current_pool.can_cast(cost)):
            return cost
        return None

    def gate_costs(cast: str | None = None) -> list[list[dict]]:
        """The still-open gates (DEC-944), each as the costs any one of which
        reaches it: the comboLethal gate (the cheapest costs of each line
        whose pieces resolve, combo_line_costs), then one per unassembled
        KEY_COMBOS line (the cheapest costs of its tutors,
        assembly_tutor_cost; none when no tutor can fill its slots). Hand and
        battlefield are read as they stand; with ``cast``, a line piece being
        cast, as they will stand once it is on the battlefield (G1: the rest
        of the line)."""
        board, in_hand = permanents, hand
        if cast is not None:
            in_hand = list(hand)
            if cast in in_hand:
                in_hand.remove(cast)
            board = permanents + [{"name": cast, "kind": "spell", "enteredTurn": turn}]
        gates = []
        if combo_lines and not combo_ready_ever:
            gates.append(combo_line_costs(turn, in_hand, board, combo_lines, profiles, commander_name))
        for idx, line in enumerate(assembly_lines):
            if assembly_turn[idx] is not None:
                continue
            gates.append(assembly_tutor_cost(in_hand, board, library, line, profiles, commander_name))
        return gates

    def holds(current_pool: "GoldfishManaPool", held: dict | None = None,
              cast: str | None = None) -> list[list[dict]]:
        """What a spend must leave payable (DEC-944), for find_payment: each
        gate `current_pool` reaches now, and the held activation `held`. Where
        the held activation and a gate can be paid together now, they are kept
        together, from the same mana (G2: the activation plus each of the
        gate's lines); a gate it cannot be paid with is kept on its own, and
        the activation alone when it goes with no gate. A gate it cannot reach
        holds nothing back."""
        gates = ([costs for costs in gate_costs(cast)
                  if any(current_pool.can_cast(cost) for cost in costs)] if has_gates else [])
        if held is None:
            return gates
        keep, joined = [], False
        for costs in gates:
            together = [combine_mana_costs([held, cost]) for cost in costs]
            if any(current_pool.can_cast(cost) for cost in together):
                keep.append(together)
                joined = True
            else:
                keep.append(costs)
        return keep if joined else [[held]] + keep

    def refresh() -> None:
        """Read the pool's unspent mana from the board again (refresh_pool)."""
        refresh_pool(pool, permanents, profiles, turn)

    def spend(cost: dict, keep=(), strict: bool = True, taps: dict | None = None,
              paid: "GoldfishManaPool | None" = None) -> bool:
        """Pay `cost` out of the turn's pool through spend_mana (the one
        payment path) and keep what it leaves, read from the board again (a
        source that sacrificed itself is gone). False, with nothing paid, when
        no payment keeps `keep`."""
        nonlocal pool
        left = spend_mana(pool, cost, permanents, battlefield_lands, profiles, keep, strict, taps, paid)
        if left is None:
            return False
        pool = left
        refresh()
        return True

    def x_payment(cost: dict, keep) -> tuple | None:
        """(X, the payment) for an X spell: the largest X >= X_SPELL_MIN_X the
        pool pays while keeping the DEC-944 holds, or None."""
        top = (pool.total - cost["total"]) // cost["X"]
        for x in range(top, X_SPELL_MIN_X - 1, -1):
            paid = find_payment(pool, x_spell_cost(cost, x), keep)
            if paid is not None:
                return x, paid
        return None

    by_turn = {}

    for turn in range(1, NUM_TURNS + 1):
        copy_gate_uses = 0
        # Untap step (R1): every permanent untaps, except a one-shot source
        # that does not untap (its ``onceSpent`` stays until it re-arms).
        for permanent in permanents:
            permanent["tapped"] = bool(permanent.get("onceSpent")) and not permanent["manaAtoms"]
        # TOKEN_MAKER_ENGINE commander draw: the tokens untapped at the last
        # opponent's end step are every Food except any that entered tapped on
        # your last turn, and the creature tokens made then, which could not
        # attack.
        commander_draw_tokens = 0
        if token_makers is not None and commander_in_play:
            commander_draw_tokens = food_tokens - food_entered_tapped + swarm_tokens_new
        food_entered_tapped = 0
        swarm_tokens_ready += swarm_tokens_new
        swarm_tokens_new = 0

        # Turn order, as the game runs it: the opponents' turns since your
        # last turn (recurring draw triggers, the token makers' commander
        # draw at the last end step, opponent-cast amass), then your
        # upkeep (the Ring tempt), then your draw step, then your main phase
        # (The One Ring's activation, the land drop, casts). So the tempt
        # reads the hand before the draw step's card arrives.
        #
        # Recurring draw triggers (owner-approved 2026-11-17): their cards
        # come in the opponents' draw steps, so they are in hand before this
        # turn's upkeep tempt below.
        if draw_engines:
            for permanent in permanents:
                engine = draw_engines.get(permanent["name"])
                if engine is None or "drawsPerTurn" not in engine:
                    continue
                for _ in range(engine["drawsPerTurn"]):
                    if library:
                        hand.append(library.pop())
        # TOKEN_MAKER_ENGINE commander draw, at the last opponent's end step.
        if token_makers is not None:
            for _ in range(commander_draw_tokens // token_makers["commanderDrawTokens"]):
                if library:
                    hand.append(library.pop())

        # DEC-533 — opponent-cast amass floor (3 opponent spells per turn
        # cycle) plus the Call of the Ring upkeep tempt. A tempt converts to
        # Sauron's discard-hand-draw-four only at hand size <= temptDrawHandMax,
        # read at upkeep, before the draw step below.
        if amass_engine is not None and commander_in_play:
            # These spells were cast on the opponents' turns since your last
            # turn, so an Army they create has been under your control since
            # before this turn began: it can attack this turn.
            for _ in range(amass_engine["opponentCastsPerTurn"]):
                apply_amass(1, turn, ready_turn=turn)
            has_tempt_permanent = any(
                permanent["name"] in amass_engine["temptPermanents"]
                for permanent in permanents
            )
            if (has_tempt_permanent
                    and len(hand) <= amass_engine["temptDrawHandMax"]):
                hand.clear()
                for _ in range(4):
                    if library:
                        hand.append(library.pop())

        # Draw step: after the upkeep tempt, before the main-phase activations.
        # Turn 1 draws too: the goldfish models a four-player free-for-all
        # Commander game, in which no player skips the draw step of their
        # first turn (CR 103.8c).
        if library:
            hand.append(library.pop())

        # DEC-472 activated draw engines: an engine cast on an earlier turn
        # activates again — counter total +1, draw that many — until its
        # maxActivations stopping rule (life-loss proxy) is reached.
        if draw_engines:
            for permanent in permanents:
                engine = draw_engines.get(permanent["name"])
                if engine is None or "maxActivations" not in engine:
                    continue
                activations = draw_engine_activations.setdefault(permanent["name"], 1)
                if activations >= engine["maxActivations"]:
                    continue
                activations += 1
                draw_engine_activations[permanent["name"]] = activations
                if profiles[permanent["name"]].get("drawTapsSelf"):
                    permanent["tapped"] = True  # its {T}: no mana for Urza this turn
                for _ in range(activations):
                    if library:
                        hand.append(library.pop())

        # A Saga's last chapter resolves after the draw step, before the land
        # drop: it is tapped for its mana in response (that mana joins this
        # turn's pool) and leaves the battlefield (F4).
        floating_mana = []
        for permanent in list(permanents):
            if permanent.get("manaLastTurn") == turn:
                # Its mana and the extras the triggers out add for it.
                floating_mana += [atom for atom in board_mana(permanents, turn, profiles)
                                  if atom.source is permanent]
                leave_battlefield(permanent, permanents, battlefield_lands)
        land_name = choose_land_to_play(hand, profiles, battlefield_lands, permanents,
                                        commander_colors, library, context["handOnlyPieces"])
        if land_name:
            hand.remove(land_name)
            if profiles[land_name]["landEntryCost"]:
                # Mana of lands given up that was tapped first (a Lotus Field
                # or Growth Chamber trigger) joins this turn's pool only.
                floating_mana += give_up_lands(profiles[land_name]["landEntryCost"], turn, hand,
                                               permanents, battlefield_lands, profiles)
            if profiles[land_name]["landCrack"]:
                land_record = crack_fetch_land(land_name, turn, library, hand, permanents,
                                               battlefield_lands, profiles, commander_colors)
            else:
                land_record = put_land_onto_battlefield(
                    land_name, turn,
                    land_enters_tapped(profiles[land_name]["landEntry"], battlefield_lands,
                                       permanents, profiles, hand),
                    permanents, battlefield_lands, profiles, commander_colors)
            if profiles[land_name]["imprint"]:
                imprint_from_hand(land_record, profiles[land_name], hand, profiles, context,
                                  commander_in_play)
            # TOKEN_MAKER_ENGINE landfall makers: one token per natural land
            # drop (one creation event each); lands a fetch land or a ramp
            # spell puts onto the battlefield are a floor.
            if token_makers is not None:
                for maker in sorted(token_makers["landfallMakers"]):
                    if any(permanent["name"] == maker for permanent in permanents):
                        make_tokens(1, 0)
            # DEC-938 — landfall Egg makers (Nesting Dragon) mint one Egg per
            # land drop, from the turn after the maker landed. Only the natural
            # land drop counts; lands fetched by ramp spells are a floor. These
            # Eggs are 0/2, so they go to the Skullclamp-proof counter.
            if hatch_engine is not None:
                for maker, entry_turn in landfall_entry.items():
                    if turn > entry_turn and any(
                            permanent["name"] == maker for permanent in permanents):
                        tough_eggs_on_board += hatch_egg_multiplier(
                            hatch_engine, permanents)

        # DEC-937 — one pool per turn. It is built once, after the land drop,
        # and carried through every cast: each payment (spend, spend_mana)
        # removes the mana it used, and after every resolution its unspent
        # mana is read from the board again (refresh_pool, invariant I1: the
        # mana already floating plus what the untapped permanents not yet
        # used give). Rebuilding it per cast from every permanent (the
        # pre-DEC-937 behaviour) let the goldfish spend the same lands again
        # for every spell in the turn. Mana already floating (a Saga's, lands
        # given up) has no source left to tap: it is spent first.
        pool = GoldfishManaPool([floated(atom) for atom in floating_mana], turn=turn)
        refresh()

        while True:
            refresh()
            candidates = []
            for name in ordered_unique(hand):
                profile = profiles[name]
                if goldfish_never_casts(name, profile, context):
                    continue
                # Chrome Mox is not cast while nothing can be exiled for it.
                if not can_imprint_from_hand(name, profile, hand, profiles, context, commander_in_play):
                    continue
                # DEC-393 — hold per_other_creature engine fuel (spells that
                # target only the commander) until the commander is online;
                # casting Expedite into an empty board is a goldfish-only
                # misplay a real pilot never makes.
                if (copy_engine is not None
                        and copy_engine["mode"] == "per_other_creature"
                        and not commander_in_play
                        and not profile["isPermanent"]
                        and profile["targetsOnlyCreature"]
                        and ("Instant" in profile["typeLine"]
                             or "Sorcery" in profile["typeLine"])):
                    continue
                if not pool.can_cast(profile["manaCost"]):
                    continue
                candidates.append(name)
            if not commander_in_play and pool.can_cast(profiles[commander_name]["manaCost"]):
                candidates.append(commander_name)

            if not candidates:
                break

            candidates.sort(key=lambda name: proactive_cast_priority(
                name, profiles[name], commander_name, commander_in_play,
                line_members))
            # DEC-944 — cast priority. The commander, mana sources and the
            # line's own pieces go first and are never held back. Anything
            # else is filler, and filler only gets cast if a payment leaves
            # (b) the turn's reachable combo/assembly gates and (c) the deck's
            # configured paid activations payable (holds, checked jointly
            # with the payment). The casts never held back take a payment
            # that keeps them when there is one. A hold the pool cannot
            # afford in the first place is dropped rather than left to block
            # development for nothing.
            held = engine_hold_cost()
            if held is not None and not pool.can_cast(held):
                held = None
            keep = holds(pool, held)
            chosen = None
            chosen_x = None
            paid = None
            for name in candidates:
                profile = profiles[name]
                # An X spell (X_SPELL_MIN_X) takes the mana left after the
                # holds as X, or stays in hand. A line piece with {X} in the
                # hand is kept there (decision C), never a candidate; a
                # commander named in a combo line's pieces, cast from the
                # command zone, can be one, and is cast below at X = 0 with
                # the line pieces (one named only in a KEY_COMBOS slot is no
                # line member: the X rule; none in the fleet has {X}). An X
                # spell is never a mana source (its profile
                # says so), so nothing else exempts it from the holds.
                if profile["manaCost"]["X"] and name not in line_members:
                    found = x_payment(profile["manaCost"], keep)
                    if found is None:
                        continue
                    chosen_x, paid = found
                    chosen = name
                    break
                never_held = (name == commander_name or name in line_members
                              or is_mana_source(profile))
                # G1: a line piece keeps the rest of its line, priced with the
                # piece on the battlefield, not the piece's own cost again.
                paid = find_payment(pool, profile["manaCost"],
                                    holds(pool, held, cast=name) if name in line_members else keep,
                                    strict=not never_held)
                if paid is None:
                    continue
                chosen = name
                break
            if chosen is None:
                break
            chosen_profile = profiles[chosen]
            if chosen_x is not None:
                chosen_profile = x_cast_profile(
                    chosen_profile, chosen_x,
                    0 if commander_play_turn is None else 1)
            spend(chosen_profile["manaCost"], paid=paid)
            if chosen in hand:
                hand.remove(chosen)
            # "Whenever you cast a spell, add ..." (Birgi): each such permanent
            # already out adds its mana as the spell is cast (M2).
            for permanent in permanents:
                pool.add(tag_atoms(permanent.get("manaOnCast", ()), None, 0))  # a trigger taps nothing

            # Zhulodok-style cascade fires on cast, so eligibility is checked
            # before resolution; commander CZ casts are not "from hand".
            cascade_fires = (
                cascade is not None
                and commander_in_play
                and chosen != commander_name
                and spell_qualifies_for_cascade(chosen_profile, cascade)
            )

            # DEC-393 — copy-trigger engines also fire on cast: lock the copy
            # count from the board state at trigger time, before the original
            # resolves (its own tokens can't feed its own trigger).
            engine_copies = 0
            if (copy_engine is not None and commander_in_play
                    and chosen != commander_name
                    and not chosen_profile["isPermanent"]
                    and ("Instant" in chosen_profile["typeLine"]
                         or "Sorcery" in chosen_profile["typeLine"])):
                creature_count = (count_creature_permanents(permanents, profiles)
                                  + token_creatures)
                engine_copies = copy_engine_copy_count(
                    copy_engine, chosen_profile, creature_count, copy_gate_uses)
                if engine_copies and copy_engine["mode"] == "tap_gate":
                    copy_gate_uses += 1

            resolve_cast_effects(chosen, chosen_profile, turn, pool, library, hand,
                                 permanents, battlefield_lands, profiles,
                                 commander_colors)
            imprint_on_entry(chosen, chosen_profile, turn, pool, hand, permanents, profiles, context,
                             commander_in_play)
            if copy_engine is not None:
                token_creatures += chosen_profile["tokenCreatures"]

            # DEC-533 — cast/ETB amass credits (an amass X spell amasses the X
            # paid), Saruman's per-noncreature-cast amass X (X = the spell's
            # mana value, X paid included), and entry tracking for the
            # repeatable amass permanents (their triggers start the next turn).
            if amass_engine is not None:
                on_resolve = (chosen_x if chosen in amass_engine["amassXNames"]
                              else amass_engine["amassOnResolve"].get(chosen, 0))
                if on_resolve:
                    apply_amass(on_resolve, turn)
                saruman = amass_engine["perNoncreatureCastMV"]
                if (chosen != commander_name
                        and "Creature" not in chosen_profile["typeLine"]
                        and any(permanent["name"] == saruman
                                for permanent in permanents)):
                    apply_amass(chosen_profile["manaCost"].get("total", 0), turn)
                if chosen in amass_engine["amassPerTurn"]:
                    amass_perm_entry.setdefault(chosen, turn)

            # DEC-404 — token-swarm engine fires on cast (commander already on
            # the battlefield; the commander's own cast never triggers). Mint
            # one token per configured pip in the spell's printed mana cost.
            if (token_engine is not None and commander_in_play
                    and chosen != commander_name
                    and not (token_engine["nonCreatureOnly"]
                             and "Creature" in chosen_profile["typeLine"])):
                swarm_tokens_new += chosen_profile["manaCost"].get(
                    token_engine["pipColor"], 0)

            # TOKEN_MAKER_ENGINE — tokens the cast card makes as it resolves
            # or enters; an X spell makes them at the X paid.
            if token_makers is not None:
                if chosen in token_makers["onResolve"]:
                    make_tokens(*token_makers["onResolve"][chosen])
                if chosen in token_makers["perX"] and chosen_x:
                    make_tokens(token_makers["perX"][chosen] * chosen_x, 0)

            if hatch_engine is not None or haste_sources is not None:
                on_permanent_entered(chosen, turn)

            if chosen == commander_name:
                commander_in_play = True
                if commander_play_turn is None:
                    commander_play_turn = turn
                    # DEC-938 — Thornbite Staff's free attach is "whenever a
                    # Shaman creature enters"; with no equip path in the sim it
                    # only lands if the Staff was already on the battlefield.
                    if hatch_engine is not None:
                        untapper_attached = any(
                            permanent["name"] == hatch_engine["untapperName"]
                            for permanent in permanents
                        )

            if cascade_fires:
                resolve_cascade_triggers(chosen_profile, cascade, turn, pool, library,
                                         hand, permanents, battlefield_lands, profiles,
                                         commander_colors, reserved_combo_pieces, context,
                                         commander_in_play)

            # Copies are not cast (CR 707.10): they re-credit resolution effects
            # (draw, land-ramp, ledger tokens) but never re-trigger the engine.
            for _ in range(engine_copies):
                resolve_cast_effects(chosen, chosen_profile, turn, pool, library, hand,
                                     permanents, battlefield_lands, profiles,
                                     commander_colors)
                token_creatures += chosen_profile["tokenCreatures"]

        # DEC-405 — transform, then free-deploy at the beginning of combat.
        # The activation ({4}{U}{R}, no {T}) is sorcery-speed and paid out of
        # the turn pool like every other cast in this engine; it is never
        # held back, and takes a payment that keeps the gates when one does.
        deploy_combat = 0.0
        if (deploy_engine is not None and commander_in_play
                and not commander_transformed):
            reducer_on_board = any(
                permanent["name"] == deploy_engine["reducerName"]
                for permanent in permanents
            )
            transform_cost = (deploy_engine["reducedTransformCost"]
                              if reducer_on_board
                              else deploy_engine["transformCost"])
            if spend(transform_cost, holds(pool), strict=False):
                commander_transformed = True
                for permanent in permanents:
                    if permanent["name"] == commander_name:
                        # Commander damage moves to the engine ledger below —
                        # zero the record so it isn't double-counted.
                        permanent["combat"] = 0
        if deploy_engine is not None and commander_transformed:
            # Every reserved card (reservedPieces: a line piece kept in the
            # hand, a Walking Ballista, or a tutor or recursion card) is left
            # in the hand, where the combo checks read the ones that can
            # supply a piece (Wishclaw Talisman).
            deploy_name = deploy_engine_choice(
                deploy_engine, [card for card in hand if card not in reserved_combo_pieces], profiles,
                attached_equipment)
            if deploy_name is not None:
                hand.remove(deploy_name)
                deploy_profile = profiles[deploy_name]
                # Free put-onto-battlefield, not a cast: it re-credits
                # resolution effects but never triggers cast-gated models.
                resolve_cast_effects(deploy_name, deploy_profile, turn, pool,
                                     library, hand, permanents, battlefield_lands,
                                     profiles, commander_colors)
                if "Equipment" in deploy_profile["typeLine"]:
                    attached_equipment.add(deploy_name)
            # Back face is 5/5 flying haste — it swings from the transform
            # turn, pumped by attached bonuses, doubled by double strike.
            attack = deploy_engine["transformedPower"] + sum(
                deploy_engine["equipmentPower"].get(name, 0)
                for name in attached_equipment
            )
            if attached_equipment & deploy_engine["doubleStrikeNames"]:
                attack *= 2
            deploy_combat = float(attack)
            cumulative_damage += deploy_combat

        # DEC-533 — repeatable amass triggers fire from the turn after their
        # permanent landed; March from the Black Gate also needs a combat-ready
        # Army (its trigger is "whenever an Army you control attacks"). Then
        # the Army swings for its counter total, and a connecting Army tempts
        # once more (converted under the same hand-size gate).
        army_combat = 0.0
        if amass_engine is not None:
            army_attacks = (army_ready_turn is not None
                            and turn >= army_ready_turn
                            and army_counters > 0)
            for name, entry_turn in amass_perm_entry.items():
                if turn <= entry_turn:
                    continue
                if name == "March from the Black Gate" and not army_attacks:
                    continue
                if any(permanent["name"] == name for permanent in permanents):
                    apply_amass(amass_engine["amassPerTurn"][name], turn)
            if army_attacks:
                army_combat = float(army_counters)
                cumulative_damage += army_combat
                if (commander_in_play
                        and len(hand) <= amass_engine["temptDrawHandMax"]):
                    hand.clear()
                    for _ in range(4):
                        if library:
                            hand.append(library.pop())
            cumulative_damage += amass_ping_damage
            amass_ping_damage = 0.0

        # DEC-938 — hatch engine. Eggs are made (commander activations, entry
        # and landfall makers), an outlet kills them, and every death reveals
        # the top creature card of the library onto the battlefield free.
        if hatch_engine is not None:
            hatches_left = hatch_engine["maxHatchesPerTurn"]  # noqa: F841 (nonlocal)
            haste_now = (haste_sources is not None
                         and team_haste_active(haste_sources, permanents))
            # `hatch_engine_state` holds the commander-readiness and outlet
            # rules (DEC-944 moved them there so the activation hold and the
            # activations themselves agree). Skullclamp and Palani's Hatcher add
            # own-turn capacity once an instant-speed outlet is online but do
            # not open the engine on their own (board scope, DEC-938) — Eggs
            # they would eat with no altar out are a floor.
            refresh()
            engine_state = hatch_engine_state()
            board = engine_state["board"]
            instant_outlet = engine_state["instantOutlet"]
            outlet_online = engine_state["outletOnline"]
            engine_online = engine_state["online"]
            commander_record = engine_state["commander"]
            # Thornbite Staff, attached as she entered, untaps her whenever a
            # creature dies (an Egg, to any outlet).
            staff_attached = untapper_attached and hatch_engine["untapperName"] in board

            # Own-turn commander activations: {2}, {T} each out of what the
            # casts left, keeping the reachable gates and a held Aggravated
            # Assault (assault_hold). Her {T} taps her, so one
            # per untap and she does not attack after it — unless Thornbite
            # Staff untaps her per creature death: only with Ashnod's Altar out
            # does the Egg it just ate pay ({C}{C}) for the next activation.
            # The Eggs' deaths below untap her (staff_attached).
            if engine_online:
                thornbite = (untapper_attached
                             and hatch_engine["untapperName"] in board
                             and hatch_engine["untapperRequiresName"] in board)
                untaps = hatch_engine["maxEggsPerTurn"] if thornbite else 1
                egg_multiplier = hatch_egg_multiplier(hatch_engine, permanents)
                for activation in range(min(untaps, hatch_engine["maxEggsPerTurn"])):
                    if activation > 0 and thornbite:
                        pass  # the Altar's {C}{C} from the last Egg pays for it
                    elif not spend(hatch_engine["activationCost"], holds(pool, assault_hold(pool)),
                                   taps=commander_record):
                        break
                    eggs_on_board += egg_multiplier

            # Own-turn sacrifice outlets, in mana order: Skullclamp equips
            # ({1} each, two cards per Egg) first because they are the only
            # outlet that pays the deck back, then the free/limited ones.
            # The dies-trigger only needs the commander on the battlefield, not
            # untapped or unsick — an Egg dying on her cast turn still hatches.
            if (commander_in_play and outlet_online
                    and eggs_on_board + tough_eggs_on_board > 0):
                clamp_deaths = 0
                # +1/-1 kills a 0/1 Egg; the 0/2 Dragon Eggs survive as 1/1s.
                if hatch_engine["sorceryOutletName"] in board:
                    while (eggs_on_board > clamp_deaths
                           and spend(hatch_engine["sorceryOutletCost"], holds(pool, assault_hold(pool)))):
                        clamp_deaths += 1
                        for _ in range(hatch_engine["sorceryOutletDraw"]):
                            if library:
                                hand.append(library.pop())
                eggs_on_board -= clamp_deaths
                free_deaths = eggs_on_board + tough_eggs_on_board
                # DEC-944 — Palani's Hatcher sacrifices at the *beginning of
                # combat*, so the Egg it eats and the creature that reveals
                # belong to combat phase 0, not to the precombat main phase.
                # That matters for the DEC-940 multipliers: Xenagos cannot
                # target a creature that was not on the battlefield when his
                # beginning-of-combat trigger went on the stack, and Zopandrel's
                # doubling had already resolved. Split the free deaths so only
                # the Hatcher's share carries the `combat_phase=0` mark. With an
                # instant-speed outlet (Ashnod's Altar) the main phase has
                # already eaten every Egg, so the Hatcher gets none.
                combat_outlet_deaths = 0
                if not instant_outlet:
                    # High Market ({T}, Sacrifice a creature) sacrifices one
                    # Egg while one is untapped (its mana unspent): its {T}
                    # is paid like any cost, keeping the reachable gates and a
                    # held Aggravated Assault
                    # (G3), and the sacrifice counts only when it is paid.
                    market = next((permanent for permanent in permanents
                                   if permanent["name"] in hatch_engine["limitedOutletNames"]
                                   and not permanent.get("tapped")), None)
                    limited_capacity = 1 if (
                        market is not None and free_deaths > 0
                        and spend(combine_mana_costs([]), holds(pool, assault_hold(pool)),
                                  taps=market)) else 0
                    combat_capacity = (
                        1 if hatch_engine["combatOutletNames"] & board else 0)
                    free_deaths = min(free_deaths,
                                      limited_capacity + combat_capacity)
                    combat_outlet_deaths = max(0, free_deaths - limited_capacity)
                # Spend the Clamp-proof Eggs on the free outlets first so the
                # 0/1s stay as Clamp fuel for the next turn.
                from_tough = min(free_deaths, tough_eggs_on_board)
                tough_eggs_on_board -= from_tough
                eggs_on_board -= free_deaths - from_tough
                hatches_per_egg = 1 + len(hatch_engine["extraHatchNames"] & board)
                main_deaths = clamp_deaths + free_deaths - combat_outlet_deaths
                run_hatches(main_deaths * hatches_per_egg,
                            turn if haste_now else None)
                run_hatches(combat_outlet_deaths * hatches_per_egg,
                            turn if haste_now else None, combat_phase=0)
                if staff_attached and commander_record is not None and main_deaths + combat_outlet_deaths > 0:
                    commander_record["tapped"] = False

            # Attack-triggered hatches (Raph & Mikey): the creature enters
            # tapped and attacking, so it is combat-ready this turn. Annie Joins
            # Up doubles the trigger (they are legendary). Independent of the
            # Egg engine — no commander and no outlet needed.
            for name in sorted(hatch_engine["combatHatchNames"] & board):
                record = next((permanent for permanent in permanents
                               if permanent["name"] == name), None)
                if record is None or record["combatReadyTurn"] > turn:
                    continue
                triggers = 1 + (1 if hatch_engine["legendaryTriggerDoublerName"]
                                in board else 0)
                run_hatches(triggers, turn, combat_phase=0)

            # Seedborn Muse untaps the commander (and the lands) on each of the
            # three opponents' untap steps: three free activations after your
            # combat. Only instant-speed outlets serve them, and the creatures
            # they put down are ready on your next turn regardless of haste.
            board = {permanent["name"] for permanent in permanents}
            if (engine_online and hatch_engine["untapStepName"] in board
                    and (hatch_engine["instantOutletNames"] & board
                         or hatch_engine["limitedOutletNames"] & board)):
                activations = hatch_engine["untapStepActivations"]
                eggs = activations * hatch_egg_multiplier(hatch_engine, permanents)
                # High Market alone still sacrifices one Egg per opponent untap.
                deaths = eggs if (hatch_engine["instantOutletNames"] & board) \
                    else min(eggs, activations)
                eggs_on_board += eggs - deaths
                hatches_per_egg = 1 + len(hatch_engine["extraHatchNames"] & board)
                run_hatches(deaths * hatches_per_egg, None)

        # DEC-940 — combat phases. A deck with no COMBAT_MODIFIERS entry runs
        # exactly one phase and `combat_phase_damage` returns the unmodified sum
        # of ready attackers, so this is the behaviour the goldfish has always
        # had. For a configured deck each phase re-applies the multipliers
        # (Zopandrel -> Xenagos -> Raphael), the per-combat hatch triggers fire
        # again at every extra combat, and extra phases come from the trigger
        # queue first, then from Aggravated Assault paid out of what the turn's
        # casts and Egg activations left in the pool.
        combat_total = 0.0
        phase_index = 0
        max_phases = combat_modifiers["maxCombatPhases"] if combat_modifiers else 1
        trigger_extras = 0
        excluded_attackers: set[str] = set()
        if combat_modifiers is not None and celebrant_exert_turn == turn - 1:
            # An exerted creature does not untap during your next untap step.
            excluded_attackers |= combat_modifiers["exertCombatNames"]
        # R1 — attackers are declared after the gates' reachability is
        # checked, on the mana the cast loop held for them (the gates are read
        # after combat, below). A creature tapped this turn (by its own {T}
        # for mana or an ability) does not attack; a creature whose mana a
        # reachable gate, or a held Aggravated Assault, needs is kept back (the
        # most combat attacks first); a creature that attacked pays for nothing
        # afterwards with mana its own {T} makes (Urza's mana taps other
        # artifacts: it stays); a creature whose {T} land fetch the turn can
        # pay stays home to fetch (fetches_instead).
        refresh()
        board_now = {permanent["name"] for permanent in permanents}
        paid_combat = (combat_modifiers is not None
                       and combat_modifiers["paidCombatName"] in board_now)
        # What the attackers must leave payable: the reachable gates and a
        # held Aggravated Assault, together where they can be paid together
        # (holds, G2).
        combat_keep = (holds(pool, combat_modifiers["paidCombatCost"] if paid_combat else None)
                       if (has_gates or paid_combat) else [])

        def taps_to_attack(permanent: dict) -> bool:
            """Attacking taps it and its mana needs it untapped."""
            profile = profiles[permanent["name"]]
            return not profile["vigilance"] and profile["manaTapsSelf"]

        def after_attack(attacking: list[dict]) -> "GoldfishManaPool":
            gone = {id(p) for p in attacking if taps_to_attack(p)}
            return pool.without(lambda atom: atom_source_id(atom) not in gone)

        def held_reach(test_pool: "GoldfishManaPool") -> tuple:
            return (tuple(any(test_pool.can_cast(cost) for cost in costs) for costs in combat_keep)
                    + tuple(test_pool.lasting().can_cast(cost) for cost in fetch_keep))

        def loses_hold(baseline: tuple, attacking: list[dict]) -> bool:
            return any(was and not now for was, now in zip(baseline, held_reach(after_attack(attacking))))

        def fetches_instead(permanent: dict) -> bool:
            """A creature with a {T} land fetch (Embodiment of Spring) stays
            home when the end of the turn can activate it: by the test the
            activation itself uses (land_fetch_payment), on the lasting mana it
            is paid from (one-shot mana such as Lotus Petal's is not), leaving
            the holds payable (the reachable gates and a held Aggravated
            Assault). An attack would leave it tapped. A creature with
            vigilance attacks and fetches."""
            profile = profiles[permanent["name"]]
            search = profile["landFetch"]
            return bool(search and search["tapsSelf"] and not profile["vigilance"]
                        and land_fetch_payment(permanent, turn, pool.lasting(), library, permanents,
                                               battlefield_lands, profiles, commander_colors, combat_keep)
                        is not None)

        fetch_home = {id(p) for p in ready_attackers(permanents, turn) if fetches_instead(p)}
        # The fetch of a creature kept home joins what the attackers must leave
        # payable, as the holds do, read on the lasting mana the end of the
        # turn pays it from (held_reach): a mana creature whose {T} mana it
        # needs (Llanowar Elves) stays home too.
        fetch_keep = [profiles[p["name"]]["landFetch"]["cost"]
                      for p in ready_attackers(permanents, turn) if id(p) in fetch_home]
        candidates_to_attack = [permanent for permanent in ready_attackers(permanents, turn)
                                if permanent["name"] not in excluded_attackers
                                and not permanent.get("tapped") and id(permanent) not in fetch_home]
        first_attackers = candidates_to_attack
        hold_baseline = held_reach(pool)
        if any(hold_baseline) and loses_hold(hold_baseline, candidates_to_attack):
            kept = {id(p) for p in candidates_to_attack}
            for permanent in sorted(candidates_to_attack, key=lambda p: (-p["combat"], p["name"])):
                trial = [p for p in candidates_to_attack if id(p) not in kept or p is permanent]
                if not loses_hold(hold_baseline, trial):
                    kept.discard(id(permanent))
            first_attackers = [p for p in candidates_to_attack if id(p) not in kept]
        # The gates are read after combat (below) on the mana kept for them:
        # what was reachable before attackers were declared still is.
        attacked: set = set()
        any_attacker = False
        while True:
            if phase_index > 0:
                run_combat_phase_hatches(phase_index)
            board_now = {permanent["name"] for permanent in permanents}
            if phase_index == 0:
                attackers = [p for p in first_attackers if p["name"] not in excluded_attackers]
            else:
                # Every extra combat follows an effect that untaps the
                # creatures (Aggravated Assault, Aurelia, Tifa, Combat
                # Celebrant's "all other creatures"), so creatures tapped for
                # mana attack in it too; the mana they would make after the
                # untap is not credited (a floor). A creature kept home whose
                # mana is still held for a gate stays home.
                held_home = {atom_source_id(atom) for atom in pool.sources} & {
                    id(p) for p in candidates_to_attack if p not in first_attackers}
                attackers = [p for p in ready_attackers(permanents, turn)
                             if p["name"] not in excluded_attackers and id(p) not in held_home
                             and id(p) not in fetch_home]
            any_attacker = any_attacker or bool(attackers)
            for permanent in attackers:
                if not profiles[permanent["name"]]["vigilance"]:
                    permanent["tapped"] = True
                if taps_to_attack(permanent):
                    attacked.add(id(permanent))
            pool = pool.without(lambda atom: atom_source_id(atom) not in attacked)
            refresh()
            combat_total += combat_phase_damage(
                attackers, combat_modifiers, board_now, phase_index)
            if combat_modifiers is None:
                break
            if phase_index == 0:
                # Aurelia and Tifa both trigger off the first combat only, and
                # both are legendary creatures, so Annie Joins Up doubles them.
                annie = (2 if combat_modifiers["legendaryTriggerDoublerName"]
                         in board_now else 1)
                attacker_names = {permanent["name"] for permanent in attackers}
                if combat_modifiers["extraCombatAttackerNames"] & attacker_names:
                    trigger_extras += annie
                if (combat_modifiers["powerGatedCombatNames"] & attacker_names
                        and any(profiles[permanent["name"]]["printedPower"]
                                >= combat_modifiers["powerGateThreshold"]
                                for permanent in attackers)):
                    trigger_extras += annie
                celebrant = combat_modifiers["exertCombatNames"] & attacker_names
                if celebrant:
                    celebrant_exert_turn = turn
                    trigger_extras += 1
                    # It untaps all *other* creatures, so it sits out the rest
                    # of this turn's combats.
                    excluded_attackers |= celebrant
            if phase_index + 1 >= max_phases:
                break
            if trigger_extras > 0:
                trigger_extras -= 1
            elif (combat_modifiers["paidCombatName"] in board_now
                  and spend(combat_modifiers["paidCombatCost"], holds(pool))):
                pass
            else:
                break
            phase_index += 1
        cumulative_damage += combat_total
        # Combat is over: no creature attacks again this turn, so its mana
        # costs what a land's does (GoldfishManaPool.rank).
        pool = pool.after_combat()
        refresh()
        # TOKEN_MAKER_ENGINE attack makers: from the turn after the maker was
        # cast it attacks, its trigger makes tokens tapped and attacking, and
        # they join the ready tokens that swing below.
        if token_makers is not None:
            out_before_this_turn = {permanent["name"] for permanent in permanents
                                    if permanent.get("enteredTurn", turn) < turn}
            for maker, count in sorted(token_makers["attackMakers"].items()):
                if maker in out_before_this_turn:
                    make_tokens(count, 0, attacking=True)
            for maker in sorted(token_makers["growingAttackMakers"]):
                if maker in out_before_this_turn:
                    attack_maker_counters[maker] = attack_maker_counters.get(maker, 0) + 1
                    make_tokens(attack_maker_counters[maker], 0, attacking=True)
        # DEC-404 — token-swarm combat: ready tokens swing every turn, each
        # pumped by battlefield anthems; the commander's variable power adds
        # commanderPowerPerToken per ready token once he can attack himself.
        # TOKEN_MAKER_ENGINE tokens swing on the same ledger and convention.
        swarm_combat = 0.0
        swarm_config = token_engine if token_engine is not None else token_makers
        if swarm_config is not None and swarm_tokens_ready > 0:
            anthem_count = sum(
                1 for permanent in permanents
                if permanent["name"] in swarm_config["anthemNames"]
            )
            swarm_combat = swarm_tokens_ready * (
                swarm_config["tokenPower"] + anthem_count)
            if (token_engine is not None
                    and commander_in_play and commander_play_turn is not None
                    and commander_play_turn < turn):
                swarm_combat += (token_engine["commanderPowerPerToken"]
                                 * swarm_tokens_ready)
            cumulative_damage += swarm_combat
        if not combo_ready_ever and combo_lines:
            combo_ready_ever = combo_ready_this_turn(
                turn=turn,
                hand=hand,
                permanents=permanents,
                combo_lines=combo_lines,
                profiles=profiles,
                pool=pool,
                commander_name=commander_name,
            )
        for idx, line in enumerate(assembly_lines):
            if assembly_turn[idx] is not None:
                continue
            if combo_assembled_this_turn(
                turn=turn,
                hand=hand,
                permanents=permanents,
                library=library,
                assembly_line=line,
                profiles=profiles,
                pool=pool,
                commander_name=commander_name,
            ):
                assembly_turn[idx] = turn
        # TOKEN_MAKER_ENGINE activated makers, once per turn each in name
        # order, paid out of the mana the turn's casts left after the gates
        # above have read the pool. Each cost has the maker's own {T}: it
        # must be untapped (a land that entered tapped is tapped) and is
        # tapped for the ability, so a land maker's own mana cannot pay (spend
        # ``taps``). A cost that untaps a tapped creature needs one (G7): a
        # creature that attacked or was tapped for mana, or a token that
        # attacked (stampede-acres' one vigilance creature, Adeline, makes
        # tapped tokens when she attacks).
        if token_makers is not None:
            tapped_creature = swarm_tokens_ready > 0 or any(
                permanent.get("tapped") and "Creature" in profiles[permanent["name"]]["typeWords"]
                for permanent in permanents)
            for maker, cost in sorted(token_makers["activatedMakers"].items()):
                record = next((permanent for permanent in permanents
                               if permanent["name"] == maker), None)
                if record is None or (
                        maker in token_makers["needsTappedCreature"] and not tapped_creature):
                    continue
                if spend(cost, taps=record):
                    make_tokens(1, 0)
                    if maker in token_makers["needsTappedCreature"]:
                        # Its cost untaps the tapped creature (the first in
                        # board order; a token that attacked otherwise).
                        untapped = next((permanent for permanent in permanents if permanent.get("tapped")
                                         and "Creature" in profiles[permanent["name"]]["typeWords"]), None)
                        if untapped is not None:
                            untapped["tapped"] = False
                            refresh()
        # End of turn, out of the lasting mana the turn left (one-shot mana not
        # spent is kept): a spent Basalt Monolith re-arms, then the land
        # fetches are activated, each payment settled before the next
        # (spend_mana). The board, and availableMana (a land a fetch puts
        # onto the battlefield untapped adds its mana), are read after these.
        lasting_left = rearm_once_sources(permanents, pool.lasting(), battlefield_lands, profiles)
        available_mana = activate_land_fetches(turn, lasting_left, library, hand, permanents, battlefield_lands,
                                               profiles, commander_colors).added
        # `metrics_from_board` re-sums one unmodified combat from the board, so
        # hand it the difference the extra phases, the multipliers and the
        # creatures that did not attack made — exactly 0.0 for a deck with no
        # COMBAT_MODIFIERS entry whose ready creatures all attacked.
        combat_modifier_bonus = combat_total - sum(
            permanent["combat"] for permanent in ready_attackers(permanents, turn))
        by_turn[turn] = metrics_from_board(
            turn=turn,
            permanents=permanents,
            profiles=profiles,
            commander_name=commander_name,
            commander_in_play=commander_in_play,
            cumulative_damage=cumulative_damage,
            meaningful_threshold=meaningful_threshold,
            combo_ready_ever=combo_ready_ever,
            extra_combat=(swarm_combat + deploy_combat + army_combat
                          + combat_modifier_bonus),
            available_mana=available_mana,
        )

    return by_turn, assembly_turn


def _run_goldfish_chunk(args):
    """Worker chunk for multiprocessing goldfish simulation."""
    decklist, context, num_games, meaningful_threshold, seed = args
    # Seed per chunk so the whole run is reproducible regardless of how the games
    # are split across workers (fixed chunk count + fixed per-chunk seed). (DEC-363)
    random.seed(seed)
    num_combos = len(context.get("assemblyLines", []))
    aggregate = {
        "lands": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "ramp": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "threats": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "available_mana": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "pressure": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "combat": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "cumulative_damage": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "commander_cast": Counter(),
        "first_threat": Counter(),
        "meaningful_board": Counter(),
        "lethal_proxy": Counter(),
        "combo_lethal": Counter(),
        # Per-combo cumulative "assembled by turn T" game counts.
        "combo_assembled": [{turn: 0 for turn in range(1, NUM_TURNS + 1)} for _ in range(num_combos)],
    }

    for _ in range(num_games):
        by_turn, assembly_turn = simulate_goldfish_game(
            decklist, context, meaningful_threshold)
        for turn in range(1, NUM_TURNS + 1):
            metrics = by_turn[turn]
            aggregate["lands"][turn].append(metrics["lands"])
            aggregate["ramp"][turn].append(metrics["ramp"])
            aggregate["threats"][turn].append(metrics["threats"])
            aggregate["available_mana"][turn].append(metrics["availableMana"])
            aggregate["pressure"][turn].append(metrics["pressure"])
            aggregate["combat"][turn].append(metrics["combat"])
            aggregate["cumulative_damage"][turn].append(metrics["cumulativeDamage"])
            aggregate["commander_cast"][turn] += metrics["commanderCast"]
            aggregate["first_threat"][turn] += metrics["firstThreat"]
            aggregate["meaningful_board"][turn] += metrics["meaningfulBoard"]
            aggregate["lethal_proxy"][turn] += metrics["lethalProxy"]
            aggregate["combo_lethal"][turn] += metrics["comboLethal"]
        for idx, earliest in enumerate(assembly_turn):
            if earliest is None:
                continue
            for turn in range(earliest, NUM_TURNS + 1):
                aggregate["combo_assembled"][idx][turn] += 1

    return aggregate


def merge_goldfish_stats(chunks: list[dict]) -> dict:
    """Merge multiprocessing goldfish chunk results."""
    num_combos = len(chunks[0]["combo_assembled"]) if chunks else 0
    merged = {
        "lands": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "ramp": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "threats": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "available_mana": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "pressure": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "combat": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "cumulative_damage": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "commander_cast": Counter(),
        "first_threat": Counter(),
        "meaningful_board": Counter(),
        "lethal_proxy": Counter(),
        "combo_lethal": Counter(),
        "combo_assembled": [{turn: 0 for turn in range(1, NUM_TURNS + 1)} for _ in range(num_combos)],
    }

    for chunk in chunks:
        for key in ("lands", "ramp", "threats", "available_mana", "pressure", "combat", "cumulative_damage"):
            for turn in range(1, NUM_TURNS + 1):
                merged[key][turn].extend(chunk[key][turn])
        for key in ("commander_cast", "first_threat", "meaningful_board", "lethal_proxy", "combo_lethal"):
            merged[key].update(chunk[key])
        for idx in range(num_combos):
            for turn in range(1, NUM_TURNS + 1):
                merged["combo_assembled"][idx][turn] += chunk["combo_assembled"][idx][turn]
    return merged


GOLDFISH_MANA_METHODOLOGY = (
    " Mana model (owner-approved 2026-11-19, review rounds 1 to 5 2026-11-20): a permanent gives the "
    "mana its own text gives a pilot on a normal turn, using only itself and what the goldfish has on"
    " its own battlefield; a wording the parser is known not to read stops the export. The face on "
    "the battlefield is read (a modal DFC with a spell front and a land back is on the battlefield "
    "as its land face, played as a land unless it is a combo-line or assembly piece the goldfish "
    "keeps in the hand; a Pathway "
    "played from the hand enters as the face that adds a commander colour the lands lack, one a "
    "search or a fetch land puts onto the battlefield front face up), without reminder text; an "
    "ability granted to a group the card belongs to counts for the card itself, the grant's subject "
    "read in full (\"Other creatures you control have\" gives the card nothing); basic land types make "
    "their colour, and a land that gives every land a type (Urborg, Tomb of Yawgmoth) or a permanent "
    "that gives every land exactly \"{T}: Add\" one mana (Chromatic Lantern) lets every land make that "
    "colour too (one mana a land, a land with no mana ability of its own included: Maze of Ith), from"
    " the moment it enters. A permanent taps once a turn: its best single ability, and at one mana "
    "the union of the colours of the abilities it could use instead; mana \"of any one color\" (Lotus "
    "Field, Wirewood Channeler, Nykthos) is all one colour, Nykthos each colour as much as its own "
    "devotion. Mana in an ability's cost is netted. A permanent that sacrifices itself for mana, or "
    "does not untap, gives that mana once, kept until a turn needs it; one that sacrifices itself "
    "leaves the battlefield as its mana is spent; one with \"{N}: Untap this\" (Basalt Monolith) is "
    "untapped at the end of the turn it was spent or any later turn with N of the lasting mana left. "
    "A cost that taps or sacrifices another permanent gives nothing, even \"Sacrifice an artifact\" on "
    "an artifact (Krark-Clan Ironworks), except Urza, Lord High Artificer's \"Tap an untapped "
    "artifact\": his Construct token's {U} is his, and each other untapped noncreature artifact with "
    "no mana of its own taps for its own {U} (it is the permanent tapped, and then cannot pay its own"
    " {T} cost), from the turn he enters or it does; never a combo-line or assembly-line member whose"
    " line needs it untapped, one with an activated ability of its own with {T} in its cost (Isochron"
    " Scepter; an Equipment such as Sword of Feast and Famine can be tapped), nor an artifact that "
    "entered tapped (Nevinyrral's Disk) or whose own {T} ability was used (The One Ring's draw, as it"
    " is cast and each later activation). Conditions on the goldfish's own battlefield are read as "
    "each turn's pool is built and as a permanent enters (land types; land and artifact counts; "
    "Elves; Swamps; Tron; devotion; colours among permanents; a legendary creature; Reflecting Pool's"
    " colours: what the other lands could produce, the face a Pathway was played as and what each of "
    "their mana abilities would make on this board, read before the ability's cost is netted and "
    "whatever its condition or cost (The Mycosynth Gardens' {1}, {T} any colour; Cabal Coffers makes "
    "black only with a Swamp out)). After every resolution (a cast, a land put onto the battlefield, "
    "a permanent leaving, a grant or trigger source entering) the turn's unspent mana is read from "
    "the board again: the mana already made (floating) plus what the untapped permanents not yet used"
    " give, with the triggers and grants out at that moment. Variable amounts count what the card "
    "alone guarantees. A creature's {T} mana (a land creature's too: Dryad Arbor enters untapped and "
    "summoning sick) and a permanent that enters tapped (a rider after it included: Noble's Purse) "
    "make mana from the next turn, and a creature's other {T} abilities wait too (Embodiment of "
    "Spring's land fetch; Sakura-Tribe Elder's has no {T}); a non-land ability with mana in its cost "
    "(a Signet) also from the next turn, a floor: using it the turn it is cast needs a spare mana the"
    " goldfish does not plan for. Each permanent is tapped or untapped for the turn: tapped as it "
    "enters tapped, when its own {T} makes mana that is spent (Urza taps other artifacts, not "
    "himself; a vigilant creature is not: M9, the pilot attacks first and casts after combat, so a "
    "vigilant mana creature both attacks and pays), when it attacks (not with vigilance) and when one"
    " of its own {T} abilities is used (the hatch commander's Egg, until Thornbite Staff untaps her "
    "as an Egg dies to any outlet; High Market's sacrifice, which counts only when paid; Castle "
    "Ardenvale's token; a land fetch). Every spend (casts, X, activations, the end of the turn's "
    "untaps and land fetches) is one exact payment, settled before the next: a payment is found "
    "whenever the cost and what the turn holds can be paid together, never otherwise, and of the "
    "payments that keep the holds the most preferred is taken (a one-colour activation is made as one"
    " colour, and its other mana is that colour). The holds: each reachable gate, and the held "
    "activation, the two kept together from the same mana where they can be paid together; a line "
    "piece being cast keeps the rest of its line, priced with the piece on the battlefield; the hatch"
    " engine's payments (the Egg activation, Skullclamp's equip, High Market's {T}) keep the "
    "reachable gates and a held Aggravated Assault the pool can still pay. A hold is checked against "
    "the pool as it stands before a source that sacrifices itself for the payment leaves (Lotus Petal"
    " as the only artifact beside Spire of Industry), an over-credit. Spend order: mana already made "
    "(floating) first; then lands, noncreature mana and creatures that could not attack (the "
    "narrowest colours first; a land with a {T} ability the turn uses later, as Castle Ardenvale, "
    "High Market and a Myriad Landscape whose fetch can net a land in this deck, last among them); "
    "then one-shot mana (the fewest sources); then creatures that could attack and are not vigilant "
    "(the fewest, then the least combat, then the fewest one-shot sources beside them). After combat "
    "a creature's mana costs what a land's does. The combo and assembly gates' reachability is "
    "checked before attackers are declared, and the gates are read after combat on the mana kept for "
    "them: a creature whose mana a reachable gate, or a held Aggravated Assault, needs stays home; a "
    "tapped creature does not attack, and one that attacked pays for nothing afterwards with mana its"
    " own {T} makes. An extra combat follows an effect that untaps the creatures, so creatures tapped"
    " for mana attack in it too; the mana they would make after that untap is not credited. \"Whenever"
    " you cast a spell, add\" (Birgi) adds as each spell is cast and taps nothing; \"add an additional\""
    " triggers (Crypt Ghast, Badgermole Cub, Forsaken Monument) add one per permanent tapped that "
    "fires them, also for mana that comes online during the turn (a source entering, a Saga's last "
    "chapter); Forsaken Monument's extra belongs to the colourless choice of an activation: a "
    "permanent that makes {C} always gets it (one-shot {C} included: that extra is one-shot too), one"
    " that makes {C} or a colour (Nykthos, a pain land) gets it only when it makes {C}. Halo "
    "Fountain's token needs a tapped creature to untap (one that attacked or was tapped for mana, not"
    " one only waiting out the turn it entered), and that creature is untapped: one that attacked can"
    " then make its mana; one already tapped for mana is not credited again. Lands: how a land enters"
    " is read against the lands, permanents and hand at that moment (a Snarl reveals from the hand; "
    "\"two or more opponents\" is always met; \"your opponents control eight or more lands\" is met from "
    "the fourth land drop, DEC-688 / DEC-929); a fetch land is cracked as it is played for the best "
    "legal land left in the library, which enters with its own types, colours and entry rule (tapped "
    "when the search says so, untapped by the search's own condition), and the fetch land leaves; "
    "with nothing to find it stays and makes no mana of its own. A land that sacrifices or returns "
    "lands as it enters waits for them, and they leave at once (the fewest mana first), so later land"
    " counts fall: sacrificed instead of entering (Scorched Ruins) they are lost untapped, taken by "
    "its entering trigger (Lotus Field, Simic Growth Chamber) they are tapped first and that mana, "
    "floating, is spent first that turn, and a returned land goes back to the hand. A Saga makes its "
    "mana for as many turns as it has chapters, is tapped as its last chapter resolves (that mana "
    "floats) and leaves. Imprint (owner-approved): Ugin's Labyrinth exiles a colourless card of mana "
    "value 7 or more from the hand and makes {C}{C}, else {C}; Chrome Mox exiles a coloured "
    "nonartifact, nonland card and makes one mana of its colours, and is not cast, paid or by "
    "cascade, while no card can be exiled for it; the card exiled is one the goldfish holds back as "
    "interaction or an alternative a combo line or a table slot keeps in the hand and no line names "
    "plainly, ranked together (the most colours, then the highest mana value, then the name latest in the "
    "alphabet, first), "
    "if the hand holds one, else the castable card last in its cast order, and it leaves the hand; "
    "never exiled, in every deck: tutor and recursion cards (by their roles), combo-line "
    "and assembly-line members, the other reserved combo pieces, deploy-engine Equipment, a land, and a modal "
    "card with a spell front and a land back (played as its land, or kept in the hand as a line "
    "piece); a transforming card with a land back (Growing Rites of Itlimoc, an enchantment on its "
    "front) can be exiled. Land-ramp spells move the lands their text says, each destination "
    "as written (an untapped land's mana joins the turn); a search looks at a card as it is in the "
    "library, its front face (a modal DFC whose front is a spell is not a land card there); a land a "
    "search puts onto the battlefield gives up the lands its entry takes, as one that is played does "
    "(Simic Growth Chamber), and a search chooses its land as a land drop does (a land creature is "
    "not usable that turn); land-fetching permanents (Wayfarer's Bauble, Sakura-Tribe Elder, Myriad "
    "Landscape) are cracked at the end of the turn with mana the turn left when they net a land, a "
    "{T} cost needing them untapped, and \"share a land type\" finds the most lands of one type. Mana "
    "sources for the cast order, the mulligan and the holds: a permanent with mana every turn, a "
    "land-ramp spell, a land-fetching permanent, an imprint permanent. availableMana is the mana the "
    "pilot could have spent that turn: the turn's pool plus every mana added during the turn (cast "
    "triggers, sources and lands that came online untapped, the end of the turn's land fetches "
    "included, mana of lands given up or of a Saga leaving after it was tapped). The other per-turn "
    "counts (lands, ramp, threats, pressure) are read after the end-of-turn actions. Not read (the "
    "export stops): a nonland card with no mana cost (suspend), a card that gives up a land as it "
    "acts or enters (Harrow, Mox Diamond, Coral Atoll, Brokers Hideout), a land that sacrifices, "
    "returns or exiles itself in a trigger (City of Traitors), a land search whose count or filter no"
    " rule places (\"up to X\", \"four\", \"that many\", a snow land, a qualification after \"card\": \"with "
    "different names\", \"that each have a basic land type\", \"or Planet card\"; a list of cards; a "
    "destination other than the battlefield, the hand, or the two split as written; a later "
    "\"instead\") or behind a cost that keeps the permanent (Thawing Glaciers), lasting mana beside an "
    "ability that sacrifices the permanent for more (Crystal Vein), exhaust abilities, a land whose "
    "type or copy is chosen as it enters, a fetch land with its own entry rule, a non-land permanent "
    "that grants or sets land types (Prismatic Omen, Realmwright's chosen type, Blood Moon beside "
    "other colours), a grant to every land of anything but \"{T}: Add\" one mana, and triggered mana "
    "other than the named floors below. Convention: Exotic Orchard and Fellwar Stone make the "
    "commander's colours (opponents' lands are not modelled). Named floors (not credited): Treasure "
    "and other mana tokens; rituals and other instants and sorceries that add mana; cost reducers and"
    " commander cost reductions; mana from tapping or sacrificing other creatures (Heritage Druid, "
    "Elven Chorus, Cryptolith Rite, Sliver grants to other Slivers, Ashnod's Altar, Phyrexian Tower's"
    " second ability); Crime Novelist's mana when an artifact is sacrificed; untappers (Dramatic "
    "Reversal, Seedborn Muse, Quirion Ranger, Wirewood Symbiote, Wirewood Lodge's untap); mana that "
    "needs the graveyard, the hand or opponents; Three Tree City's chosen type; growth past printed "
    "power (Marwyn, the Nurturer, Vivi Ornitier and Kami of Whispered Hopes are credited at their "
    "printed power); Rubble Rouser; Mutable Explorer's token; Extraplanar Lens (the goldfish casts "
    "it and exiles no land to it, so it adds no mana); Emrakul, the Exigent Doom's untap and hand "
    "ability; Growing Rites of Itlimoc's transformation (cast as its front); Urza's Saga's chapter "
    "III search; \"Nonbasic lands are\" a type in a deck of that type's one colour (Harbinger of the "
    "Seas' Islands in a mono-blue deck), not applied to the goldfish's own lands; an Aura that makes "
    "another permanent a colourless land (Imprisoned in the Moon). Dryad Arbor is a land and never "
    "attacks. Restricted mana (\"Spend this mana only ...\") counts in full, an over-credit."
)

# card_mana_model verdicts that name a floor in this deck's own words
# ("printed power": a variable amount counted at the card's printed power,
# its growth not credited).
MANA_FLOOR_VERDICTS = MANA_FLOORS + ("trigger floor", "needs another resource", "minus loyalty",
                                     "grant floor", "printed power", "land types set, not applied")


def goldfish_mana_methodology(context: dict, decklist: list[str]) -> str:
    """The mana paragraph of the goldfish methodology: the fleet-wide rules
    (GOLDFISH_MANA_METHODOLOGY), then this deck's own cards in each modelled
    class and the ones whose mana is a named floor, read from its profiles
    and the verdicts card_mana_model left on them. A class the deck has no
    card in is left out."""
    profiles = context["profiles"]
    names = sorted(set(decklist) | {context["commanderName"]})

    def having(test) -> str:
        return ", ".join(name for name in names if test(profiles[name]))

    classes = [
        ("fetch lands, cracked as they are played", having(lambda p: p["landCrack"])),
        ("one-shot mana", having(lambda p: p["manaOnce"])),
        ("untapped with mana left", having(lambda p: p["onceRearm"])),
        ("imprint", having(lambda p: p["imprint"])),
        ("lands that take lands as they enter", having(lambda p: p["landEntryCost"])),
        ("land-fetching permanents", having(lambda p: p["landFetch"])),
        ("mana read on the battlefield", having(lambda p: p["manaBoard"])),
        ("all of one activation's mana one colour", having(lambda p: p["manaOneColour"])),
        ("colours granted to every land", having(lambda p: p["landGrant"])),
        ("mana as spells are cast", having(lambda p: p["manaOnCast"])),
        ("mana creatures that tap instead of attacking", having(
            lambda p: (p["manaAtoms"] or any(t[0] != "extra" for t in p["manaBoard"]))
            and p["manaTapsSelf"] and "Creature" in p["typeWords"] and not p["isLand"]
            and not p["vigilance"])),
        ("vigilant mana creatures, which attack and pay (M9)", having(
            lambda p: (p["manaAtoms"] or any(t[0] != "extra" for t in p["manaBoard"]))
            and p["manaTapsSelf"] and "Creature" in p["typeWords"] and not p["isLand"]
            and p["vigilance"])),
    ]
    floors = []
    for name in names:
        verdicts = sorted({verdict for _, verdict in profiles[name]["manaVerdicts"]
                           if verdict in MANA_FLOOR_VERDICTS})
        if verdicts:
            floors.append(f"{name} ({', '.join(verdicts)})")
    parts = [f"{label}: {cards}" for label, cards in classes if cards]
    if floors:
        parts.append("abilities not credited: " + ", ".join(floors))
    return GOLDFISH_MANA_METHODOLOGY + (" In this deck, " + "; ".join(parts) + "." if parts else "")


def compute_goldfish_section(decklist: list[str], deck_data: dict, metadata: dict,
                             commander_name: str, commander_colors: list[str],
                             deck_id: str = "") -> tuple[dict, dict]:
    """Compute solitaire goldfish metrics + tutor-aware combo assembly for a deck.

    Returns ``(goldfish_section, combo_assembly)``; the assembly curves are
    derived from the same Monte-Carlo run (DEC-363), not a separate closed form.
    """
    context = build_goldfish_context(decklist, deck_data, metadata, commander_name,
                                     commander_colors, deck_id)
    meaningful_threshold = max(
        GOLDFISH_MEANINGFUL_PRESSURE_FLOOR,
        int(round(compute_avg_cmc(decklist, metadata) * 2)),
    )
    import multiprocessing
    # Fixed chunk count (independent of CPU count) keeps the seeded run identical
    # across machines: GOLDFISH_CHUNKS deterministic chunks, each with its own seed.
    base, remainder = divmod(GOLDFISH_GAMES, GOLDFISH_CHUNKS)
    chunk_sizes = [base + (1 if i < remainder else 0) for i in range(GOLDFISH_CHUNKS)]
    chunk_args = [
        (decklist, context, games, meaningful_threshold, GOLDFISH_SEED + i)
        for i, games in enumerate(chunk_sizes) if games > 0
    ]
    n_workers = min(GOLDFISH_CHUNKS, os.cpu_count() or 4)
    with multiprocessing.Pool(n_workers) as pool:
        chunk_results = pool.map(_run_goldfish_chunk, chunk_args)
    stats = merge_goldfish_stats(chunk_results)

    by_turn = {}
    commander_curve = {}
    threat_curve = {}
    meaningful_curve = {}
    lethal_curve = {}
    combo_curve = {}

    for turn in range(1, NUM_TURNS + 1):
        commander_curve[str(turn)] = pct(stats["commander_cast"][turn], GOLDFISH_GAMES)
        threat_curve[str(turn)] = pct(stats["first_threat"][turn], GOLDFISH_GAMES)
        meaningful_curve[str(turn)] = pct(stats["meaningful_board"][turn], GOLDFISH_GAMES)
        lethal_curve[str(turn)] = pct(stats["lethal_proxy"][turn], GOLDFISH_GAMES)
        combo_curve[str(turn)] = pct(stats["combo_lethal"][turn], GOLDFISH_GAMES)
        by_turn[str(turn)] = {
            "lands": mana_stats(stats["lands"][turn]),
            "rampPermanents": mana_stats(stats["ramp"][turn]),
            "threats": mana_stats(stats["threats"][turn]),
            "availableMana": mana_stats(stats["available_mana"][turn]),
            "pressureScore": mana_stats(stats["pressure"][turn]),
            "combatPressure": mana_stats(stats["combat"][turn]),
            "cumulativeDamageProxy": mana_stats(stats["cumulative_damage"][turn]),
            "commanderCast": commander_curve[str(turn)],
            "firstThreat": threat_curve[str(turn)],
            "meaningfulBoard": meaningful_curve[str(turn)],
            "lethalProxy": lethal_curve[str(turn)],
            "comboLethal": combo_curve[str(turn)],
        }

    combo_lines = context.get("comboLines", [])
    combo_assembly = combo_assembly_from_goldfish(
        context.get("assemblyLines", []), stats["combo_assembled"])
    # The deck's X spells the cast loop casts under the X rule (X_SPELL_MIN_X):
    # every X card it can cast from hand (a line piece with {X} is reserved,
    # decision C). They decide the X wording of the methodology below.
    x_spells = sorted(
        name for name, profile in context["profiles"].items()
        if profile["manaCost"]["X"] and not goldfish_never_casts(name, profile, context))
    x_creature_score = ", MV + X for an X creature cast with X paid" if x_spells else ""
    section = {
        "numGames": GOLDFISH_GAMES,
        "byTurn": by_turn,
        "comboLines": [
            {"pieces": line["pieces"]} for line in combo_lines
        ],
        "speed": {
            "commanderCast": {
                "byTurn": commander_curve,
                "medianTurn": median_turn_from_cumulative(commander_curve),
            },
            "firstThreat": {
                "byTurn": threat_curve,
                "medianTurn": median_turn_from_cumulative(threat_curve),
            },
            "meaningfulBoard": {
                "byTurn": meaningful_curve,
                "medianTurn": median_turn_from_cumulative(meaningful_curve),
            },
            "lethalProxy": {
                "byTurn": lethal_curve,
                "medianTurn": median_turn_from_cumulative(lethal_curve),
            },
            "comboLethal": {
                "byTurn": combo_curve,
                "medianTurn": median_turn_from_cumulative(combo_curve),
            },
        },
        "methodology": (
            f"{GOLDFISH_GAMES:,}-game solitaire heuristic. Every turn draws a card, turn 1 "
            "included: the simulation models a four-player free-for-all Commander game, in which "
            "no player skips the draw step of their first turn (CR 103.8c). Sequencing: land "
            "drop, cheapest ramp, "
            "commander on affordability, combo/assembly pieces, biggest affordable threat, then "
            "other proactive spells. "
            "Mana is spent once per turn: the turn's pool is built after the land drop and each "
            "cast removes the sources it paid with, so the whole turn's casts (plus the combo and "
            "engine-activation gates, which are checked against what is left) never exceed the "
            "available mana (DEC-937). Sources that come online untapped mid-turn join the pool. "
            "Cast priority holds mana for the line instead of emptying the pool into filler "
            "(DEC-944). The commander, mana sources and the castable cards named by the deck's "
            "combo gate or KEY_COMBOS assembly slots (not a card named only in a list of a combo "
            "line's pieces or in a slot flagged noPriority) are cast freely — mana sources are mana-positive across "
            "the turn and a piece cast advances a line rather than spending it. Every other cast "
            "is filler, and filler is skipped when the pool it would leave behind no longer pays "
            "for (a) a combo or assembly line that was reachable this turn before the cast, or "
            "(b) the deck's configured paid activations: one commander Egg activation while the "
            "hatch engine is online (DEC-938) and one Aggravated Assault combat while the "
            "enchantment is out with an attacker (DEC-940). The gate outranks the activations: "
            "an Egg activation, a Skullclamp equip or an extra combat is itself skipped when "
            "paying for it would lose a reachable gate. A hold the pool cannot afford at all is "
            "dropped rather than left blocking development. One activation of each kind is held, "
            "not an open-ended budget. Decks with no combo win condition, no KEY_COMBOS entry and "
            "no configured engine have no holds and sequence exactly as before. "
            f"Meaningful board = pressure score >= {meaningful_threshold} or 2+ threats. "
            f"Lethal proxy = cumulative combat-pressure proxy >= {GOLDFISH_LETHAL_DAMAGE_PROXY}; "
            "combat pressure uses mana-value-based creature scoring (min(8, MV) plus one for a "
            "listed combat keyword" + x_creature_score + ") so the curve stays comparable "
            "across the fleet — printed "
            "power/toughness is in the card metadata since DEC-940 but is deliberately not used "
            "for the damage sum, only for the combat modifiers' power gates. "
            "Combo lethal = at least one winConditions[] entry tagged kind:'combo' has all pieces "
            "present (hand, battlefield, or supplied by a substitute) and the combined mana cost "
            "payable. A substitute is a tutor or recursion card in hand (decklist[] role tutor or "
            "recursion), read by its tags (combo-check step 1, owner-approved 2026-11-24): the card "
            "types, subtypes, colours and mana value it may find or return, read on the piece's front "
            "face and printed mana value, and where it puts the card. Into the hand (a tutor; Final "
            "Parting's hand half), back to the hand or castable from the graveyard (a recursion "
            "card): the card and the piece are paid. Onto the battlefield (a tutor or a recursion "
            "card): the card is paid, not the piece, and it never supplies a piece the line's minX "
            "lists or its start piece. Beseech the Mirror, bargained, casts a piece of mana value 4 "
            "or less that the line's minX does not list free, sacrificing an artifact or "
            "enchantment; otherwise the piece goes to the hand. A "
            "card with {X} in its cost pays X = the piece's mana value. A card with a separate search "
            "or return cost (tutor_cost, recursion_cost) pays its cast and that cost if its front face "
            "is a permanent, that cost alone otherwise (cycling, transmute). Each extra cost (a "
            "creature, a green creature or an artifact sacrificed, a creature card discarded, the "
            "bargain object) takes its own object: never the commander, a piece of the line, a card "
            "the assignment uses or a permanent whose mana comes from sacrificing it (Lotus Petal); "
            "a land or a token is never sacrificed or bargained, but a land creature card in hand "
            "(Dryad Arbor) can be discarded. A Theros god is a creature to sacrifice only once its "
            "devotion (the colours and number its text names, counted as for Nykthos over the mana "
            "costs of the non-land permanents as the check starts, its own included; a Room counts "
            "only its first door, the door the goldfish casts, as it never unlocks the other, which "
            "reads too little) is met: a cast that would add devotion that turn is not counted "
            "(reads too little), nor a sacrifice that would remove it (reads too much; no deck "
            "holds two gods whose creature status depends on devotion); below "
            "it, it is still the bargain object as an enchantment and, in the hand, a creature card "
            "to discard. Each card supplies one piece; a permanent "
            "piece cast from the hand may also supply one other piece with its own ability (Sun "
            "Titan returning Kaya's Ghostform), paying only that ability's cost. Every assignment of "
            "the missing pieces to different cards is tried. Supplying nothing until the goldfish "
            "casts tutors and recursion cards from the hand, uses abilities and lands (step 2) and "
            "tracks the "
            "graveyard (step 3): a card that puts the found card on top of the library or into the "
            "graveyard, an ability that cannot act the turn the card is cast (tutor_timing / "
            "recursion_timing 'later'), a land in hand, a card that returns only itself or acts only "
            "after a permanent dies, and a no-credit card (tutor_mode or recursion_mode 'none': a "
            "restriction the tags cannot state, where crediting it would mostly be wrong). Other "
            "restrictions the tags cannot state are credited, the gap a known limit: a condition not "
            "tested (Victimize, Unfinished Business, Gamble, Underworld Breach), several cards counted "
            "as one (Agadeem's Awakening, Victimize), a restriction read wider than the text "
            "(Elena, Turk Recruit's historic card). Not tracked: the graveyard (a piece a recursion "
            "card could return is assumed to be in it, an over-read) and a tutor's target in the "
            "library. Not counted: life paid, cards exiled from the graveyard, a random discard, "
            "equip (but a combo line's listed haste Equipment, winConditions[].readyHaste, pays its "
            "equip), improvise; a card that finds or returns several counts one, and a piece put onto "
            "the battlefield does not then supply another piece with its own ability. A split card "
            "is read by its first half's type. In a cost, hybrid and Phyrexian mana symbols are read "
            "as free (devotion counts them). "
            "Held back as interaction (owner-approved 2026-11-23): a card whose primary role in "
            "this deck is removal-spot, removal-board, counterspell or protection and that is an "
            "instant or sorcery (no permanent type on its type line) is never cast from the hand, "
            "as the goldfish has no opponents' cards or spells to answer; its secondary role, guide "
            "categories and text are not read, and the commander is never held. A permanent with "
            "one of those roles (a creature, an Aura, an Adventure creature) is cast like any other "
            "card; a modal card with a spell front and a land back is played as that land unless it "
            "is a line piece kept in the hand (below; a Pathway, a land on both faces, enters as "
            "either), and a transforming card is cast as its front (verdant-tide's Growing Rites of "
            "Itlimoc). A paid mulligan bottoms from a seven with fewer than five lands it can play "
            "the spells it does not keep first (a held card before the others, then the dearest), "
            "then the spells it keeps (the combo checks' cards and a deploy engine's configured "
            "Equipment, the dearest first, a held card among them too: gandalf-party-guest's Muddle "
            "the Mixture), then lands; from five or more, a land first. An imprint "
            "exiles first, if it can, a held card or an alternative a combo line or a table slot keeps "
            "in the hand and no line names plainly, ranked together (the most colours, then the highest "
            "mana value, then the name latest in the alphabet, first), ahead of the castable cards; never a "
            "kept card or another "
            "reserved card. "
            "Known limits: a creature is credited by mana value, by what the general parsers read in "
            "its text (a draw as it enters: exponential-growth's Zegana, Utopian Speaker; its mana) "
            "and by what an engine table credits (The Great Goblin's damage per amass, Vodalian "
            "Hexcatcher's anthem); not credited: a removal ability as it enters, Orcish Bowmasters' "
            "ping and amass; a permanent whose text damages or "
            "destroys creatures is cast and nothing is applied to the pilot's own board "
            "(hoard-and-bleed's Spiteful Banditry, cast under the X rule, deals no damage; "
            "verdant-tide's Whiptongue Hydra destroys nothing), nor a mandatory target or a "
            "symmetric sacrifice; an Aura is cast without checking that something can be "
            "enchanted (creeping-corruption's Corrupted Conscience, as before); ordinary paid equips "
            "are not modeled: an Equipment cast from the hand stays unattached and counts by its "
            "pressure score (shield-doctrine's Mjölnir, Hammer of Thor and Sword of Fire and Ice), "
            "or, if it is also a creature, as any creature does, by its mana value "
            "(shield-doctrine's The Reality Chip: 2 pressure, and 2 combat once ready), except where "
            "a table models an attachment: broodfire-hatchery's "
            "Thornbite Staff attaches to the commander when she enters after it, and its "
            "Skullclamp's {1} equip on a 0/1 Egg (the commander's or Palani's Hatcher's) draws two, "
            "while Nesting Dragon's 0/2 Dragon Egg survives the -1 and draws nothing; "
            "armory-protocol's deploy engine, once the "
            "commander has transformed, puts one artifact from the hand onto the battlefield free at "
            "each combat (a put, not a cast; never a reserved card, below), the one with the highest "
            "score, as that deck's own "
            "methodology states: an Equipment it "
            "puts out counts as attached and adds its table's bonus to the commander's damage (none "
            "when the table does not list it), its own pressure score applying once it is out, and "
            "only the table's Equipment is held in the hand for it; +1/+1 counter growth is not modeled, "
            "so a counter doubler adds no damage of its own; a protection spell with a proactive "
            "use (a pump, a draw) is held; gathering-shadow's Foray of Orcs is in the amass table "
            "but held as a removal sorcery, so its amass never counts. "
            "In a deck with a combo win condition or a KEY_COMBOS line, the tutor and recursion "
            "cards, and the combo-line and assembly pieces whose front face is not a permanent or "
            "that have {X} in their cost (owner-approved 2026-11-23), are reserved from filler "
            "casting from the hand; in a deck with neither, the reservation of tutor and recursion "
            "cards is lifted, and the other rules still apply (a held instant or sorcery stays "
            "held; a modal card with a spell front and a land back is still played as its land). "
            "Those line pieces kept in the hand are also never played as a land, counted as a land "
            "by the mulligan, deployed free or cast from a cascade. A reserved tutor or recursion "
            "card is neither cast from the hand nor deployed free (it is left in the hand), but one "
            "played as a land (a land, or a modal card with "
            "a land back) is played and counted as a land, and a cascade can free-cast any other "
            "that is a permanent. A commander with {X} named in a combo line's pieces is "
            "cast from the command zone at X = 0; one named only in a KEY_COMBOS slot waits for a "
            "positive X under the X rule (no commander in the fleet has {X}). "
            "The spells a paid mulligan keeps, bottoming them last of "
            "the spells, are the line pieces (not a card named only in a list of a combo line's pieces "
            "or in a slot flagged noPriority), the tutor and recursion cards whose tags can supply one "
            "of the deck's line pieces from the hand, and a deploy engine's configured Equipment. "
            "Other limitations: "
            "lines that do not win with the pieces they list still count, no opponent interaction, "
            "no multi-turn assembly tracking, no stack-trigger ordering."
        ) + goldfish_mana_methodology(context, decklist),
    }
    if any(line["startPiece"] for line in combo_lines):
        section["methodology"] += (
            " A combo line's start piece (winConditions[].startPiece, the piece its loop "
            "starts by casting) is free only if it was the last of the line's pieces to "
            "enter this turn; if it has been on the battlefield since an earlier turn its "
            "cost is paid again; if it entered this turn before a partner, or could only "
            "be put onto the battlefield, the line is not ready that turn."
        )
    priced_x = ordered_unique([f"{piece} at X = {x}" for line in combo_lines for piece, x in line["minX"].items()])
    if priced_x:
        section["methodology"] += (
            " A combo line's X piece (winConditions[].minX, owner-approved 2026-11-19) is "
            "priced at the X of the cheapest direct cast with which the line's listed pieces "
            "work: " + ", ".join(priced_x) + " (each {X} in its cost is X mana). It is "
            "supplied from the hand, by a tutor that puts it into the hand (a bargain tutor by "
            "its paid route to the hand) or by a card that returns it to the hand or lets it be "
            "cast from the graveyard, cast at that X; a card that puts it onto the battlefield "
            "and a bargained free cast do not supply it. Known limits: an X piece a card returns "
            "is assumed to be in the graveyard, which is not tracked (an over-read), and an X piece "
            "already on the battlefield counts whatever X it entered with."
        )
    # The combo-line corrections' fields (owner decision 27, 2026-11-25), each
    # stated where one of the deck's lines uses it (extract_combo_lines).
    ready_pieces = ordered_unique([piece for line in combo_lines for piece in line["readyPieces"]])
    if ready_pieces:
        section["methodology"] += (
            " A combo line's ready pieces (winConditions[].readyPieces, owner-approved 2026-11-25: "
            + ", ".join(ready_pieces) + ", the pieces its loop taps or attacks with) count only once "
            "they have been on the battlefield since the turn began (whether they are untapped is not "
            "checked). One that entered this turn, is cast from the hand or is supplied by a tutor or "
            "recursion card counts only with one of the line's haste sources "
            "(winConditions[].readyHaste), chosen with the rest of the line's cost so that the cheapest "
            "payable one counts: a static grant on the battlefield, free; an Equipment on the "
            "battlefield, at its equip cost, or an instant in the hand, at its cost, each for one piece. "
            "A source the line relies on is never sacrificed or bargained for it. Known limits: a grant "
            "a creature gets only as it enters after the grant (riot, a trigger) is read as static, an "
            "over-read when the piece entered first; an equip is charged without checking that it can "
            "be activated (at sorcery speed, on a creature that can be targeted); a listed haste "
            "instant counts only while it is still in the hand, and the goldfish, which does not hold "
            "it for the line, may already have cast it, an under-read."
        )
    cast_pieces = ordered_unique([piece for line in combo_lines for piece in line["castFromHand"]])
    if cast_pieces:
        section["methodology"] += (
            " A combo line's cast pieces (winConditions[].castFromHand, owner-approved 2026-11-25: "
            + ", ".join(cast_pieces) + ") count only when cast during the combo: from the hand, or "
            "supplied by a tutor that puts one into the hand or a card that returns one to the hand "
            "or lets it be cast from the graveyard; one on the battlefield does not count, and a card "
            "that puts one onto the battlefield or a bargained free cast does not supply it. The "
            "goldfish keeps them in the hand, for every line of the deck, not only the line that asks "
            "for it: it never casts one from the hand, plays one as a land, deploys one or casts one "
            "from a cascade."
        )
    if any(line["needsCreature"] for line in combo_lines):
        section["methodology"] += (
            " A combo line that needs a creature to target (winConditions[].needsCreature) is ready "
            "only with that many creatures on the battlefield that are not its pieces (a land creature "
            "counts; a Theros god once its devotion is met), and no extra cost of the line takes one "
            "of them; tokens are not seen, an under-read."
        )
    if any(line["extraCost"] is not None for line in combo_lines):
        section["methodology"] += (
            " A combo line's extra cost (winConditions[].extraCost, owner-approved 2026-11-25: mana "
            "its loop pays besides casting its pieces) is added to the line's cost each time it is "
            "counted, its pieces on the battlefield or not."
        )
    commander_pieces = ordered_unique([piece for line in combo_lines for piece in line["pieces"]
                                       if piece == commander_name])
    if commander_pieces:
        section["methodology"] += (
            " A commander named as a combo line's piece (" + ", ".join(commander_pieces) + ") counts "
            "only on the battlefield: a tutor or recursion card never supplies it."
        )
    listed = any(line["alternatives"] for line in combo_lines)
    flagged = any(slot["noPriority"] for line in context.get("assemblyLines", []) for slot in line["slots"])
    if listed:
        section["methodology"] += (
            " A list in a combo line's pieces (owner-approved 2026-11-25) is a choice of one of its "
            "cards: the entry counts as one line per choice."
        )
    if listed or flagged:
        where = " or ".join(text for text, used in (("in a list of a combo line's pieces", listed),
                                                    ("in a KEY_COMBOS slot flagged noPriority", flagged)) if used)
        section["methodology"] += (
            " A card named only " + where + " (owner-approved 2026-11-25) is no line member: it is "
            "cast like any other card (no cast priority, held back for a reachable gate) and gets no "
            "paid-mulligan keep and no imprint protection from that line (an imprint may exile it: "
            "with the held cards when it is kept in the hand, else as a castable card); it is kept in the hand like a line piece when its front face is not a "
            "permanent or it has {X}."
        )
    if x_spells:
        # Only this deck's own X_SPELL_DRAW cards, in the table's words.
        draws = ", ".join(f"{name} {X_SPELL_DRAW[name][0]}"
                          for name in x_spells if name in X_SPELL_DRAW)
        x_tokens = bool(context.get("tokenMakers")
                        and set(x_spells) & set(context["tokenMakers"]["perX"]))
        section["methodology"] += (
            " X spells modeled (owner-approved 2026-11-18): a spell with {X} in its mana "
            "cost keeps its place in the cast order (never the ramp tier) and, when "
            "reached, is cast with X = the largest value the mana left pays after its "
            "coloured pips and the holds above, with no mana-source exemption; {X}{X} "
            f"costs two per X. Below X = {X_SPELL_MIN_X} it stays in hand and the next "
            "spell is tried. Combo-line pieces and KEY_COMBOS assembly members with {X} are "
            "not cast from the hand (owner-approved 2026-11-23): they stay there for the combo "
            "checks (a commander with {X} named in a combo line's pieces is cast from the command "
            "zone at X = 0; one named only in a KEY_COMBOS slot falls under this rule), and the "
            "combo gate prices its pieces at X = 0"
            + (" except the X pieces above" if priced_x else "") + ". "
            "Credited at the paid X: a creature's combat, and a threat creature's pressure "
            "score, read mana value + X (capped at 8, keyword bonus as before)"
            + (f"; cards drawn: {draws}" if draws else "")
            + ("; amass X spells amass X, and Saruman, the White Hand's amass counts the X "
               "paid" if context.get("amassEngine") else "")
            + ("; X token spells make their tokens at the X paid (token makers below)"
               if x_tokens else "")
            + ". Every other X effect (" + ("" if x_tokens else "tokens, ")
            + "life loss, damage, tutoring, pumps, "
            "proliferate, recursion, manifest) is not credited: those spells are only "
            "re-timed. Floors: convoke, improvise and cost reducers are not modeled."
        )
    cascade = context.get("cascade")
    if cascade:
        section["methodology"] += (
            f" Commander-granted cascade modeled (DEC-385): with the commander on the battlefield, "
            f"each {'colorless ' if cascade.get('colorlessOnly') else ''}spell of mana value "
            f"{cascade['minValue']}+ cast from hand resolves {cascade['triggers']} cascade trigger(s) — "
            "dig the library for the first cheaper nonland card, read as it is in the library (a "
            "modal DFC whose front is a spell is one), free-cast it (a card held back as "
            "interaction, a combo-line or assembly piece whose front face is not a permanent or "
            "that has {X} in its cost, a reserved tutor or recursion card that is not a permanent, "
            "and a card the goldfish plays as its land face are declined and bottomed), bottom the "
            "rest; "
            + ("free-casts do not re-trigger (from-hand grant)."
               if cascade.get("fromHandOnly") else "qualifying free-casts re-trigger.")
        )
    copy_engine = context.get("copyEngine")
    if copy_engine:
        if copy_engine["mode"] == "per_other_creature":
            gate_text = (
                "each instant/sorcery that targets only a single creature resolves one extra "
                "copy per other creature you control (qualifying fuel is held in hand until "
                "the commander is online)"
            )
        else:
            gate_text = (
                f"each instant/sorcery cast resolves one extra copy while {copy_engine['tapCost']} "
                f"untapped creatures remain to tap (each use taps {copy_engine['tapCost']} for the "
                "turn — board-state gated, not always-on)"
            )
        section["methodology"] += (
            f" Commander copy-trigger engine modeled (DEC-393): with the commander on the "
            f"battlefield, {gate_text}. Creature counts = creature permanents + a stat-less "
            "ledger of creature tokens from resolved spells (fixed counts only; X-spells and "
            "storm credit 0, so copy counts are floors). Copies re-credit draw and land-ramp "
            "but are not cast (CR 707.10) — they never re-trigger the engine."
        )
    token_engine = context.get("tokenEngine")
    if token_engine:
        section["methodology"] += (
            f" Commander token-swarm engine modeled (DEC-404): with the commander on the "
            f"battlefield, each {'noncreature ' if token_engine['nonCreatureOnly'] else ''}"
            f"spell cast mints one {token_engine['tokenPower']}-power token per "
            f"{{{token_engine['pipColor']}}} symbol in its printed mana cost. Tokens attack "
            "from the turn after minting (summoning sickness); each contributes tokenPower "
            f"plus one per battlefield anthem ({len(token_engine['anthemNames'])} tracked), "
            "and the commander adds one damage per ready token once he can attack (variable "
            "power). A copy of a spell made on the stack is not cast (CR 707.10) and never "
            "mints. A card that lets its controller cast a copy (Harmonized Trio, prepared) does "
            "cast it, and a free cast is a cast too: either would trigger the commander (his "
            "trigger is on casting, paid or not), but the engine is credited only on the cast "
            "loop's casts from the hand, so neither mints: a limit of the model, which reads too "
            "little. "
            "Counts are floors: X pips credit printed symbols only, anthems don't pump "
            "nontoken creatures, and token-hit draw engines are not modeled."
        )
    deploy_engine = context.get("deployEngine")
    if deploy_engine:
        section["methodology"] += (
            " Commander transform/free-deploy engine modeled (DEC-405): once the "
            "commander is in play, the transform activation "
            f"({deploy_engine['transformCost']['generic']} generic + colored pips; "
            f"{deploy_engine['reducedTransformCost']['generic']} generic with "
            f"{deploy_engine['reducerName']} on the battlefield) is paid on "
            "affordability like any other cast. From the transform turn (haste) the "
            f"{deploy_engine['transformedPower']}-power back face attacks every turn, "
            "and one artifact from hand is put onto the battlefield free at each "
            "combat, never a card reserved for the combo checks (in a deck with a combo or "
            "KEY_COMBOS line, a line piece kept in the hand and the tutor and recursion cards: it is "
            "left in the hand), the one with the highest score: an Equipment by its attach bonus (0 when the "
            "table does not list it; one listed in the table's double-strike names, while none of "
            "those is attached, by its bonus plus the commander's whole swing; one that grants "
            "double strike but is not listed, such as Genji Glove, scores 0 and loses to The Reaver "
            "Cleaver's 1), an artifact creature by its combat score, another artifact "
            "by its pressure score, which adds no combat damage (so Nexus of Becoming, 8, goes "
            "before Kaldra Compleat, bonus 5), ties to the higher mana value, then to the name "
            "later in alphabetical order. "
            "Deployed creatures are summoning-sick; every deployed Equipment counts as attached "
            f"and adds its attach bonus to commander damage ({len(deploy_engine['equipmentPower'])} "
            "configured), its own pressure score applying once it is out; an Equipment listed in "
            "the table's double-strike names doubles the commander's damage while attached. "
            "Configured Equipment are held in hand as deploy fuel (no equip-cost path "
            "exists in the sim). Floors: the front-face artifact dig, Nexus of "
            "Becoming's second deploy stream, backup attachers, and paid equips are "
            "not modeled."
        )
    draw_engines = context.get("drawEngines") or {}
    activated_engines = {name: cfg for name, cfg in draw_engines.items() if "maxActivations" in cfg}
    triggered_engines = {name: cfg for name, cfg in draw_engines.items() if "drawsPerTurn" in cfg}
    if activated_engines:
        engine_list = ", ".join(
            f"{name} (max {cfg['maxActivations']} activations)"
            for name, cfg in sorted(activated_engines.items())
        )
        section["methodology"] += (
            f" Activated draw engines modeled (DEC-472): {engine_list}. Each turn on the "
            "battlefield the engine activates once — its counter total grows by one and "
            "that many cards are drawn (the cast-turn draw stays on the immediateDraw "
            "path). maxActivations is the stopping rule standing in for The One Ring's "
            "upkeep life loss, which the goldfish does not track. Floors: the on-cast "
            "protection turn and opponent-dependent draw taxes (Rhystic Study / Mystic "
            "Remora class) are not modeled."
        )
    if triggered_engines:
        engine_list = ", ".join(
            f"{name} ({cfg['drawsPerTurn']} per turn)"
            for name, cfg in sorted(triggered_engines.items())
        )
        section["methodology"] += (
            f" Recurring draw triggers modeled (owner-approved 2026-11-17): {engine_list}. "
            "These stand in for draws on opponents' turns (The Theorist, Jace Beleren: one "
            "card at the beginning of each opponent's draw step), so the cards are drawn at "
            "the start of each of your turns from the turn after the permanent is cast. "
            "Assumes all three opponents stay in the game and the permanent survives; there "
            "is no stopping rule."
        )
    hatch_engine = context.get("hatchEngine")
    if hatch_engine:
        section["methodology"] += (
            " Commander hatch engine modeled (DEC-938): with the commander on the "
            "battlefield and at least one instant-speed sacrifice outlet "
            f"({len(hatch_engine['instantOutletNames'])} free/unlimited, "
            f"{len(hatch_engine['limitedOutletNames'])} once-per-untap) online, each "
            "Egg that dies reveals from the top of the library until a creature card "
            "and puts it onto the battlefield free — a put, not a cast, so it credits "
            "impact, combat and draw like a cast but never re-triggers a cast-gated "
            "model. Egg supply per own turn: commander activations paid at "
            f"{hatch_engine['activationCost']['generic']} generic out of what the "
            f"turn's casts left, one per untap and at most "
            f"{hatch_engine['maxEggsPerTurn']} before doublers (Thornbite Staff, if it "
            "was on the battlefield when she entered, untaps her as an Egg dies to any "
            "outlet; a further activation that turn only while Ashnod's Altar is out "
            "to pay it), plus entry Eggs (Palani's Hatcher's two, doubled again by Elesh "
            "Norn) and one per land drop from a landfall Egg maker the turn after it "
            f"lands. Each of {len(hatch_engine['tokenDoublerNames'])} token doublers "
            f"doubles every Egg; each of {len(hatch_engine['extraHatchNames'])} "
            "trigger doublers adds one hatch per death. Skullclamp equips own-turn "
            f"Eggs at {hatch_engine['sorceryOutletCost']['generic']} generic each and "
            f"credits {hatch_engine['sorceryOutletDraw']} cards, but only the 0/1 "
            "Eggs — its +1/-1 leaves Nesting Dragon's 0/2 Dragon Egg alive as a 1/1, "
            "so those are tracked apart and only the free/limited outlets eat them. "
            "Seedborn Muse adds "
            f"{hatch_engine['untapStepActivations']} free activations on the "
            "opponents' untap steps (instant-speed outlets only; those creatures are "
            "ready next turn regardless of haste). Attack-triggered hatches (Raph & "
            "Mikey) enter attacking and are ready the same combat. Hard cap "
            f"{hatch_engine['maxHatchesPerTurn']} hatches per turn — the Thornbite "
            "infinite is scored by the combo systems, not here. Floors: no blockers "
            "or opponents, Eggs left over never block or trade, the Dinosaur and "
            "Dragon tokens that Egg sacrifices leave behind are not credited, "
            "Skullclamp and Palani's Hatcher do not open the engine on their own, "
            "ramp-fetched lands do not trigger landfall, and Maskwood Nexus turning "
            "every creature into an Egg, the paid Zopandrel/Mondrak outlets, "
            "Thornbite Staff's equip (cast after the commander, it never attaches) and "
            "opponent-end-step hatching beyond Seedborn are unmodelled."
        )
    token_makers = context.get("tokenMakers")
    if token_makers:
        # One phrase per maker kind the config holds; an empty one is left out.
        on_resolve = sorted(token_makers["onResolve"].items())
        makers = [
            ("creature tokens as a card resolves or enters",
             ", ".join(f"{name} {creatures}" for name, (creatures, _) in on_resolve
                       if creatures)),
            ("X spells at the X paid",
             ", ".join(f"{name} {'X' if per_x == 1 else f'{per_x}X'}"
                       for name, per_x in sorted(token_makers["perX"].items()))),
            ("whenever you attack, tapped and attacking, from the turn after the maker "
             "is cast",
             ", ".join([f"{name} {count}"
                        for name, count in sorted(token_makers["attackMakers"].items())]
                       + [f"{name} one more each attack (1, 2, 3 ...)"
                          for name in sorted(token_makers["growingAttackMakers"])])),
            ("one per natural land drop while on the battlefield",
             ", ".join(sorted(token_makers["landfallMakers"]))),
            ("at most once per turn each, after combat, in this order, paid out of the "
             "mana the turn's casts left",
             ", ".join(f"{name} ("
                       + " + ".join(f"{amount} {key}" for key, amount in cost.items())
                       + ("; only with a tapped creature, one that attacked or was tapped "
                          "for mana, which it untaps"
                          if name in token_makers["needsTappedCreature"] else "")
                       + ")"
                       for name, cost in sorted(token_makers["activatedMakers"].items()))),
            ("Food as a card resolves or enters",
             ", ".join(f"{name} {food}" for name, (_, food) in on_resolve if food)),
        ]
        text = (" Token makers modeled (owner-approved 2026-11-18): this deck's token "
                "makers feed the DEC-404 token ledger, one creation event per resolution, "
                "trigger or activation. Credited: "
                + "; ".join(f"{label}: {names}" for label, names in makers if names) + ".")
        if token_makers["activatedMakers"]:
            text += (" An activated maker must be untapped and is tapped for its ability "
                     "(its {T}, not in the costs above); a land's own mana then leaves the "
                     "pool.")
        if token_makers["extraFoodName"]:
            text += (f" {token_makers['extraFoodName']} adds one Food to each event before "
                     "any doubler (the controller orders replacement effects, so the Food "
                     "is doubled too); Food made with tokens that enter tapped enters "
                     "tapped.")
        if token_makers["doublerNames"]:
            text += (f" Each of {'; '.join(sorted(token_makers['doublerNames']))} doubles every "
                     "token of an event.")
        if token_makers["artifactTokensReplacedBy"]:
            text += (f" While {token_makers['artifactTokensReplacedBy']} is on the "
                     "battlefield no new Food is credited: it would be a creature token "
                     "the engine does not credit.")
        anthems = ", ".join(sorted(token_makers["anthemNames"]))
        text += (" Combat, the DEC-404 convention: each creature token deals "
                 f"{token_makers['tokenPower']} plus one per anthem on the battlefield"
                 + (f" ({anthems})" if anthems else "")
                 + " every turn from the turn after it is made, tokens made tapped and "
                 "attacking deal damage the turn they are made, every creature token able "
                 "to attack attacks, and no token is ever removed or spent.")
        draw_tokens = token_makers["commanderDrawTokens"]
        text += (f" Commander draw: {context['commanderName']} taps {draw_tokens} "
                 "untapped tokens to draw a card. The cost has no {T} symbol, so "
                 "summoning-sick tokens can pay, and a token that attacked stays tapped "
                 "until your untap step; so at the last opponent's end step before each of "
                 "your turns, while it is on the battlefield, the commander draws one card "
                 f"per {draw_tokens} untapped tokens: every Food except any that entered "
                 "tapped on your last turn, and the creature tokens made on your last turn. "
                 "The cards arrive before your upkeep.")
        not_credited = ["; ".join(f"{', '.join(cards)} ({reason})"
                                  for reason, cards in token_makers["excluded"]),
                        ", ".join(token_makers["notCredited"])]
        if any(not_credited):
            text += (" The maker list is a floor; not credited: "
                     + "; nor ".join(part for part in not_credited if part) + ".")
        if token_makers["notModeled"]:
            text += f" Not modeled: {', '.join(token_makers['notModeled'])}."
        section["methodology"] += text
    haste_sources = context.get("hasteSources")
    if haste_sources:
        section["methodology"] += (
            " Team-haste rule modeled (DEC-938): the combat profile ignores printed "
            "Haste fleet-wide, so a creature that enters — cast or hatched — while "
            f"any of {len(haste_sources['staticNames'])} continuous haste grants, "
            f"both halves of {len(haste_sources['staticPairs'])} configured pair, or "
            f"{len(haste_sources['entryGatedNames'])} entry-gated grant (riot) is on "
            "the battlefield is combat-ready the turn it entered, as are "
            f"{len(haste_sources['printedHasteNames'])} printed-haste creatures. The "
            "commander's tap ability reads the continuous grants live (they cover "
            "her retroactively) but reads riot only off her own entry record, since "
            "riot never hastes a creature already on the battlefield. Floor: the "
            "entry-time rule misses other creatures already out when a continuous "
            "source lands — at most one creature-turn each."
        )
    combat_modifiers = context.get("combatModifiers")
    if combat_modifiers:
        section["methodology"] += (
            " Combat modifiers modeled (DEC-940, DEC-935 Phase 2): the base combat "
            "proxy is unchanged — every creature still scores min(8, MV) plus one for "
            "a listed keyword" + x_creature_score + ", so this deck's per-creature "
            "values stay comparable with "
            "the rest of the fleet, and printed power is read only by the power gate "
            "below. What changes is that the turn can hold up to "
            f"{combat_modifiers['maxCombatPhases']} combat phases, and each phase "
            "applies, in this order: Zopandrel's beginning-of-combat team doubling "
            "(until end of turn, so it compounds once per phase a creature was "
            "present for), Xenagos doubling the single largest other attacker that "
            "was already on the battlefield when the trigger went on the stack, then "
            "Raphael doubling the whole phase (double strike). Extra phases come from "
            "Aurelia and Tifa (first combat only; Tifa gated on a ready attacker with "
            f"printed power >= {combat_modifiers['powerGateThreshold']}; Annie Joins "
            "Up doubles both legendary triggers), Combat Celebrant's exert (it untaps "
            "all other creatures, so it sits out the rest of the turn's combats and "
            "does not untap next turn), and Aggravated Assault paid at "
            f"{combat_modifiers['paidCombatCost']['generic']} generic + "
            f"{combat_modifiers['paidCombatCost']['R']} red out of whatever the turn's "
            "casts and Egg activations left, repeating while the pool allows. The "
            "per-combat hatch triggers (Palani's Hatcher's Egg sacrifice, Raph & "
            "Mikey's attack hatch) fire again at each extra combat, and a creature "
            "that enters during a combat phase counts in that phase but is not a legal "
            "Xenagos target until the next one. Floors, not ceilings: no blockers, no "
            "opponents and no fogs, so every phase connects; Annie also doubling "
            "Zopandrel's trigger (x4 per phase), Roaming Throne under Maskwood Nexus "
            "doubling the combat triggers again, Ghalta and Mavren's attack token, and "
            "Combat Celebrant untapping off a later untap-all effect are all "
            "unmodelled. Only this deck is configured; shield-doctrine, "
            "armory-protocol, hidden-legion, gathering-shadow, anvil-chorus and "
            "eternal-agony carry comparable effects and can opt in later, each with "
            "its own review and a calibration re-run."
        )
    return section, combo_assembly


def combo_assembly_from_goldfish(assembly_lines: list[dict],
                                 combo_assembled_counts: list[dict]) -> dict:
    """Build the comboAssembly section from goldfish per-combo assembly counts.

    Replaces the old closed-form hypergeometric ``compute_combo_assembly`` (DEC-363).
    Each combo's ``byTurn`` is the % of goldfish games in which it was assembled by
    that turn (slots filled by drawn members or by tutors, assembly_tutor_cost), and
    ``bestByTurn`` is the per-turn max across the deck's combos. Output shape is
    unchanged so downstream consumers (health score, UI) need no changes.
    """
    combos = []
    best_by_turn = {str(turn): 0.0 for turn in range(1, NUM_TURNS + 1)}

    for line, counts in zip(assembly_lines, combo_assembled_counts):
        by_turn = {}
        for turn in range(1, NUM_TURNS + 1):
            pct_value = pct(counts[turn], GOLDFISH_GAMES)
            by_turn[str(turn)] = pct_value
            best_by_turn[str(turn)] = max(best_by_turn[str(turn)], pct_value)
        combos.append({
            "name": line["name"],
            "pieces": line["pieces"],
            "requiresCommander": line["requiresCommander"],
            "description": line["description"],
            "byTurn": by_turn,
            "medianAssemblyTurn": median_turn_from_cumulative(by_turn),
        })

    fastest = None
    if combos:
        fastest = min(
            combos,
            key=lambda combo: combo["medianAssemblyTurn"] if combo["medianAssemblyTurn"] is not None else 999,
        )["name"]

    return {
        "combos": combos,
        "bestByTurn": best_by_turn,
        "fastestCombo": fastest,
        "medianAssemblyTurn": median_turn_from_cumulative(best_by_turn),
        "methodology": (
            "Tutor/redundancy-aware Monte-Carlo assembly (DEC-363): share of "
            f"{GOLDFISH_GAMES:,} seeded goldfish games in which every combo slot is filled by "
            "the given turn. A slot is filled by a drawn member (hand or battlefield) or by a "
            "tutor in hand whose tags (combo-check step 1, owner-approved 2026-11-24) allow a "
            "member still in the library: one that puts the card into the hand (Final Parting's "
            "hand half; Beseech the Mirror by its route to the hand) or onto the battlefield (a "
            "permanent member). Each tutor and each member fills one slot (no card is listed in two "
            "slots of a line), every assignment is tried, and the tutors' cost must be payable: "
            "the tutor's use (its cast, plus a separate search cost when it is a permanent; that "
            "cost alone when it is used another way, such as cycling) and X = the member's mana "
            "value, never the member itself. Each extra cost takes its own object (never the "
            "commander or a permanent whose mana comes from sacrificing it; a land or a token is "
            "never sacrificed or bargained, but a land creature card in hand can be discarded; a "
            "Theros god is a creature to sacrifice only once its devotion, read as the check starts, "
            "is met: a cast that would add devotion that turn is not counted, which reads too "
            "little, nor a sacrifice that would remove it, which reads too much; below it, it is the "
            "bargain object as an enchantment), and every filled slot keeps one drawn "
            "member that pays nothing: a member may be sacrificed, discarded or bargained, or cast "
            "as an instant or sorcery tutor, only if another drawn member of its slot is left; a "
            "member that is a permanent tutor stays when cast and pays its cast. The commander slot "
            "is auto-filled from the command zone. Recursion cards fill no slot, and neither do "
            "tutors that put the card on top of the library or into the graveyard, abilities that "
            "cannot act the turn the card is cast, lands in hand and no-credit cards."
        ),
    }


def produced_colors_for_card(name: str, meta: dict, commander_colors: list[str]) -> set[str]:
    """Best-effort color production / fixing derived from oracle text."""
    oracle = meta.get("oracle_text", "")
    lower = oracle.lower()
    colors = set()

    if "add one mana of any color in your commander's color identity" in lower:
        return set(commander_colors)
    if "add one mana of any color" in lower:
        return set(commander_colors)

    add_clauses = re.findall(r"Add([^.\n]+)", oracle)
    for clause in add_clauses:
        colors.update(symbol for symbol in re.findall(r"\{([WUBRG])\}", clause))

    # Fetchlands / land tutors that represent true source access in deck construction.
    if "type_line" in meta and "Land" in meta.get("type_line", "") and "search your library for a" in lower:
        for subtype, color in {
            "plains": "W",
            "island": "U",
            "swamp": "B",
            "mountain": "R",
            "forest": "G",
        }.items():
            if subtype in lower:
                colors.add(color)

    return colors


def is_static_source_card(meta: dict) -> bool:
    """Cards that remain on board and contribute mana after resolution."""
    type_line = meta.get("type_line", "")
    return "Land" in type_line or ("Artifact" in type_line or "Creature" in type_line)


def source_count_for_color(decklist: list[str], metadata: dict, commander_colors: list[str],
                           color: str, deadline_turn: int) -> int:
    """Count sources for a color by a given turn using static board sources only."""
    count = 0
    for name in decklist:
        meta = metadata.get(name, {})
        if not meta or not is_static_source_card(meta):
            continue

        produces = produced_colors_for_card(name, meta, commander_colors)
        if color not in produces:
            continue

        type_line = meta.get("type_line", "")
        cmc = int(meta.get("cmc", 0) or 0)
        if "Land" in type_line:
            count += 1
        elif cmc <= max(1, deadline_turn - 1):
            count += 1
    return count


def compute_probability_curve(card_pool: list[str]) -> dict[str, float]:
    """Probability of seeing at least one card from pool by each turn."""
    hit_count = len(card_pool)
    curve = {}
    for turn in range(1, NUM_TURNS + 1):
        curve[str(turn)] = r1(hypergeom_at_least(99, hit_count, cards_seen_by_turn(turn), 1) * 100)
    return curve


def compute_threat_density(threat_cards: list[str], metadata: dict,
                           mana_counts: dict[int, Counter]) -> dict:
    """Deployable threat density curve over the whole mana distribution
    (owner-approved 2026-11-25). At turn t: the sum over mana totals m of (the
    share of the mana-simulation games with m mana on turn t) x (the chance
    that at least one threat of mana value m or less is among the 7 + t cards
    seen of 99), rounded once. A cutoff at the median mana stepped by a whole
    mana when the games at or below a total crossed 50%. Colours are not read,
    and the mana and the cards seen are taken as independent.

    `mana_counts` maps each turn to its games by mana total."""
    threat_cmcs = [metadata.get(name, {}).get("cmc", 0) or 0 for name in threat_cards]
    by_turn = {}
    for turn in range(1, NUM_TURNS + 1):
        counts = mana_counts[turn]
        games = sum(counts.values())
        chance = sum(
            count / games * hypergeom_at_least(
                99, sum(1 for cmc in threat_cmcs if cmc <= mana), cards_seen_by_turn(turn), 1)
            for mana, count in sorted(counts.items())
        )
        by_turn[str(turn)] = r1(chance * 100)
    return {
        "count": len(threat_cards),
        "examples": ordered_unique(threat_cards)[:8],
        "byTurn": by_turn,
        "medianDeploymentTurn": median_turn_from_cumulative(by_turn),
    }


def compute_reliability_curve(cards: list[str], label: str) -> dict:
    """Shared schema for draw / interaction availability curves."""
    by_turn = compute_probability_curve(cards)
    return {
        "count": len(cards),
        "examples": ordered_unique(cards)[:8],
        "byTurn": by_turn,
        "medianTurn": median_turn_from_cumulative(by_turn),
        "label": label,
    }


def compute_colored_source_adequacy(decklist: list[str], metadata: dict,
                                    commander_name: str, commander_colors: list[str]) -> dict:
    """Hypergeometric colored-source adequacy by spell deadline."""
    if not commander_colors:
        return None

    score_rows = []
    by_color = {}
    candidate_spells = decklist + ([commander_name] if commander_name else [])

    for color in commander_colors:
        rows = []
        for name in candidate_spells:
            meta = metadata.get(name, {})
            if not meta or "Land" in meta.get("type_line", ""):
                continue
            pips = parse_generic_mana_cost(meta.get("mana_cost", ""))
            needed = pips.get(color, 0)
            if needed <= 0:
                continue

            deadline_turn = max(1, min(NUM_TURNS, int(meta.get("cmc", 0) or pips["total"] or 1)))
            sources = source_count_for_color(decklist, metadata, commander_colors, color, deadline_turn)
            probability = hypergeom_at_least(99, sources, cards_seen_by_turn(deadline_turn), needed)
            row = {
                "card": name,
                "pips": needed,
                "deadlineTurn": deadline_turn,
                "sources": sources,
                "probability": r1(probability * 100),
            }
            rows.append(row)
            score_rows.append((probability * 100, needed))

        rows.sort(key=lambda row: (row["probability"], row["deadlineTurn"], row["card"]))
        turn3 = source_count_for_color(decklist, metadata, commander_colors, color, 3)
        turn4 = source_count_for_color(decklist, metadata, commander_colors, color, 4)
        turn5 = source_count_for_color(decklist, metadata, commander_colors, color, 5)
        by_color[color] = {
            "turn3Sources": turn3,
            "turn4Sources": turn4,
            "turn5Sources": turn5,
            "weightedAdequacy": r1(weighted_average([(row["probability"], row["pips"]) for row in rows])),
            "weakSpells": rows[:5],
        }

    overall = r1(weighted_average(score_rows))
    return {
        "overallScore": overall,
        "byColor": by_color,
        "method": ("Hypergeometric source adequacy using cards seen by spell CMC turn (the "
                   "opening seven and one draw a turn from turn 1: the simulators model a "
                   "four-player free-for-all Commander game, in which no player skips the draw "
                   "step of their first turn, CR 103.8c) and source counts from lands plus "
                   "low-CMC mana permanents."),
    }


def compute_commander_dependency(deck_data: dict, commander_name: str, commander_meta: dict,
                                 combo_assembly: dict, threat_density: dict,
                                 draw_reliability: dict, interaction_availability: dict) -> dict:
    """Heuristic commander dependency. Higher means deck leans harder on commander access."""
    synergies = deck_data.get("synergies", [])
    synergy_hits = sum(1 for synergy in synergies if commander_name in synergy.get("cards", []))
    synergy_share = (synergy_hits / len(synergies) * 100) if synergies else 0.0
    combo_requires_commander = any(combo.get("requiresCommander") for combo in combo_assembly.get("combos", []))
    commander_engine = 100.0 if text_matches(commander_meta.get("oracle_text", ""), COMMANDER_ENGINE_PATTERNS) else 0.0
    self_sufficiency = weighted_average([
        (threat_density["byTurn"].get("4", 0.0), 0.35),
        (draw_reliability["byTurn"].get("4", 0.0), 0.35),
        (interaction_availability["byTurn"].get("3", 0.0), 0.30),
    ])
    dependency = clamp(
        0.45 * synergy_share +
        0.25 * (100.0 if combo_requires_commander else 0.0) +
        0.20 * commander_engine +
        0.10 * (100.0 - self_sufficiency)
    )
    if dependency >= 70:
        label = "high"
    elif dependency >= 45:
        label = "moderate"
    else:
        label = "low"
    return {
        "score": r1(dependency),
        "label": label,
        "synergyShare": r1(synergy_share),
        "comboRequiresCommander": combo_requires_commander,
        "selfSufficiency": r1(self_sufficiency),
    }


def compute_deck_health_score(result: dict, threat_density: dict, draw_reliability: dict,
                              interaction_availability: dict, combo_assembly: dict,
                              color_adequacy: dict, commander_dependency: dict,
                              wincon_style: str | None = None) -> dict:
    """Composite deck health score from mana, pressure, interaction, combo, and commander independence."""
    mana_reliability = weighted_average([
        (pct_to_score(result["commanderTiming"]["byTurn"].get(str(result["commanderTiming"]["cmc"]), 0.0)), 0.35),
        (pct_to_score(color_adequacy["overallScore"] if color_adequacy else 100.0), 0.30),
        (pct_to_score((100.0 - (result["mulliganStats"]["paidMulligan"] * 12.0))
                      - (result["mulliganStats"]["freeMulligan"] * 3.0)), 0.20),
        (pct_to_score((result["manaByTurn"]["4"]["mean"] / max(1.0, result["deckComposition"]["avgCmc"])) * 100), 0.15),
    ])
    threat_score = weighted_average([
        (threat_density["byTurn"].get("4", 0.0), 0.45),
        (threat_density["byTurn"].get("5", 0.0), 0.35),
        (threat_density["byTurn"].get("6", 0.0), 0.20),
    ])
    interaction_score = weighted_average([
        (interaction_availability["byTurn"].get("2", 0.0), 0.30),
        (interaction_availability["byTurn"].get("3", 0.0), 0.45),
        (interaction_availability["byTurn"].get("4", 0.0), 0.25),
    ])
    # DEC-362 #1: floor declared-combo decks at the neutral default (50) so declaring
    # an honest finisher can only help, never hurt. DEC-363 #2: bestByTurn now comes
    # from the tutor/redundancy-aware Monte-Carlo assembly model. The raw assembly
    # rate of a Bracket-4 precon combo peaks ~20-25% by turns 5-6 — always below the
    # 50 floor — so a literal max(50, assembly%) would leave EVERY deck at 50 and the
    # axis non-discriminating, defeating the point of this work. Instead we anchor the
    # speed-weighted assembly signal into the upper [50,100] half: combo-less decks and
    # combos that never come together stay at 50; a deck that always assembles its best
    # combo fast reaches 100. Turn-5/6 weighting keeps the speed emphasis from #2's plan.
    assembly_signal = weighted_average([
        (combo_assembly["bestByTurn"].get("5", 0.0), 0.40),
        (combo_assembly["bestByTurn"].get("6", 0.0), 0.60),
    ])
    # DEC-365: scale the assembly bonus by the deck's wincon_style confidence —
    # full for combo decks, reduced where a declared combo is a backup. The 50
    # floor is unscaled, so this can only shrink the bonus, never breach the
    # floor (combo_lambda >= 0, assembly_signal >= 0 => combo_score >= 50).
    combo_lambda = WINCON_COMBO_WEIGHT.get(wincon_style, WINCON_COMBO_WEIGHT_DEFAULT)
    combo_score = max(50.0, 50.0 + combo_lambda * assembly_signal / 2.0) if combo_assembly["combos"] else 50.0
    commander_independence = 100.0 - commander_dependency["score"]

    overall = weighted_average([
        (mana_reliability, 0.30),
        (threat_score, 0.20),
        (interaction_score, 0.20),
        (combo_score, 0.15),
        (commander_independence, 0.15),
    ])

    # The grade is decided on the exported one-decimal score, so the score and
    # the grade a deck shows always agree (owner decision 26, 2026-11-25).
    score = r1(overall)
    if score >= 75:
        grade = "A"
    elif score >= 65:
        grade = "B"
    elif score >= 55:
        grade = "C"
    else:
        grade = "D"

    return {
        "score": score,
        "grade": grade,
        "components": {
            "manaReliability": r1(mana_reliability),
            "threatDeployment": r1(threat_score),
            "interactionDensity": r1(interaction_score),
            "comboConsistency": r1(combo_score),
            "commanderIndependence": r1(commander_independence),
        },
        "methodology": "Weighted composite: mana 30%, threats 20%, interaction 20%, combo 15%, commander independence 15%. Combo term scaled by wincon_style confidence (DEC-365).",
    }


def enrich_result(result: dict, deck_id: str, deck_data: dict, decklist: list[str],
                  metadata: dict, commander_name: str, colors: list[str],
                  mana_counts: dict[int, Counter]) -> dict:
    """Attach enhanced reliability metrics and deck health score.
    `mana_counts`: the mana simulation's games by mana total, each turn."""
    functional = classify_functional_cards(decklist, deck_data, metadata)
    threat_density = compute_threat_density(functional["threats"], metadata, mana_counts)
    draw_reliability = compute_reliability_curve(functional["draw"], "Card draw")
    interaction_availability = compute_reliability_curve(functional["interaction"], "Interaction")
    color_adequacy = compute_colored_source_adequacy(decklist, metadata, commander_name, colors)
    commander_colors = colors or ["C"]
    # Goldfish now produces the tutor-aware combo assembly (DEC-363), so it runs
    # before commander-dependency and the health score, which both consume it.
    goldfish, combo_assembly = compute_goldfish_section(
        decklist=decklist,
        deck_data=deck_data,
        metadata=metadata,
        commander_name=commander_name,
        commander_colors=commander_colors,
        deck_id=deck_id,
    )
    commander_dependency = compute_commander_dependency(
        deck_data=deck_data,
        commander_name=commander_name,
        commander_meta=metadata.get(commander_name, {}),
        combo_assembly=combo_assembly,
        threat_density=threat_density,
        draw_reliability=draw_reliability,
        interaction_availability=interaction_availability,
    )

    result["reliabilityMetrics"] = {
        "threatDensity": threat_density,
        "drawEngineReliability": draw_reliability,
        "interactionAvailability": interaction_availability,
        "comboAssembly": combo_assembly,
        "coloredSourceAdequacy": color_adequacy,
        "commanderDependency": commander_dependency,
    }
    result["deckHealthScore"] = compute_deck_health_score(
        result=result,
        threat_density=threat_density,
        draw_reliability=draw_reliability,
        interaction_availability=interaction_availability,
        combo_assembly=combo_assembly,
        color_adequacy=color_adequacy,
        commander_dependency=commander_dependency,
        wincon_style=deck_data.get("wincon_style"),
    )
    result["goldfish"] = goldfish
    return result


def derive_assessment(result: dict, mana_counts: dict[int, Counter]) -> dict:
    """Derive qualitative assessments from simulation data.
    `mana_counts`: the mana simulation's games by mana total, each turn."""
    # Mana adequacy (owner-approved 2026-11-25), decided on shares of games,
    # not on median mana, which steps by a whole mana when the games at or
    # below a total cross 50%. Targets: the exported one-decimal average mana
    # value on turn 4, that + 2 on turn 5, rounded up to whole mana. Each share
    # (the games with the target or more) is rounded once to one decimal (pct)
    # and the label read on that shown value. Turn 5 first: over 51.0 strong,
    # 49.0 to 51.0 inclusive near strong; below that, turn 4: over 51.0
    # adequate, 49.0 to 51.0 near adequate, below light. The share that
    # decided the label goes out with it: turn 5's for strong and near strong,
    # turn 4's otherwise.
    avg_cmc = result["deckComposition"]["avgCmc"]
    shares = {}
    for turn, target in ((4, math.ceil(avg_cmc)), (5, math.ceil(avg_cmc + 2))):
        counts = mana_counts[turn]
        shares[turn] = {
            "turn": turn,
            "manaTarget": target,
            "share": pct(sum(count for mana, count in counts.items() if mana >= target),
                         sum(counts.values())),
        }

    if shares[5]["share"] > 51.0:
        mana_adequacy, mana_share = "strong", shares[5]
    elif shares[5]["share"] >= 49.0:
        mana_adequacy, mana_share = "near strong", shares[5]
    elif shares[4]["share"] > 51.0:
        mana_adequacy, mana_share = "adequate", shares[4]
    elif shares[4]["share"] >= 49.0:
        mana_adequacy, mana_share = "near adequate", shares[4]
    else:
        mana_adequacy, mana_share = "light", shares[4]

    # Mulligan verdict
    paid_pct = result["mulliganStats"]["paidMulligan"]
    if paid_pct < 3:
        mulligan_verdict = "excellent"
    elif paid_pct < 5:
        mulligan_verdict = "acceptable"
    else:
        mulligan_verdict = "concerning"

    # Commander timing
    # For 4+ color commanders, the simultaneous multi-pip requirement makes
    # casting structurally harder than equivalent CMC with fewer colors.
    # Allow +1 turn grace for 4+ color identities.
    cmd = result["commanderTiming"]
    cmd_cmc = cmd["cmc"]
    median_turn = cmd["medianTurn"]
    cb = result.get("colorBalance") or {}
    num_colors = len(cb.get("colors", []))
    curve_grace = 2 if num_colors >= 4 else 0
    if median_turn is None:
        cmd_timing = "unreliable"
    elif median_turn <= cmd_cmc - 1:
        cmd_timing = "ahead of curve"
    elif median_turn <= cmd_cmc + curve_grace:
        cmd_timing = "on curve"
    else:
        cmd_timing = "behind curve"

    return {
        "manaAdequacy": mana_adequacy,
        "manaAdequacyShare": mana_share,
        "mulliganVerdict": mulligan_verdict,
        "commanderTiming": cmd_timing,
    }


def _run_seeded_chunk(args):
    """Worker chunk for run_parallel: seed `random`, then run one mana-sim chunk."""
    run_chunk_fn, seed, decklist, metadata, num_games = args
    # Seed at the start of each chunk, inside the worker, so a chunk's games
    # depend only on its seed and size, not on which worker runs it or what that
    # worker ran before. Every mana sim draws from the module-level `random`
    # (library shuffle; Titan's Gemstone Caverns roll). (DEC-1115)
    random.seed(seed)
    return run_chunk_fn((decklist, metadata, num_games))


def run_parallel(run_chunk_fn, merge_fn, decklist, metadata, num_games):
    """Run simulation with multiprocessing, return merged stats."""
    import multiprocessing
    # Fixed chunk count and one seed for each chunk (DEC-1115); only the worker
    # count follows the CPU count. pool.map keeps chunk order, so merge_fn sees
    # the chunks in index order on every machine.
    base, remainder = divmod(num_games, MANA_SIM_CHUNKS)
    chunk_sizes = [base + (1 if i < remainder else 0) for i in range(MANA_SIM_CHUNKS)]
    chunk_args = [
        (run_chunk_fn, MANA_SIM_SEED + i, decklist, metadata, games)
        for i, games in enumerate(chunk_sizes) if games > 0
    ]
    n_workers = min(MANA_SIM_CHUNKS, os.cpu_count() or 4)
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_seeded_chunk, chunk_args)
    return merge_fn(results)


def validate_output(result: dict, deck_id: str) -> bool:
    """Validate required top-level keys and manaByTurn entries."""
    required_keys = [
        "metadata", "deckComposition", "manaByTurn", "mulliganStats",
        "openingHand", "commanderTiming", "colorBalance", "curveEfficiency",
        "specialMetrics", "assessment", "reliabilityMetrics", "deckHealthScore",
        "goldfish",
    ]
    for key in required_keys:
        if key not in result:
            print(f"  VALIDATION FAIL [{deck_id}]: missing key '{key}'")
            return False

    for t in range(1, NUM_TURNS + 1):
        if str(t) not in result["manaByTurn"]:
            print(f"  VALIDATION FAIL [{deck_id}]: manaByTurn missing turn {t}")
            return False

    return True


# --- Deck-specific exporters ---


def export_titan(metadata: dict) -> dict:
    """Export Titan Convergence (colorless Eldrazi) simulation."""
    deck_file = PROJECT_ROOT / "data" / "commanders" / "titan-convergence" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)

    decklist = sim_titan.build_decklist(deck_data)
    classified = sim_titan.classify_cards(decklist, metadata)
    avg_cmc = compute_avg_cmc(decklist, metadata)

    print(f"  Running {NUM_GAMES:,} games for Titan Convergence...")
    stats = run_parallel(sim_titan._run_chunk, sim_titan.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    # manaByTurn
    mana_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        mana_by_turn[str(t)] = mana_stats(stats["mana_by_turn"][t])

    # mulliganStats
    mull = stats["mulligan_attempts"]
    mulligan_stats = {
        "keptFirst": pct(mull.get(0, 0), total),
        "freeMulligan": pct(mull.get(1, 0), total),
        "paidMulligan": paid_mulligan_pct(mull, total),
    }

    # openingHand
    land_dist = {}
    for n in range(8):
        count = stats["hand_land_counts"].get(n, 0)
        if count > 0:
            land_dist[str(n)] = pct(count, total)
    opening_hand = {"landDistribution": land_dist}

    # commanderTiming (Zhulodok = 6 CMC, cumulative % by turn)
    cmd_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cmd_by_turn[str(t)] = cumulative_pct(stats["zhulodok_turns"], t, total)

    commander_timing = {
        "name": "Zhulodok, Void Gorger",
        "cmc": 6,
        "byTurn": cmd_by_turn,
        "medianTurn": median_turn_from_cumulative(cmd_by_turn),
    }

    # curveEfficiency
    castable_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        castable_by_turn[str(t)] = pct(stats["castable_spell_by_turn"][t], total)

    curve_efficiency = {
        "castableByTurn": castable_by_turn,
        "curveOutRate": pct(stats["curve_out_games"], total),
    }

    # specialMetrics: cascadeReadiness
    cascade_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cascade_by_turn[str(t)] = cumulative_pct(stats["cascade_ready_turns"], t, total)

    special_metrics = {
        "cascadeReadiness": {
            "byTurn": cascade_by_turn,
            "medianTurn": median_or_null(stats["cascade_ready_turns"]),
        },
        "etbTapped": None,
    }

    result = {
        "metadata": {
            "numGames": NUM_GAMES,
            "numTurns": NUM_TURNS,
            "generatedAt": str(date.today()),
        },
        "deckComposition": {
            "totalCards": len(decklist),
            "lands": len(classified["lands"]),
            "rocks": len(classified["rocks"]),
            "spells": len(classified["spells"]) + len(classified.get("amplifiers", [])),
            "avgCmc": r1(avg_cmc),
        },
        "manaByTurn": mana_by_turn,
        "mulliganStats": mulligan_stats,
        "openingHand": opening_hand,
        "commanderTiming": commander_timing,
        "colorBalance": None,
        "curveEfficiency": curve_efficiency,
        "specialMetrics": special_metrics,
        "assessment": {},
    }
    # Games by mana total each turn: the mana label and threat density read
    # the whole distribution, not the median.
    mana_counts = {t: Counter(stats["mana_by_turn"][t]) for t in range(1, NUM_TURNS + 1)}
    result["assessment"] = derive_assessment(result, mana_counts)
    return enrich_result(
        result=result,
        deck_id="titan-convergence",
        deck_data=deck_data,
        decklist=decklist,
        metadata=metadata,
        commander_name="Zhulodok, Void Gorger",
        colors=[],
        mana_counts=mana_counts,
    )


def _export_colored(sim_module, deck_id: str, deck_name: str,
                    commander_name: str, commander_cmc: int,
                    colors: list[str], metadata: dict) -> dict:
    """Export a colored (Rakdos/Grixis) simulation."""
    deck_file = PROJECT_ROOT / "data" / "commanders" / deck_id / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)

    decklist = sim_module.build_decklist(deck_data)
    classified = sim_module.classify_cards(decklist, metadata)
    avg_cmc = compute_avg_cmc(decklist, metadata)

    print(f"  Running {NUM_GAMES:,} games for {deck_name}...")
    stats = run_parallel(sim_module._run_chunk, sim_module.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    # manaByTurn
    mana_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        mana_by_turn[str(t)] = mana_stats(stats["mana_by_turn"][t])

    # mulliganStats
    mull = stats["mulligan_attempts"]
    mulligan_stats = {
        "keptFirst": pct(mull.get(0, 0), total),
        "freeMulligan": pct(mull.get(1, 0), total),
        "paidMulligan": paid_mulligan_pct(mull, total),
    }

    # openingHand
    land_dist = {}
    for n in range(8):
        count = stats["hand_land_counts"].get(n, 0)
        if count > 0:
            land_dist[str(n)] = pct(count, total)
    opening_hand = {"landDistribution": land_dist}

    # commanderTiming (cumulative from commander_by_turn)
    cmd_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cmd_by_turn[str(t)] = pct(stats["commander_by_turn"][t], total)

    commander_timing = {
        "name": commander_name,
        "cmc": commander_cmc,
        "byTurn": cmd_by_turn,
        "medianTurn": median_turn_from_cumulative(cmd_by_turn),
    }

    # colorBalance
    color_keys = {c: c.lower() for c in colors}
    color_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        turn_data = {}
        for color in colors:
            key = f"{color_keys[color]}_by_turn"
            data = stats[key][t]
            turn_data[color] = {
                "median": r1(statistics.median(data)),
                "mean": r1(statistics.mean(data)),
            }
        color_by_turn[str(t)] = turn_data

    color_screw_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        turn_screw = {}
        for color in colors:
            key = f"zero_{color_keys[color]}_by_turn"
            turn_screw[color] = pct(stats[key][t], total)
        color_screw_by_turn[str(t)] = turn_screw

    color_balance = {
        "colors": colors,
        "byTurn": color_by_turn,
        "colorScrewByTurn": color_screw_by_turn,
    }

    # curveEfficiency
    castable_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        castable_by_turn[str(t)] = pct(stats["castable_spell_by_turn"][t], total)

    curve_efficiency = {
        "castableByTurn": castable_by_turn,
        "curveOutRate": pct(stats["curve_out_games"], total),
    }

    # specialMetrics: etbTapped
    etb_tapped = {}
    for t in stats["tapped_land_turns"]:
        etb_tapped[str(t)] = pct(stats["tapped_land_turns"][t], total)

    special_metrics = {
        "cascadeReadiness": None,
        "etbTapped": etb_tapped,
    }

    result = {
        "metadata": {
            "numGames": NUM_GAMES,
            "numTurns": NUM_TURNS,
            "generatedAt": str(date.today()),
        },
        "deckComposition": {
            "totalCards": len(decklist),
            "lands": len(classified["lands"]),
            "rocks": len(classified["rocks"]),
            "spells": len(classified["spells"]),
            "avgCmc": r1(avg_cmc),
        },
        "manaByTurn": mana_by_turn,
        "mulliganStats": mulligan_stats,
        "openingHand": opening_hand,
        "commanderTiming": commander_timing,
        "colorBalance": color_balance,
        "curveEfficiency": curve_efficiency,
        "specialMetrics": special_metrics,
        "assessment": {},
    }
    # Games by mana total each turn: the mana label and threat density read
    # the whole distribution, not the median.
    mana_counts = {t: Counter(stats["mana_by_turn"][t]) for t in range(1, NUM_TURNS + 1)}
    result["assessment"] = derive_assessment(result, mana_counts)
    return enrich_result(
        result=result,
        deck_id=deck_id,
        deck_data=deck_data,
        decklist=decklist,
        metadata=metadata,
        commander_name=commander_name,
        colors=colors,
        mana_counts=mana_counts,
    )


def export_rakdos(metadata: dict) -> dict:
    """Export Eternal Agony (Rakdos) simulation."""
    return _export_colored(
        sim_module=sim_rakdos,
        deck_id="eternal-agony",
        deck_name="Eternal Agony",
        commander_name="Valgavoth, Harrower of Souls",
        commander_cmc=4,
        colors=["B", "R"],
        metadata=metadata,
    )


def export_grixis(metadata: dict) -> dict:
    """Export Gathering Shadow (Grixis) simulation."""
    return _export_colored(
        sim_module=sim_grixis,
        deck_id="gathering-shadow",
        deck_name="Gathering Shadow",
        commander_name="Sauron, the Dark Lord",
        commander_cmc=6,
        colors=["U", "B", "R"],
        metadata=metadata,
    )


def export_golgari(metadata: dict) -> dict:
    """Export Eternal Harvest (Golgari) simulation."""
    return _export_colored(
        sim_module=sim_golgari,
        deck_id="eternal-harvest",
        deck_name="Eternal Harvest",
        commander_name="Meren of Clan Nel Toth",
        commander_cmc=4,
        colors=["B", "G"],
        metadata=metadata,
    )




def export_witherbloom(metadata: dict) -> dict:
    """Export Witherbloom Balance (Golgari aristocrats) simulation."""
    return _export_colored(
        sim_module=sim_witherbloom,
        deck_id="witherbloom-the-balancer",
        deck_name="Witherbloom Balance",
        commander_name="Witherbloom, the Balancer",
        commander_cmc=8,
        colors=["B", "G"],
        metadata=metadata,
    )


def export_mono_white(metadata: dict) -> dict:
    """Export The White Forge (mono-white Gandalf) simulation."""
    return _export_colored(
        sim_module=sim_mono_white,
        deck_id="the-white-forge",
        deck_name="The White Forge",
        commander_name="Gandalf the White",
        commander_cmc=5,
        colors=["W"],
        metadata=metadata,
    )


def export_hidden_legion(metadata: dict) -> dict:
    """Export Hidden Legion (5-color Ur-Dragon changeling tribal) simulation."""
    result = _export_colored(
        sim_module=sim_hidden_legion,
        deck_id="hidden-legion",
        deck_name="Hidden Legion",
        commander_name="The Ur-Dragon",
        commander_cmc=9,
        colors=["W", "U", "B", "R", "G"],
        metadata=metadata,
    )

    # Add Ur-Dragon-specific metrics: engine readiness, changelings curve, Ur castability
    deck_file = PROJECT_ROOT / "data" / "commanders" / "hidden-legion" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)
    decklist = sim_hidden_legion.build_decklist(deck_data)

    print(f"  Running {NUM_GAMES:,} games for Hidden Legion engine metrics...")
    stats = run_parallel(sim_hidden_legion._run_chunk, sim_hidden_legion.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    engine_ready = {}
    for t in range(1, NUM_TURNS + 1):
        engine_ready[str(t)] = pct(stats["engine_ready_by_turn"][t], total)

    ur_castable = {}
    for t in range(1, NUM_TURNS + 1):
        ur_castable[str(t)] = pct(stats["ur_castable_by_turn"][t], total)

    changelings_curve = {}
    for t in range(1, NUM_TURNS + 1):
        changelings_curve[str(t)] = mana_stats(stats["changelings_by_turn"][t])

    result["specialMetrics"]["engineReadiness"] = {
        "description": (
            "Probability Ur-Dragon is castable (9 mana with WUBRG) AND at least one "
            "changeling is in play. Core engine state — Ur-Dragon as a Dragon with "
            "the tribe assembled enables Eminence-discounted casts, attack triggers, "
            "and Sliver Legion / Dragon Tempest payoffs."
        ),
        "byTurn": engine_ready,
    }
    result["specialMetrics"]["urDragonCastable"] = {
        "description": "Ur-Dragon (9 CMC, {4}{W}{U}{B}{R}{G}) castable by turn",
        "byTurn": ur_castable,
    }
    result["specialMetrics"]["changelingsInPlay"] = {
        "description": "Changelings on battlefield per turn (median/mean). Drives Eminence-discount value and tribal scaling.",
        "byTurn": changelings_curve,
    }

    return result


def export_gandalf_party_guest(metadata: dict) -> dict:
    """Export Arcane Convocation (Jeskai — Gandalf, Party Guest) simulation."""
    return _export_colored(
        sim_module=sim_gandalf,
        deck_id="gandalf-party-guest",
        deck_name="Arcane Convocation",
        commander_name="Gandalf, Party Guest",
        commander_cmc=4,
        colors=["U", "R", "W"],
        metadata=metadata,
    )


def export_zada(metadata: dict) -> dict:
    """Export Hedron Storm (mono-R — Zada, Hedron Grinder) simulation."""
    return _export_colored(
        sim_module=sim_zada,
        deck_id="zada-hedron-grinder",
        deck_name="Hedron Storm",
        commander_name="Zada, Hedron Grinder",
        commander_cmc=4,
        colors=["R"],
        metadata=metadata,
    )


def export_tidal_legion(metadata: dict) -> dict:
    """Export Tidal Legion (mono-U — Namor the Sub-Mariner) simulation."""
    return _export_colored(
        sim_module=sim_tidal_legion,
        deck_id="tidal-legion",
        deck_name="Tidal Legion",
        commander_name="Namor the Sub-Mariner",
        commander_cmc=3,
        colors=["U"],
        metadata=metadata,
    )


def export_armory_protocol(metadata: dict) -> dict:
    """Export Armory Protocol (Izzet — Tony Stark) simulation.

    commander_cmc=6 is the transform activation ({4}{U}{R}) — the sim's
    commanderTiming tracks the suit-online event, not the {1}{U} front-face
    cast (Esika/Prismatic Bridge precedent, DEC-405).
    """
    return _export_colored(
        sim_module=sim_armory_protocol,
        deck_id="armory-protocol",
        deck_name="Armory Protocol",
        commander_name="Tony Stark // The Invincible Iron Man",
        commander_cmc=6,
        colors=["U", "R"],
        metadata=metadata,
    )


def export_grave_dividends(metadata: dict) -> dict:
    """Export Grave Dividends (Orzhov Bartolomé aristocrats sacrifice-loop) simulation."""
    return _export_colored(
        sim_module=sim_grave_dividends,
        deck_id="grave-dividends",
        deck_name="Grave Dividends",
        commander_name="Bartolomé del Presidio",
        commander_cmc=2,
        colors=["W", "B"],
        metadata=metadata,
    )


def export_hoard_and_bleed(metadata: dict) -> dict:
    """Export Hoard and Bleed (Rakdos Smaug Treasure-aristocrats) simulation."""
    return _export_colored(
        sim_module=sim_hoard_and_bleed,
        deck_id="hoard-and-bleed",
        deck_name="Hoard and Bleed",
        commander_name="Smaug, Wicked Worm",
        commander_cmc=5,
        colors=["B", "R"],
        metadata=metadata,
    )


def export_exponential_growth(metadata: dict) -> dict:
    """Export Exponential Growth (Simic Zimone +1/+1 counters / Hydra) simulation."""
    return _export_colored(
        sim_module=sim_exponential_growth,
        deck_id="exponential-growth",
        deck_name="Exponential Growth",
        commander_name="Zimone, Infinite Analyst",
        commander_cmc=3,
        colors=["U", "G"],
        metadata=metadata,
    )


def export_slivers(metadata: dict) -> dict:
    """Export Hivebound Cascade (5C Slivers — The First Sliver) simulation."""
    return _export_colored(
        sim_module=sim_slivers,
        deck_id="slivers",
        deck_name="Hivebound Cascade",
        commander_name="The First Sliver",
        commander_cmc=5,
        colors=["W", "U", "B", "R", "G"],
        metadata=metadata,
    )


def export_stampede_acres(metadata: dict) -> dict:
    """Export Field of Blades (Naya tokens — Baylen, the Haymaker) simulation."""
    return _export_colored(
        sim_module=sim_stampede_acres,
        deck_id="stampede-acres",
        deck_name="Field of Blades",
        commander_name="Baylen, the Haymaker",
        commander_cmc=3,
        colors=["R", "G", "W"],
        metadata=metadata,
    )


def export_broodfire_hatchery(metadata: dict) -> dict:
    """Export Broodfire Hatchery (Naya eggs — Atla Palani, Nest Tender) simulation."""
    return _export_colored(
        sim_module=sim_broodfire_hatchery,
        deck_id="broodfire-hatchery",
        deck_name="Broodfire Hatchery",
        commander_name="Atla Palani, Nest Tender",
        commander_cmc=4,
        colors=["R", "G", "W"],
        metadata=metadata,
    )


def export_shield_doctrine(metadata: dict) -> dict:
    """Export Shield Doctrine (Jeskai equipment voltron — Captain America) simulation."""
    return _export_colored(
        sim_module=sim_shield_doctrine,
        deck_id="shield-doctrine",
        deck_name="Shield Doctrine",
        commander_name="Captain America, First Avenger",
        commander_cmc=3,
        colors=["W", "U", "R"],
        metadata=metadata,
    )


def export_anvil_chorus(metadata: dict) -> dict:
    """Export Anvil Chorus (mono-white Fíli Dwarf ETB/token) simulation."""
    return _export_colored(
        sim_module=sim_anvil_chorus,
        deck_id="anvil-chorus",
        deck_name="Anvil Chorus",
        commander_name="Fíli the Pathfinder",
        commander_cmc=4,
        colors=["W"],
        metadata=metadata,
    )


def export_wubg_poison(metadata: dict) -> dict:
    """Export Creeping Corruption (WUBG Atraxa poison/proliferate) simulation."""
    return _export_colored(
        sim_module=sim_wubg_poison,
        deck_id="creeping-corruption",
        deck_name="Creeping Corruption",
        commander_name="Atraxa, Praetors' Voice",
        commander_cmc=4,
        colors=["W", "U", "B", "G"],
        metadata=metadata,
    )


def export_verdant_tide(metadata: dict) -> dict:
    """Export Verdant Tide (mono-green Eladamri) simulation."""
    result = _export_colored(
        sim_module=sim_mono_green,
        deck_id="verdant-tide",
        deck_name="Verdant Tide",
        commander_name="Eladamri, Korvecdal",
        commander_cmc=3,
        colors=["G"],
        metadata=metadata,
    )

    # Add Eladamri-specific: creature topcast probability
    deck_file = PROJECT_ROOT / "data" / "commanders" / "verdant-tide" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)
    decklist = sim_mono_green.build_decklist(deck_data)

    print(f"  Running {NUM_GAMES:,} games for Eladamri-specific metrics...")
    stats = run_parallel(sim_mono_green._run_chunk, sim_mono_green.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    creature_on_top = {}
    for t in range(1, NUM_TURNS + 1):
        creature_on_top[str(t)] = pct(stats["creature_on_top_by_turn"][t], total)

    result["specialMetrics"]["creatureTopcast"] = {
        "description": "Probability of creature on top of library (Eladamri free cast)",
        "byTurn": creature_on_top,
    }

    return result


# --- Main ---


DECKS = [
    ("titan-convergence", "Titan Convergence", export_titan),
    ("eternal-agony", "Eternal Agony", export_rakdos),
    ("gathering-shadow", "Gathering Shadow", export_grixis),
    ("eternal-harvest", "Eternal Harvest", export_golgari),
    ("witherbloom-the-balancer", "Witherbloom Balance", export_witherbloom),
    ("the-white-forge", "The White Forge", export_mono_white),
    ("verdant-tide", "Verdant Tide", export_verdant_tide),
    ("creeping-corruption", "Creeping Corruption", export_wubg_poison),
    ("grave-dividends", "Grave Dividends", export_grave_dividends),
    ("hidden-legion", "Hidden Legion", export_hidden_legion),
    ("zada-hedron-grinder", "Hedron Storm", export_zada),
    ("exponential-growth", "Exponential Growth", export_exponential_growth),
    ("slivers", "Hivebound Cascade", export_slivers),
    ("stampede-acres", "Field of Blades", export_stampede_acres),
    ("tidal-legion", "Tidal Legion", export_tidal_legion),
    ("armory-protocol", "Armory Protocol", export_armory_protocol),
    ("shield-doctrine", "Shield Doctrine", export_shield_doctrine),
    ("gandalf-party-guest", "Arcane Convocation", export_gandalf_party_guest),
    ("hoard-and-bleed", "Hoard and Bleed", export_hoard_and_bleed),
    ("broodfire-hatchery", "Broodfire Hatchery", export_broodfire_hatchery),
    ("anvil-chorus", "Anvil Chorus", export_anvil_chorus),
]


DECK_MAP = {deck_id: (deck_name, export_fn) for deck_id, deck_name, export_fn in DECKS}


def resolve_decks(deck_ids: list[str] | None) -> list[tuple[str, str, object]]:
    """Return selected deck tuples in canonical order."""
    if not deck_ids:
        return DECKS
    requested = set(deck_ids)
    return [deck for deck in DECKS if deck[0] in requested]


def output_path_for(deck_id: str, output_dir: Path | None) -> Path:
    """Resolve output path for a deck export."""
    if output_dir is None:
        return PROJECT_ROOT / "data" / "commanders" / deck_id / "simulation.json"
    return output_dir / deck_id / "simulation.json"


def export_selected_decks(metadata: dict, selected_decks: list[tuple[str, str, object]],
                          output_dir: Path | None) -> int:
    """Export selected decks. Return number of failures."""
    failures = 0

    for deck_id, deck_name, export_fn in selected_decks:
        try:
            print(f"[{deck_name}]")
            result = export_fn(metadata)

            if not validate_output(result, deck_id):
                print(f"  SKIPPED: validation failed\n")
                failures += 1
                continue

            out_path = output_path_for(deck_id, output_dir)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"  Written: {out_path}")
            print(f"  Size: {out_path.stat().st_size / 1024:.1f} KB\n")

        except Exception:
            failures += 1
            print(f"  ERROR processing {deck_name}:")
            traceback.print_exc()
            print()

    return failures


def main():
    global NUM_GAMES, GOLDFISH_GAMES

    parser = argparse.ArgumentParser(
        description="Export mana simulation results as JSON")
    parser.add_argument(
        "--deck",
        dest="deck_ids",
        action="append",
        choices=sorted(DECK_MAP),
        help="Export only the specified deck id. Repeat to select multiple decks.",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=NUM_GAMES,
        help=f"Monte Carlo games per deck (default: {NUM_GAMES})",
    )
    parser.add_argument(
        "--goldfish-games",
        type=int,
        default=GOLDFISH_GAMES,
        help=f"Goldfish games per deck (default: {GOLDFISH_GAMES})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional base directory for outputs; writes {output-dir}/{deck-id}/simulation.json",
    )
    args = parser.parse_args()

    if args.games <= 0:
        parser.error("--games must be > 0")
    if args.goldfish_games <= 0:
        parser.error("--goldfish-games must be > 0")

    NUM_GAMES = args.games
    GOLDFISH_GAMES = args.goldfish_games
    selected_decks = resolve_decks(args.deck_ids)

    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print(f"Loaded card metadata ({len(metadata)} cards)")
    print(f"Exporting simulation results for {len(selected_decks)} decks...")
    print(f"  Mana sim games: {NUM_GAMES:,}")
    print(f"  Goldfish games: {GOLDFISH_GAMES:,}")
    if args.output_dir:
        print(f"  Output dir: {args.output_dir}")
    print()

    failures = export_selected_decks(metadata, selected_decks, args.output_dir)

    if failures:
        print(f"Done with {failures} failure(s).")
        raise SystemExit(1)

    print("Done.")


if __name__ == "__main__":
    main()
