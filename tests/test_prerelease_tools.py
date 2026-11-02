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
