# Combo Lab — Tier-B loop verifier (closure model)

DEC-501 (DEC-476 Phase 3). The deterministic loop verifier is the Combo Lab's
Tier-B layer: it decides whether a small candidate loop **closes** under an
explicit semantic model, classifies the verified loop, computes its prerequisites
and (on failure) its deficit vector, and records a full provenance chain. It is the
single most soundness-sensitive component in the product — a false Tier-B positive
is the worst failure class (PRD QE-4.1) — so this document states the model, the
per-template soundness argument, and the measured recall, in full.

Source of truth: [`scripts/combo_verifier_lib.py`](../scripts/combo_verifier_lib.py).
Fleet precompute: [`scripts/build_tier_b_candidates.py`](../scripts/build_tier_b_candidates.py)
→ `data/commanders/{id}/tier-b-loops.json`. Regression + calibration:
[`scripts/qe1_regression.py`](../scripts/qe1_regression.py). Tests:
[`tests/test_combo_verifier.py`](../tests/test_combo_verifier.py).

## 1. The closure model (PRD 6.1–6.5)

A **candidate loop** is a small set of cards (2–3 cycle pieces plus any number of
ambient modifiers, DB-3) intended to return to a re-executable state. The verifier
models each member from its **Tier-B knowledge-base view** — the deterministic /
human-reviewed items only (see §4) — as:

- **mana produced** per activation (from `mana_add` magnitude, a deterministic pip
  count);
- **priced costs** (activated-ability mana costs, parsed strictly: see §3);
- **events emitted** (`etb`, `dies`, `untap`, `sacrifice`, …);
- **triggers** consumed (event-pattern → effect);
- **guards** (zone / timing / control / summoning-sickness);
- **feature roles** (`untap_permanent`, `blink`, `sac_outlet`, …).

A candidate **verifies** (PRD 6.5) when, over one iteration:

1. **Piece recurrence** — every cycle piece returns to an executable state;
2. **Resource solvency** — every consumed resource has net delta ≥ 0;
3. **Strict gain** — at least one accumulator has net delta > 0;
4. **Finite-zone soundness** — a finite zone (library/graveyard/exile) that is
   net-consumed makes the loop **bounded** with a derived iteration count, not
   infinite.

### Classification: the pair (k, finite-zone bound)

Per the plan's recorded clarification, classification is the pair
**(turn-cost k, finite-zone bound)**, not three exclusive classes:

- **k = 0** → **infinite** loop (executable arbitrarily many times in a turn);
- **k > 0** → **per-turn value engine**;
- the **finite-zone bound** is an *attribute* reported on either class (an infinite
  loop that self-mills is still bound by the library), never a third class.

## 2. Closure templates and their soundness arguments

The verifier recognises a small, closed set of loop templates. Each is a precise
structural matcher over the modelled economies with an encoded closure argument.
**Only templates whose closure is fully derivable from the coarse features may
assert a closed loop** (`CLOSE_SAFE`); the rest detect structure and abstain. This
single backstop is the primary guard against QE-4.1.

| Template | Closure argument | May assert closure? |
|---|---|---|
| **`untap_mana`** | A self-untapping mana rock (taps for `p`, untaps for priced `u`) plus a *triggered per-tap mana amplifier* nets `p + amp − u`. Closes iff net > 0. Recurrence is intrinsic (the rock untaps itself); no finite zone consumed ⇒ k=0 infinite mana. Worked example: **Basalt Monolith** (tap +3, untap {3}) + **Forsaken Monument** (+1 per tap-for-{C}) ⇒ net +1 ⇒ infinite colorless mana. | **Yes** (mana magnitudes + priced untap cost are deterministic). |
| **`blink_untap_mana`** | A `blink` piece + an `etb_trigger` piece whose ETB untaps ≥ `blink_cost` lands ⇒ infinite mana. | **Yes**, but only when both the blink cost and the untap count are priced (rare; usually abstains). |
| **`blink_value`** | `blink` + `etb_trigger` value payoff. | **No** — the blink's activation cost cannot be reliably attributed from the KB (Deadeye Navigator grants its blink to a *paired* creature). Detects structure, abstains. |
| **`sac_recursion`** | Aristocrats: `sac_outlet` + `sac_fodder` + death payoff. | **No** — the fodder's return cost and which activated ability is the outlet are not captured deterministically; pricing them fabricates numbers. Detects structure, abstains (a QE-2 diagnostic). |

### The Basalt + Thran non-example (the QE-4 regression guard)

`untap_mana`'s amplifier term counts **only** a *triggered per-tap mana amplifier*
(a "whenever you tap … for {C}, add …" trigger — Forsaken Monument, Mana
Reflection). A second standalone mana rock (Thran Dynamo, Mana Vault) taps **once**
and is then tapped — it is not an amplifier. Summing it would make every deck with
two rocks falsely report infinite mana. `tests/test_combo_verifier.py::
test_basalt_plus_thran_is_NOT_infinite` pins this.

## 3. Mana parsing (strictly pure-mana)

