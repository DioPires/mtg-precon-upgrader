"""DEC-1215: apply board verdict card c2f407b6, lines A and C, to broodfire-hatchery.

    A: +Galactus, Devourer of Worlds / -Zacama, Primal Calamity
    C: +Summon: Bahamut / -Blightsteel Colossus

    uv run python agents/ceo/analysis/dec1215/apply.py

Each prose edit asserts that its old span occurs exactly once. A second run prints
`already` for every edit and writes nothing new.
"""
import json
import sys
from pathlib import Path

PATH = Path("data/commanders/broodfire-hatchery/deck.json")
deck = json.loads(PATH.read_text())

GAL = "Galactus, Devourer of Worlds"
BAH = "Summon: Bahamut"
ZAC = "Zacama, Primal Calamity"
BLI = "Blightsteel Colossus"
REVIEW = "DEC-1215 — board question, CEO review (approved 2026-10-20)"


def replace_once(obj, key, old, new, label):
    text = obj[key]
    if new in text:
        print(f"already  {label}")
        return
    n = text.count(old)
    assert n == 1, f"{label}: old span occurs {n} times"
    obj[key] = text.replace(old, new)
    print(f"edited   {label}")


def swap_in_list(lst, old, new, label):
    if new in lst and old not in lst:
        print(f"already  {label}")
        return
    assert lst.count(old) == 1 and new not in lst, label
    lst[lst.index(old)] = new
    print(f"edited   {label}")


def add_to_list(lst, new, label):
    if new in lst:
        print(f"already  {label}")
        return
    lst.append(new)
    print(f"edited   {label}")


# 1. Decklist: each new card takes the cut card's slot.
NEW_ENTRIES = {
    ZAC: {"name": GAL, "type": "Legendary Creature — Elder Alien", "primary_role": "wincon",
          "secondary_role": "removal-spot", "wincon_style": "combat"},
    BLI: {"name": BAH, "type": "Enchantment Creature — Saga Dragon", "primary_role": "removal-spot",
          "secondary_role": "wincon", "wincon_style": "burst"},
}
names = [e["name"] for e in deck["decklist"]]
for cut, entry in NEW_ENTRIES.items():
    if entry["name"] in names and cut not in names:
        print(f"already  decklist {entry['name']}")
        continue
    assert names.count(cut) == 1 and entry["name"] not in names, cut
    deck["decklist"][names.index(cut)] = entry
    print(f"edited   decklist {cut} -> {entry['name']}")

# 2. Strategy overview.
gc = deck["guideContent"]
replace_once(gc, "strategyOverview",
             "Worldspine Wurm, Blightsteel Colossus, Apex Altisaur, Zacama, Primal Calamity, Avacyn",
             f"Worldspine Wurm, {GAL}, Apex Altisaur, {BAH}, Avacyn",
             "overview: bomb list")
replace_once(gc, "strategyOverview",
             "Zopandrel doubles twice, Xenagos fires twice —",
             "Zopandrel doubles twice, Xenagos fires twice, Galactus exiles two permanents —",
             "overview: Annie Joins Up")
replace_once(gc, "strategyOverview",
             "of Craterhoof Behemoth, Palani's Hatcher, Etali and Apex Altisaur while",
             "of Craterhoof Behemoth, Palani's Hatcher, Etali, Galactus and Apex Altisaur while",
             "overview: Elesh Norn")
replace_once(gc, "strategyOverview",
             "Enlightened Tutor finds Rhythm of the Wild, Annie Joins Up, Aggravated Assault, Maskwood Nexus "
             "or an Altar;",
             "Enlightened Tutor finds Rhythm of the Wild, Annie Joins Up, Aggravated Assault, Maskwood Nexus "
             f"or an Altar, or puts {BAH} on top for the next hatch;",
             "overview: Enlightened Tutor")
replace_once(gc, "strategyOverview",
             "and Settle the Wreckage exiles one player's attackers at instant speed.",
             "and Settle the Wreckage exiles one player's attackers at instant speed. Two bombs also remove "
             "on arrival. Galactus exiles any permanent when it enters. Summon: Bahamut destroys a nonland "
             "permanent when it enters and another a turn later, then draws two cards. Its last chapter, "
             "Mega Flare, deals damage equal to the total mana value of your other permanents to each "
             "opponent: a second route to the win when combat stalls.",
             "overview: removal on arrival")

# 3. Deck categories.
cats = {c["name"]: c for c in gc["deckCategories"]}
bombs = cats["Bombs to Hatch"]
swap_in_list(bombs["cards"], BLI, GAL, "Bombs to Hatch: Blightsteel -> Galactus")
swap_in_list(bombs["cards"], ZAC, BAH, "Bombs to Hatch: Zacama -> Bahamut")
replace_once(bombs, "description",
             "Blightsteel Colossus with Xenagos is 22 infect trample, lethal to one player in a single hit.",
             "Galactus is an indestructible 12/12 flier with trample that exiles a permanent when it "
             "enters. Summon: Bahamut is a 9/9 flier that destroys two nonland permanents, draws two cards "
             "and ends with Mega Flare.",
             "Bombs to Hatch: description")
replace_once(cats["Tutors"], "description",
             "Thornbite Staff or either Altar;",
             f"Thornbite Staff or either Altar, or puts {BAH} on top for the next hatch;",
             "Tutors: description")
