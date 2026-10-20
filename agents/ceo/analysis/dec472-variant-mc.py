"""DEC-472 Gandalf, Party Guest — variant power iteration (goldfish combo-close model).

Comparative Monte Carlo: estimates the first turn each variant has a
deterministic win engine online. Simplified mana model (every land = 1 mana
from its turn, tapped-land tempo ignored, color requirements ignored,
Ancient Tomb = 2). Results are comparative between variants, not absolute
turn predictions. 4-player goldfish: no opponent interaction.
"""
import random
import statistics
from collections import Counter

random.seed(472)

# ---- post-swap 99 (six accepted swaps applied), nonland portion ----
WIZARDS = [
    "Baral, Chief of Compliance", "Stenn, Paranoid Partisan", "Kaza, Roil Chaser",
    "Kitsa, Otterball Elite", "Balmor, Battlemage Captain", "Raff, Weatherlight Stalwart",
    "Vivi Ornitier", "Veyran, Voice of Duality", "Adeliz, the Cinder Wind",
    "Vadrik, Astral Archmage", "Jori En, Ruin Diver", "Hurkyl, Master Wizard",
    "Vendilion Clique", "Venser, Shaper Savant", "Mizzix of the Izmagnus",
    "Kykar, Wind's Fury", "Johann, Apprentice Sorcerer", "Naru Meha, Master Wizard",
    "Gandalf the Grey", "Deekah, Fractal Theorist",
]
SUPPORT = ["Harmonic Prodigy", "Wizard's Staff", "Archmage Emeritus", "Storm-Kiln Artist"]
PAYOFFS = ["Jeskai Revelation", "Sublime Epiphany", "Magma Opus", "Temporal Mastery",
           "Alrund's Epiphany", "Insurrection"]
COMBO_SPELLS = ["Fury Storm", "Ghostly Flicker"]
DRAW = ["Dig Through Time", "Treasure Cruise", "Frantic Search", "Ponder", "Preordain",
        "Brainstorm", "Whirlwind of Thought"]
INTERACTION = ["Counterspell", "Arcane Denial", "Wizard's Retort", "Dovin's Veto",
               "Mystic Confluence", "Swords to Plowshares", "Generous Gift", "Chaos Warp",
               "Prismari Command", "Wear // Tear", "Flame of Anor", "Olorin's Searing Light",
               "Blasphemous Act", "Erode", "Raise the Palisade"]
PROTECTION = ["Unbreakable Formation", "Clever Concealment"]
ROCKS = ["Sol Ring", "Arcane Signet", "Lotus Petal", "Izzet Signet", "Fellwar Stone",
         "Talisman of Creativity", "Talisman of Progress"]
N_LANDS = 36  # incl. the two Turbulents

BASE_NONLAND = WIZARDS + SUPPORT + PAYOFFS + COMBO_SPELLS + DRAW + INTERACTION + PROTECTION + ROCKS
assert len(BASE_NONLAND) + N_LANDS == 99, len(BASE_NONLAND)

ROCK_COST = {"Sol Ring": 1, "Arcane Signet": 2, "Lotus Petal": 0, "Izzet Signet": 2,
             "Fellwar Stone": 2, "Talisman of Creativity": 2, "Talisman of Progress": 2,
             "Mox Amber": 0}
ROCK_MANA = {"Sol Ring": 2, "Lotus Petal": 1}  # default 1; Lotus Petal one-shot approximated as persistent 1 (optimistic, equal across variants)

MAGECRAFT_PAYOFFS = {"Storm-Kiln Artist", "Archmage Emeritus", "Deekah, Fractal Theorist"}
MAGECRAFT_COST = {"Storm-Kiln Artist": 4, "Archmage Emeritus": 4, "Deekah, Fractal Theorist": 5}
CANTRIP_DRAW = {"Ponder": 1, "Preordain": 1, "Brainstorm": 1, "Frantic Search": 1,
                "Jori En, Ruin Diver": 0}  # net cards after put-backs/discards; selection bonus ignored
