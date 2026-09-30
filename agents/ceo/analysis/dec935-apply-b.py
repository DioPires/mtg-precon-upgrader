"""DEC-935 round 3b: apply the two follow-up lines approved on verdict card ad106107
(2026-09-30): +Raphael, the Nightwatcher / -Eladamri's Call; +Rising of the Day / -Clever Concealment.

    uv run python agents/ceo/analysis/dec935-apply-b.py
"""
import json

PATH = "data/commanders/broodfire-hatchery/deck.json"
SCRY = {"type": "scryfall", "name": "Scryfall"}
AI = {"type": "ai-inferred", "name": "DEC-935 combat remake (CEO, board-approved 2026-09-30)"}
d = json.load(open(PATH))

names = {c["name"] for c in d["decklist"]}
assert {"Eladamri's Call", "Clever Concealment"} <= names
assert not {"Raphael, the Nightwatcher", "Rising of the Day"} & names
d["decklist"] = [c for c in d["decklist"] if c["name"] not in ("Eladamri's Call", "Clever Concealment")] + [
    {"name": "Raphael, the Nightwatcher", "type": "Legendary Creature — Mutant Ninja Turtle", "primary_role": "payoff"},
    {"name": "Rising of the Day", "type": "Enchantment", "primary_role": "engine"},
]
assert sum(c.get("quantity", 1) for c in d["decklist"]) == 99

g = d["guideContent"]
so = g["strategyOverview"]
reps = [
    ("Rhythm of the Wild gives every nontoken creature riot, Samut, Hazoret's Champion gives the team haste for two mana, Palani's Hatcher",
     "Rhythm of the Wild gives every nontoken creature riot, Samut, Hazoret's Champion gives the team haste for two mana, Rising of the Day does the same on an enchantment and gives the deck's 14 legendary creatures +1/+0, Palani's Hatcher"),
    ("Raph & Mikey hatch a creature tapped and attacking every time they attack. Zopandrel",
     "Raph & Mikey hatch a creature tapped and attacking every time they attack. Raphael, the Nightwatcher gives every attacking creature double strike. Zopandrel"),
    ("4 tutors (Worldly Tutor puts the next hatch on top of the library; Enlightened Tutor finds Rhythm of the Wild, Annie Joins Up, Aggravated Assault, Maskwood Nexus or an Altar; Eladamri's Call and Natural Order find a bomb, and Natural Order can sacrifice an Egg as its cost, which also hatches)",
     "3 tutors (Worldly Tutor puts the next hatch on top of the library; Enlightened Tutor finds Rhythm of the Wild, Rising of the Day, Annie Joins Up, Aggravated Assault, Maskwood Nexus or an Altar; Natural Order finds a bomb and can sacrifice an Egg as its cost, which also hatches)"),
    ("6 protection pieces (Deflecting Swat and Flawless Maneuver are free with the commander out; Clever Concealment phases the board out of a wipe)",
     "5 protection pieces (Deflecting Swat and Flawless Maneuver are free with the commander out; Vigor and Avacyn carry the hatched board through damage-based and destroy-based wipes)"),
]
for a, b in reps:
    assert a in so, a[:60]
    so = so.replace(a, b)
g["strategyOverview"] = so

cats = {c["name"]: c for c in g["deckCategories"]}
c = cats["Haste"]
c["cards"].insert(2, "Rising of the Day")
c["description"] = c["description"].replace(
    "Samut, Hazoret's Champion is a 2-mana anthem Atla can hatch,",
    "Samut, Hazoret's Champion is a 2-mana anthem Atla can hatch, Rising of the Day is the same anthem on an enchantment and gives the 14 legendary creatures +1/+0,")
c = cats["Power Multipliers"]
c["cards"].insert(2, "Raphael, the Nightwatcher")
c["description"] = c["description"].replace(
    "and Worldspine Wurm attacks as a 60/60.",
    "and Worldspine Wurm attacks as a 60/60; Raphael, the Nightwatcher gives every attacking creature double strike, so that Wurm deals 60 twice. Raphael is a creature, so Atla can hatch him (his sneak cost returns an unblocked attacker to hand, which is only worth it with a token).")
