#!/usr/bin/env python3
"""The tutor and recursion tag vocabulary of a deck's ``decklist`` entries.

The goldfish's two combo checks (scripts/export_simulation_results.py:
``combo_line_costs`` and ``assembly_tutor_cost``) read these fields to decide
which piece a tutor or recursion card in hand may stand in for, and what it
costs (owner-approved plan "combo checks, step 1", 2026-11-24). This module is
the one definition of the fields, their closed value sets and the checks on
them, and of the closed role set (ROLES) every entry's roles are checked
against: the exporter (substitute_tables) and scripts/validate_deck_json.py both
call entry_errors, so a decklist entry one accepts the other accepts. What
each value means to the checks is documented in data/bracket-philosophy.md
("comboLethal proxy schema") and in the exporter.

Known limit: a cost tag (``tutor_cost``, ``recursion_cost``) may hold the
hybrid and Phyrexian symbols a printed cost can hold, and the exporter prices
them as free, as it does in a card's printed cost.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

# The closed role set of decklist[].primary_role and secondary_role and of
# commanderRoles (docs/role-taxonomy.md). compute_deck_metrics.py scores role
# coverage against it, and the goldfish holds an instant or sorcery back by its
# primary role (export_simulation_results.goldfish_holds_back), so entry_errors
# refuses a role that is not a string or is outside it, and a missing primary
# role on a card whose front face is not a land or is not known.
ROLES = frozenset({
    "land", "ramp", "mana-fixing", "card-draw", "tutor",
    "removal-spot", "removal-board", "counterspell", "protection",
    "recursion", "payoff", "wincon", "engine", "threat", "utility",
})
# Card types a target list may name, lower-case, read on the front face of the
# card found or returned; "any" allows every card type.
CARD_TYPES = frozenset({"artifact", "battle", "creature", "enchantment", "instant", "land",
                        "planeswalker", "sorcery"})
TARGET_VALUES = CARD_TYPES | {"any"}
# Subtypes a tag may name, read on the front face as printed. A Changeling card
# has every creature subtype, not the others (export_simulation_results.
# substitute_allows).
CREATURE_SUBTYPES = frozenset({"Goblin", "Wizard"})
NONCREATURE_SUBTYPES = frozenset({"Aura", "Equipment"})
SUBTYPE_VALUES = CREATURE_SUBTYPES | NONCREATURE_SUBTYPES
# Colours of the card found; C means colourless.
COLOR_VALUES = frozenset({"W", "U", "B", "R", "G", "C"})
# Where a tutor puts the card it finds. A missing tutor_mode means to_hand.
TUTOR_MODES = frozenset({"to_hand", "to_top", "to_battlefield", "to_graveyard", "split_hand_graveyard", "none"})
# Where a recursion card puts the card it returns, or why it supplies nothing:
# self (returns only itself), on_death (acts only after a permanent dies or
# leaves the battlefield), none (no credit).
RECURSION_MODES = frozenset({"to_battlefield", "to_hand", "cast_from_graveyard", "self", "on_death", "none"})
# An additional cost the search or return takes: one object each.
EXTRA_COSTS = frozenset({"sacrifice-creature", "sacrifice-green-creature", "sacrifice-artifact",
                         "discard-creature"})
# "later": the search or return cannot happen the turn the card is cast.
TIMINGS = frozenset({"later"})
# A mana cost string: a run of braced symbols, each one of MANA_SYMBOLS or a
# GENERIC number.
MANA_COST = re.compile(r"(\{[^{}]+\})+")
COLOURS = ("W", "U", "B", "R", "G")
# The ten two-colour hybrid symbols, in the order cards print them.
HYBRID_PAIRS = ("W/U", "U/B", "B/R", "R/G", "G/W", "W/B", "U/R", "B/G", "R/W", "G/U")
# The symbols a cost tag may hold besides a generic number, without their
# braces, in the form cards print them: X, the five colours and C, the hybrid
# pairs, the generic hybrids (2/W), the colourless hybrids (C/W), the
# Phyrexian symbols (W/P) and the ten hybrid Phyrexian symbols (W/U/P). Four
# of those ten are printed in a mana cost today ({G/U/P}, {G/W/P}, {R/G/P},
# {R/W/P}, in the 2026-11-23 oracle mirror); the other six pairs are accepted
# in the same form. The exporter prices the hybrid and Phyrexian symbols as
# free (parse_generic_mana_cost), as for printed costs: a known limit.
MANA_SYMBOLS = frozenset({"X", *COLOURS, "C", *HYBRID_PAIRS, *(f"2/{c}" for c in COLOURS),
                          *(f"C/{c}" for c in COLOURS), *(f"{c}/P" for c in COLOURS),
                          *(f"{pair}/P" for pair in HYBRID_PAIRS)})
# A generic number in ASCII digits, as printed: no leading zero ({01} fails).
GENERIC = re.compile(r"0|[1-9][0-9]*")


def is_mana_symbol(symbol: str) -> bool:
    """Whether a symbol, without its braces, is one a cost tag may hold: a
    generic number in ASCII digits with no leading zero, or one of
    MANA_SYMBOLS, in the form cards print symbols (upper case, the colours in
    the printed order). Any other symbol fails."""
    return symbol in MANA_SYMBOLS or GENERIC.fullmatch(symbol) is not None


def _names(values: frozenset) -> str:
    return ", ".join(sorted(values))


def _list_of(values: frozenset) -> Callable[[object], str | None]:
    def check(value: object) -> str | None:
        if (not isinstance(value, list) or not value or len(set(map(str, value))) != len(value)
                or not all(isinstance(item, str) and item in values for item in value)):
            return f"a non-empty list without repeats of: {_names(values)}"
        return None
    return check


def _one_of(values: frozenset) -> Callable[[object], str | None]:
    def check(value: object) -> str | None:
        return None if isinstance(value, str) and value in values else f"one of: {_names(values)}"
    return check


def _count(value: object) -> str | None:
    return None if type(value) is int and value >= 0 else "an integer of 0 or more"


def _mv_cap(value: object) -> str | None:
    return None if value == "X" or (type(value) is int and value >= 0) else 'an integer of 0 or more, or "X"'


def _true(value: object) -> str | None:
    return None if value is True else "true"


def _mana_cost(value: object) -> str | None:
    if (isinstance(value, str) and MANA_COST.fullmatch(value)
            and all(is_mana_symbol(symbol) for symbol in re.findall(r"\{([^{}]+)\}", value))):
        return None
    return ('a mana cost such as "{1}{B}" (symbols as cards print them: a number, X, W, U, B, R, G, C, or a '
            'hybrid or Phyrexian symbol such as {B/G}, {2/W} or {G/P})')


# Every tutor_* and recursion_* field a decklist entry may carry, with the
# check its value must pass.
TAG_FIELDS: dict[str, Callable[[object], str | None]] = {
    "tutor_targets": _list_of(TARGET_VALUES),
    "tutor_subtypes": _list_of(SUBTYPE_VALUES),
    "tutor_colors": _list_of(COLOR_VALUES),
    "tutor_mv_cap": _mv_cap,
    "tutor_mv_exact": _count,
    "tutor_mode": _one_of(TUTOR_MODES),
    "tutor_cost": _mana_cost,
    "tutor_timing": _one_of(TIMINGS),
    "tutor_extra_cost": _one_of(EXTRA_COSTS),
    "tutor_free_cast_via_bargain": _true,
    "recursion_targets": _list_of(TARGET_VALUES),
    "recursion_subtypes": _list_of(SUBTYPE_VALUES),
    "recursion_mv_cap": _mv_cap,
    "recursion_mv_odd": _true,
    "recursion_mode": _one_of(RECURSION_MODES),
    "recursion_cost": _mana_cost,
    "recursion_timing": _one_of(TIMINGS),
    "recursion_extra_cost": _one_of(EXTRA_COSTS),
}


def is_tag_field(key: str) -> bool:
    """A key the vocabulary governs: every key that names a tutor or recursion
    field in any spelling ("tutor" or "recursion" in it, any case), so a
    misspelt key such as ``tutorMode`` is refused, not read as no tag."""
    return "tutor" in key.lower() or "recursion" in key.lower()


def tag_errors(entry: Mapping[str, object]) -> list[str]:
    """One message per key of a decklist entry that names a tutor or recursion
    field (is_tag_field) but is not a field of the vocabulary, or whose value
    fails the field's check."""
    errors = []
    for key, value in entry.items():
        if not is_tag_field(key):
            continue
        check = TAG_FIELDS.get(key)
        if check is None:
            errors.append(f"{key}: unknown field (known: {_names(frozenset(TAG_FIELDS))})")
            continue
        expected = check(value)
        if expected is not None:
            errors.append(f"{key}: {value!r} is not {expected}")
    return errors


