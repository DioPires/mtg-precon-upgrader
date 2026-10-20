"""DEC-472 Gandalf, Party Guest — speed iteration (goldfish combo-close model v2).

Baseline S0 = the board-approved 99 (7 power swaps + Dualcaster Mage in/Preordain
out + Displace in/Frantic Search out). Model v2 change vs the previous run:
Gandalf's combat trigger (free instant/sorcery with MV <= 2x legendary Wizards,
Gandalf counts himself) is now modeled in the win checks. Still ignored, so the
numbers stay conservative: the five cost reducers (Baral, Stenn, Kaza, Vadrik,
Mizzix), Jeska's Will exile-top-3 mode, and card selection quality.

Simplified mana model as before (every land = 1 mana, Ancient Tomb = 2, color
requirements ignored). Comparative between variants, not absolute predictions.
"""
import random
import statistics

random.seed(472)

# ---- approved 99 (V7), nonland portion ----
WIZARDS = [  # all legendary Wizards (Gandalf's X counts these + himself)
    "Baral, Chief of Compliance", "Stenn, Paranoid Partisan", "Kaza, Roil Chaser",
    "Kitsa, Otterball Elite", "Balmor, Battlemage Captain", "Raff, Weatherlight Stalwart",
    "Vivi Ornitier", "Veyran, Voice of Duality", "Adeliz, the Cinder Wind",
    "Vadrik, Astral Archmage", "Jori En, Ruin Diver", "Hurkyl, Master Wizard",
    "Vendilion Clique", "Venser, Shaper Savant", "Mizzix of the Izmagnus",
    "Kykar, Wind's Fury", "Johann, Apprentice Sorcerer", "Naru Meha, Master Wizard",
    "Gandalf the Grey", "Deekah, Fractal Theorist",
]
SUPPORT = ["Harmonic Prodigy", "Wizard's Staff", "Archmage Emeritus", "Storm-Kiln Artist",
           "Dualcaster Mage"]
PAYOFFS = ["Jeskai Revelation", "Sublime Epiphany", "Magma Opus", "Temporal Mastery",
           "Alrund's Epiphany"]
COMBO_SPELLS = ["Fury Storm", "Ghostly Flicker", "Displace", "Panoptic Mirror"]
TUTORS = ["Mystical Tutor", "Solve the Equation", "Merchant Scroll"]
DRAW = ["Dig Through Time", "Treasure Cruise"]
INTERACTION = ["Counterspell", "Wizard's Retort", "Dovin's Veto",
               "Mystic Confluence", "Fierce Guardianship",
               "Swords to Plowshares", "Generous Gift", "Chaos Warp",
               "Prismari Command", "Wear // Tear", "Flame of Anor", "Olorin's Searing Light",
               "Blasphemous Act", "Erode", "Raise the Palisade"]
PROTECTION = ["Unbreakable Formation", "Clever Concealment"]
ROCKS = ["Sol Ring", "Arcane Signet", "Lotus Petal", "Izzet Signet", "Mox Amber",
         "Talisman of Creativity", "Talisman of Progress"]
N_LANDS = 36

BASE_NONLAND = WIZARDS + SUPPORT + PAYOFFS + COMBO_SPELLS + TUTORS + DRAW \
    + INTERACTION + PROTECTION + ROCKS
assert len(BASE_NONLAND) + N_LANDS == 99, len(BASE_NONLAND)

ROCK_COST = {"Sol Ring": 1, "Arcane Signet": 2, "Lotus Petal": 0, "Izzet Signet": 2,
             "Talisman of Creativity": 2, "Talisman of Progress": 2, "Mox Amber": 0}
ROCK_MANA = {"Sol Ring": 2, "Lotus Petal": 1}

MAGECRAFT_PAYOFFS = {"Storm-Kiln Artist", "Archmage Emeritus", "Deekah, Fractal Theorist"}
MAGECRAFT_COST = {"Storm-Kiln Artist": 4, "Archmage Emeritus": 4, "Deekah, Fractal Theorist": 5}
BIG_DRAW = {"Dig Through Time": 2, "Treasure Cruise": 3}
BIG_DRAW_COST = {"Dig Through Time": 4, "Treasure Cruise": 3}  # delve avg discount

TUTOR_TO_HAND = {"Solve the Equation": 3, "Merchant Scroll": 2}
BLUE_INSTANTS_FETCHABLE = {"Ghostly Flicker", "Sublime Epiphany", "Mystical Tutor",
                           "Displace", "Dramatic Reversal"}
ANY_IS_FETCHABLE = {"Fury Storm", "Ghostly Flicker", "Sublime Epiphany", "Temporal Mastery",
                    "Alrund's Epiphany", "Mystical Tutor", "Displace",
                    "Dramatic Reversal", "Twinflame"}