c = cats["Tutors"]
c["cards"] = ["Enlightened Tutor", "Worldly Tutor", "Natural Order"]
c["description"] = ("Three tutors, each with a job: Worldly Tutor puts a creature on top of the library, which is exactly where Atla's next hatch comes from; "
                    "Enlightened Tutor finds Rhythm of the Wild, Rising of the Day, Annie Joins Up, Aggravated Assault, Maskwood Nexus, Thornbite Staff or either Altar; "
                    "Natural Order sacrifices an Egg (which hatches) and puts Craterhoof, Vigor, Worldspine Wurm or Zopandrel onto the battlefield.")
c = cats["Protection"]
c["cards"] = ["Deflecting Swat", "Flawless Maneuver", "Lightning Greaves", "Vigor", "Avacyn, Angel of Hope"]
c["description"] = ("The deck taps out on its own turn with the commander on the battlefield, so every protection piece is chosen to be live then. "
                    "Deflecting Swat and Flawless Maneuver cost nothing while Atla is out, Lightning Greaves gives Atla shroud, and Vigor and Avacyn make the "
                    "hatched board survive damage-based and destroy-based wipes. Clever Concealment was traded for a third haste anthem at DEC-935.")
c = cats["Key Lands"]
c["description"] = c["description"].replace("13 in the deck", "14 in the deck")

for w in d["winConditions"]:
    if w["title"] == "Hatch and Swing":
        w["cards"] = ["Rhythm of the Wild", "Samut, Hazoret's Champion", "Rising of the Day", "Xenagos, God of Revels", "Zopandrel, Hunger Dominus",
                      "Raphael, the Nightwatcher", "Craterhoof Behemoth", "Worldspine Wurm", "Blightsteel Colossus",
                      "Etali, Primal Conqueror // Etali, Primal Sickness"]
        w["description"] = w["description"].replace(
            "attacks as a 60/60 trampler and Blightsteel Colossus as 22 infect.",
            "attacks as a 60/60 trampler and Blightsteel Colossus as 22 infect; Raphael, the Nightwatcher gives every attacker double strike on top.")

hl = d["highlights"]
idx = next(i for i, h in enumerate(hl) if h["name"] == "Aggravated Assault")
hl.insert(idx + 1, {"name": "Raphael, the Nightwatcher", "price": "€PRICE_RAPHAEL", "isGameChanger": False,
                    "reason": "{2}{R}{R} 2/3: attacking creatures you control have double strike. Hatchable, unlike an enchantment anthem; a Zopandrel-and-Xenagos Worldspine Wurm deals 60 twice.",
                    "sources": [SCRY]})
idx = next(i for i, h in enumerate(hl) if h["name"] == "Samut, Hazoret's Champion")
hl.insert(idx + 1, {"name": "Rising of the Day", "price": "€PRICE_RISING", "isGameChanger": False,
                    "reason": "{2}{R} enchantment: creatures you control have haste, legendary creatures +1/+0 (14 in the deck, Atla included). The third team-wide haste source, on the permanent type that survives a wipe.",
                    "sources": [SCRY]})

for s in d["synergies"]:
    if s["title"].startswith("Zopandrel + Xenagos"):
        s["description"] += " With Raphael, the Nightwatcher on the battlefield the Wurm deals that damage twice."
        s["cards"].append("Raphael, the Nightwatcher")

d["sources"].append({
    "type": "ai-inferred",
    "name": "Swap round 3b — DEC-935 follow-up lines (board-approved 2026-09-30)",
    "detail": "Verdict card ad106107, both lines approved: ADD Raphael, the Nightwatcher / CUT Eladamri's Call (Nesting Dragon kept after the Egg-producer count: Atla with Seedborn Muse and the doublers makes 2 to 8 Eggs per turn cycle, so Eggs are not the bottleneck, but Nesting Dragon is the only free land-drop Egg source; Eladamri's Call was the one tutor that puts a creature in hand rather than on top or onto the battlefield); ADD Rising of the Day / CUT Clever Concealment (third team-wide haste anthem: chance of having seen one by turn 5 rises from 21% to 30% on the anthems alone, about 45% counting Enlightened, Worldly and Natural Order as virtual copies; protection 6 -> 5 against a target of 4). Caretaker's Talent kept (board: card draw).",
})

json.dump(d, open(PATH, "w"), indent=2, ensure_ascii=False)
open(PATH, "a").write("\n")
print("applied 3b; entries", len(d["decklist"]), "sum", sum(c.get("quantity", 1) for c in d["decklist"]))