`parse_mana` returns an integer **only** for a purely-mana cost (`{3}`, `{1}{B}`,
`{C}{C}`); it returns `None` for any cost with a non-mana component — a tap `{T}`,
untap `{Q}`, sacrifice/discard/life text, `{X}`, or Phyrexian. This is deliberately
strict: an unpriceable cost must never be treated as "free", which is exactly the
channel that would fabricate a closed loop. It prevents two concrete false
positives — a tap-gated blink priced as 0, and a target-untapper's `{G}{T}` priced
as 1.

## 4. Provenance gate (plan decision 6b, ENFORCED)

A Tier-B verdict may consume **only** deterministic or human-reviewed KB items
(`combo_kb_lib.tier_b_view`). LLM- and community-tag-sourced items are dropped. If a
candidate would close using a dropped item, it is **capped at Tier C** with an
explicit reason and never labelled verified until a human reviews the entry (KB-7).
The gate can only *withhold* a "verified" label, never inflate one — the
conservative direction QE-4 demands. `test_provenance_gate_caps_llm_amplifier` pins
this via the dual gated/ungated evaluation path.

## 5. Corroboration vs. novel (DB-7 / DC-6)

- **Corroboration.** A loop already in the curated corpus is reported at **Tier A**
  (Commander Spellbook ground truth); the computed verdict is recorded as
  *corroboration* and can never inflate the tier. This is the safe path and is
  exactly what QE-1b measures.
- **Novel.** A loop *not* in the corpus that the verifier closes is a **novel Tier-B
  finding**, gated stricter still: a `CLOSE_SAFE` template, strict resource gain, no
  deficit, no capped provenance. DC-6 says novel infinite discovery is rare; the
  fleet precompute confirms it (0 novel across 21 decks — the only fleet infinite
  loop, Basalt + Forsaken in titan-convergence, is curated and corroborated).

## 6. Prerequisites (PR-3) and deficit vectors (6.6 / DB-4)

- **Minimal initial stock via ordering optimisation.** The same loop can need 3
  floating mana under one action order and 0 under another. The verifier enumerates
  every ordering of the priced actions (cycle sizes are tiny) and takes the minimal
  worst-case running deficit. Basalt + Forsaken → **0** (tap for mana before paying
  the untap).
- **Guard set (IN-4).** Zone / timing / control / summoning-sickness guards from the
  members, plus the command-zone condition when a member is the deck commander (a
  commander is reliably castable in a way a library card is not — and CR 903.3d:
  "controlling a commander" is the battlefield only).
- **Deficit vector.** On failure the verifier emits the per-iteration shortfall
  ("nets +0 mana; needs a +1 amplifier"), which drives the Tier-B near-miss surface
  (NM-1 Tier B) and the UC3 failure explanation (TX-3). A `shortfall` of `null` is a
  KB-gap abstention (the structure is present but the KB cannot price it) — a QE-2
  diagnostic, not surfaced as an actionable near-miss.

## 7. Ranking (RK-2 completion, RK-3/RK-4 calibration)

Phase 2 shipped a reduced-signal Tier-C ranking. Phase 3 completes RK-2 for
verified/engine findings by adding the two signals that only exist once a loop is
modelled — **mechanistic rate** (accumulator delta per turn; an infinite loop
saturates high, a k>0 engine's rate falls with k) and **startup cost** (from PR-3
minimal stock + piece count). Weights are **calibrated** by `qe1_regression.py
--calibrate` (a deterministic grid maximising the RK-3 top-decile rate) with a
hand-labelled engine set as a second source (RK-4 bias control), written to
`data/combo-kb/verifier-ranking.json`. Re-run on any KB ontology-version change
(QE-6). Ranking never alters tier (RK-6); presentation is coarse bands only (RK-5).

## 8. Measured recall (QE-1b) and its diagnostics (QE-2)

Soundness is the invariant; recall is **measured, never asserted**. On a 2,000-combo
sample of the curated corpus the B-layer verifies **1** (`untap_mana`). This is
**KB-extraction-bound, not verifier-bound**: the dominant miss classes are

- `sac-recursion return cost not priceable` (Phase-1 extraction gap),
- `no modelled loop template` (structure not represented),
- `untap-all / blink loop not in modelled templates` (out of template scope),
- `life-loop drain not extracted` (Phase-1 ontology gap — e.g. Sanguine Bond +
  Exquisite Blood: the "opponent loses life" drain is not tagged, so the loop is
  invisible to the model),

each a QE-2 diagnostic that localises future work. Recall grows only as the ontology
and extractor deepen (QE-3, DEC-488's domain) — never by loosening the closure
model, which would trade the product's core promise for a bigger number. This is the
deliberate DC-6 / QE-4 posture: "Phase 1 is the dominant cost; the knowledge base is
the real project; phases 2–4 consume it."

## 9. Epistemic surface (EI-1/EI-2/EI-4)

Every Tier-B finding is labelled and qualified as **"verified under Laço's game
model"** (EI-2), with a goldfish disclosure (NG1). Corroborated loops render at Tier
A; novel loops at Tier B; capped loops are disclosed but never labelled verified.
Tier labels and the model-conditional qualifier survive every export path (EI-4);
`web/src/__tests__/lib/tierBReport.test.ts` pins that. The verifier never claims
exhaustiveness (EI-3).