MV2_POOL = {"Isochron Scepter", "Dramatic Reversal", "Twinflame"}   # Muddle transmute
WIZARD_POOL = {"Naru Meha, Master Wizard", "Dualcaster Mage"}       # Step Through

FLICKERS = {"Ghostly Flicker": 3, "Displace": 3}
STARTERS = {"Naru Meha, Master Wizard": 4, "Dualcaster Mage": 3}
LEGENDARY_WIZ = set(WIZARDS)  # Dualcaster is not legendary


def make_variant(name, add=(), cut=()):
    deck = list(BASE_NONLAND)
    for c in cut:
        deck.remove(c)
    deck += list(add)
    assert len(deck) + N_LANDS == 99, (name, len(deck))
    return {"name": name, "nonland": deck}


VARIANTS = [
    make_variant("S0 approved 99 (V7 baseline)"),
    make_variant("A1 +Scepter+Reversal -Staff -JoriEn",
                 ["Isochron Scepter", "Dramatic Reversal"],
                 ["Wizard's Staff", "Jori En, Ruin Diver"]),
    make_variant("A2 +Twinflame+StepThrough -Johann -MagmaOpus",
                 ["Twinflame", "Step Through"],
                 ["Johann, Apprentice Sorcerer", "Magma Opus"]),
    make_variant("S2 = A1+A2 (4 adds)",
                 ["Isochron Scepter", "Dramatic Reversal", "Twinflame", "Step Through"],
                 ["Wizard's Staff", "Jori En, Ruin Diver",
                  "Johann, Apprentice Sorcerer", "Magma Opus"]),
    make_variant("S3 = S2 +Muddle -TreasureCruise",
                 ["Isochron Scepter", "Dramatic Reversal", "Twinflame", "Step Through",
                  "Muddle the Mixture"],
                 ["Wizard's Staff", "Jori En, Ruin Diver",
                  "Johann, Apprentice Sorcerer", "Magma Opus", "Treasure Cruise"]),
    make_variant("S4 = S3 +JeskasWill -Balmor",
                 ["Isochron Scepter", "Dramatic Reversal", "Twinflame", "Step Through",
                  "Muddle the Mixture", "Jeska's Will"],
                 ["Wizard's Staff", "Jori En, Ruin Diver",
                  "Johann, Apprentice Sorcerer", "Magma Opus", "Treasure Cruise",
                  "Balmor, Battlemage Captain"]),
]

ENGINE_DRAW = False


def combo_wants(hand, battlefield, fetch_pool, deck, scepter_online):
    """Pick the missing combo piece a tutor should fetch, if any (priority order)."""
    have_payoff = bool(battlefield & MAGECRAFT_PAYOFFS)
    starter = any(s in hand for s in STARTERS)
    naru = "Naru Meha, Master Wizard" in hand
    wants = []
    # cheapest lines first
    if "Dualcaster Mage" in hand and "Twinflame" not in hand:
        wants.append("Twinflame")
    if have_payoff and ("Isochron Scepter" in hand or scepter_online) \
            and "Dramatic Reversal" not in hand and not scepter_online:
        wants.append("Dramatic Reversal")
    if have_payoff and "Dramatic Reversal" in hand and "Isochron Scepter" not in hand \
            and not scepter_online:
        wants.append("Isochron Scepter")
    if have_payoff and "Fury Storm" not in hand:
        wants.append("Fury Storm")
    if have_payoff and starter and not any(f in hand for f in FLICKERS):
        wants += ["Ghostly Flicker", "Displace"]
    if naru and "Sublime Epiphany" not in hand:
        wants.append("Sublime Epiphany")
    if "Panoptic Mirror" in battlefield and not any(
            s in hand for s in ("Temporal Mastery", "Alrund's Epiphany")):
        wants += ["Temporal Mastery", "Alrund's Epiphany"]
    for w in wants:
        if w in fetch_pool and w in deck:
            return w
    return None


def starter_wants(hand, deck):
    """Step Through target: fetch a starter when a partner spell is in hand."""
    if any(s in hand for s in STARTERS):
        return None
    if "Twinflame" in hand and "Dualcaster Mage" in deck:
        return "Dualcaster Mage"
    if any(f in hand for f in FLICKERS) or "Sublime Epiphany" in hand:
        for s in ("Naru Meha, Master Wizard", "Dualcaster Mage"):
            if s in deck:
                return s
    return None


