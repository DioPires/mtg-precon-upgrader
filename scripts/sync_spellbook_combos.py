#!/usr/bin/env python3
"""Sync the Commander Spellbook combo corpus and emit committed derivatives.

DEC-487 (DEC-476 Phase 0). The Grimoire's runtime never calls Commander
Spellbook; instead this script downloads the weekly bulk export locally and
emits plain-JSON derivatives that the static site serves and matches against
client-side.

Pipeline (all generation local, no Vercel build step depends on it):

  1. Download https://json.commanderspellbook.com/variants.json.gz into the
     gitignored priv_data/spellbook/ cache. Freshness follows the
     refresh_scryfall_mirror.py convention: compare the export's top-level
     `timestamp` against the stored spellbook.meta.json; skip the download when
     unchanged. Atomic tmp-write-then-replace. Schema access is defensive —
     validate expected fields, fail loud with a clear message.

  2. Emit derivatives (plain .json, stable key order so git packs delta-compress
     the weekly diff efficiently):
       - data/spellbook/matcher-index.json  — compact, normalized dictionaries;
         what paste mode matches against client-side.
       - data/commanders/{id}/spellbook-combos.json — precomputed included +
         near-miss combos with embedded details, one standalone file per deck
         (like metrics.json), so fleet mode is self-contained.
       - data/spellbook/details/{shard}.json — optional sharded full details for
         paste mode. Off by default (--emit-details); the script always measures
         and reports the would-be size so the plan's ~150 MB gate can be applied.

Matching model (Phase 0, deterministic, identical for local precompute and the
client): a variant is INCLUDED when the deck contains every `uses` card (by
normalized oracle name; a `mustBeCommander` use must be the deck's commander)
and the variant carries no template requirements. It is a Tier-A NEAR-MISS when
the number of unmet elements (missing cards + required templates) is 1 or 2.
Template requirements are surfaced as named missing capabilities rather than
auto-evaluated against the pool; full template evaluation is a later phase.

Usage:
    uv run python scripts/sync_spellbook_combos.py [--force] [--offline]
        [--emit-details] [--deck ID ...]
"""

import argparse
import gzip
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIV_DIR = PROJECT_ROOT / "priv_data" / "spellbook"
RAW_FILE = PRIV_DIR / "variants.json.gz"
META_FILE = PRIV_DIR / "spellbook.meta.json"
DATA_SPELLBOOK_DIR = PROJECT_ROOT / "data" / "spellbook"
MATCHER_INDEX_FILE = DATA_SPELLBOOK_DIR / "matcher-index.json"
DETAILS_DIR = DATA_SPELLBOOK_DIR / "details"
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"

VARIANTS_URL = "https://json.commanderspellbook.com/variants.json.gz"
COMBO_PERMALINK = "https://commanderspellbook.com/combo/{id}/"
USER_AGENT = "mtg-precon-upgrader/1.0 (DEC-487 Combo Lab sync; +https://archidekt.com/u/pirex)"

# Only human-verified, commander-legal, released variants become Tier-A facts.
KEEP_STATUS = {"OK"}

# Detail shards: bucket variants by a stable 2-hex-digit hash so shard
# membership is deterministic and the weekly diff stays local to changed shards.
DETAILS_SHARD_COUNT = 256

# Commander Spellbook's per-combo bracket tag (authoritative labels from the
# backend OpenAPI BracketTagEnum). Surfaced with attribution for BR-2 — this is
# Spellbook's classification, never Laço's own judgment.
BRACKET_TAG_LEGEND = {
    "E": "Exhibition",
    "C": "Core",
    "P": "Powerful",
    "O": "Oddball",
    "S": "Spicy",
    "R": "Ruthless",
    "B": "Banned",
}


class SchemaError(RuntimeError):
    """Raised when the upstream export shape is not what we expect."""


# ─── name normalization (shared contract with the TS client) ──────────────────

_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    """Casefold + strip accents/punctuation so oracle names compare stably.

    Mirrors normalizeName() in web/src/lib/spellbookMatch.ts — keep them in sync.
    """
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = ascii_only.casefold()
    stripped = _PUNCT_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", stripped).strip()


def name_keys(name: str) -> set[str]:
    """Normalized full name plus front-face key for split/DFC/adventure cards."""
    keys = {normalize_name(name)}
    if "//" in name:
        keys.add(normalize_name(name.split("//", 1)[0]))
    keys.discard("")
    return keys


# ─── download + freshness ─────────────────────────────────────────────────────

