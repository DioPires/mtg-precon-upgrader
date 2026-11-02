"""Tests for the scripts/prerelease toolkit.

No network: dump_set is exercised against a nine-card fixture cut from the
Reality Fracture dump. The two regression tests rebuild the DEC-925 worked
example and compare byte for byte with what is committed.
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import shutil
import sys
from html.parser import HTMLParser

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "prerelease"))

import build_cheat_sheet  # noqa: E402
import build_grades  # noqa: E402
import build_html  # noqa: E402
import compare_grades  # noqa: E402
import dump_set  # noqa: E402
import setlib  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "prerelease"
DEC925 = ROOT / "analysis" / "prerelease" / "fra"
TRK = ROOT / "analysis" / "prerelease" / "trk"


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


def _rarity_entries(uncommon_grade) -> list:
    def entry(rarity, grade, type_line="Creature — Human"):
        return {"rarity": rarity, "grade": grade, "type_line": type_line}

    return [
        entry("common", 3), entry("common", 4),
        entry("uncommon", uncommon_grade), entry("uncommon", uncommon_grade),
        entry("rare", 6), entry("mythic", 8.5),
        # Lands do not count: this one would pull the common mean down to 2.33.
        entry("common", 0, "Land"),
    ]


def test_rarity_gap_at_1_or_more_prints_no_check(capsys):
    build_grades.rarity_gap(_rarity_entries(4.5))
    out = capsys.readouterr().out.split("\n")
    assert out[0] == (
        "mean grade by rarity (non-land): common 3.50 (n=2), uncommon 4.50 (n=2), "
        "rare 6.00 (n=1), mythic 8.50 (n=1)"
    )
    assert out[1] == "uncommon - common gap: 1.00"
    assert not any(l.startswith("CHECK:") for l in out)


def test_rarity_gap_below_1_prints_the_check(capsys):
    build_grades.rarity_gap(_rarity_entries(4))
    out = capsys.readouterr().out.split("\n")
    assert out[1] == "uncommon - common gap: 0.50"
    assert out[2] == (
        "CHECK: the uncommon - common gap is below 1.0; re-read before shipping (playbook step 3)"
    )


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


def _dec925_without_sims(tmp_path, prose=None, grades=None) -> pathlib.Path:
    """The DEC-925 inputs minus the three sim files, with an optional prose.json."""
    work = tmp_path / "nosim"
    work.mkdir()
    for name in ("fra_all_cards.json", "grades.json", "collation.json", "format_rules.md"):
        shutil.copy(DEC925 / name, work / name)
    if prose is not None:
        (work / "prose.json").write_text(json.dumps(prose), encoding="utf-8")
    if grades is not None:
        (work / "grades.json").write_text(json.dumps(grades, indent=1), encoding="utf-8")
    return work


def _section(text: str, number: int) -> list:
    """The lines of section `number`, from its heading up to the next section."""
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith(f"## {number}."))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
    return lines[start:end]


TWO_PLANS = {
    "pair_plans": {
        "BR": {"name": "Test Burn", "plan": "Burn them out.", "look_for": "Grim Repriser [5]."},
        "WU": {"name": "Test Flyers", "plan": "Win in the air."},
    }
}


def test_section_5_without_a_sim_lists_the_ten_archetypes(tmp_path):
    work = _dec925_without_sims(tmp_path, prose=TWO_PLANS)
    section = _section(build_cheat_sheet.build(str(work)), 5)
    assert section[:3] == ["## 5. The ten archetypes", "", build_cheat_sheet.PAIR_PLANS_LEAD]
    titles = [re.match(r"^- \S+ \*\*([WUBRG]{2})", l).group(1) for l in section if l.startswith("- ")]
    # The named pairs first, in prose.json's key order; then the other eight.
    assert titles == ["BR", "WU", "WB", "WR", "WG", "UB", "UR", "UG", "BG", "RG"]
    assert "- ⚫🔴 **BR Test Burn** — Burn them out." in section
    assert "    - Look for: Grim Repriser [5]." in section
    assert "- ⚪🔵 **WU Test Flyers** — Win in the air." in section
    assert "- ⚪⚫ **WB**" in section
    assert "    - Signposts: Vindictive Triumph [8]; Twisted Fates [7]; Edgar, Ancient Bloodlord [5]" in section


def test_section_5_without_a_sim_takes_the_heading_and_commentary_from_prose(tmp_path):
    prose = dict(TWO_PLANS, ranking_heading="## 5. Archetypes", ranking_commentary="Unranked.")
    work = _dec925_without_sims(tmp_path, prose=prose)
    section = _section(build_cheat_sheet.build(str(work)), 5)
    assert section[:5] == ["## 5. Archetypes", "", "Unranked.", "", build_cheat_sheet.PAIR_PLANS_LEAD]


def test_no_section_5_without_a_sim_or_pair_plans(tmp_path):
    work = _dec925_without_sims(tmp_path)
    assert "\n## 5." not in build_cheat_sheet.build(str(work))


def test_procedure_replaces_the_section_1_steps(tmp_path):
    procedure = ["1. **Sort.** By colour.", "2. **Count** creatures.", "3. **Build.**"]
    work = _dec925_without_sims(tmp_path, prose={"procedure": procedure})
    section = _section(build_cheat_sheet.build(str(work)), 1)
    assert section == ["## 1. Scoring your pool by hand (10 minutes)", ""] + procedure + [""]


def test_procedure_with_a_step_override_stops(tmp_path):
    prose = {"procedure": ["1. Sort."], "procedure_splash": "5. Splash."}
    work = _dec925_without_sims(tmp_path, prose=prose)
    with pytest.raises(SystemExit, match="procedure_splash"):
        build_cheat_sheet.build(str(work))


def _edgar_as(grade, roles) -> list:
    graded = json.loads((DEC925 / "grades.json").read_text(encoding="utf-8"))
    for entry in graded:
        if entry["name"] == "Edgar, Ancient Bloodlord":
            entry["grade"], entry["roles"] = grade, roles
    return graded


def test_cardadv_role_shows_the_card_advantage_mark(tmp_path):
    assert build_cheat_sheet.mark({"roles": ["removal", "fixing", "cardadv"]}) == "✕◆✚"
    work = _dec925_without_sims(tmp_path, grades=_edgar_as(5, ["threat", "cardadv"]))
    edgar = next(l for l in build_cheat_sheet.build(str(work)).split("\n") if "Edgar, Ancient Bloodlord |" in l)
    assert edgar.split(" | ")[4] == "✚"


def test_half_grade_builds_and_prints(tmp_path, fixture_cards):
    work = _dec925_without_sims(tmp_path, prose=TWO_PLANS, grades=_edgar_as(6.5, ["threat"]))
    text = build_cheat_sheet.build(str(work))
    assert "| 6.5 | 🟡 Edgar, Ancient Bloodlord |" in text
    # 6.5 sorts between 7 and 6 and still counts for the 5+ signposts.
    assert "    - Signposts: Vindictive Triumph [8]; Twisted Fates [7]; Edgar, Ancient Bloodlord [6.5]" in text
    graded = [
        (c["name"], 6.5 if c["name"] == "Memory Trap" else 4, ["threat"], "note", None)
        for c in fixture_cards
        if "Basic" not in c["type_line"]
    ]
    out = {e["name"]: e for e in build_grades.build(fixture_cards, graded, _rules())}
    assert json.dumps(out["Memory Trap"]["grade"]) == "6.5"
    assert "bomb" not in out["Memory Trap"]["roles"]


def test_kill_share_reads_star_trek_wordings():
    # DEC-1220: the Star Trek dump in place; census 46% / 75% / 88% at toughness 2 / 3 / 4.
    cards = {c["name"]: c for c in setlib.load_cards(str(TRK))}
    _, cum, _, _ = build_cheat_sheet.toughness_census(cards)
    expected = {
        "Command Decision": "power 4+ only",
        "De-evolve": "lock",
        "Eject the Warp Core": "≤2 toughness (46%) or ≤6 (100%)",
        "Planetary Bombardment": "≤2 toughness (46%) or ≤4 (88%)",
        "Set Phasers to . . .": "≤3 toughness (75%), attackers only",
        "U.S.S. Excelsior, Cutting Edge": "tapped only",
        "Resistance Is Futile": "nonartifact only",
        "Marooned": "lock",
        "Khaaaaaaaaaaaannn!": "all (2X damage)",
        "Common Goal": "fight (your creature's power)",
    }
    got = {name: build_cheat_sheet.kill_share({}, cards[name], cum) for name in expected}
    assert got == expected


# DEC-1221: the Scryfall link on every card name, on the Star Trek sheet in place.
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@pytest.fixture(scope="module")
def trk_sheets() -> tuple:
    """(the sheet as build() returns it, the same sheet with links, card name -> page)."""
    cards = setlib.load_cards(str(TRK))
    plain = build_cheat_sheet.build(str(TRK))
    pages = {c["name"]: c["scryfall_uri"].split("?")[0] for c in cards}
    return plain, build_cheat_sheet.link_cards(plain, cards), pages


def test_removing_the_links_gives_back_the_built_sheet(trk_sheets):
    plain, linked, _ = trk_sheets
    assert linked != plain
    assert LINK.sub(r"\1", linked) == plain


def test_every_graded_card_has_a_link_to_its_own_page(trk_sheets):
    _, linked, pages = trk_sheets
    links = LINK.findall(linked)
    graded = json.loads((TRK / "grades.json").read_text(encoding="utf-8"))
    assert {e["name"] for e in graded} <= {text for text, _ in links}
    assert all(url == pages[text] for text, url in links)


def test_eject_the_warp_core_is_one_link_with_none_inside(trk_sheets):
    plain, linked, pages = trk_sheets
    eject = f"[Eject the Warp Core]({pages['Eject the Warp Core']})"
    assert linked.count(eject) == plain.count("Eject the Warp Core") > 0
    # The card "Warp Core" is linked only where it stands alone (its own row).
    assert linked.count("[Warp Core](") == plain.count("Warp Core") - plain.count("Eject the Warp Core")
    assert all("[" not in text and "](" not in text for text, _ in LINK.findall(linked))


def test_no_heading_holds_a_link(trk_sheets):
    _, linked, _ = trk_sheets
    headings = [line for line in linked.split("\n") if line.startswith("#")]
    assert headings and not any("](" in line for line in headings)


def test_link_cards_links_the_front_face_and_only_whole_names():
    cards = [
        {"name": "Blossom-Blessed Angel // Seed Suture", "scryfall_uri": "https://s/a?x=1"},
        {"name": "Hemmer, Fixing What Is Broken", "scryfall_uri": "https://s/h?x=1"},
        {"name": "Warp Core", "scryfall_uri": "https://s/w?x=1"},
    ]
    text = (
        "# Warp Core\n"
        "Blossom-Blessed Angel [5]; Blossom-Blessed Angel // Seed Suture; Hemmer loots; "
        "Warp Cores; [Warp Core](https://elsewhere)"
    )
    assert build_cheat_sheet.link_cards(text, cards) == (
        "# Warp Core\n"
        "[Blossom-Blessed Angel](https://s/a) [5]; "
        "[Blossom-Blessed Angel // Seed Suture](https://s/a); Hemmer loots; "
        "Warp Cores; [Warp Core](https://elsewhere)"
    )


# ---------------------------------------------------------------- build_html
# DEC-1223: the page for a phone. The pool counts by hand, the search, and the
# committed Star Trek page against the committed sheet. These fail when the
# sheet changes and the page is not rebuilt.

# One of each kind of card the counts treat apart (grade, tags, kind).
SAMPLE_POOL = {
    "Captain Jean-Luc Picard": 1,  # W 8.5 ★ creature, MV 3
    "Malfunctioning Holodeck": 2,  # W 7.5 ✕, two copies
    "U.S.S. Excelsior, Cutting Edge": 1,  # W 6.5 ✕ Spacecraft: not a creature
    "Command Decision": 1,  # W 5.5 ✕ sorcery, MV 2: 4+, not 6+
    "Picard, Leading by Example": 1,  # W 5.5 creature, MV 2
    "Marooned": 1,  # U 6 ✕, MV 1
    "Guidance Failure": 1,  # U 5 ✕⚡, MV 4
    "Constable Odo": 1,  # hybrid W/U 6 creature, MV 5
    "The Duras Sisters": 1,  # hybrid B/R 5.5 creature, MV 2
    "Locutus, the One Who Speaks": 1,  # gold WB 6 creature, MV 2
    "Hemmer, Fixing What Is Broken": 1,  # gold WU 5.5 creature, MV 2
    "Crystalline Entity": 1,  # colourless 8 ★ creature, MV 8
    "Cybernetic Specialist": 1,  # colourless 3.5 creature: under 4
    "Vulcan": 1,  # land 4 ◆
    "Sarek, Federation Ambassador": 1,  # three colours 2.5
}


@pytest.fixture(scope="module")
def trk_grades() -> list:
    return json.loads((TRK / "grades.json").read_text(encoding="utf-8"))


def test_pool_summary_counts_the_sample_pool_by_hand(trk_grades):
    assert build_html.CHECK_POOLS["sample"] == SAMPLE_POOL  # check_html.mjs loads the same pool
    s = build_html.pool_summary(SAMPLE_POOL, trk_grades)
    assert s["cards"] == 16
    # Step 2. W: Picard ★, Holodeck x2, Excelsior and Odo are 6+; the two 5.5s are 4+ only.
    # U: Marooned and Odo 6+, Guidance Failure 4+. B and R: Duras Sisters (5.5).
    assert s["colours"] == {
        "W": {"six": 5, "four": 7, "bombs": 1},
        "U": {"six": 2, "four": 3, "bombs": 0},
        "B": {"six": 0, "four": 1, "bombs": 0},
        "R": {"six": 0, "four": 1, "bombs": 0},
        "G": {"six": 0, "four": 0, "bombs": 0},
    }
    # Step 3 score: Picard 2 + Holodeck 2 + Excelsior 1 + Odo 1 = 6 for every W pair; WU adds
    # Marooned. Step 4: the pair's cards plus its gold card and Crystalline Entity (Cybernetic
    # Specialist is under 4; Vulcan is a land; Sarek has three colours).
    rows = [
        (p["pair"], p["score"], p["four"], p["creatures"], p["bombs"], p["cardadv"], p["removal"], p["two_drops"])
        for p in s["pairs"]
    ]
    assert rows == [
        ("WU", 7, 11, 5, 2, 0, 6, 3),
        ("WB", 6, 10, 6, 2, 0, 4, 4),
        ("WR", 6, 9, 5, 2, 0, 4, 3),
        ("WG", 6, 8, 4, 2, 0, 4, 2),
        ("UB", 2, 5, 3, 1, 0, 2, 1),
        ("UR", 2, 5, 3, 1, 0, 2, 1),
        ("UG", 2, 4, 2, 1, 0, 2, 0),
        ("BR", 0, 2, 2, 1, 0, 0, 1),
        ("BG", 0, 2, 2, 1, 0, 0, 1),
        ("RG", 0, 2, 2, 1, 0, 0, 1),
    ]
    assert [(t["above"], t["below"], t["by"]) for t in s["ties"]] == [
        ("WB", "WR", "two-drops"),
        ("WR", "WG", "two-drops"),
        ("UB", "UR", "pair order"),
        ("UR", "UG", "two-drops"),
        ("BR", "BG", "pair order"),
        ("BG", "RG", "pair order"),
    ]


def test_pool_summary_breaks_ties_on_bombs_card_advantage_removal(trk_grades):
    pool = {
        "Captain Jean-Luc Picard": 1,  # W 8.5 ★
        "Marooned": 2,  # U 6 ✕
        "Phlox, Unorthodox Doctor": 1,  # gold WG 6.5 ✚
        "Borg Cube": 1,  # gold WB 7 ✕
    }
    assert build_html.CHECK_POOLS["ties"] == pool
    s = build_html.pool_summary(pool, trk_grades)
    # WB, WR, WG and the three U pairs all score 2. The W pairs hold Picard (★), WG has
    # Phlox (✚), WB has Borg Cube (✕); the U pairs differ in nothing.
    assert [(p["pair"], p["score"]) for p in s["pairs"]] == [
        ("WU", 4), ("WG", 2), ("WB", 2), ("WR", 2), ("UB", 2), ("UR", 2), ("UG", 2),
        ("BR", 0), ("BG", 0), ("RG", 0),
    ]
    assert [(t["above"], t["below"], t["by"]) for t in s["ties"]] == [
        ("WG", "WB", "✚"),
        ("WB", "WR", "✕"),
        ("WR", "UB", "★"),
        ("UB", "UR", "pair order"),
        ("UR", "UG", "pair order"),
        ("BR", "BG", "pair order"),
        ("BG", "RG", "pair order"),
    ]


def test_pool_summary_skips_unknown_names_and_zero_counts(trk_grades):
    s = build_html.pool_summary({"Not a card": 3, "Marooned": 0}, trk_grades)
    assert s["cards"] == 0 and all(p["score"] == 0 for p in s["pairs"])


def test_search_examples_find_their_cards(trk_grades):
    names = [e["name"] for e in trk_grades]
    assert [q for q, _ in build_html.SEARCH_EXAMPLES] == ["obrien", "uss ent", "spock", "khaan"]
    for query, expected in build_html.SEARCH_EXAMPLES:
        assert build_html.search(query, names) == [n for n in names if n in expected], query
    assert build_html.SEARCH_EXAMPLES[2][1] == tuple(n for n in names if "spock" in n.lower())


def test_normalize_name_drops_accents_apostrophes_and_full_stops():
    assert build_html.normalize_name("Miles O’Brien, Transporter Ops") == "miles obrien transporter ops"
    assert build_html.normalize_name("U.S.S. Enterprise-A, Free Spirit") == "uss enterprise a free spirit"
    assert build_html.normalize_name("Khaaaaaaaaaaaannn!") == "khaann"
    assert build_html.normalize_name("  Éowyn's  Ni'Var ") == "eowyns nivar"


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
FIELDS = ("gb", "syn", "cn", "cost", "rar", "tags", "note")


class Page(HTMLParser):
    """The committed page, read back: card blocks, groups, links and addresses."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.cards, self.groups = [], [], []
        self.ids, self.addresses = set(), []
        self.links, self.mana = [], []  # in the intro and sections 1 to 5
        self.in_main = self.past_5 = False
        self.link = None

    def field(self):
        for _, classes, _ in reversed(self.stack):
            for name in FIELDS:
                if name in classes:
                    return name
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.addresses += [(k, a[k]) for k in ("href", "src") if k in a]
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "main":
            self.in_main = True
        if a.get("id") == "cards":
            self.past_5 = True
        classes = set((a.get("class") or "").split())
        sheet_part = self.in_main and not self.past_5
        if sheet_part and "data-mana" in a:
            self.mana.append(a["data-mana"])
        if tag == "li" and "card" in classes:
            self.cards.append({"name": a["data-name"], **{f: "" for f in FIELDS}, "link": None})
            self.groups[-1][1].append(a["data-name"])
        field = self.field()
        if self.cards and field == "cost" and "data-mana" in a:
            self.cards[-1]["cost"] += a["data-mana"]
        if tag == "a" and "cn" in classes:
            self.cards[-1]["link"] = a["href"]
        elif tag == "a" and field == "note":
            self.cards[-1]["note"] += "["
        if tag == "a" and sheet_part:
            self.link = [a["href"], ""]
        if tag not in VOID:
            self.stack.append((tag, classes, a))

    def handle_endtag(self, tag):
        open_tag, _, a = self.stack.pop()
        assert open_tag == tag, (open_tag, tag)
        if tag == "a" and self.field() == "note":
            self.cards[-1]["note"] += f"]({a['href']})"
        if tag == "a" and self.link is not None:
            self.links.append((self.link[1], self.link[0]))
            self.link = None

    def handle_data(self, data):
        if self.link is not None:
            self.link[1] += data
        if self.stack and self.stack[-1][0] == "h3" and "list" in {x[2].get("id") for x in self.stack}:
            self.groups.append([data, []])
        field = self.field()
        if self.cards and field and field != "cost" and not any("data-mana" in x[2] for x in self.stack):
            self.cards[-1][field] += data


