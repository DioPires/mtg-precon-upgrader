# DEC-566 — Hoard and Bleed: should the deck pivot to attack-based value?

**Date:** 2026-08-27. **Deck:** hoard-and-bleed (Smaug, Wicked Worm), bracket 4-, 1 GC.
**Baseline:** DEC-548 state at commit `9579a86`. Card pool + metrics refreshed 2026-08-27: global 97 (norm 100), gaps 0 — unchanged.

## Verdict

**No. Keep the cast-engine architecture. Zero swaps proposed.** An attack pivot builds around
triggers the commander does not have, fires at most once per turn cycle, and asks a
47-total-power utility creature base to do a job the drain layers already do better.

## The commander pays for casts, not attacks (oracle-verified 2026-08-27)

Smaug, Wicked Worm ({3}{B}{R}, 5/5 flying):
1. ETB: create X tapped Treasures, X = artifacts opponents control.
2. "Whenever you cast a spell, if mana from a Treasure was spent to cast it, you draw a card and lose 1 life."

There is no attack text anywhere on the card. Every recurring point of commander value is
gated on casting spells with Treasure mana.

## Trigger-frequency math (DEC-477 basis: vanilla 4-player model, same turn, same board)

- **Cast engine:** goldfish available mana is 6.6 (T6) / 7.4 (T7) mean, before Treasure bursts.
  At 2.97 avg nonland MV that is 2–3 Treasure-fueled casts per own turn, and the 21
  instants/sorceries let the trigger also fire on opponents' turns. Call it **2–3+ draws per turn cycle** with Smaug out (median cast T5; 81.7% of games by T7).
- **Attack triggers fire ×1 per turn cycle** (own-attack-gated), require a creature that
  survives to attack, and for the combat-damage class (Grim Hireling, Cavern-Hoard Dragon,
  Ancient Copper Dragon) also require connecting through blockers. Best case, Grim Hireling
  yields 2 Treasures per cycle — Black Market Connections-class output with a combat condition attached.

The cast engine outproduces the best attack trigger roughly 2–3 : 1 on frequency with no
combat precondition. That ratio is the whole strategic answer.

## The creature base cannot carry a combat plan

21 creatures, 47 total power (avg 2.2), weighted toward toughness (Fireweaver 1/3,
Manufactor 1/3, Marionette Master 1/3, Plunderer 1/4). Sim: threats on board mean 2.8 at T7;
combat pressure mean 12.4 at T7 vs lethalProxy 45.8% (T7) / 67.9% (T8) from the noncombat
layers. A combat kill needs ~120 damage across three opponents through blockers; Marionette
Master, Exsanguinate, Mirkwood Bats and the loop hit all opponents at once.

Three costs of attacking with this suite:
1. **Blocker economics.** The deck is a documented self-bleeder (Smaug tax, pain lands, Black
   Market Connections). Turning engine bodies sideways removes blockers and shortens our own
   clock, which is already the deck's tightest resource.
2. **Sac economics.** Aristocrats fodder wants to die to our outlets on our terms. Combat lets
   opponents choose trades and eat engine pieces (DEC-543 rule: fodder ≠ payoff; combat deaths
   feed neither cleanly when the piece lost is the payoff itself).
3. **Wincon mismatch.** Hellkite Tyrant's win is an upkeep artifact-count check, not combat;
   its steal trigger is a free bonus on opportunistic swings, which the deck already makes.

## The attack-value upside is already captured

Professional Face-Breaker and Goldspan Dragon are in the 99. They fire on the opportunistic
attacks the deck actually takes (Smaug 5/5 flier, Goldspan 4/4 flier haste, Tyrant 6/5).
Of the deck's 19 Treasure sources, these are the only 2 attack-gated ones — the other 17
scale with what the deck does every turn (cast, sac, death, ETB). No build-around is needed
to keep this upside.

## Re-triage of the attack-value class under the DEC-566 lens (oracle-verified)

- **Smaug the Magnificent** (74.3% EDHREC) — REJECT stands, now with the anti-synergy on the
  record: his attack damage equals Treasures *you control*, so he wants a hoard held; the
  commander's draw engine wants Treasures *spent* per spell. The two halves fight over the
  same resource every turn. Damage is ×1/cycle at one target vs drains at all opponents.
- **Cavern-Hoard Dragon** (63.7%) — REJECT: 9 MV (variable discount), combat-connect-gated,
  in a 2.97-curve deck built on cheap-spell density.
- **Grim Hireling** (56.0%) — DEFER: best pure fit of the class (4 MV, 2 Treasures/connect,
  Treasure sac outlet), but still combat-conditioned ×1/cycle and no current slot beats an
  engine piece for it (DEC-548 top-50 triage found only Fake Your Own Death slot-worthy).
  The candidate if the board ever wants exactly one attack-value slot.
- **Ancient Copper Dragon** — REJECT: 6 MV, attack + connect gated; off-curve for this list.

EDHREC context, stated honestly: the crowd's Smaug build is a midrange dragons-and-Treasures
deck and runs these cards at 56–74%. Those rates measure the default archetype's popularity,
not a deficiency in this list. Our tuned aristocrats build shows global 97 (norm 100),
gaps 0, 5 included combos, and the DEC-548 review confirmed the architecture.

## Process record

Ran `refresh_card_pool.py --deck hoard-and-bleed` (mandatory step 2): scores unchanged,
top-50 delta vs DEC-548 is nil for this question (top attack-gated candidates re-triaged
above). Oracle text pulled fresh via Scryfall for all cards named here. No deck files edited;
candidates.json/metrics.json regen is post-review hygiene.
