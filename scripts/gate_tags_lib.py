#!/usr/bin/env python3
"""The tutor and recursion tag vocabulary of a deck's ``decklist`` entries,
and the fields of a ``winConditions`` combo line.

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

The same holds for a deck's ``winConditions`` (the value, each entry's keys
and its combo-line fields: pieces, startPiece, minX and the combo-line
corrections' fields, owner decision 27, 2026-11-25): the exporter
(extract_combo_lines) raises on what win_conditions_errors finds and the
validator reports it.

Known limit: a cost tag (``tutor_cost``, ``recursion_cost``) may hold the
hybrid and Phyrexian symbols a printed cost can hold, and the exporter prices
them as free, as it does in a card's printed cost; the same holds for a combo
line's ``extraCost`` and ``readyHaste`` costs.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Iterable, Mapping

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


# The fields of a winConditions entry the combo check reads, on a kind
# "combo" entry only: startPiece and minX, and the combo-line corrections'
# fields (owner decision 27, 2026-11-25). Their meanings are in
# export_simulation_results.extract_combo_lines and data/bracket-philosophy.md.
COMBO_LINE_FIELDS = ("startPiece", "minX", "readyPieces", "readyHaste", "castFromHand", "needsCreature",
                     "extraCost")
# Every key a winConditions entry may carry, a closed list: the keys the deck
# files use (the deck page reads title, description and cards; mana_cost and
# sources are read by no code) and the combo-line fields. Any other key is
# refused, not read as no field.
WINCON_KEYS = frozenset({"title", "kind", "description", "cards", "sources", "mana_cost", "pieces",
                         *COMBO_LINE_FIELDS})
# The kinds of haste source readyHaste lists: a static grant on the battlefield
# (a list of card names), an Equipment on the battlefield or an instant in the
# hand (each a mapping of card names to the mana cost of the equip or the cast).
HASTE_KINDS = ("static", "equip", "instant")


def combo_line_cards(commander: str | None, decklist: Iterable[str]) -> list[str]:
    """The cards a combo line may name, in one definition for both readers
    (the exporter builds its card profiles from it, the validator its deck
    set): the decklist and the commander, named as the deck lists them (a
    face name is not the card's name). A partner is not one: the goldfish
    models no partner (wincon_errors refuses a line that names it)."""
    return list(dict.fromkeys([*decklist, *([] if commander is None else [commander])]))


def win_conditions_errors(win_conditions: object, cards: Mapping[str, str], x_cards: Collection[str],
                          partner: object = None) -> list[tuple[int | None, str]]:
    """Every error of a deck's winConditions value, as (the entry's index, or
    None for the value itself, the message): a value that is not a list (null
    included; a reader passes [] for an omitted key), an entry that is not an
    object, and each entry's wincon_errors."""
    if not isinstance(win_conditions, list):
        return [(None, f"{win_conditions!r} is not a list of win conditions")]
    errors = []
    for index, wincon in enumerate(win_conditions):
        if not isinstance(wincon, Mapping):
            errors.append((index, f"{wincon!r} is not an object"))
            continue
        errors.extend((index, error) for error in wincon_errors(wincon, cards, x_cards, partner))
    return errors


def _fixed_cost(value: object) -> str | None:
    """The cost check of extraCost and of readyHaste's costs: a mana cost (the
    cost tags' check) with no {X}, which nothing would pay."""
    if _mana_cost(value) is None and "{X}" not in str(value):
        return None
    return ('a mana cost with no {X}, such as "{1}{W}" (symbols as cards print them: a number, W, U, B, R, G, '
            'C, or a hybrid or Phyrexian symbol such as {B/G}, {2/W} or {G/P})')


