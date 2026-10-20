"""DEC-945: apply board-approved swap +Avacyn, Angel of Horror / -Harvester of Souls (eternal-harvest)."""
import json

P = "data/commanders/eternal-harvest/deck.json"
d = json.load(open(P))

OLD = "Harvester of Souls"
NEW = "Avacyn, Angel of Horror"
EDHREC = {"type": "edhrec", "name": "EDHREC - Meren", "url": "https://edhrec.com/commanders/meren-of-clan-nel-toth"}
SCRY = {"type": "scryfall", "name": "Scryfall - Avacyn, Angel of Horror",
        "url": "https://scryfall.com/card/frc/7/avacyn-angel-of-horror",
        "detail": "Oracle text + 2026-08-21 ruling verified 2026-10-07"}
AI = {"type": "ai-inferred", "name": "Claude analysis",
      "detail": "DEC-945 board-approved swap for Harvester of Souls (verdict card c8a17383, 2026-10-07)"}

# decklist
idx = [i for i, c in enumerate(d["decklist"]) if c["name"] == OLD]
assert len(idx) == 1, idx
d["decklist"][idx[0]] = {"name": NEW, "type": "Creature", "primary_role": "engine", "secondary_role": "payoff"}

# highlight
hidx = [i for i, h in enumerate(d["highlights"]) if h.get("name") == OLD]
assert len(hidx) == 1, hidx
d["highlights"][hidx[0]] = {
    "name": NEW, "price": "$9-16", "isGameChanger": False,
    "reason": ("Mass-recursion engine: \"Whenever Avacyn or another nontoken creature you control dies, return that card "
               "to the battlefield under your control at the beginning of the next end step.\" One trigger per death, no "
               "per-turn cap. A creature returned at an end step can be sacrificed again in that end step to an instant-speed "
               "outlet (Ashnod's Altar, Phyrexian Altar, Greater Good, Yawgmoth, Priest of Forgotten Gods) and returns at the "
               "next player's end step, so each nontoken creature can die up to four times per turn cycle. Destroy and -X/-X "
               "effects only delay her one end step; only exile, bounce or theft answer her for good. Covers the Humans Mikaeus "
               "skips (Meren, Yawgmoth, Plaguecrafter, Eternal Witness, Zulaport Cutthroat). Ruling: if she dies at the same "
               "time as other nontoken creatures, she triggers for each of them, so Toxic Deluge and Living Death become "
               "one-sided. 8 MV: cheat her in with Reanimate, Animate Dead, Victimize, Living Death, Colossal Grave-Reaver or "
               "The Soul Stone; Entomb and Buried Alive bin her."),
    "sources": [SCRY, EDHREC, AI],
}

# synergies: replace the Harvester synergy, add the Spore Frog loop
sidx = [i for i, s in enumerate(d["synergies"]) if OLD in json.dumps(s)]
assert len(sidx) == 1, sidx
d["synergies"][sidx[0]] = {
    "title": "Avacyn Kokusho Drain Loop",
    "cards": [NEW, "Kokusho, the Evening Star", "Drivnod, Carnage Dominus"],
    "description": ("With Avacyn out and an instant-speed free outlet, Kokusho dies in every end step: sacrifice it on your "
                    "turn, it returns at your end step, sacrifice it again, it returns at the next opponent's end step, and so "
                    "on. Four deaths per turn cycle drain 5 each, 20 life from each opponent per cycle. Drivnod doubles "
                    "Kokusho's death trigger, so the same loop drains 40 per cycle, lethal from 40 life in one cycle. Blood "
                    "Artist, Zulaport Cutthroat and Bastion of Remembrance add 1 per death on top. Not an infinite loop; the "
                    "return is bound to end steps."),
    "sources": [SCRY, AI],
}
d["synergies"].append({
    "title": "Avacyn Frog Lock",
    "cards": [NEW, "Spore Frog"],
    "description": ("Spore Frog sacrificed during opponent A's combat returns at A's end step, so it is ready for opponent "
                    "B's combat, then C's. Three fogs per turn cycle instead of the one Meren gives. Sakura-Tribe Elder works "
                    "the same way for up to four basics per cycle, and Plaguecrafter re-enters each end step for four edicts "
                    "per cycle when sacrificed to a free outlet."),
    "sources": [SCRY, AI],
})

# categories
for c in d["categories"]:
    if OLD in c["cards"]:
        c["cards"].remove(OLD)
    if c["name"] == "Engine Pieces" and NEW not in c["cards"]:
        c["cards"].append(NEW)
    if c["name"] == "Death Payoffs" and NEW not in c["cards"]:
        c["cards"].append(NEW)

# prose
so = d["guideContent"]["strategyOverview"]
assert OLD not in so
anchor = "Walking Ballista at X=0 with Mikaeus"
assert anchor in so
so = so.replace(anchor, ("Avacyn, Angel of Horror returns every nontoken creature that dies at the next end step, so with a "
                         "free outlet each creature can die once per end step, four times per turn cycle; Kokusho alone drains "
                         "20 per cycle that way, 40 with Drivnod. " + anchor), 1)
d["guideContent"]["strategyOverview"] = so

d["sources"].append({
    "type": "other",
    "name": "Board swap approval, DEC-945, 2026-10-07",
    "detail": ("Board verdict card c8a17383 on DEC-945: IN Avacyn, Angel of Horror, OUT Harvester of Souls. Avacyn returns "
               "every nontoken creature that dies at the next end step, so with an instant-speed outlet each creature can die "
               "up to four times per turn cycle (Kokusho: 20 life per opponent per cycle, 40 with Drivnod). She covers the "
               "Humans Mikaeus skips and makes Toxic Deluge and Living Death one-sided. Harvester of Souls was one draw trigger "
               "among nine draw sources, below the EDHREC listing floor, in no Spellbook combo or Tier B loop. Same slot class "
               "(6+ MV reanimation target). Avacyn is unowned (EUR 8.77 on 2026-10-07, information only). Alternative cut "
               "offered and not taken: Liliana, Dreadhorde General."),
})
d["lastUpdatedSet"] = "Reality Fracture Commander"

# stale-ref sweep over card arrays + prose (attribution text in sources[].detail may name the cut card)
scan = {
    "decklist": [c["name"] for c in d["decklist"]],
    "highlights": [h["name"] for h in d["highlights"]],
    "synergies": [s["cards"] + [s["description"]] for s in d["synergies"]],
    "categories": [c["cards"] for c in d["categories"]],
    "winConditions": d["winConditions"],
    "strategy": d["guideContent"]["strategyOverview"],
}
assert OLD not in json.dumps(scan), "stale ref"
json.dump(d, open(P, "w"), indent=2, ensure_ascii=False)
open(P, "a").write("\n")
print("deck.json updated; total", sum(c.get("quantity", 1) for c in d["decklist"]))

# card-metadata.json (strict format: sorted keys, indent=2, ensure_ascii=True, no trailing newline)
MP = "data/card-metadata.json"
m = json.load(open(MP))
m[NEW] = {"cmc": 8.0, "colors": ["B"], "mana_cost": "{5}{B}{B}{B}",
          "oracle_text": ("Flying, deathtouch\nWhenever Avacyn or another nontoken creature you control dies, return that "
                          "card to the battlefield under your control at the beginning of the next end step."),
          "power": "8", "toughness": "8", "type_line": "Legendary Creature — Angel"}
with open(MP, "w") as f:
    json.dump(m, f, indent=2, sort_keys=True)
print("card-metadata updated")