PERMANENT_TYPE_WORDS = frozenset({"Artifact", "Battle", "Creature", "Enchantment", "Land", "Planeswalker"})


def entry_errors(entry: Mapping[str, object], has_combo_line: bool,
                 front: tuple[str, str] | None) -> list[str]:
    """Every error of one decklist entry's tags: tag_errors, and the checks
    that need the entry's roles, its deck and its card:

    - a ``primary_role`` or ``secondary_role`` that is present and not a
      string, JSON null included (the role checks below then read only the
      roles that are), or a string outside ROLES (a typo, a legacy word such
      as "removal");
    - a missing ``primary_role`` on a card whose front face is not a land,
      or not known (``front`` None): the goldfish's hold reads it;
    - a ``tutor_*`` field on an entry without the ``tutor`` role, or a
      ``recursion_*`` field without the ``recursion`` role (a forgotten role
      would leave the tags unread);
    - in a deck with a ``kind: "combo"`` win condition (``has_combo_line``), a
      recursion entry whose front face is not a land and that has no
      ``recursion_mode`` (rule B9);
    - a ``*_mv_cap`` of "X" on a card whose cost paid for that role has no
      {X}: the cost tag when there is one (with the printed cost too when the
      front face is a permanent, as it is cast first), else the printed cost.

    ``front`` is the card's front face as (type line, mana cost), or None
    when the card is not known (the last two checks are then skipped)."""
    errors = tag_errors(entry)
    roles = set()
    for key in ("primary_role", "secondary_role"):
        if key not in entry:
            continue
        value = entry[key]
        if not isinstance(value, str):
            errors.append(f"{key}: {value!r} is not a string")
        elif value not in ROLES:
            errors.append(f"{key}: {value!r} is not a role (docs/role-taxonomy.md)")
        else:
            roles.add(value)
    if "primary_role" not in entry:
        if front is None:
            errors.append("primary_role: missing on a card whose front face is not known")
        elif "Land" not in re.findall(r"[\w'-]+", front[0]):
            errors.append("primary_role: missing on a card whose front face is not a land")
    for role in ("tutor", "recursion"):
        tagged = sorted(key for key in entry if key in TAG_FIELDS and key.startswith(f"{role}_"))
        if tagged and role not in roles:
            errors.append(f"{', '.join(tagged)}: on an entry without the {role} role")
    if front is None:
        return errors
    type_line, mana_cost = front
    words = set(re.findall(r"[\w'-]+", type_line))
    if (has_combo_line and "recursion" in roles and "recursion_mode" not in entry and "Land" not in words):
        errors.append("recursion_mode: missing on a recursion entry in a deck with a kind \"combo\" win condition")
    for role in ("tutor", "recursion"):
        if entry.get(f"{role}_mv_cap") != "X":
            continue
        cost_tag = entry.get(f"{role}_cost")
        paid = mana_cost if cost_tag is None else (
            mana_cost + str(cost_tag) if words & PERMANENT_TYPE_WORDS else str(cost_tag))
        if "{X}" not in paid:
            errors.append(f"{role}_mv_cap: \"X\" but the cost the card pays has no {{X}}")
    return errors