def simulate(variant, max_turn=14):
    deck = variant["nonland"] + ["LAND"] * N_LANDS
    random.shuffle(deck)
    hand = [deck.pop() for _ in range(7)]
    if ENGINE_DRAW:
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
    scepter_online = False
    top_stack = []

    for turn in range(1, max_turn + 1):
        if top_stack:
            hand.append(top_stack.pop())
        elif deck:
            hand.append(deck.pop())
        if "LAND" in hand:
            hand.remove("LAND")
            lands += 1
            if tomb_bonus == 0 and lands >= 3 and random.random() < 0.35:
                tomb_bonus = 1  # Ancient Tomb drawn-and-played approximation
        mana = lands + tomb_bonus + mana_rocks
        pool = mana

        for r in list(hand):
            if r in ROCK_COST and ROCK_COST[r] <= pool:
                if r == "Mox Amber" and not any(w in battlefield for w in WIZARDS) \
                        and gandalf_cast_turn is None:
                    continue
                hand.remove(r)
                pool -= ROCK_COST[r]
                mana_rocks += ROCK_MANA.get(r, 1)
                battlefield.add(r)

        if gandalf_cast_turn is None and pool >= 4:
            gandalf_cast_turn = turn
            pool -= 4

        for p in MAGECRAFT_PAYOFFS:
            if p in hand and MAGECRAFT_COST[p] <= pool:
                hand.remove(p)
                battlefield.add(p)
                pool -= MAGECRAFT_COST[p]
                break

        # Naru/Dualcaster are HELD in hand (ETB-copy only works flashed in
        # response to our own spell still on the stack).
        for w in WIZARDS:
            if w == "Naru Meha, Master Wizard":
                continue
            if w in hand and pool >= 3:
                hand.remove(w)
                battlefield.add(w)
                pool -= 3
                break

        # Isochron Scepter: cast + imprint Dramatic Reversal
        if "Isochron Scepter" in hand and "Dramatic Reversal" in hand and pool >= 2:
            hand.remove("Isochron Scepter")
            hand.remove("Dramatic Reversal")
            battlefield.add("Isochron Scepter")
            scepter_online = True
            pool -= 2

        if "Panoptic Mirror" in hand and pool >= 5:
            hand.remove("Panoptic Mirror")
            battlefield.add("Panoptic Mirror")
            pool -= 5
        if "Panoptic Mirror" in battlefield and pool >= 7 and \
           any(s in hand for s in ("Temporal Mastery", "Alrund's Epiphany")):
            return turn + 1

        # tutors
        for t, cost in TUTOR_TO_HAND.items():
            if t in hand and pool >= cost:
                fetch_pool = BLUE_INSTANTS_FETCHABLE if t == "Merchant Scroll" else ANY_IS_FETCHABLE
                want = combo_wants(hand, battlefield, fetch_pool, deck, scepter_online)
                if want:
                    hand.remove(t)
                    pool -= cost
                    deck.remove(want)
                    hand.append(want)
        if "Mystical Tutor" in hand and pool >= 1:
            want = combo_wants(hand, battlefield, ANY_IS_FETCHABLE, deck, scepter_online)
            if want:
                hand.remove("Mystical Tutor")
                pool -= 1
                deck.remove(want)
                top_stack.append(want)
        if "Muddle the Mixture" in hand and pool >= 3:
            want = combo_wants(hand, battlefield, MV2_POOL, deck, scepter_online)
            if want:
                hand.remove("Muddle the Mixture")
                pool -= 3
                deck.remove(want)
                hand.append(want)
        if "Step Through" in hand and pool >= 2:
            want = starter_wants(hand, deck)
            if want:
                hand.remove("Step Through")
                pool -= 2
                deck.remove(want)
                hand.append(want)

        for c in list(hand):
            if c in BIG_DRAW_COST and BIG_DRAW_COST[c] <= pool:
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

        # ---- win checks (engine online at combat) ----
        payoff_out = bool(battlefield & MAGECRAFT_PAYOFFS)
        commander_out = gandalf_cast_turn is not None
        naru_in_hand = "Naru Meha, Master Wizard" in hand
        # Gandalf free-cast budget: one instant/sorcery, MV <= 2x legendary Wizards
        # (Gandalf counts himself)
        free_mv = 2 * (1 + len(battlefield & LEGENDARY_WIZ)) if commander_out else 0
        # Jeska's Will: +5 red minus its 3 cost = +2 net for the combo turn
        jeska = 2 if ("Jeska's Will" in hand and commander_out and pool >= 3) else 0
        p = pool + jeska

        # W5 Twinflame + flashed Dualcaster = infinite hasty attackers (no payoff needed)
        if "Twinflame" in hand and "Dualcaster Mage" in hand:
            cost = 3 if free_mv >= 2 else 5   # Gandalf free-casts Twinflame at combat
            if p >= cost:
                return turn
        # W4 Scepter loop (needs rocks producing >= 2 to sustain the activation)
        if payoff_out and mana_rocks >= 2:
            if scepter_online and p >= 2:
                return turn
            if "Isochron Scepter" in hand and "Dramatic Reversal" in hand and p >= 4:
                return turn
        # W1 Fury Storm loop (free-cast the cheap target spell via Gandalf)
        if "Fury Storm" in hand and payoff_out and commander_out and len(hand) >= 2:
            cost = 4 if free_mv >= 2 else 6
            if p >= cost:
                return turn
        # W2 flash a starter in response to our own blink spell
        for f, fc in FLICKERS.items():
            for s, sc in STARTERS.items():
                if f in hand and s in hand and payoff_out:
                    cost = sc if free_mv >= fc else fc + sc
                    if p >= cost:
                        return turn
        # W3 Naru flashed in response to our own Sublime Epiphany
        if "Sublime Epiphany" in hand and payoff_out and naru_in_hand:
            cost = 4 if free_mv >= 6 else 10
            if p >= cost:
                return turn
    return None


