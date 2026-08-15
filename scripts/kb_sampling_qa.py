#!/usr/bin/env python3
"""Combo Lab KB sampling QA (QE-5 / KB-7) — DEC-476 Phase 1 (DEC-488).

Two layers:

1. Automatic fidelity checks over the WHOLE KB (cheap, deterministic): every
   extracted item's evidence must actually occur in the card's oracle text,
   magnitudes must be positive, provenances must be in vocabulary, and activated
   costs must occur in oracle text. Reports pass rates overall and for the KB-7
   high-impact subset (cards that appear in a Spellbook combo variant — these
   feed Tier-B verdicts, so their extraction fidelity is what matters most).

2. A stratified human-review worksheet (QE-5 methodology): draws a seeded random
   sample, oversampling the KB-7 subset, and writes an editable worksheet so a
   human can sign off (provenance -> human-reviewed on pass). Seeded for
   reproducibility.

Usage:
    uv run python scripts/kb_sampling_qa.py                       # full report
    uv run python scripts/kb_sampling_qa.py --sample 60 --seed 488 --worksheet ws.json
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from combo_kb_lib import ALL_PROVENANCES, ITEM_FIELDS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIRROR_FILE = PROJECT_ROOT / "priv_data" / "scryfall-oracle.json"
MATCHER_INDEX = PROJECT_ROOT / "data" / "spellbook" / "matcher-index.json"
ENTRIES_DIR = PROJECT_ROOT / "data" / "combo-kb" / "entries"


def norm(s: str) -> str:
    return " ".join((s or "").split()).lower()


def oracle_text_for(card: dict) -> str:
    if card.get("card_faces"):
        return "\n".join(f.get("oracle_text", "") for f in card["card_faces"])
    return card.get("oracle_text", "")


def evidence_core(ev: str) -> str:
    return norm(ev.rstrip("…").strip())


def check_entry(entry: dict, oracle: str) -> list[str]:
    """Return a list of failure codes for this entry (empty = clean)."""
    fails = []
    onorm = norm(oracle)
    for field in ITEM_FIELDS:
        for item in entry.get(field) or []:
            if item.get("provenance") not in ALL_PROVENANCES:
                fails.append(f"{field}:bad_provenance")
            mag = item.get("magnitude", 1)
            if isinstance(mag, int) and mag < 1:
                fails.append(f"{field}:nonpositive_magnitude")
            # Evidence grounding applies to deterministic items (they carry a
            # verbatim oracle snippet). LLM items carry model evidence; skip.
            if item.get("provenance") == "deterministic":
                core = evidence_core(item.get("evidence", ""))
                if core and core not in onorm:
                    fails.append(f"{field}:evidence_not_in_oracle")
    for cost in (entry.get("costs") or {}).get("activated") or []:
        if cost.get("provenance") == "deterministic":
            core = evidence_core(cost.get("cost", ""))
            if core and core not in onorm:
                fails.append("costs:cost_not_in_oracle")
    return fails


def kb7_oracle_ids() -> set[str]:
    """KB-7 high-impact set: cards that appear in at least one Spellbook combo
    variant (their KB entry can feed a Tier-B verdict)."""
    idx = json.loads(MATCHER_INDEX.read_text(encoding="utf-8"))
    return {c["o"] for c in idx["cards"].values() if c.get("o")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--seed", type=int, default=488)
    ap.add_argument("--worksheet", type=Path, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    mirror = {c["oracle_id"]: c for c in json.loads(MIRROR_FILE.read_text(encoding="utf-8"))
              if c.get("oracle_id")}
    kb7 = kb7_oracle_ids()

    entries = []
    for fp in ENTRIES_DIR.glob("*.json"):
        entries.extend(json.loads(fp.read_text(encoding="utf-8")))

    stats = {"total": 0, "clean": 0, "kb7_total": 0, "kb7_clean": 0}
    fail_codes: dict[str, int] = {}
    failing_examples = []
    for e in entries:
        oid = e["oracle_id"]
        oracle = oracle_text_for(mirror.get(oid, {}))
        fails = check_entry(e, oracle)
        is_kb7 = oid in kb7
        stats["total"] += 1
        stats["kb7_total"] += int(is_kb7)
        if not fails:
            stats["clean"] += 1
            stats["kb7_clean"] += int(is_kb7)
        else:
            for f in fails:
                fail_codes[f] = fail_codes.get(f, 0) + 1
            if len(failing_examples) < 15:
                failing_examples.append({"name": e["name"], "fails": sorted(set(fails))})

    pass_rate = stats["clean"] / stats["total"] if stats["total"] else 0.0
    kb7_rate = stats["kb7_clean"] / stats["kb7_total"] if stats["kb7_total"] else 0.0

    # Stratified human-review worksheet (oversample KB-7).
    if args.worksheet:
        rng = random.Random(args.seed)
        kb7_entries = [e for e in entries if e["oracle_id"] in kb7]
        rest = [e for e in entries if e["oracle_id"] not in kb7]
        n_kb7 = min(len(kb7_entries), args.sample * 2 // 3)
        n_rest = min(len(rest), args.sample - n_kb7)
        sample = rng.sample(kb7_entries, n_kb7) + rng.sample(rest, n_rest)
        worksheet = {
            "schema": "combo-kb-qa-worksheet",
            "seed": args.seed,
            "methodology": (
                "Human reviewer checks each entry's provides/wants/ambient/"
                "triggers/costs/guards against the card's oracle text. Mark "
                "verdict pass|fail and, on pass for a KB-7 card, the operator may "
                "promote its provenance to human-reviewed (KB-7 elevated review). "
                "Record the measured error rate back on the DEC-488 issue."),
            "kb7_oversampled": n_kb7,
            "items": [{
                "oracle_id": e["oracle_id"], "name": e["name"],
                "is_kb7": e["oracle_id"] in kb7,
                "oracle_text": oracle_text_for(mirror.get(e["oracle_id"], {})),
                "extracted": {f: e.get(f) for f in ITEM_FIELDS},
                "verdict": "", "notes": "",
            } for e in sample],
        }
        args.worksheet.write_text(json.dumps(worksheet, indent=2, ensure_ascii=False) + "\n",
                                  encoding="utf-8")

    result = {
        "entries_checked": stats["total"],
        "auto_pass_rate": round(pass_rate, 4),
        "kb7_entries": stats["kb7_total"],
        "kb7_auto_pass_rate": round(kb7_rate, 4),
        "failure_codes": dict(sorted(fail_codes.items(), key=lambda kv: -kv[1])),
        "failing_examples": failing_examples,
    }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"KB automatic fidelity QA over {stats['total']} entries")
        print(f"  overall auto-pass rate: {pass_rate:.2%} "
              f"({stats['clean']}/{stats['total']})")
        print(f"  KB-7 auto-pass rate:    {kb7_rate:.2%} "
              f"({stats['kb7_clean']}/{stats['kb7_total']})")
        if fail_codes:
            print("  failure codes:")
            for code, n in sorted(fail_codes.items(), key=lambda kv: -kv[1]):
                print(f"    {code}: {n}")
        if args.worksheet:
            print(f"  wrote human-review worksheet: {args.worksheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
