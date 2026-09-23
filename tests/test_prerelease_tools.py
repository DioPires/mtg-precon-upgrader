"""Tests for the scripts/prerelease toolkit.

No network: dump_set is exercised against a nine-card fixture cut from the
Reality Fracture dump. The two regression tests rebuild the DEC-925 worked
example and compare byte for byte with what is committed.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "prerelease"))

import build_cheat_sheet  # noqa: E402
import build_grades  # noqa: E402
import compare_grades  # noqa: E402
import dump_set  # noqa: E402
import setlib  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "prerelease"
DEC925 = ROOT / "agents" / "ceo" / "analysis" / "dec925"

requires_dec925 = pytest.mark.skipif(
    not (DEC925 / "fra_all_cards.json").exists(),
    reason="DEC-925 worked example is absent",
)


@pytest.fixture(scope="module")
def fixture_cards() -> list:
    with open(FIXTURES / "fix_all_cards.json", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def fixture_prints() -> list:
    with open(FIXTURES / "fix_all_prints.json", encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------- dump_set


def test_gradable_drops_basic_lands(fixture_cards):
    names = {c["name"] for c in dump_set.gradable(fixture_cards)}
    assert "Plains" not in names
    assert len(names) == len(fixture_cards) - 1


def test_grading_sheet_line_format(fixture_cards):
    lines = dump_set.grading_sheet(fixture_cards).rstrip("\n").split("\n")
    # Two lines per card: a header and an indented oracle line.
    assert len(lines) == 2 * (len(fixture_cards) - 1)
    header_re = re.compile(
        r"^#(\S+) (.+) \| (.*) \| ([CURMSB]) (W|U|B|R|G|C|[A-Z]{2,5}) \| (.+) \| WM:(.+)$"
    )
    for header, oracle in zip(lines[0::2], lines[1::2]):
        assert header_re.match(header), header
        assert oracle.startswith("   ")

    by_name = {line.split(" | ")[0].split(" ", 1)[1]: line for line in lines[0::2]}
    # Creature: power/toughness after the type line.
    assert by_name["Memory Trap"] == "#15 Memory Trap | {2}{W} | C W | Enchantment | WM:-"
    # Planeswalker: loyalty after the type line.
    assert by_name["Ajani Resolute"].endswith("Legendary Planeswalker — Ajani L2 | WM:-")
    # Land: empty mana cost column.
    assert by_name["Dedicated Commons"] == "#175 Dedicated Commons |  | C C | Land | WM:-"
    # Two-faced card: both costs, the joined type line, front-face P/T.
    assert by_name["Blossom-Blessed Angel // Seed Suture"] == (
        "#3 Blossom-Blessed Angel // Seed Suture | {3}{W} // {G/W} | C W | "
        "Creature — Angel Cleric // Sorcery 2/4 | WM:-"
    )


def test_grading_sheet_multiface_oracle_has_a_header_per_face(fixture_cards):
    lines = dump_set.grading_sheet(fixture_cards).split("\n")
    i = next(i for i, l in enumerate(lines) if l.startswith("#3 Blossom-Blessed Angel"))
    oracle = lines[i + 1]
    assert oracle.startswith("   [Blossom-Blessed Angel {3}{W} Creature — Angel Cleric 2/4] ")
    # A face without power/toughness still gets the "/" placeholder.
    assert " // [Seed Suture {G/W} Sorcery /] Put a +1/+1 counter" in oracle
    assert "\n" not in oracle


def test_grading_sheet_sorts_by_colour_then_rarity_then_name(fixture_cards):
    headers = dump_set.grading_sheet(fixture_cards).split("\n")[0::2]
    order = [h.split(" | ")[0].split(" ", 1)[1] for h in headers if h.startswith("#")]
    assert order == [
        # white commons alphabetically, then the white mythic
        "Academic Ascent",
        "Blossom-Blessed Angel // Seed Suture",
        "Memory Trap",
        "Ajani Resolute",
        # black
        "Last Gasp",
        # gold pairs after mono colours
        "Twisted Fates",
        # colourless last
        "Dedicated Commons",
        "Emrakul, the Exigent Doom",
    ]


def test_color_sort_key_orders_mono_then_gold_then_colourless():
    keys = [
        setlib.color_sort_key(c)
        for c in ([], ["W"], ["U"], ["B"], ["R"], ["G"], ["U", "W"], ["B", "W"], ["G", "R"])
    ]
    assert keys[1:] == sorted(keys[1:])
    assert keys[0] == max(keys)


def test_set_facts_reports_counts_and_censuses(fixture_cards, fixture_prints):
    info = {"name": "Reality Fracture", "code": "fra", "released_at": "2026-09-26", "card_count": 9}
    text = dump_set.set_facts(fixture_cards, fixture_prints, info)
    assert "# Reality Fracture (FRA) — set facts" in text
    assert "Cards in this dump (`unique=cards`): 9 (8 excluding basic lands)" in text
    assert "## Counts by rarity" in text
    assert "| common | 5 |" in text  # 6 commons minus the basic Plains
    assert "## Creature toughness census" in text
    assert "## Collector-number gaps" in text
    assert "showcase-first printing" in text
    assert "## Watermarks" in text
    assert "## Two-colour uncommons per pair" in text
    assert "| WB | 1 |" in text  # Twisted Fates


def test_main_numbering_end_stops_before_the_showcase_block():
    # 1-5 is the main run; 60-62 are special treatments numbered well above it.
    assert dump_set.main_numbering_end([1, 2, 3, 4, 5, 60, 61, 62]) == 5
    # A one-number hole is a gap in the main run, not the end of it.
    assert dump_set.main_numbering_end([1, 2, 4, 5]) == 5
    assert dump_set.main_numbering_end([]) == 0


def test_set_facts_counts_mechanics_case_insensitively(fixture_cards, fixture_prints):
    # "Empower Jace" appears capitalised in rules text and lower-cased in reminder
    # text; the count must catch both (DEC-925 lesson).
    info = {"name": "x", "code": "x", "released_at": "", "card_count": 0}
    text = dump_set.set_facts(fixture_cards, fixture_prints, info)
    row = next(l for l in text.split("\n") if l.startswith("| Flashback |") or l.startswith("| Flying |"))
    assert row.endswith("|")
    assert "empower jace" in setlib.oracle_text(
        next(c for c in fixture_cards if c["name"] == "Academic Ascent")
    )


# --------------------------------------------------------------- build_grades


def _rules() -> list:
    with open(ROOT / "scripts" / "prerelease" / "tags_default.json", encoding="utf-8") as fh:
        return json.load(fh)["rules"]


def test_build_grades_rejects_a_missing_card(fixture_cards):
    graded = [(c["name"], 4, ["threat"], "note", None) for c in fixture_cards[:3]]
    with pytest.raises(SystemExit):
        build_grades.build(fixture_cards, graded, _rules())


def test_build_grades_rejects_an_unknown_card(fixture_cards):
    graded = [
        (c["name"], 4, ["threat"], "note", None)
        for c in fixture_cards
        if "Basic" not in c["type_line"]
    ]
    graded.append(("Black Lotus", 10, ["bomb"], "not in this set", None))
    with pytest.raises(SystemExit):
        build_grades.build(fixture_cards, graded, _rules())


def test_build_grades_rejects_a_duplicate(fixture_cards):
    graded = [
        (c["name"], 4, ["threat"], "note", None)
        for c in fixture_cards
        if "Basic" not in c["type_line"]
    ]
    graded.append(graded[0])
    with pytest.raises(SystemExit):
        build_grades.build(fixture_cards, graded, _rules())


def test_build_grades_tags_bombs_and_synergies(fixture_cards):
    graded = []
    for card in fixture_cards:
        if "Basic" in card["type_line"]:
            continue
        if card["name"] == "Memory Trap":
            graded.append((card["name"], 9, ["removal"], "premium", None))
        elif card["name"] == "Academic Ascent":
            graded.append((card["name"], 4, ["trick"], "trick", ("lifegain", 4, 5)))
        else:
            graded.append((card["name"], 4, ["threat"], "note", None))
    out = {e["name"]: e for e in build_grades.build(fixture_cards, graded, _rules())}
    assert "bomb" in out["Memory Trap"]["roles"]
    assert out["Academic Ascent"]["needs"] == "lifegain"
    assert out["Academic Ascent"]["needs_threshold"] == 4
    assert out["Academic Ascent"]["grade_synergy"] == 5
    # provides comes from the tag rules, not from the grade file
    assert "jace" in out["Academic Ascent"]["provides"]
    assert "planeswalker" in out["Ajani Resolute"]["provides"]
    assert out["Memory Trap"]["provides"] == []


# --------------------------------------------------------- build_cheat_sheet


def test_tier_sentence_names_a_tier_1_only_on_a_clear_lead():
    clear = {"WB": 0.136, "BR": 0.115, "WG": 0.112, "RG": 0.059}
    assert build_cheat_sheet.tier_sentence(clear).startswith("Tier 1: WB.")
    close = {"WB": 0.120, "BR": 0.115, "WG": 0.112, "RG": 0.059}
    assert build_cheat_sheet.tier_sentence(close).startswith("No clear tier 1.")


def test_tier_sentence_puts_pairs_below_8_percent_in_tier_3():
    sentence = build_cheat_sheet.tier_sentence(
        {"WB": 0.136, "BR": 0.115, "UG": 0.079, "RG": 0.059}
    )
    assert "Tier 2: BR." in sentence
    assert sentence.endswith("Tier 3: UG, RG.")


# ------------------------------------------------------------ compare_grades


def test_normalize_straightens_curly_punctuation():
    assert compare_grades.normalize("Ajani’s “Resolute”") == "Ajani's \"Resolute\""
    assert compare_grades.normalize("a  b\n c") == "a b c"


def test_parse_draftsim_reads_ratings_back_to_card_names():
    raw = (FIXTURES / "draftsim_fragment.html").read_text(encoding="utf-8")
    names = [
        "Academic Ascent",
        "Ajani Resolute",
        "Blossom-Blessed Angel // Seed Suture",
        "Memory Trap",
        "Last Gasp",
        "Twisted Fates",
        "Emrakul, the Exigent Doom",
    ]
    out = compare_grades.parse_draftsim(raw, names)
    assert out == {
        "Academic Ascent": 2,
        "Ajani Resolute": 2,
        # matched on the front face alone, keyed by the full name
        "Blossom-Blessed Angel // Seed Suture": 3,
        "Memory Trap": 7,
        "Last Gasp": 8,
        "Twisted Fates": 4,
    }
    # a card with no rating on the page is simply absent
    assert "Emrakul, the Exigent Doom" not in out
    # ratings inside <script>/<style> are not picked up
    assert 9 not in out.values()


def test_pearson_on_a_known_pair():
    assert compare_grades.pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert compare_grades.pearson([1, 2, 3], [6, 4, 2]) == pytest.approx(-1.0)


# ----------------------------------------------------------------- regression


@requires_dec925
def test_build_grades_reproduces_the_dec925_grades(tmp_path):
    work = tmp_path / "dec925"
    work.mkdir()
    for name in ("fra_all_cards.json", "grades_src.py"):
        shutil.copy(DEC925 / name, work / name)
    cards = setlib.load_cards(str(work))
    graded = build_grades.load_grade_source(str(work))
    rules, _ = build_grades.load_tag_rules(str(work))
    built = build_grades.build(cards, graded, rules)
    assert json.dumps(built, indent=1) == (DEC925 / "grades.json").read_text(encoding="utf-8")


@requires_dec925
def test_build_cheat_sheet_reproduces_the_dec925_cheat_sheet(tmp_path):
    work = tmp_path / "dec925"
    work.mkdir()
    for name in (
        "fra_all_cards.json",
        "grades.json",
        "collation.json",
        "format_rules.md",
        "prose.json",
        "sim_results.json",
        "sim_results_spec_splash.json",
        "sim_results_nosplash.json",
    ):
        shutil.copy(DEC925 / name, work / name)
    built = build_cheat_sheet.build(str(work))
    assert built == (DEC925 / "cheat_sheet.md").read_text(encoding="utf-8")
