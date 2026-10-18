"""DEC-1197 description edits from the DEC-1198 rulings (CEO run 15bb14f0, 2026-10-17).

Usage: python3 -I d1197_edits.py <old description file> <new description file> <rulings comment id>
Each edit finds its old text once or stops.
"""
import sys
from pathlib import Path

old_path, new_path, rulings = sys.argv[1], sys.argv[2], sys.argv[3]
s = Path(old_path).read_text().rstrip("\n")

OLD_TOP = (
    "**BACKLOG until PR #81 ([DEC-1191](/DEC/issues/DEC-1191)) merges. Do not start before then.** The CEO run that "
    "merges PR #81 writes a \"Started\" section at the top of this description, with the basis (the merge commit and "
    "its push runs), and sets `todo`."
)
NEW_TOP = (
    "**Started by the owner on 2026-10-17 at 11:46:27Z, before PR #81 ([DEC-1191](/DEC/issues/DEC-1191)) merged. "
    "The gate stays: PR #81's merge.** This leg edits `_REPEATABLE_DRAW` and `_is_cantrip`, which exist only on PR "
    "#81's branch, and PR #81's fix round 1 (Design System Engineer, routed on 2026-10-17) changes "
    "`_REPEATABLE_DRAW` again (CEO run `15bb14f0`, rulings `" + rulings + "` on DEC-1191). At your start, run "
    "`gh pr view 81 --json state,mergeCommit`:\n"
    "- **`MERGED`:** do the work on `main`. If no \"Started\" section stands above this paragraph, take the merge "
    "commit and `main`'s newest `python-tests` and `web-ci` push runs as your basis, and name them.\n"
    "- **Not `MERGED`:** post one line on this issue that says so, with the time, and hand back at once with the "
    "Handoff PATCH below. Do no other work. The CEO run that merges PR #81 writes the \"Started\" section and assigns "
    "this issue back to you.\n"
    "- **CEO run that such a hand-back starts:** read DEC-1191. If PR #81 merged, write the \"Started\" section and "
    "assign this issue to the Founding Engineer with `todo` and `monitor: null`. If not, park this issue `in_review` "
    "with a monitor 30 minutes after DEC-1191's monitor, and end.\n\n"
    "**Changes from the DEC-1198 review (CEO rulings `" + rulings + "` on DEC-1191).** Item 3 loses its graveyard "
    "form, which PR #81's fix round 1 takes (B4), and gains the CEO's mutant G3 as a candidate rule. A new item 7a "
    "holds the reviewer's probe P3. The reviewer's evidence is in the kit "
    "`/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1198-r1/followups/` "
    "(the kit's `README.txt` lists the files)."
)

OLD_ITEM3 = (
    "## Item 3. A cost that spends the card by its name, or exiles it from your graveyard, is once (CEO probe P2)\n"
)
NEW_ITEM3 = OLD_ITEM3 + (
    "- **Since PR #81's fix round 1 (DEC-1198 B4):** `_REPEATABLE_DRAW` already reads \"exile this card from your "
    "graveyard\" as a cost that spends the card, and `GraveyardCostFaultTests` pins it. That moved 10 mirror cards "
    "(Campus Crier, Cobbled Lancer, Faerie Dreamthief, Unwilling Ingredient, White Tiger, Amulet Keeper and five "
    "Surveyors) and 2 pool entries. So this item keeps the name form only (Stone of Erech, Apple of Eden, Isu Relic), "
    "and its graveyard test and mutant are done. Read the bullets below with that change.\n"
    "- **Candidate rule G3 (CEO mutant, ruling 3).** \"Exile this card\" in any cost spends the card, also from your "
    "hand, and so do \"exile this creature\" and \"exile this artifact\". On PR #81's round the mutant G3 (\"exile "
    "this card\" for \"exile this card from your graveyard\") passes every test, because its only kill case would pin "
    "a fault that `main` shares. Take it into this item if its census passes the bar, with a case that kills the "
    "round's narrower line.\n"
)

ANCHOR_8 = "## Item 8. \"Up to N target\" after \"destroy\" and in the bounce read (P1)\n"
ITEM_7A = (
    "## Item 7a. A one-shot draw that the card gives again is `card-draw` (DEC-1198 probe P3)\n"
    "- PR #81 counts one draw of one card as once. Some cards give that draw again through a word that "
    "`_is_cantrip` does not read: gravestorm, storm and replicate; \"copy it\" or \"copy this spell\"; \"you may choose "
    "the same mode more than once\"; \"return this card from your graveyard to your hand\"; \"becomes prepared\"; "
    "\"enters or is put into a graveyard\" and \"enters or dies\"; flashback, buyback, cipher, escape and harmonize; "
    "and \"investigate twice\". Read them outside reminder text.\n"
    "- **Do it after items 4 and 7.** The reviewer's narrow rule (`_DRAW_AGAIN` in the kit's `followups/atr_fix_p3.py`) "
    "moves 20 cards from none to `card-draw` on PR #81's head (`followups/fix_p3_changed.txt`). 13 are right and 2 "
    "are near cases (Eldrazi Ravager, Hormagaunt Horde). 5 are false, and all 5 are loots or rummages: Fiery Encore, "
    "Obscura Confluence, Oracle of Tragedy, Silvan Reveler and Undead Gladiator. That fails the bar, so the loot rules "
    "must win over this item's rule.\n"
    "- **Pool entries to bring back** (the reviewer's reading, 0 seats move): Season of Weaving (tidal-legion), Ominous "
    "Harvest (witherbloom-the-balancer), Striding Shotcaller // Run the Play (creeping-corruption, exponential-growth), "
    "Killian's Confidence (creeping-corruption) and Ichor Wellspring (anvil-chorus, grave-dividends). Mirror cards "
    "outside the pools: Secrets of the Key and Think Twice (flashback), Whispers of the Muse (buyback), Last Thoughts "
    "(cipher) and Detective's Satchel (investigate twice).\n"
    "- **Near cases to read** (DEC-1198 N-d): Jace's Machinations (3 pools, Empower Jace 8) and Way of the "
    "Wildspeaker (1 pool, Empower Jace 7). With 7 or more counters the Jace token can use −3 twice, so each card nets "
    "+1. Say how your rule reads them.\n"
    "- **Census, readings and bar** as in Basis. **Tests,** with invented names: a sorcery with \"Draw a card.\" and "
    "flashback reads `card-draw`; an artifact with \"When this artifact enters or is put into a graveyard from the "
    "battlefield, draw a card.\" does; a loot with flashback does not. Run one mutant for each group of words.\n\n"
)

for old, new, label in ((OLD_TOP, NEW_TOP, "top"), (OLD_ITEM3, NEW_ITEM3, "item 3")):
    assert s.count(old) == 1, f"{label}: {s.count(old)}"
    s = s.replace(old, new)
assert s.count(ANCHOR_8) == 1 and s.count("## Item 7a.") == 0
s = s.replace(ANCHOR_8, ITEM_7A + ANCHOR_8)
Path(new_path).write_text(s)
print("ok", len(s))