inter = cats["Interaction and Hoser Coverage"]
add_to_list(inter["cards"], GAL, "Interaction: + Galactus")
add_to_list(inter["cards"], BAH, "Interaction: + Bahamut")
replace_once(inter, "description",
             "which costs nothing when Seedborn Muse untaps the lands.",
             "which costs nothing when Seedborn Muse untaps the lands. Two bombs remove on arrival: Galactus "
             "exiles any permanent when it enters (twice with Annie Joins Up), and Summon: Bahamut destroys "
             "a nonland permanent with each of its first two chapters.",
             "Interaction: description")

# 4. Win condition "Hatch and Swing".
wc = {w["title"]: w for w in deck["winConditions"]}["Hatch and Swing"]
swap_in_list(wc["cards"], BLI, GAL, "Hatch and Swing: Blightsteel -> Galactus")
add_to_list(wc["cards"], BAH, "Hatch and Swing: + Bahamut")
replace_once(wc, "description",
             "and Blightsteel Colossus as 22 infect;",
             "and Galactus as a 24/24 flier with trample;",
             "Hatch and Swing: Galactus")
replace_once(wc, "description",
             "Rogue's Passage makes it unblockable outright.",
             "Rogue's Passage makes it unblockable outright. If combat stalls, Summon: Bahamut's Mega Flare "
             "deals damage equal to the total mana value of your other permanents to each opponent.",
             "Hatch and Swing: Mega Flare")

# 5. Synergy "Zopandrel + Xenagos on one body".
syn = {s["title"]: s for s in deck["synergies"]}["Zopandrel + Xenagos on one body = 60 trample"]
replace_once(syn, "description",
             "Blightsteel Colossus on the same line is 44 infect trample.",
             "Galactus on the same line is a 48/48 flier with trample.",
             "synergy: Galactus")

# 6. Highlights (prices: data/card-metadata.json, eur).
meta = json.loads(Path("data/card-metadata.json").read_text())
HIGHLIGHTS = [
    {"name": GAL,
     "reason": "{10} colorless 12/12 with flying, trample and indestructible. When it enters, it exiles "
               "target permanent of any type; Annie Joins Up makes that two, and Elesh Norn one more. Nobody "
               "casts it: Atla's or Raph & Mikey's reveal puts it onto the battlefield, where Zopandrel makes "
               "it a 24/24 flier. It must attack the opponent with the most life each combat."},
    {"name": BAH,
     "reason": "{9} colorless 9/9 flying Saga creature. Chapter I destroys a nonland permanent when it "
               "enters, chapter II destroys another, chapter III draws two cards, and chapter IV (Mega Flare) "
               "deals damage equal to the total mana value of your other permanents to each opponent before "
               "you sacrifice it. It attacks two or three times first. It is an enchantment, so Enlightened "
               "Tutor puts it on top for the next hatch; under Maskwood Nexus, Roaming Throne doubles each "
               "chapter."},
]
have = {h["name"] for h in deck["highlights"]}
for h in HIGHLIGHTS:
    if h["name"] in have:
        print(f"already  highlight {h['name']}")
        continue
    if h["name"] not in meta:
        print(f"pending  highlight {h['name']} (run fetch_card_metadata.py, then this script again)")
        continue
    eur = meta[h["name"]]["eur"]
    deck["highlights"].append({
        "name": h["name"], "price": f"€{eur:.2f}", "isGameChanger": False, "reason": h["reason"],
        "sources": [{"type": "scryfall", "name": "Scryfall"}, {"type": "ai-inferred", "name": REVIEW}],
    })
    print(f"edited   highlight {h['name']}")

# 7. Root source entry. SPOT is filled from metrics.json after the metrics run.
SOURCE_NAME = "Swap round 7 — DEC-1215 Galactus and Summon: Bahamut (board-approved 2026-10-20)"
SPOT = sys.argv[1] if len(sys.argv) > 1 else None
detail = (
    "Board asked whether to consider Summon: Bahamut and Galactus, Devourer of Worlds. Verdict card "
    "c2f407b6, lines A and C approved: ADD Galactus, Devourer of Worlds / CUT Zacama, Primal Calamity "
    "(Zacama's land untap works only when it is cast, and Atla's reveal never casts it; Galactus arrives "
    "as a flying, trampling, indestructible 12/12 that exiles any permanent, twice with Annie Joins Up); "
    "ADD Summon: Bahamut / CUT Blightsteel Colossus (two removals, a 9/9 flier that attacks two or three "
    "times, two cards and Mega Flare as a second finisher; wincon was the only role above its target, 5 "
    "of 3; Blightsteel's damage is poison, so it does not add to the life damage from the rest of the "
    "deck). Not taken: line B (cut Llanowar Elves for Galactus) and line D (cut Etali, Primal Conqueror "
    "for Bahamut). Board rule (DEC-1215, 2026-10-20): the deck wins mainly through combat with big "
    "creatures; noncombat damage is allowed as a second route. Ownership: the board owns Summon: Bahamut "
    "(DEC-1215 comment, 2026-10-20); priv_data/Owned.csv does not list it yet. "
    + (f"Spot removal {SPOT}. " if SPOT else "")
    + "Swap round 2 since the round-5 reset."
)
srcs = {s["name"]: s for s in deck["sources"]}
if SOURCE_NAME in srcs:
    if srcs[SOURCE_NAME]["detail"] == detail:
        print("already  source entry")
    else:
        srcs[SOURCE_NAME]["detail"] = detail
        print("edited   source entry (detail)")
else:
    deck["sources"].append({"type": "ai-inferred", "name": SOURCE_NAME, "detail": detail})
    print("edited   source entry")

assert sum(e.get("quantity", 1) for e in deck["decklist"]) == 99
PATH.write_text(json.dumps(deck, indent=2, ensure_ascii=False) + "\n")