CANTRIP_COST = {"Ponder": 1, "Preordain": 1, "Brainstorm": 1, "Frantic Search": 3}
BIG_DRAW = {"Dig Through Time": 2, "Treasure Cruise": 3, "Whirlwind of Thought": 0}
BIG_DRAW_COST = {"Dig Through Time": 4, "Treasure Cruise": 3, "Whirlwind of Thought": 5}  # delve avg discount

TUTOR_TO_HAND = {"Solve the Equation": 3, "Merchant Scroll": 2}  # cost; Merchant Scroll blue instants only
TUTOR_TO_TOP = {"Mystical Tutor": 1}
BLUE_INSTANTS_FETCHABLE = {"Ghostly Flicker", "Sublime Epiphany", "Mystical Tutor", "Displace"}
ANY_IS_FETCHABLE = {"Fury Storm", "Ghostly Flicker", "Sublime Epiphany", "Temporal Mastery",
                    "Alrund's Epiphany", "Mystical Tutor", "Displace"}

# ETB-copy loop pieces: blink spell (cost) x starter creature flashed from hand (cost)
FLICKERS = {"Ghostly Flicker": 3, "Displace": 3}
STARTERS = {"Naru Meha, Master Wizard": 4, "Dualcaster Mage": 3}

def make_variant(name, add=(), cut=(), extra_land_mana=0):
    deck = list(BASE_NONLAND)
    for c in cut:
        deck.remove(c)
    deck += list(add)
    n_lands = N_LANDS
    assert len(deck) + n_lands == 99, (name, len(deck))
    return {"name": name, "nonland": deck, "lands": n_lands, "tomb": extra_land_mana}

POWER_ADDS = ["Mystical Tutor", "Solve the Equation", "Merchant Scroll", "Panoptic Mirror",
              "Mox Amber", "Fierce Guardianship"]
POWER_CUTS = ["Brainstorm", "Ponder", "Whirlwind of Thought", "Insurrection",
              "Fellwar Stone", "Arcane Denial"]

VARIANTS = [
    make_variant("V0 baseline (6 swaps, no power pkg)"),
    make_variant("V1 full package (named cuts)", POWER_ADDS, POWER_CUTS, extra_land_mana=1),
    make_variant("V2 tutors only", ["Mystical Tutor", "Solve the Equation", "Merchant Scroll"],
                 ["Brainstorm", "Ponder", "Whirlwind of Thought"]),
    make_variant("V3 fast mana only", ["Mox Amber"], ["Fellwar Stone"], extra_land_mana=1),
    make_variant("V4 full pkg, keep Time Stretch drop Flicker",
                 [c for c in POWER_ADDS] + ["Time Stretch"],
                 POWER_CUTS + ["Ghostly Flicker"], extra_land_mana=1),
    make_variant("V5 = V1 + Displace (blink #2)",
                 POWER_ADDS + ["Displace"], POWER_CUTS + ["Preordain"], extra_land_mana=1),
    make_variant("V6 = V1 + Dualcaster (starter #2)",
                 POWER_ADDS + ["Dualcaster Mage"], POWER_CUTS + ["Preordain"], extra_land_mana=1),
    make_variant("V7 = V1 + both redundancy pieces",
                 POWER_ADDS + ["Displace", "Dualcaster Mage"],
                 POWER_CUTS + ["Preordain", "Frantic Search"], extra_land_mana=1),
]

ENGINE_DRAW = False  # second pass: creature draw engines (Archmage/Jori En/Raff/Kitsa) approximated

