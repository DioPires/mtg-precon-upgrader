#!/usr/bin/env python3
"""Deterministic Combo Lab knowledge-base extraction (DEC-476 Phase 1 / DEC-488).

Reads the local Scryfall mirror (priv_data/scryfall-oracle.json) and the
versioned ontology (data/combo-kb/ontology.json), and emits one KB entry per
card expressing — in the vocabulary of PRD Section 6 — provides/wants features
(with scalar magnitudes, KB-2), ambient modifiers, emitted events, triggers,
costs, and guards. Every field/item carries per-field provenance (KB-4); this
pass stamps everything it derives ``deterministic``. Fields it cannot derive are
left empty and the card is flagged ``needs_llm`` for the offline classifier pass
(classify_combo_kb.py) — the LLM never runs on the query path (NF-1/KB-5).

Deterministic first (plan Phase-1 row): mechanical extraction is the cheapest
way to satisfy the Tier-B provenance gate, so we maximise its coverage before
any LLM pass.

Output: data/combo-kb/entries/{shard}.json (sharded by oracle_id[:2], stable
key order for git-delta friendliness) + data/combo-kb/meta.json.

Usage:
    uv run python scripts/build_combo_kb.py                 # full pool
    uv run python scripts/build_combo_kb.py --limit 2000    # smoke subset
    uv run python scripts/build_combo_kb.py --names-file X   # only these names
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from combo_kb_lib import PROV_DETERMINISTIC, provenance_summary  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIRROR_FILE = PROJECT_ROOT / "priv_data" / "scryfall-oracle.json"
MIRROR_META = PROJECT_ROOT / "priv_data" / "scryfall-oracle.meta.json"
ONTOLOGY_FILE = PROJECT_ROOT / "data" / "combo-kb" / "ontology.json"
KB_DIR = PROJECT_ROOT / "data" / "combo-kb"
ENTRIES_DIR = KB_DIR / "entries"
META_FILE = KB_DIR / "meta.json"

EXTRACTOR_VERSION = "det-1.0.0"

_WORD_NUM = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
}
_WORD_NUM_RE = re.compile(
    r"\b(" + "|".join(_WORD_NUM) + r")\b", re.IGNORECASE
)

# Trigger clauses (PRD 6.2). Capture the trigger condition up to the first comma.
_TRIGGER_RE = re.compile(
    r"\b(when|whenever|at the (?:beginning|end) of)\b[^.,]{0,120}", re.IGNORECASE
)
# Activated-ability cost detection: a "COST: EFFECT" line whose cost prefix names
# a real cost token. Reminder text (parenthetical) is stripped first.
_COST_TOKEN_RE = re.compile(
    r"\{t\}|\{[wubrgcx0-9/]+\}|\bsacrifice\b|\bdiscard\b|\bpay\b|\bexile\b|\btap\b|\bremove\b",
    re.IGNORECASE,
)
_REMINDER_RE = re.compile(r"\([^)]*\)")


def normalise_numbers(text: str) -> str:
    return _WORD_NUM_RE.sub(lambda m: _WORD_NUM[m.group(1).lower()], text)


def truncate(s: str, n: int = 80) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def load_ontology() -> dict:
    ont = json.loads(ONTOLOGY_FILE.read_text(encoding="utf-8"))
    # Pre-compile.
    for f in ont["features"]:
        f["_patterns"] = [re.compile(p, re.IGNORECASE) for p in f["patterns"]]
        m = f.get("magnitude")
        if m:
            m["_re"] = re.compile(m["pattern"], re.IGNORECASE)
    for g in ont["guards"]:
        g["_patterns"] = [re.compile(p, re.IGNORECASE) for p in g["patterns"]]
    return ont


def card_faces(card: dict) -> list[dict]:
    """Return per-face {name,type_line,oracle_text,mana_cost}. Handles DFCs whose
    oracle_text lives in card_faces (PRD IN-5; local-mirror DFC caveat)."""
    if card.get("card_faces"):
        faces = []
        for face in card["card_faces"]:
            faces.append({
                "type_line": face.get("type_line") or "",
                "oracle_text": face.get("oracle_text") or "",
                "mana_cost": face.get("mana_cost") or "",
            })
        return faces
    return [{
        "type_line": card.get("type_line") or "",
        "oracle_text": card.get("oracle_text") or "",
        "mana_cost": card.get("mana_cost") or "",
    }]


def extract_features(text: str, text_norm: str, ontology: dict) -> tuple[list, list, list]:
    provides, wants, ambient = [], [], []
    buckets = {"provides": provides, "wants": wants, "ambient": ambient}
    for feat in ontology["features"]:
        hit = None
        for pat in feat["_patterns"]:
            m = pat.search(text)
            if m:
                hit = m
                break
        if not hit:
            continue
        item = {
            "feature": feat["id"],
            "economy": feat["economy"],
            "provenance": PROV_DETERMINISTIC,
            "evidence": truncate(hit.group(0)),
        }
        mag = feat.get("magnitude")
        if mag:
            mm = mag["_re"].search(text_norm)
            if mm and mag.get("kind") == "pip_count":
                item["magnitude"] = len(re.findall(r"\{[^}]+\}", mm.group(mag["group"])))
            elif mm:
                try:
                    item["magnitude"] = int(mm.group(mag["group"]))
                except (ValueError, IndexError):
                    item["magnitude"] = mag.get("default", 1)
            else:
                item["magnitude"] = mag.get("default", 1)
        else:
            item["magnitude"] = 1
        buckets[feat["kind"]].append(item)
    return provides, wants, ambient


def extract_triggers(text: str) -> list:
    out = []
    seen = set()
    for m in _TRIGGER_RE.finditer(text):
        clause = truncate(m.group(0), 100)
        key = clause.lower()
        if key in seen:
            continue
        seen.add(key)
        guarded = bool(re.search(r"if |as long as|only if|unless", m.group(0), re.I))
        out.append({
            "trigger": clause,
            "guarded": guarded,
            "provenance": PROV_DETERMINISTIC,
        })
    return out


def extract_events(text: str, provides: list) -> list:
    events = set()
    econ_to_event = {
        "etb": "etb", "dies": "dies", "ltb": "ltb", "cast": "cast",
        "token": "token_create", "mill": "mill", "drain": "lifeloss",
        "lifegain": "lifegain", "counters": "counter_add",
        "draw": "draw", "damage": "damage", "turn_phase_budget": "extra_turn",
    }
    for p in provides:
        ev = econ_to_event.get(p["economy"])
        if ev:
            events.add(ev)
    # Direct textual cues the features may not have surfaced.
    cues = {
        r"\benters\b": "etb", r"\bdies\b": "dies",
        r"leaves the battlefield": "ltb", r"\bsacrifices?\b": "sacrifice",
        r"\bexiles?\b": "exile", r"\btapped\b": "tap", r"\buntaps?\b": "untap",
        r"\battacks?\b": "attack", r"\bdiscards?\b": "discard",
    }
    for pat, ev in cues.items():
        if re.search(pat, text, re.I):
            events.add(ev)
    return sorted(events)


def extract_costs(card: dict, faces: list) -> dict:
    mana_cost = card.get("mana_cost") or (faces[0]["mana_cost"] if faces else "")
    costs = {
        "mana_cost": mana_cost,
        "mana_value": card.get("cmc"),
        "activated": [],
    }
    seen = set()
    for face in faces:
        for raw_line in face["oracle_text"].split("\n"):
            line = _REMINDER_RE.sub("", raw_line).strip()
            if ":" not in line:
                continue
            prefix = line.split(":", 1)[0].strip()
            # Costs are short and contain a cost token; skip "Choose one" etc.
            if len(prefix) > 60 or not _COST_TOKEN_RE.search(prefix):
                continue
            key = prefix.lower()
            if key in seen:
                continue
            seen.add(key)
            costs["activated"].append({
                "cost": truncate(prefix, 80),
                "provenance": PROV_DETERMINISTIC,
            })
    return costs


def extract_guards(text: str, ontology: dict) -> list:
    out = []
    for g in ontology["guards"]:
        for pat in g["_patterns"]:
            if pat.search(text):
                out.append({"guard": g["id"], "provenance": PROV_DETERMINISTIC})
                break
    return out


def is_vanilla(card: dict, combined_text: str) -> bool:
    """Cards that legitimately need no LLM enrichment: basic lands and effectively
    text-free permanents (vanilla creatures, plain-adding mana rocks the patterns
    already caught)."""
    tl = (card.get("type_line") or "").lower()
    if "basic" in tl and "land" in tl:
        return True
    stripped = _REMINDER_RE.sub("", combined_text).strip()
    return len(stripped) < 15


def build_entry(card: dict, ontology: dict, corpus_version: str) -> dict:
    faces = card_faces(card)
    combined = "\n".join(f["oracle_text"] for f in faces)
    norm = normalise_numbers(combined)

    provides, wants, ambient = extract_features(combined, norm, ontology)
    triggers = extract_triggers(combined)
    events = extract_events(combined, provides)
    costs = extract_costs(card, faces)
    guards = extract_guards(combined, ontology)

    field_prov = {}
    for name, val in [("provides", provides), ("wants", wants),
                      ("ambient", ambient), ("triggers", triggers),
                      ("guards", guards)]:
        if val:
            field_prov[name] = PROV_DETERMINISTIC
    if events:
        field_prov["events_emitted"] = PROV_DETERMINISTIC
    field_prov["costs"] = PROV_DETERMINISTIC  # structural: always deterministic

    has_signal = bool(provides or wants or ambient or triggers)
    needs_llm = (not has_signal) and (not is_vanilla(card, combined))

    entry = {
        "oracle_id": card.get("oracle_id"),
        "name": card.get("name"),
        "type_line": card.get("type_line"),
        "mana_cost": card.get("mana_cost"),
        "cmc": card.get("cmc"),
        "color_identity": card.get("color_identity") or [],
        "is_dfc": bool(card.get("card_faces")),
        "provides": provides,
        "wants": wants,
        "ambient": ambient,
        "events_emitted": events,
        "triggers": triggers,
        "costs": costs,
        "guards": guards,
        "field_provenance": field_prov,
        "needs_llm": needs_llm,
        "ontology_version": ontology["version"],
        "extractor_version": EXTRACTOR_VERSION,
        "corpus_version": corpus_version,
    }
    entry["provenance_summary"] = provenance_summary(entry)
    return entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="cap number of cards (smoke runs)")
    ap.add_argument("--names-file", type=Path, default=None,
                    help="only build entries for card names in this file (one per line)")
    args = ap.parse_args()

    if not MIRROR_FILE.exists():
        print(f"ERROR: mirror missing at {MIRROR_FILE}. Run refresh_scryfall_mirror.py.",
              file=sys.stderr)
        return 1

    ontology = load_ontology()
    corpus_version = ""
    if MIRROR_META.exists():
        meta_src = json.loads(MIRROR_META.read_text())
        corpus_version = (meta_src.get("scryfall_updated_at")
                          or meta_src.get("downloaded_at") or "")

    cards = json.loads(MIRROR_FILE.read_text(encoding="utf-8"))
    name_filter = None
    if args.names_file:
        name_filter = {n.strip() for n in args.names_file.read_text().splitlines() if n.strip()}

    shards: dict[str, list] = defaultdict(list)
    prov_hist = Counter()
    feature_hist = Counter()
    n_needs_llm = 0
    n = 0
    for card in cards:
        if not card.get("oracle_id"):
            continue
        if name_filter is not None and card.get("name") not in name_filter \
                and card.get("name", "").split(" // ")[0] not in name_filter:
            continue
        entry = build_entry(card, ontology, corpus_version)
        shard = (entry["oracle_id"] or "00")[:2]
        shards[shard].append(entry)
        for p, c in entry["provenance_summary"].items():
            prov_hist[p] += c
        for it in entry["provides"] + entry["wants"] + entry["ambient"]:
            feature_hist[it["feature"]] += 1
        n_needs_llm += int(entry["needs_llm"])
        n += 1
        if args.limit and n >= args.limit:
            break

    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    # Clean stale shards on a full build so removed cards don't linger.
    if name_filter is None and not args.limit:
        for old in ENTRIES_DIR.glob("*.json"):
            old.unlink()
    for shard, entries in shards.items():
        entries.sort(key=lambda e: e["oracle_id"])
        path = ENTRIES_DIR / f"{shard}.json"
        path.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    meta = {
        "schema": "combo-kb-meta",
        "ontology_version": ontology["version"],
        "extractor_version": EXTRACTOR_VERSION,
        "corpus_version": corpus_version,
        "card_count": n,
        "shard_count": len(shards),
        "needs_llm_count": n_needs_llm,
        "deterministic_signal_count": n - n_needs_llm,
        "provenance_histogram": dict(sorted(prov_hist.items())),
        "feature_histogram": dict(sorted(feature_hist.items(), key=lambda kv: -kv[1])),
        "note": "Deterministic extraction pass. needs_llm entries await the "
                "offline classifier (classify_combo_kb.py). Tier-B verdicts "
                "consume only deterministic/human-reviewed items (combo_kb_lib).",
    }
    META_FILE.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")

    print(f"Built {n} entries across {len(shards)} shards.")
    print(f"  deterministic signal: {n - n_needs_llm}  needs_llm: {n_needs_llm}")
    print(f"  provenance histogram: {dict(prov_hist)}")
    print(f"  top features: {dict(list(feature_hist.most_common(8)))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