def wincon_errors(wincon: Mapping[str, object], cards: Mapping[str, str], x_cards: Collection[str],
                  partner: object = None) -> list[str]:
    """Every error of one winConditions entry.

    ``cards`` maps each card a combo line may name (combo_line_cards) to its
    front face's type line ("" when it is not known), ``x_cards`` holds those
    whose front-face mana cost has {X}, ``partner`` is the deck's partner
    commander, if any. The errors:

    - a key that is not one of WINCON_KEYS;
    - a combo-line field on an entry whose kind is not "combo";
    - on a combo entry, ``pieces`` that is not a non-empty list whose entries
      are card names or lists of two or more card names (a list is a choice
      of one of its cards; lists do not nest), a card named twice in the
      entry's pieces, a card that is not in the deck, the partner;
    - ``startPiece`` that is not one of the pieces named outside a list;
    - ``minX`` that is not a mapping of cards its pieces name (in a list or
      not), with {X} in their cost, to positive integers;
    - ``readyPieces`` or ``castFromHand`` that is not a non-empty list,
      without repeats, of pieces named outside a list; a ``readyPieces``
      card whose front face is a land (the goldfish does not track when a
      land entered);
    - ``readyHaste`` without ``readyPieces``, or that is not a non-empty
      mapping of HASTE_KINDS (static: a non-empty list of card names; equip,
      instant: a non-empty mapping of card names to mana costs with no {X}),
      a haste card not in the deck, named twice or one of the entry's pieces,
      an equip card known not to be an Equipment or an instant card known
      not to be an instant;
    - ``needsCreature`` that is not {"count": N}, N a positive integer;
    - ``extraCost`` that is not a mana cost with no {X}."""
    errors = [f"{key}: unknown field (known: {', '.join(sorted(WINCON_KEYS))})"
              for key in wincon if key not in WINCON_KEYS]
    present = [key for key in COMBO_LINE_FIELDS if key in wincon]
    if wincon.get("kind") != "combo":
        if present:
            errors.append(f"{', '.join(present)}: read only on a kind \"combo\" entry")
        return errors
    pieces = wincon.get("pieces")
    if not isinstance(pieces, list) or not pieces:
        errors.append(f"pieces: {pieces!r} is not a non-empty list of card names and lists of card names")
        return errors
    plain, named = [], []
    for entry in pieces:
        if isinstance(entry, str):
            plain.append(entry)
            named.append(entry)
        elif isinstance(entry, list):
            if any(isinstance(item, list) for item in entry):
                errors.append(f"pieces: {entry!r} holds a list (lists do not nest)")
            errors.extend(f"pieces: {entry!r} holds {item!r}, not a card name"
                          for item in entry if not isinstance(item, (str, list)))
            if len(entry) < 2:
                errors.append(f"pieces: {entry!r} is a list of fewer than two cards")
            named.extend(item for item in entry if isinstance(item, str))
        else:
            errors.append(f"pieces: {entry!r} is not a card name or a list of card names")
    errors.extend(f"pieces: {name!r} is named twice" for name in dict.fromkeys(named) if named.count(name) > 1)
    errors.extend(_deck_errors("pieces", named, cards, partner))
    if "startPiece" in wincon and wincon["startPiece"] not in plain:
        errors.append(f"startPiece: {wincon['startPiece']!r} is not one of its pieces named outside a list")
    if "minX" in wincon:
        min_x = wincon["minX"]
        if not isinstance(min_x, Mapping):
            errors.append(f"minX: {min_x!r} is not a mapping")
        else:
            # A piece not in the deck is reported above, once.
            errors.extend(
                f"minX: {piece!r}: {x!r} is not a positive integer for one of its pieces that is in the deck and "
                "has {X} in its mana cost"
                for piece, x in min_x.items()
                if piece not in named or type(x) is not int or x < 1 or (piece in cards and piece not in x_cards))
    for key in ("readyPieces", "castFromHand"):
        value = wincon.get(key)
        if key in wincon and (not isinstance(value, list) or not value
                              or not all(isinstance(name, str) and name in plain for name in value)
                              or len(set(value)) != len(value)):
            errors.append(f"{key}: {value!r} is not a non-empty list without repeats of its pieces named outside "
                          "a list")
    if isinstance(wincon.get("readyPieces"), list):
        # Card names only: any other element is refused above, never hashed.
        names = dict.fromkeys(name for name in wincon["readyPieces"] if isinstance(name, str))
        errors.extend(f"readyPieces: {name!r} is a land: the goldfish does not track when a land entered, so it "
                      "never counts on the battlefield" for name in names
                      if "Land" in re.findall(r"[\w'-]+", cards.get(name) or ""))
    if "readyHaste" in wincon:
        errors.extend(_haste_errors(wincon["readyHaste"], cards, named, partner))
        if "readyPieces" not in wincon:
            errors.append("readyHaste: without readyPieces")
    need = wincon.get("needsCreature")
    if "needsCreature" in wincon and not (isinstance(need, Mapping) and set(need) == {"count"}
                                          and type(need["count"]) is int and need["count"] >= 1):
        errors.append(f"needsCreature: {need!r} is not {{\"count\": N}} with N a positive integer")
    if "extraCost" in wincon and _fixed_cost(wincon["extraCost"]) is not None:
        errors.append(f"extraCost: {wincon['extraCost']!r} is not {_fixed_cost(wincon['extraCost'])}")
    return errors


def _deck_errors(field: str, names: list[str], cards: Mapping[str, str], partner: object) -> list[str]:
    """A card a field names that is the partner (whether or not the decklist
    also lists it), or that is not in the deck."""
    return [f"{field}: {name!r} is the partner commander, which the goldfish does not model" if name == partner
            else f"{field}: {name!r} is not in the deck"
            for name in dict.fromkeys(names) if name == partner or name not in cards]


def _haste_errors(haste: object, cards: Mapping[str, str], pieces: list[str], partner: object) -> list[str]:
    """The errors of a readyHaste value (wincon_errors)."""
    if not isinstance(haste, Mapping) or not haste or not set(haste) <= set(HASTE_KINDS):
        return [f"readyHaste: {haste!r} is not a non-empty mapping of {', '.join(HASTE_KINDS)}"]
    errors, names = [], []
    for kind, sources in haste.items():
        if kind == "static":
            if not isinstance(sources, list) or not sources or not all(isinstance(name, str) for name in sources):
                errors.append(f"readyHaste: static: {sources!r} is not a non-empty list of card names")
                continue
            names.extend(sources)
            continue
        if not isinstance(sources, Mapping) or not sources:
            errors.append(f"readyHaste: {kind}: {sources!r} is not a non-empty mapping of card names to mana costs")
            continue
        names.extend(sources)
        errors.extend(f"readyHaste: {kind}: {name!r}: {cost!r} is not {_fixed_cost(cost)}"
                      for name, cost in sources.items() if _fixed_cost(cost) is not None)
        # A source of a known type that cannot give haste that way.
        word, label = ("Equipment", "an Equipment") if kind == "equip" else ("Instant", "an instant")
        errors.extend(f"readyHaste: {kind}: {name!r} is not {label}"
                      for name in sources if cards.get(name) and word not in re.findall(r"[\w'-]+", cards[name]))
    errors.extend(f"readyHaste: {name!r} is named twice" for name in dict.fromkeys(names) if names.count(name) > 1)
    errors.extend(f"readyHaste: {name!r} is one of the line's pieces" for name in dict.fromkeys(names)
                  if name in pieces)
    errors.extend(_deck_errors("readyHaste", names, cards, partner))
    return errors