def simulate(variant, max_turn=14):
    deck = variant["nonland"] + ["LAND"] * variant["lands"]
    random.shuffle(deck)
    hand = [deck.pop() for _ in range(7)]
    if ENGINE_DRAW:
        # mulligan-lite: one free reshuffle if hand has <2 or >5 lands
        nl = hand.count("LAND")
        if nl < 2 or nl > 5:
            deck += hand
            random.shuffle(deck)
            hand = [deck.pop() for _ in range(7)]
    battlefield = set()
    mana_rocks = 0
    lands = 0
    tomb_bonus = 0
    gandalf_cast_turn = None
    top_stack = []  # mystical tutor targets

    for turn in range(1, max_turn + 1):
        # draw
        if top_stack:
            hand.append(top_stack.pop())
        elif deck:
            hand.append(deck.pop())
        # land drop
        if "LAND" in hand:
            hand.remove("LAND")
            lands += 1
            if variant["tomb"] and tomb_bonus == 0 and lands >= 3 and random.random() < 0.35:
                tomb_bonus = 1  # Ancient Tomb drawn-and-played approximation
        mana = lands + tomb_bonus + mana_rocks
        pool = mana

        # cast rocks first
        for r in list(hand):
            if r in ROCK_COST and ROCK_COST[r] <= pool:
                if r == "Mox Amber" and not any(w in battlefield for w in WIZARDS) and gandalf_cast_turn is None:
                    continue
                hand.remove(r)
                pool -= ROCK_COST[r]
                mana_rocks += ROCK_MANA.get(r, 1)
                battlefield.add(r)

        # commander on 4 mana
        if gandalf_cast_turn is None and pool >= 4:
            gandalf_cast_turn = turn
            pool -= 4

        # cast a magecraft payoff if affordable (assembly priority)
        for p in MAGECRAFT_PAYOFFS:
            if p in hand and MAGECRAFT_COST[p] <= pool:
                hand.remove(p)
                battlefield.add(p)
                pool -= MAGECRAFT_COST[p]
                break

        # Naru Meha is HELD in hand: her copy trigger is an ETB (mirror-verified),
        # so the loops only start when she is flashed in response to our own
        # Flicker/Sublime still on the stack. Pre-casting her kills the combo.

        # cast a spare wizard for board presence (X engine)
        for w in WIZARDS:
            if w == "Naru Meha, Master Wizard":
                continue
            if w in hand and pool >= 3:
                hand.remove(w)
                battlefield.add(w)
                pool -= 3
                break

        # Panoptic Mirror line: cast (5), imprint extra turn (7) later
        if "Panoptic Mirror" in hand and pool >= 5:
            hand.remove("Panoptic Mirror")
            battlefield.add("Panoptic Mirror")
            pool -= 5
        if "Panoptic Mirror" in battlefield and pool >= 7 and \
           any(s in hand for s in ("Temporal Mastery", "Alrund's Epiphany", "Time Stretch")):
            return turn + 1  # imprint now, first free extra turn next upkeep -> lock online

        # tutors
        for t, cost in TUTOR_TO_HAND.items():
            if t in hand and pool >= cost:
                fetch_pool = BLUE_INSTANTS_FETCHABLE if t == "Merchant Scroll" else ANY_IS_FETCHABLE
                want = combo_wants(hand, battlefield, fetch_pool, deck)
                if want:
                    hand.remove(t)
                    pool -= cost
                    deck.remove(want)
                    hand.append(want)
        if "Mystical Tutor" in hand and pool >= 1:
            want = combo_wants(hand, battlefield, ANY_IS_FETCHABLE, deck)
            if want:
                hand.remove("Mystical Tutor")
                pool -= 1
                deck.remove(want)
                top_stack.append(want)

        # cantrips / draw with leftover mana
        for c in list(hand):
            if c in CANTRIP_COST and CANTRIP_COST[c] <= pool:
                hand.remove(c)
                pool -= CANTRIP_COST[c]
                for _ in range(CANTRIP_DRAW.get(c, 1)):
                    if deck:
                        hand.append(deck.pop())
        for c in list(hand):
            if c in BIG_DRAW_COST and BIG_DRAW_COST[c] <= pool and BIG_DRAW[c]:
                hand.remove(c)
                pool -= BIG_DRAW_COST[c]
                for _ in range(BIG_DRAW[c]):
                    if deck:
                        hand.append(deck.pop())

        if ENGINE_DRAW:
            engines = battlefield & {"Archmage Emeritus", "Jori En, Ruin Diver",
                                     "Raff, Weatherlight Stalwart", "Kitsa, Otterball Elite"}
            for _ in range(min(len(engines), 2)):
                if deck:
                    hand.append(deck.pop())

        # ---- win checks (engine online) ----
        # All Naru lines require Naru IN HAND: her copy trigger is an ETB, so she
        # must be flashed in while our own Flicker/Sublime is still on the stack.
        payoff_out = bool(battlefield & MAGECRAFT_PAYOFFS)
        commander_out = gandalf_cast_turn is not None
        naru_in_hand = "Naru Meha, Master Wizard" in hand
        # W1 Fury Storm loop: copies of FS keep targeting the original FS on the
        # stack; needs commander cast >=1, a second spell to target, and a
        # magecraft payoff to convert. FS 4 + cheap target spell ~2.
        if "Fury Storm" in hand and payoff_out and commander_out and pool >= 6 \
           and len(hand) >= 2:
            return turn
        # W2 flash a starter (Naru/Dualcaster) in response to our own blink spell
        if payoff_out and any(
                f in hand and s in hand and pool >= fc + sc
                for f, fc in FLICKERS.items() for s, sc in STARTERS.items()):
            return turn
        # W3 flash Naru in response to own Sublime Epiphany (6 + 4 mana);
        # payoff required as the uniform kill-conversion standard (conservative:
        # the token-Naru loop alone already draws the deck via the draw mode)
        if "Sublime Epiphany" in hand and payoff_out and naru_in_hand and pool >= 10:
            return turn
    return None