N = 20000


def run_pass(label):
    print(label)
    print(f"{'variant':46s} {'median':>6s} {'<=T6':>6s} {'<=T7':>6s} {'<=T8':>6s} {'<=T9':>6s} {'none<=14':>8s}")
    for v in VARIANTS:
        res = [simulate(v) for _ in range(N)]
        hits = [r for r in res if r is not None]
        med = statistics.median(hits) if hits else float("nan")
        by6 = sum(1 for r in hits if r <= 6) / N
        by7 = sum(1 for r in hits if r <= 7) / N
        by8 = sum(1 for r in hits if r <= 8) / N
        by9 = sum(1 for r in hits if r <= 9) / N
        none = (N - len(hits)) / N
        print(f"{v['name']:46s} {med:6.1f} {by6:6.1%} {by7:6.1%} {by8:6.1%} {by9:6.1%} {none:8.1%}")


run_pass("PASS A - topdeck only")
ENGINE_DRAW = True
run_pass("PASS B - engine draw + mulligan-lite (realistic pass)")


def assembled_turn(variant, max_turn=10):
    """First turn the cards of any win line are assembled in hand/board (mana ignored)."""
    deck = variant["nonland"] + ["LAND"] * N_LANDS
    random.shuffle(deck)
    hand = [deck.pop() for _ in range(7)]
    nl = hand.count("LAND")
    if nl < 2 or nl > 5:
        deck += hand
        random.shuffle(deck)
        hand = [deck.pop() for _ in range(7)]
    have = set(hand)
    for turn in range(1, max_turn + 1):
        for _ in range(1 + (1 if turn >= 4 else 0)):
            if deck:
                c = deck.pop()
                hand.append(c)
                have.add(c)
        # tutors grab the best missing piece (mana ignored, one per turn)
        for t in ("Mystical Tutor", "Solve the Equation", "Merchant Scroll",
                  "Muddle the Mixture", "Step Through"):
            if t in have:
                pool = {"Mystical Tutor": ANY_IS_FETCHABLE, "Solve the Equation": ANY_IS_FETCHABLE,
                        "Merchant Scroll": BLUE_INSTANTS_FETCHABLE, "Muddle the Mixture": MV2_POOL,
                        "Step Through": WIZARD_POOL}[t]
                want = combo_wants(hand, set(), pool, deck, False) or \
                    (starter_wants(hand, deck) if t == "Step Through" else None)
                if want and want in pool and want in deck:
                    have.discard(t); hand.remove(t)
                    deck.remove(want); hand.append(want); have.add(want)
                    break
        payoff = bool(have & MAGECRAFT_PAYOFFS)
        if ("Twinflame" in have and "Dualcaster Mage" in have) or \
           (payoff and "Isochron Scepter" in have and "Dramatic Reversal" in have) or \
           (payoff and "Fury Storm" in have) or \
           (payoff and any(f in have for f in FLICKERS) and any(s in have for s in STARTERS)) or \
           (payoff and "Sublime Epiphany" in have and "Naru Meha, Master Wizard" in have):
            return turn
    return None


print()
print("ASSEMBLED-BY (pieces in hand, mana ignored, tutor 1/turn, +1 draw from T4)")
for v in VARIANTS:
    res = [assembled_turn(v) for _ in range(N)]
    hits = [r for r in res if r is not None]
    by6 = sum(1 for r in hits if r <= 6) / N
    by7 = sum(1 for r in hits if r <= 7) / N
    print(f"{v['name']:46s} <=T6 {by6:6.1%}  <=T7 {by7:6.1%}")