@pytest.fixture(scope="module")
def trk_page() -> tuple:
    """(the page read back, its raw text, the committed sheet split at section 6)."""
    raw = (TRK / "cheat_sheet.html").read_text(encoding="utf-8")
    page = Page()
    page.feed(raw)
    page.close()
    sheet = (TRK / "cheat_sheet.md").read_text(encoding="utf-8")
    cut = sheet.index("\n## 6.")
    return page, raw, sheet[:cut], sheet[cut:]


def test_page_has_one_block_per_graded_card_equal_to_the_sheet_row(trk_page, trk_grades):
    page, _, _, section6 = trk_page
    names = collections.Counter(c["name"] for c in page.cards)
    assert names == collections.Counter(e["name"] for e in trk_grades)
    assert set(names.values()) == {1}
    rows, groups = [], []
    for line in section6.split("\n"):
        if line.startswith("### "):
            groups.append([line[4:], []])
        elif line.startswith("| ") and not line.startswith(("| Grade |", "|---")):
            grade, card, cost, rarity, tags, note = line[2:-2].split(" | ")
            name, link = re.fullmatch(r"\S+ \[(.+)\]\((\S+)\)", card).groups()
            rows.append({"name": name, "grade": grade, "cost": cost, "rarity": rarity,
                         "tags": tags, "note": note, "link": link})
            groups[-1][1].append(name)
    got = [
        {"name": c["cn"], "grade": c["gb"] + c["syn"], "cost": c["cost"], "rarity": c["rar"],
         "tags": c["tags"], "note": c["note"], "link": c["link"]}
        for c in page.cards
    ]
    assert len(rows) == len(trk_grades)
    assert got == rows
    assert page.groups == groups


