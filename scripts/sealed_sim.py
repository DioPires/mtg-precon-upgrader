#!/usr/bin/env python3
"""Monte Carlo simulator for Sealed pools.

Built for DEC-926 (Reality Fracture prerelease) but set-agnostic: the booster
collation lives entirely in a JSON config, so a new set needs a new config, a
Scryfall card dump, a grade file and -- if the set has a paired cycle -- a pair
table. Nothing about `fra` is hard-coded here.

    uv run python scripts/sealed_sim.py \
        --config agents/ceo/analysis/dec925/collation.json \
        --cards  agents/ceo/analysis/dec925/fra_all_cards.json \
        --pairs  agents/ceo/analysis/dec925/echoed_pairs.json \
        --grades agents/ceo/analysis/dec925/grades.json \
        --pools 100000 --seed 20260925 \
        --out agents/ceo/analysis/dec925/sim_results.json

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import time
from collections import Counter

COLOR_ORDER = "WUBRG"
COLOR_BIT = {c: 1 << i for i, c in enumerate(COLOR_ORDER)}

PAIR_NAMES = [
    "WU", "WB", "WR", "WG", "UB", "UR", "UG", "BR", "BG", "RG",
]
PAIR_MASKS = [
    COLOR_BIT[a] | COLOR_BIT[b] for a, b in PAIR_NAMES
]

DECK_SIZE = 23
PLAYABLE_FLOOR = 4.0
BOMB_FLOOR = 8.0
SPLASH_FLOOR = 7.0
SPLASH_MAX = 2
SPLASH_FIXERS_REQUIRED = 2
VIABLE_REMOVAL = 3
VIABLE_BOMBS = 1
FILLER_GRADE = 1.0

PIP_RE = re.compile(r"\{([^}]+)\}")
DUAL_MANA_RE = re.compile(r"\{T\}: Add \{([WUBRG])\} or \{([WUBRG])\}")
ANY_COLOR_MANA_RE = re.compile(r"\{T\}: Add one mana of (any|the chosen) color")
LANDCYCLING_RE = re.compile(r"basic landcycling", re.IGNORECASE)


# --------------------------------------------------------------------------
# card model
# --------------------------------------------------------------------------


def collector_num(card: dict) -> int:
    return int("".join(ch for ch in card["collector_number"] if ch.isdigit()))


def color_mask(card: dict) -> int:
    m = 0
    for c in card.get("colors") or []:
        m |= COLOR_BIT.get(c, 0)
    return m


def front_face_cost(card: dict) -> str:
    """The mana cost you actually pay to cast the card from hand.

    Split/`prepare` layouts carry both halves in the top-level `mana_cost`
    (`"{2}{R} // {B/R}"`); `card_faces[0]` is the authoritative front face.
    """
    faces = card.get("card_faces")
    if faces:
        return faces[0].get("mana_cost") or ""
    cost = card.get("mana_cost") or ""
    return cost.split("//")[0].strip()


def pip_mask(symbol: str) -> int | None:
    """Colours that can pay one mana symbol, or None if anything can pay it.

    `{W}` -> W. Hybrid `{W/B}` -> W or B. Generic-hybrid `{2/W}`, Phyrexian
    `{W/P}`, generic, `{X}`, `{C}` and `{S}` are payable by any deck.
    """
    parts = symbol.upper().split("/")
    if any(p.isdigit() for p in parts) or "P" in parts:
        return None
    m = 0
    for p in parts:
        bit = COLOR_BIT.get(p)
        if bit is None:
            return None
        m |= bit
    return m


def pip_requirements(card: dict) -> tuple[int, ...]:
    """Colour masks the card's front face requires, one per restrictive pip.

    A deck whose colour set intersects every one of these can cast the card.
    An empty tuple means castable by any deck (colourless, or lands).
    """
    reqs = []
    for symbol in PIP_RE.findall(front_face_cost(card)):
        m = pip_mask(symbol)
        if m is not None:
            reqs.append(m)
    return tuple(reqs)


def castable_subsets(reqs: tuple[int, ...]) -> int:
    """Bitmap over the 32 colour subsets: bit s set iff subset s can cast it."""
    bits = 0
    for s in range(32):
        if all(r & s for r in reqs):
            bits |= 1 << s
    return bits


def is_basic(card: dict) -> bool:
    return card["type_line"].startswith("Basic Land")


def is_dual_land(card: dict) -> bool:
    """One of the common 'Add {X} or {Y}' duals that ride in the land slot."""
    if card["rarity"] != "common" or "Land" not in card["type_line"]:
        return False
    return bool(DUAL_MANA_RE.search(card.get("oracle_text") or ""))


def fixing_mask(card: dict, count_landcycling: bool = False) -> int:
    """Which colours this card can fix for a splash.

    Board ruling (DEC-926 CEO review): a fixer is a *land in the pool that
    produces the splash colour* -- the common duals, the rare slowlands, or an
    any-colour land such as Room of Refuge. Basic-landcycling spells do not
    count: they are spells, they cost a deck slot, and they only fix when drawn.

    `count_landcycling=True` restores the original spec's wider rule, kept so
    the report can show both ends of the range.
    """
    text = card.get("oracle_text") or ""
    if "Land" not in card["type_line"] or is_basic(card):
        return 0b11111 if (count_landcycling and LANDCYCLING_RE.search(text)) else 0
    if ANY_COLOR_MANA_RE.search(text):
        return 0b11111
    m = 0
    for a, b in DUAL_MANA_RE.findall(text):
        m |= COLOR_BIT[a] | COLOR_BIT[b]
    return m


class CardTable:
    """Flat, index-addressed view of the set. All hot-loop lookups are lists."""

    def __init__(
        self,
        cards: list[dict],
        pair_table: dict | None,
        count_landcycling_as_fixer: bool = False,
    ):
        self.cards = [c for c in cards if not is_basic(c)]
        self.name = [c["name"] for c in self.cards]
        self.index = {n: i for i, n in enumerate(self.name)}
        self.rarity = [c["rarity"] for c in self.cards]
        self.cmask = [color_mask(c) for c in self.cards]
        self.reqs = [pip_requirements(c) for c in self.cards]
        self.castable = [castable_subsets(r) for r in self.reqs]
        self.is_land = ["Land" in c["type_line"] for c in self.cards]
        self.is_dual = [is_dual_land(c) for c in self.cards]
        self.fix = [
            fixing_mask(c, count_landcycling_as_fixer) for c in self.cards
        ]
        self.collector = [collector_num(c) for c in self.cards]

        paired: set[str] = set()
        self.pairs: list[tuple[int, int]] = []
        if pair_table:
            for p in pair_table["pairs"]:
                a, b = (h["name"] for h in p["halves"])
                paired.update((a, b))
                self.pairs.append((self.index[a], self.index[b]))
        self.paired_names = paired

        # cards each of the 10 two-colour pairs can cast. Castability, not
        # colour identity: {W/B} is castable by any deck with W or with B, and
        # {2/W} by any deck at all. Lands are never deck spells here -- they
        # enter the pool only as fixers.
        self.pair_slots: list[tuple[int, ...]] = []
        for i in range(len(self.cards)):
            if self.is_land[i]:
                self.pair_slots.append(())
                continue
            bits = self.castable[i]
            self.pair_slots.append(
                tuple(p for p, pm in enumerate(PAIR_MASKS) if bits >> pm & 1)
            )

    def group(self, name: str) -> list[int]:
        """Resolve a collation group name to card indices."""
        rng = range(len(self.cards))
        if name == "dual_common_land":
            return [i for i in rng if self.is_dual[i]]
        if name == "main_common":
            return [
                i for i in rng if self.rarity[i] == "common" and not self.is_dual[i]
            ]
        rarity = name.split("_")[-1]
        if rarity not in ("common", "uncommon", "rare", "mythic"):
            raise KeyError(f"unknown collation group {name!r}")
        base = [i for i in rng if self.rarity[i] == rarity and not self.is_dual[i]]
        if name.startswith("main_"):
            return base
        if name.startswith("nonpaired_"):
            return [i for i in base if self.name[i] not in self.paired_names]
        if name.startswith("paired_"):
            return [i for i in base if self.name[i] in self.paired_names]
        raise KeyError(f"unknown collation group {name!r}")

    def pair_group(self, name: str) -> list[tuple[int, int]]:
        rarity = name.split("_")[-1]
        return [p for p in self.pairs if self.rarity[p[0]] == rarity]


# --------------------------------------------------------------------------
# grades
# --------------------------------------------------------------------------

TAGS = [
    "jace", "graveyard", "heartwood", "lifegain",
    "surveil", "artifact", "prowess", "planeswalker",
]
TAG_INDEX = {t: i for i, t in enumerate(TAGS)}


class GradeTable:
    def __init__(self, table: CardTable, entries: list[dict]):
        n = len(table.cards)
        self.grade = [0.0] * n
        self.syn_grade = [0.0] * n
        self.needs = [-1] * n
        self.needs_thr = [0] * n
        self.provides = [-1] * n          # single tag index, or -1
        self.provides_extra: list[list[int]] = [[] for _ in range(n)]
        self.removal = [False] * n
        self.missing: list[str] = []

        seen = set()
        for e in entries:
            name = e["name"]
            i = table.index.get(name)
            if i is None:
                self.missing.append(name)
                continue
            seen.add(name)
            g = float(e["grade"])
            self.grade[i] = g
            self.syn_grade[i] = float(e.get("grade_synergy", g))
            need = e.get("needs")
            if need:
                if need not in TAG_INDEX:
                    raise ValueError(f"{name}: unknown needs tag {need!r}")
                self.needs[i] = TAG_INDEX[need]
                self.needs_thr[i] = int(e.get("needs_threshold", 1))
            tags = [TAG_INDEX[t] for t in e.get("provides", []) if t in TAG_INDEX]
            if tags:
                self.provides[i] = tags[0]
                self.provides_extra[i] = tags[1:]
            self.removal[i] = "removal" in e.get("roles", [])

        self.ungraded = [n_ for n_ in table.name if n_ not in seen]


# --------------------------------------------------------------------------
# collation
# --------------------------------------------------------------------------


class Collation:
    """Turns the JSON config into ready-to-sample slot descriptors."""

    def __init__(self, config: dict, table: CardTable):
        self.config = config
        self.table = table
        self.packs = int(config.get("packs_per_pool", 6))
        self.slots: list[dict] = []
        self.normalization_residuals: dict[str, float] = {}

        for spec in config["slots"]:
            weights = dict(spec["weights"])
            other = weights.pop("__other__", 0.0)
            if other:
                dest = spec.get("other_goes_to", "proportional")
                if dest == "proportional":
                    total = sum(weights.values())
                    for k in weights:
                        weights[k] += other * weights[k] / total
                else:
                    weights[dest] = weights.get(dest, 0.0) + other
            basic = weights.pop("__basic__", 0.0)
            total = sum(weights.values()) + basic
            residual = 1.0 - total
            label = ",".join(str(s) for s in spec["slots"])
            if abs(residual) > 1e-9:
                self.normalization_residuals[label] = round(residual, 6)
            keys = list(weights)
            cum: list[float] = []
            acc = 0.0
            for k in keys:
                acc += weights[k] / total
                cum.append(acc)
            basic_from = acc  # anything above this is a (dropped) basic land

            kind = spec.get("kind", "single")
            if kind == "echoed_pair":
                pools = [table.pair_group(k) for k in keys]
            else:
                pools = [table.group(k) for k in keys]
            for k, pool in zip(keys, pools):
                if not pool:
                    raise ValueError(f"collation group {k!r} resolved to 0 cards")

            # an echoed_pair descriptor yields two cards, so one descriptor
            # covers the two booster slots it is declared over
            repeats = len(spec["slots"])
            if kind == "echoed_pair":
                if repeats % 2:
                    raise ValueError(
                        f"echoed_pair slot {spec['slots']} must cover an even "
                        "number of booster slots"
                    )
                repeats //= 2
            for _ in range(repeats):
                self.slots.append(
                    {
                        "kind": kind,
                        "keys": keys,
                        "cum": cum,
                        "pools": pools,
                        "basic_from": basic_from if basic else 1.0,
                        "note": spec.get("note", ""),
                    }
                )

        promo = config.get("promo") or {}
        self.promo = None
        if promo.get("enabled"):
            weights = dict(promo["weights"])
            total = sum(weights.values())
            keys = list(weights)
            cum, acc = [], 0.0
            for k in keys:
                acc += weights[k] / total
                cum.append(acc)
            self.promo = {
                "count": int(promo.get("count", 1)),
                "cum": cum,
                "pools": [table.group(k) for k in keys],
            }

    # -- sampling ---------------------------------------------------------

    def pack(self, rnd, out: list[int]) -> None:
        for slot in self.slots:
            r = rnd()
            if r >= slot["basic_from"]:
                continue  # basic land, dropped from the pool
            cum = slot["cum"]
            j = 0
            while cum[j] < r:
                j += 1
            pool = slot["pools"][j]
            pick = pool[int(rnd() * len(pool))]
            if slot["kind"] == "echoed_pair":
                out.append(pick[0])
                out.append(pick[1])
            else:
                out.append(pick)

    def pool(self, rnd) -> list[int]:
        out: list[int] = []
        for _ in range(self.packs):
            self.pack(rnd, out)
        if self.promo:
            for _ in range(self.promo["count"]):
                r = rnd()
                cum = self.promo["cum"]
                j = 0
                while cum[j] < r:
                    j += 1
                p = self.promo["pools"][j]
                out.append(p[int(rnd() * len(p))])
        return out


# --------------------------------------------------------------------------
# deck evaluation
# --------------------------------------------------------------------------


def evaluate_pool(pool: list[int], table: CardTable, gt: GradeTable) -> list[dict]:
    """Best 23-card deck in each of the 10 two-colour pairs."""
    pair_slots = table.pair_slots
    castable = table.castable
    is_land = table.is_land
    fix = table.fix
    grade, syn, needs, thr = gt.grade, gt.syn_grade, gt.needs, gt.needs_thr
    provides, extra, removal = gt.provides, gt.provides_extra, gt.removal

    buckets: list[list[int]] = [[] for _ in range(10)]
    nonland: list[int] = []
    fixers = [0] * 5
    for i in pool:
        for p in pair_slots[i]:
            buckets[p].append(i)
        if is_land[i]:
            f = fix[i]
            if f:
                for b in range(5):
                    if f >> b & 1:
                        fixers[b] += 1
        else:
            nonland.append(i)
            f = fix[i]
            if f:
                for b in range(5):
                    if f >> b & 1:
                        fixers[b] += 1

    results = []
    for p in range(10):
        pm = PAIR_MASKS[p]
        elig = buckets[p]

        counts = [0] * len(TAGS)
        for i in elig:
            t = provides[i]
            if t >= 0:
                counts[t] += 1
                for t2 in extra[i]:
                    counts[t2] += 1

        def eff(i: int) -> float:
            t = needs[i]
            if t >= 0 and counts[t] >= thr[i]:
                return syn[i]
            return grade[i]

        cand = [(eff(i), i) for i in elig]

        # splash: up to SPLASH_MAX cards from a third colour that the pool can fix
        splash_taken: list[tuple[float, int]] = []
        splash_pool: list[tuple[float, int]] = []
        for b in range(5) if SPLASH_MAX else ():
            bit = 1 << b
            if bit & pm or fixers[b] < SPLASH_FIXERS_REQUIRED:
                continue
            allowed = pm | bit
            for i in nonland:
                bits = castable[i]
                # needs the third colour: castable with it, not without it
                if bits >> allowed & 1 and not bits >> pm & 1:
                    g = eff(i)
                    if g >= SPLASH_FLOOR:
                        splash_pool.append((g, i))
        if splash_pool:
            splash_pool.sort(reverse=True)
            seen: set[int] = set()
            for g, i in splash_pool:
                if i in seen:
                    continue
                seen.add(i)
                splash_taken.append((g, i))
                if len(splash_taken) == SPLASH_MAX:
                    break
            cand.extend(splash_taken)

        cand.sort(reverse=True)
        deck = cand[:DECK_SIZE]
        total = sum(g for g, _ in deck)
        short = DECK_SIZE - len(deck)
        if short > 0:
            total += short * FILLER_GRADE

        results.append(
            {
                "pair": PAIR_NAMES[p],
                "score": total / DECK_SIZE,
                "available": len(cand),
                "playables": sum(1 for g, _ in cand if g >= PLAYABLE_FLOOR),
                "removal": sum(1 for _, i in deck if removal[i]),
                "bombs": sum(1 for g, _ in deck if g >= BOMB_FLOOR),
                "splash": len(splash_taken),
            }
        )
    return results


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------


def run(
    collation: Collation,
    table: CardTable,
    gt: GradeTable,
    pools: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)
    rnd = rng.random

    n = 10
    viable = [0] * n
    best = [0] * n
    top2 = [0] * n
    score_sum = [0.0] * n
    avail_sum = [0] * n
    play_sum = [0] * n
    rem_sum = [0] * n
    bomb_sum = [0] * n
    splash_sum = [0] * n
    color_play = [0] * 5
    color_rem = [0] * 5
    rm_hist: Counter = Counter()
    dual_hist: Counter = Counter()
    pool_size_sum = 0
    any_viable = 0

    rarity = table.rarity
    is_dual = table.is_dual

    for _ in range(pools):
        pool = collation.pool(rnd)
        pool_size_sum += len(pool)
        rm = 0
        du = 0
        for i in pool:
            r = rarity[i]
            if r == "rare" or r == "mythic":
                rm += 1
            elif is_dual[i]:
                du += 1
        rm_hist[rm] += 1
        dual_hist[du] += 1

        res = evaluate_pool(pool, table, gt)
        # random tiebreak so equal scores share P(best) instead of the lowest
        # pair index taking it (matters most for the flat-grade placeholder run)
        jitter = [rnd() for _ in range(n)]
        ranked = sorted(range(n), key=lambda p: (-res[p]["score"], jitter[p]))
        best[ranked[0]] += 1
        top2[ranked[0]] += 1
        top2[ranked[1]] += 1
        hit = False
        for p in range(n):
            r = res[p]
            score_sum[p] += r["score"]
            avail_sum[p] += r["available"]
            play_sum[p] += r["playables"]
            rem_sum[p] += r["removal"]
            bomb_sum[p] += r["bombs"]
            splash_sum[p] += r["splash"]
            if (
                r["playables"] >= DECK_SIZE
                and r["removal"] >= VIABLE_REMOVAL
                and r["bombs"] >= VIABLE_BOMBS
            ):
                viable[p] += 1
                hit = True
            for b, c in enumerate(COLOR_ORDER):
                if c in r["pair"]:
                    color_play[b] += r["playables"]
                    color_rem[b] += r["removal"]
        if hit:
            any_viable += 1

    per_pair = []
    for p in range(n):
        per_pair.append(
            {
                "pair": PAIR_NAMES[p],
                "p_viable": viable[p] / pools,
                "mean_score": score_sum[p] / pools,
                "p_best": best[p] / pools,
                "p_top2": top2[p] / pools,
                "mean_available": avail_sum[p] / pools,
                "mean_playables": play_sum[p] / pools,
                "mean_removal": rem_sum[p] / pools,
                "mean_bombs": bomb_sum[p] / pools,
                "mean_splash": splash_sum[p] / pools,
            }
        )

    per_color = []
    for b, c in enumerate(COLOR_ORDER):
        # each colour appears in 4 of the 10 pairs
        per_color.append(
            {
                "color": c,
                "mean_playables": color_play[b] / (pools * 4),
                "mean_removal": color_rem[b] / (pools * 4),
            }
        )

    def hist(counter: Counter) -> dict:
        t = sum(counter.values())
        return {
            "mean": sum(k * v for k, v in counter.items()) / t,
            "distribution": {
                str(k): counter[k] / t for k in sorted(counter)
            },
        }

    return {
        "pools": pools,
        "seed": seed,
        "mean_pool_size": pool_size_sum / pools,
        "p_any_viable_pair": any_viable / pools,
        "per_pair": per_pair,
        "per_color": per_color,
        "rare_mythic_per_pool": hist(rm_hist),
        "dual_lands_per_pool": hist(dual_hist),
    }


def pack_expectations(
    collation: Collation, table: CardTable, packs: int, seed: int
) -> dict:
    """Mean cards per pack by rarity, excluding basics. Sampler sanity check."""
    rng = random.Random(seed)
    rnd = rng.random
    counts: Counter = Counter()
    for _ in range(packs):
        out: list[int] = []
        collation.pack(rnd, out)
        for i in out:
            if table.is_dual[i]:
                counts["dual_land"] += 1
            else:
                counts[table.rarity[i]] += 1
    return {
        "common": counts["common"] / packs,
        "uncommon": counts["uncommon"] / packs,
        "rare_plus_mythic": (counts["rare"] + counts["mythic"]) / packs,
        "dual_land": counts["dual_land"] / packs,
        "total": sum(counts.values()) / packs,
    }


def analytic_pack_expectations(collation: Collation, table: CardTable) -> dict:
    """Closed-form counterpart to pack_expectations, straight off the config.

    Per booster, excluding basics and excluding the promo (the promo is not
    part of a pack, and the CEO's sanity targets are per-pack).
    """
    acc: dict[str, float] = {
        "common": 0.0, "uncommon": 0.0, "rare": 0.0,
        "mythic": 0.0, "dual_land": 0.0,
    }
    for slot in collation.slots:
        prev = 0.0
        for j, key in enumerate(slot["keys"]):
            p = slot["cum"][j] - prev
            prev = slot["cum"][j]
            pool = slot["pools"][j]
            if slot["kind"] == "echoed_pair":
                acc[table.rarity[pool[0][0]]] += 2 * p
            else:
                i = pool[0]
                bucket = "dual_land" if table.is_dual[i] else table.rarity[i]
                acc[bucket] += p
    return {
        "common": acc["common"],
        "uncommon": acc["uncommon"],
        "rare_plus_mythic": acc["rare"] + acc["mythic"],
        "dual_land": acc["dual_land"],
    }


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------


def placeholder_grades(table: CardTable, grade: float = 5.0) -> list[dict]:
    return [{"name": n, "grade": grade, "roles": []} for n in table.name]


def grade_template(table: CardTable) -> list[dict]:
    """Placeholder grade file that is also a fill-in sheet.

    Every non-basic card at the flat placeholder grade, carrying read-only
    context columns (rarity, cost, colours, type) so grading can happen in
    place. The simulator ignores the extra keys.
    """
    rows = []
    for i, card in enumerate(table.cards):
        rows.append(
            {
                "name": table.name[i],
                "grade": 5,
                "roles": [],
                "_collector_number": card["collector_number"],
                "_rarity": card["rarity"],
                "_mana_cost": card.get("mana_cost", ""),
                "_colors": card.get("colors") or [],
                "_type_line": card["type_line"],
            }
        )
    rows.sort(key=lambda r: int("".join(c for c in r["_collector_number"] if c.isdigit())))
    return rows


def markdown_report(results: dict, meta: dict) -> str:
    L: list[str] = []
    a = L.append
    a(f"# {meta['set_name']} Sealed pool simulation")
    a("")
    a(
        f"`{results['pools']:,}` pools, seed `{results['seed']}`, "
        f"{meta['packs']} Play Boosters"
        + (" + 1 promo" if meta["promo"] else "")
        + f". Grades: **{meta['grades_label']}**."
    )
    a("")
    a("## Assumptions")
    a("")
    for x in meta["assumptions"]:
        a(f"- {x}")
    a("")
    a("## Per pair")
    a("")
    a(
        "| Pair | P(viable) | Mean score | P(best) | P(top 2) | "
        "Playables | Removal | Bombs | Splash |"
    )
    a("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in sorted(results["per_pair"], key=lambda x: -x["mean_score"]):
        a(
            f"| {r['pair']} | {r['p_viable']:.1%} | {r['mean_score']:.2f} | "
            f"{r['p_best']:.1%} | {r['p_top2']:.1%} | {r['mean_playables']:.1f} | "
            f"{r['mean_removal']:.2f} | {r['mean_bombs']:.2f} | "
            f"{r['mean_splash']:.2f} |"
        )
    a("")
    a(
        f"P(at least one viable pair in the pool): "
        f"**{results['p_any_viable_pair']:.1%}**. "
        f"Mean pool size (basics excluded): {results['mean_pool_size']:.1f} cards."
    )
    a("")
    a("## Per colour (mean over the 4 pairs containing it)")
    a("")
    a("| Colour | Mean playables | Mean removal in deck |")
    a("|---|---:|---:|")
    for r in results["per_color"]:
        a(f"| {r['color']} | {r['mean_playables']:.1f} | {r['mean_removal']:.2f} |")
    a("")
    a("## Pool composition (grade-independent)")
    a("")
    for key, label in (
        ("rare_mythic_per_pool", "Rares + mythics per pool"),
        ("dual_lands_per_pool", "Common dual lands per pool"),
    ):
        h = results[key]
        a(f"**{label}** — mean {h['mean']:.2f}")
        a("")
        a("| Count | Share |")
        a("|---:|---:|")
        for k, v in h["distribution"].items():
            if v >= 0.0005:
                a(f"| {k} | {v:.1%} |")
        a("")
    if meta.get("pack_check"):
        pc = meta["pack_check"]
        a("## Per-pack sanity check")
        a("")
        a("| Rarity | Simulated | Closed form | CEO target |")
        a("|---|---:|---:|---:|")
        for k in ("common", "uncommon", "rare_plus_mythic", "dual_land"):
            a(
                f"| {k} | {pc['simulated'][k]:.3f} | {pc['analytic'][k]:.3f} | "
                f"{pc['target'].get(k, float('nan')):.3f} |"
            )
        a("")
    return "\n".join(L) + "\n"


SPLASH_ASSUMPTION = {
    "lands": (
        "Splash gate is LANDS ONLY (board ruling, DEC-926 CEO review): up to 2 "
        "cards of a single third colour at effective grade >= 7, allowed when "
        "the pool holds >= 2 lands that produce that colour -- the common "
        "duals, the rare slowlands, Room of Refuge. Basic-landcycling spells "
        "do NOT count as fixers: they are spells, they cost a deck slot, and "
        "they only fix when drawn. Splash cards are graded against the "
        "two-colour eligible set's synergy counts."
    ),
    "spec": (
        "Splash gate is the ORIGINAL SPEC rule (superseded; kept only to show "
        "the range): same 2-fixer gate, but basic-landcycling spells and "
        "Room of Refuge each count as a fixer for all five colours."
    ),
    "none": (
        "Splash is DISABLED in this run (lower bound): decks are strictly two "
        "colours."
    ),
}

ASSUMPTIONS = [
    "Slot 6's 1.82% Special Guest is off-set and unusable in Sealed, so that "
    "slot always yields a main-set common.",
    "Slot 8's 3% 'other' folds into non-paired uncommon.",
    "Slots 9-11: the third echoed-pair card is drawn independently of the pair "
    "in slots 9-10 and may duplicate one of its halves.",
    "Slot 12's 10.8% booster-fun variants are still set rares/mythics, split "
    "proportionally (R 83.4% / M 16.6%).",
    "Slot 13 'full main set' means the 270-card main numbering, so the 10 "
    "common duals are not in the foil slot; the 2.8% residual is normalized "
    "away proportionally.",
    "Every slot's published weights are normalized to sum to 1. The published "
    "figures for slots 8, 9-11 and 13 sum to 0.97-0.972; the CEO's target of "
    "4.81 uncommons per pack was computed without that normalization and is "
    "not reachable by any proper distribution. The normalized model gives "
    "~4.94. Commons, rares+mythics and duals match the targets.",
    "Promo: one card uniform over the 64 main-set rares + 26 mythics "
    "(64/90 vs 26/90). FLAGGED - board to confirm from the pack.",
    "Basic lands are dropped from the pool (unlimited at the event).",
    "Eligibility is castability, not colour identity (DEC-927): every pip of "
    "the front-face mana cost must be payable by the pair. A hybrid pip "
    "{W/B} needs W or B; {2/W}, Phyrexian, generic, {X} and {C} are always "
    "payable. So Blessed Ghoul ({W/B}) is eligible for all 7 pairs containing "
    "W or B and Karn, Gilded Guardian ({2/W}{2/U}{2/B}{2/R}{2/G}) for all 10 "
    "-- its 8-mana reality is priced into its grade, not its eligibility. "
    "For `prepare` DFCs the front face is card_faces[0]. Lands are never deck "
    "spells; they enter only as fixers.",
    "__SPLASH__",
    "`playables` counts the pair's available cards (eligible + any splash "
    "taken) at effective grade >= 4, not base grade; the same effective grade "
    "drives deck choice, score and the bomb count.",
    "A pool shorter than 23 eligible cards is padded to 23 at grade 1 so "
    "scores stay comparable.",
]


def main() -> int:
    global SPLASH_MAX
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--cards", required=True)
    ap.add_argument("--pairs")
    ap.add_argument("--grades")
    ap.add_argument("--pools", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=20260925)
    ap.add_argument("--out")
    ap.add_argument(
        "--emit-grade-template",
        metavar="PATH",
        help="write a flat grade-5 fill-in sheet for every non-basic card and exit",
    )
    ap.add_argument(
        "--splash-max",
        type=int,
        default=SPLASH_MAX,
        help="max splashed cards from a third colour (0 disables splashing)",
    )
    ap.add_argument(
        "--splash-fixers",
        choices=("lands", "spec"),
        default="lands",
        help="lands = only lands producing the colour count as fixers (board "
        "ruling); spec = also count basic-landcycling spells (superseded)",
    )
    ap.add_argument(
        "--no-placeholder-run",
        action="store_true",
        help="skip the flat-grade comparison run",
    )
    args = ap.parse_args()
    SPLASH_MAX = args.splash_max
    splash_mode = "none" if SPLASH_MAX == 0 else args.splash_fixers

    config = json.loads(pathlib.Path(args.config).read_text())
    cards = json.loads(pathlib.Path(args.cards).read_text())
    pair_table = (
        json.loads(pathlib.Path(args.pairs).read_text()) if args.pairs else None
    )
    table = CardTable(
        cards, pair_table, count_landcycling_as_fixer=(args.splash_fixers == "spec")
    )
    assumptions = [
        SPLASH_ASSUMPTION[splash_mode] if x == "__SPLASH__" else x
        for x in ASSUMPTIONS
    ]

    if args.emit_grade_template:
        rows = grade_template(table)
        pathlib.Path(args.emit_grade_template).write_text(
            json.dumps(rows, indent=2) + "\n"
        )
        print(f"wrote {args.emit_grade_template}: {len(rows)} entries at grade 5")
        return 0

    if not args.out:
        ap.error("--out is required unless --emit-grade-template is given")

    collation = Collation(config, table)

    runs: list[tuple[str, GradeTable]] = []
    if args.grades and pathlib.Path(args.grades).exists():
        entries = json.loads(pathlib.Path(args.grades).read_text())
        if isinstance(entries, dict):
            entries = entries["cards"]
        gt = GradeTable(table, entries)
        if gt.missing:
            print(f"warning: {len(gt.missing)} graded names not in the set: "
                  f"{gt.missing[:5]}")
        if gt.ungraded:
            print(f"warning: {len(gt.ungraded)} set cards have no grade: "
                  f"{gt.ungraded[:5]}")
        runs.append(("CEO grades", gt))
    else:
        print("no --grades file; running placeholder only")
    if not args.no_placeholder_run:
        runs.append(
            ("placeholder (flat grade 5)", GradeTable(table, placeholder_grades(table)))
        )

    pack_check = {
        "simulated": pack_expectations(collation, table, 50_000, args.seed),
        "analytic": analytic_pack_expectations(collation, table),
        "target": config.get("sanity_targets", {})
        .get("per_pack_excluding_basics", {}),
    }

    meta = {
        "set_name": config.get("set_name", config["set"]),
        "packs": collation.packs,
        "promo": bool(collation.promo),
        "assumptions": assumptions,
        "pack_check": pack_check,
    }

    payload = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "set": config["set"],
        "config": args.config,
        "cards": args.cards,
        "pairs": args.pairs,
        "grades": args.grades,
        "assumptions": assumptions,
        "pack_check": pack_check,
        "normalization_residuals": collation.normalization_residuals,
        "runs": {},
    }

    md_parts = []
    for label, gt in runs:
        t0 = time.time()
        res = run(collation, table, gt, args.pools, args.seed)
        res["elapsed_seconds"] = round(time.time() - t0, 1)
        payload["runs"][label] = res
        md_parts.append(markdown_report(res, {**meta, "grades_label": label}))
        print(f"{label}: {args.pools:,} pools in {res['elapsed_seconds']}s")

    out = pathlib.Path(args.out)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    out.with_suffix(".md").write_text("\n\n---\n\n".join(md_parts))
    print(f"wrote {out} and {out.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