def download_corpus(force: bool) -> None:
    # The export's freshness lives inside the gz (top-level `timestamp`), and
    # Spellbook exposes no cheap metadata endpoint, so we always fetch the 27 MB
    # gz. The expensive work — regenerating + committing derivatives — is what the
    # freshness compare in main() actually short-circuits once the corpus
    # timestamp is unchanged.
    PRIV_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {VARIANTS_URL} ...", file=sys.stderr)
    req = urllib.request.Request(VARIANTS_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read()
    tmp = RAW_FILE.with_suffix(".gz.tmp")
    tmp.write_bytes(raw)
    tmp.replace(RAW_FILE)
    print(f"  cached {len(raw) / 1e6:.1f} MB gz", file=sys.stderr)


def read_corpus() -> tuple[str, str, "IterVariants"]:
    """Return (corpus_timestamp, spellbook_version, variant_iterator).

    Decompresses the cached gz into a single string, then hands out one variant
    object at a time via a brace scanner (IterVariants) so we never build the
    full 105 k-element parse tree — only one variant dict is live at once. The
    decompressed text itself (~630 MB) is held for the duration; this runs on the
    CEO's machine during the weekly sync, not on Vercel.
    """
    if not RAW_FILE.exists():
        raise SchemaError(
            f"{RAW_FILE.relative_to(PROJECT_ROOT)} missing — run without --offline first."
        )
    with gzip.open(RAW_FILE, "rt", encoding="utf-8") as fh:
        text = fh.read()
    header_end = text.find('"variants"')
    if header_end == -1:
        raise SchemaError("export has no top-level 'variants' key — API shape changed.")
    header = text[:header_end]
    ts_match = re.search(r'"timestamp"\s*:\s*"([^"]+)"', header)
    ver_match = re.search(r'"version"\s*:\s*"([^"]+)"', header)
    if not ts_match:
        raise SchemaError("export header has no 'timestamp' — cannot version the corpus.")
    corpus_ts = ts_match.group(1)
    version = ver_match.group(1) if ver_match else "unknown"
    return corpus_ts, version, IterVariants(text)


class IterVariants:
    """Yield each top-level object in the `variants: [...]` array via brace scan."""

    def __init__(self, text: str) -> None:
        self._text = text

    def __iter__(self):
        text = self._text
        start = text.index("[", text.index('"variants"')) + 1
        depth = 0
        in_str = False
        esc = False
        obj_start = None
        for j in range(start, len(text)):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                if depth == 0:
                    obj_start = j
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    yield json.loads(text[obj_start : j + 1])
            elif c == "]" and depth == 0:
                return


# ─── derivative extraction ────────────────────────────────────────────────────

def extract_variant(v: dict) -> dict | None:
    """Pull the fields we retain from one raw variant, or None to skip it."""
    if v.get("status") not in KEEP_STATUS:
        return None
    if v.get("spoiler"):
        return None
    if not v.get("legalities", {}).get("commander", False):
        return None

    uses = v.get("uses")
    if not isinstance(uses, list) or not uses:
        raise SchemaError(f"variant {v.get('id')!r} has no 'uses' list.")

    cards = []
    for use in uses:
        card = use.get("card") or {}
        cid = card.get("id")
        name = card.get("name")
        if cid is None or not name:
            raise SchemaError(f"variant {v.get('id')!r} use missing card id/name.")
        cards.append(
            {
                "id": cid,
                "name": name,
                "oracleId": card.get("oracleId", ""),
                "mustBeCommander": bool(use.get("mustBeCommander")),
                "quantity": use.get("quantity", 1),
                "zones": use.get("zoneLocations", []),
            }
        )

    templates = []
    for req in v.get("requires", []) or []:
        tpl = req.get("template") or {}
        tid = tpl.get("id")
        if tid is None:
            continue
        templates.append(
            {
                "id": tid,
                "name": tpl.get("name", "a required card"),
                "query": tpl.get("scryfallQuery", ""),
                "quantity": req.get("quantity", 1),
            }
        )

    produces = []
    for prod in v.get("produces", []) or []:
        feat = prod.get("feature") or {}
        fid = feat.get("id")
        if fid is None:
            continue
        produces.append({"id": fid, "name": feat.get("name", "")})

    return {
        "id": v["id"],
        "cards": cards,
        "templates": templates,
        "produces": produces,
        "identity": v.get("identity", ""),
        "bracketTag": v.get("bracketTag", ""),
        "manaNeeded": v.get("manaNeeded", ""),
        "manaValueNeeded": v.get("manaValueNeeded") or 0,
        "easyPrerequisites": v.get("easyPrerequisites", ""),
        "notablePrerequisites": v.get("notablePrerequisites", ""),
        "description": v.get("description", ""),
        "notes": v.get("notes", ""),
        "prices": v.get("prices") or {},
        "popularity": v.get("popularity") or 0,
    }


def shard_for(variant_id: str) -> str:
    """Deterministic 2-hex-digit shard key from the variant id."""
    h = 0
    for ch in variant_id:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return f"{h % DETAILS_SHARD_COUNT:02x}"


def build_matcher_variant(x: dict) -> dict:
    """Compact matcher-index row referencing the shared card/template/feature dicts."""
    return {
        "id": x["id"],
        "u": [c["id"] for c in x["cards"]],
        "c": [c["id"] for c in x["cards"] if c["mustBeCommander"]],
        "r": [t["id"] for t in x["templates"]],
        "p": [p["id"] for p in x["produces"]],
        "i": x["identity"],
        "b": x["bracketTag"],
        "m": x["manaValueNeeded"],
        "pop": x["popularity"],
    }


def build_detail(x: dict) -> dict:
    """Full, self-contained combo detail record for per-deck files and shards."""
    return {
        "id": x["id"],
        "permalink": COMBO_PERMALINK.format(id=x["id"]),
        "cards": [
            {
                "name": c["name"],
                "mustBeCommander": c["mustBeCommander"],
                "quantity": c["quantity"],
                "zones": c["zones"],
            }
            for c in x["cards"]
        ],
        "templates": [{"name": t["name"], "query": t["query"], "quantity": t["quantity"]} for t in x["templates"]],
        "produces": [p["name"] for p in x["produces"] if p["name"]],
        "identity": x["identity"],
        "bracketTag": x["bracketTag"],
        "manaNeeded": x["manaNeeded"],
        "manaValueNeeded": x["manaValueNeeded"],
        "prerequisites": {"easy": x["easyPrerequisites"], "notable": x["notablePrerequisites"]},
        "steps": x["description"],
        "notes": x["notes"],
        "prices": x["prices"],
        "popularity": x["popularity"],
    }


# ─── per-deck matching ────────────────────────────────────────────────────────

def deck_card_keys(deck: dict) -> tuple[set[str], set[str]]:
    """Return (all-card keys, commander keys) as normalized name sets."""
    all_keys: set[str] = set()
    for entry in deck.get("decklist", []) or []:
        all_keys |= name_keys(entry.get("name", ""))
    commander_keys: set[str] = set()
    for field in ("commander", "partner", "background"):
        val = deck.get(field)
        if val:
            commander_keys |= name_keys(val)
    # Commanders are castable from the command zone; count them among all cards.
    all_keys |= commander_keys
    return all_keys, commander_keys


# A Tier-A near-miss must be meaningfully close, not candidate soup (PRD DC-4):
# the deck already runs at least as many of the combo's pieces as it is missing
# ("at least halfway"), and — for near-misses only — the combo has real play
# (Spellbook popularity ≥ this floor). Included combos are facts regardless of
# popularity, so the floor never applies to them. Ranked by popularity and
# capped per deck; the true total is recorded so nothing is silently dropped.
NEAR_MISS_POPULARITY_FLOOR = 1
NEAR_MISS_PER_DECK_CAP = 120


def match_variant(x: dict, all_keys: set[str], commander_keys: set[str]) -> dict | None:
    """Classify one variant against a deck. Returns None when it is neither
    included nor a qualifying Tier-A near-miss."""
    missing_cards: list[str] = []
    present_cards = 0
    for c in x["cards"]:
        keys = name_keys(c["name"])
        if c["mustBeCommander"]:
            satisfied = bool(keys & commander_keys)
        else:
            satisfied = bool(keys & all_keys)
        if satisfied:
            present_cards += 1
        else:
            missing_cards.append(c["name"])

    templates = x["templates"]
    unmet = len(missing_cards) + len(templates)

    if unmet == 0:
        detail = build_detail(x)
        detail["distance"] = 0
        return {"kind": "included", "detail": detail}

    # Near-miss gate: 1-2 unmet, at least one piece present, deck at least
    # halfway there, and the combo has real play.
    if not (1 <= unmet <= 2):
        return None
    if present_cards < 1 or present_cards < unmet:
        return None
    if x["popularity"] < NEAR_MISS_POPULARITY_FLOOR:
        return None

    detail = build_detail(x)
    detail["distance"] = unmet
    detail["missing"] = {
        "cards": missing_cards,
        "templates": [{"name": t["name"], "query": t["query"]} for t in templates],
    }
    return {"kind": "near", "detail": detail}


# ─── writers ──────────────────────────────────────────────────────────────────

def write_json(path: Path, obj: dict, compact: bool = False) -> int:
    """Atomic write with stable key order. Returns bytes written.

    `sort_keys` (not pretty-printing) is what makes the weekly git diff
    delta-compress — git packs xdelta at the byte level, so the large matcher
    index is written compact to halve its committed footprint with no delta
    downside. Small per-deck files stay indented for reviewability.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    else:
        payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)
    return len(payload.encode("utf-8"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Sync Commander Spellbook combo corpus")
    parser.add_argument("--force", action="store_true", help="Re-download + regenerate even if current")
    parser.add_argument("--offline", action="store_true", help="Use the cached gz; do not download")
    parser.add_argument("--emit-details", action="store_true", help="Write data/spellbook/details/ shards")
    parser.add_argument("--deck", action="append", default=[], help="Limit per-deck files to these ids (repeatable)")
    args = parser.parse_args(argv)

    if not args.offline:
        download_corpus(args.force)
    elif not RAW_FILE.exists():
        print(f"ERROR: {RAW_FILE} absent and --offline set.", file=sys.stderr)
        return 1

    corpus_ts, version, variants = read_corpus()

    prev_ts = None
    if META_FILE.exists():
        try:
            prev_ts = json.loads(META_FILE.read_text()).get("corpus_timestamp")
        except (json.JSONDecodeError, OSError):
            pass
    # The freshness short-circuit only applies to a full-fleet default run. A
    # targeted `--deck` regen is intentional hygiene after a decklist change
    # (the deck's own combos depend on its list, not just the corpus), so it must
    # always rebuild — otherwise the deck's spellbook-combos.json is silently
    # left stale. --force also always rebuilds.
    if (
        prev_ts == corpus_ts
        and MATCHER_INDEX_FILE.exists()
        and not args.force
        and not args.deck
    ):
        print(f"Corpus current ({corpus_ts}); derivatives up to date. Use --force to rebuild.", file=sys.stderr)
        return 0

    print(f"Extracting variants (corpus {corpus_ts}, spellbook v{version}) ...", file=sys.stderr)
    extracted: list[dict] = []
    seen_status: dict[str, int] = {}
    bracket_tags: dict[str, int] = {}
    scanned = 0
    for raw_v in variants:
        scanned += 1
        seen_status[raw_v.get("status", "?")] = seen_status.get(raw_v.get("status", "?"), 0) + 1
        x = extract_variant(raw_v)
        if x is None:
            continue
        bracket_tags[x["bracketTag"] or "?"] = bracket_tags.get(x["bracketTag"] or "?", 0) + 1
        extracted.append(x)

    if scanned < 1000:
        raise SchemaError(f"only {scanned} variants scanned — export looks truncated.")
    print(
        f"  scanned {scanned:,}; kept {len(extracted):,} (status {seen_status}); "
        f"bracket tags {bracket_tags}",
        file=sys.stderr,
    )

    # 1. Matcher index (compact, dictionaries + rows).
    card_dict: dict[str, dict] = {}
    template_dict: dict[str, dict] = {}
    feature_dict: dict[str, str] = {}
    for x in extracted:
        for c in x["cards"]:
            card_dict.setdefault(str(c["id"]), {"n": c["name"], "o": c["oracleId"]})
        for t in x["templates"]:
            template_dict.setdefault(str(t["id"]), {"n": t["name"], "q": t["query"]})
        for p in x["produces"]:
            if p["name"]:
                feature_dict.setdefault(str(p["id"]), p["name"])

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    matcher_index = {
        "meta": {
            "source": "commanderspellbook",
            "sourceUrl": "https://commanderspellbook.com",
            "corpusVersion": corpus_ts,
            "spellbookApiVersion": version,
            "generatedAt": generated_at,
            "variantCount": len(extracted),
            "cardCount": len(card_dict),
            "matchingModel": "phase0-card-set-containment",
            "bracketTagLegend": BRACKET_TAG_LEGEND,
        },
        "cards": card_dict,
        "templates": template_dict,
        "features": feature_dict,
        "variants": [build_matcher_variant(x) for x in extracted],
    }
    size = write_json(MATCHER_INDEX_FILE, matcher_index, compact=True)
    # Tiny sidecar so the client can read the corpus version (DR-7 indicator +
    # ?v= cache-buster) without downloading the 12+ MB index first.
    write_json(MATCHER_INDEX_FILE.with_name("matcher-index.meta.json"), matcher_index["meta"])
    print(
        f"  wrote {MATCHER_INDEX_FILE.relative_to(PROJECT_ROOT)} ({size / 1e6:.1f} MB, "
        f"{len(card_dict):,} cards) + matcher-index.meta.json",
        file=sys.stderr,
    )

    # 2. Per-deck spellbook-combos.json.
    deck_ids = args.deck or sorted(p.name for p in COMMANDERS_DIR.iterdir() if (p / "deck.json").exists())
    deck_report = []
    for deck_id in deck_ids:
        deck_path = COMMANDERS_DIR / deck_id / "deck.json"
        if not deck_path.exists():
            print(f"  WARN: {deck_id} has no deck.json; skipping.", file=sys.stderr)
            continue
        deck = json.loads(deck_path.read_text())
        all_keys, commander_keys = deck_card_keys(deck)
        included, near = [], []
        for x in extracted:
            m = match_variant(x, all_keys, commander_keys)
            if m is None:
                continue
            (included if m["kind"] == "included" else near).append(m["detail"])
        included.sort(key=lambda d: (-d["popularity"], d["id"]))
        near.sort(key=lambda d: (d["distance"], -d["popularity"], d["id"]))
        near_total = len(near)
        near_capped = near[:NEAR_MISS_PER_DECK_CAP]
        commanders = [c for c in (deck.get("commander"), deck.get("partner"), deck.get("background")) if c]
        out = {
            "meta": {
                "deckId": deck_id,
                "source": "commanderspellbook",
                "corpusVersion": corpus_ts,
                "generatedAt": generated_at,
                "matchingModel": "phase0-card-set-containment",
                "nearMissCap": NEAR_MISS_PER_DECK_CAP,
                "nearMissPopularityFloor": NEAR_MISS_POPULARITY_FLOOR,
                "templateCaveat": (
                    "Template requirements (e.g. 'a sacrifice outlet') are reported as named "
                    "missing capabilities, not auto-matched against the pool; full template "
                    "evaluation is a later phase."
                ),
            },
            "commander": commanders,
            "counts": {
                "included": len(included),
                "nearMisses": len(near_capped),
                "nearMissesTotal": near_total,
            },
            "included": included,
            "nearMisses": near_capped,
        }
        write_json(COMMANDERS_DIR / deck_id / "spellbook-combos.json", out)
        deck_report.append((deck_id, len(included), len(near_capped), near_total))

    print("  per-deck combos (included / near-miss kept / near-miss total):", file=sys.stderr)
    for deck_id, inc, nm, nm_total in deck_report:
        print(f"    {deck_id:32s} {inc:4d} / {nm:4d} / {nm_total:5d}", file=sys.stderr)

    # 3. Detail shards — measure always; write only with --emit-details.
    shards: dict[str, list[dict]] = {}
    for x in extracted:
        shards.setdefault(shard_for(x["id"]), []).append(build_detail(x))
    est_bytes = 0
    for key, rows in shards.items():
        est_bytes += len(json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8"))
    print(
        f"  details tree: {len(shards)} shards, ~{est_bytes / 1e6:.0f} MB "
        f"({'WRITTEN' if args.emit_details else 'measured only — not committed'})",
        file=sys.stderr,
    )
    if args.emit_details:
        if DETAILS_DIR.exists():
            for old in DETAILS_DIR.glob("*.json"):
                old.unlink()
        for key, rows in sorted(shards.items()):
            rows.sort(key=lambda d: d["id"])
            write_json(DETAILS_DIR / f"{key}.json", {"variants": rows})

    META_FILE.write_text(
        json.dumps(
            {
                "corpus_timestamp": corpus_ts,
                "spellbook_version": version,
                "downloaded_at": generated_at,
                "variant_count": len(extracted),
                "card_count": len(card_dict),
                "details_estimated_mb": round(est_bytes / 1e6, 1),
                "source": VARIANTS_URL,
            },
            indent=2,
        )
    )
    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SchemaError as exc:
        print(f"SCHEMA ERROR: {exc}", file=sys.stderr)
        print("Corpus left unchanged (degrade to 'corpus stale').", file=sys.stderr)
        sys.exit(2)