def test_page_keeps_the_links_of_the_intro_and_sections_1_to_5(trk_page):
    page, _, head, _ = trk_page
    links = LINK.findall(head)
    assert len(links) > 100
    assert page.links == links


def test_page_keeps_the_mana_costs_of_the_intro_and_sections_1_to_5(trk_page):
    page, _, head, _ = trk_page
    assert page.mana == [f"{{{m}}}" for m in re.findall(r"\{([^}]+)\}", head)]


def test_published_copy_equals_the_page():
    # DEC-1223 C1: the site serves web/public/prerelease/trk.html; `build_html.py --publish` writes it.
    copy = ROOT / "web" / "public" / "prerelease" / "trk.html"
    assert copy.read_bytes() == (TRK / "cheat_sheet.html").read_bytes()


def test_page_links_only_scryfall_card_pages_and_its_own_anchors(trk_page):
    page, raw, _, _ = trk_page
    assert not [a for a in page.addresses if a[0] == "src"]
    hrefs = [v for k, v in page.addresses if k == "href"]
    anchors = [h for h in hrefs if h.startswith("#")]
    assert anchors and all(h[1:] in page.ids for h in anchors)
    assert all(h.startswith("https://scryfall.com/card/") for h in hrefs if not h.startswith("#"))
    # No other address anywhere: not in a style, a script or a text.
    found = re.findall(r"[a-z][a-z0-9+.-]*://", raw)
    assert found and set(found) == {"https://"}
    assert len(found) == len(hrefs) - len(anchors)


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