def combo_wants(hand, battlefield, fetch_pool, deck):
    """Pick the missing combo piece a tutor should fetch, if any."""
    have_payoff = bool(battlefield & MAGECRAFT_PAYOFFS)
    starter = any(s in hand for s in STARTERS)  # ETB trigger: only in-hand copies combo
    naru = "Naru Meha, Master Wizard" in hand
    wants = []
    if have_payoff and "Fury Storm" not in hand:
        wants.append("Fury Storm")
    if have_payoff and starter and not any(f in hand for f in FLICKERS):
        wants += ["Ghostly Flicker", "Displace"]
    if naru and "Sublime Epiphany" not in hand:
        wants.append("Sublime Epiphany")
    if "Panoptic Mirror" in battlefield and not any(
            s in hand for s in ("Temporal Mastery", "Alrund's Epiphany", "Time Stretch")):
        wants += ["Temporal Mastery", "Alrund's Epiphany"]
    for w in wants:
        if w in fetch_pool and w in deck:
            return w
    return None


N = 20000

def run_pass(label):
    print(label)
    print(f"{'variant':48s} {'median':>6s} {'p25':>4s} {'p75':>4s} {'<=T7':>6s} {'<=T8':>6s} {'<=T9':>6s} {'none<=14':>8s}")
    for v in VARIANTS:
        res = [simulate(v) for _ in range(N)]
        hits = [r for r in res if r is not None]
        med = statistics.median(hits) if hits else float("nan")
        q = statistics.quantiles(hits, n=4) if len(hits) > 2 else [0, 0, 0]
        by7 = sum(1 for r in hits if r <= 7) / N
        by8 = sum(1 for r in hits if r <= 8) / N
        by9 = sum(1 for r in hits if r <= 9) / N
        none = (N - len(hits)) / N
        print(f"{v['name']:48s} {med:6.1f} {q[0]:4.1f} {q[2]:4.1f} {by7:6.1%} {by8:6.1%} {by9:6.1%} {none:8.1%}")

run_pass("PASS A - topdeck only, keep any 7")
ENGINE_DRAW = True
run_pass("PASS B - engine draw + mulligan-lite (closer to real play)")
