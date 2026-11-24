#!/usr/bin/env python3
"""Sync the Commander Spellbook combo corpus and emit committed derivatives.

DEC-487 (DEC-476 Phase 0). The Grimoire's runtime never calls Commander
Spellbook; instead this script downloads the weekly bulk export locally and
emits plain-JSON derivatives that the static site serves and matches against
client-side.

Pipeline (all generation local, no Vercel build step depends on it):

  1. Download https://json.commanderspellbook.com/variants.json.gz to a
     temporary file of this run's own in the gitignored priv_data/spellbook/
     cache folder and read it as the corpus (a readable gzip holding one JSON
     object, read strictly, whose "variants" list holds objects of the expected
     shape, at least 1000 scanned and kept, and every string the run reads,
     the version included, can be written as UTF-8; a lone surrogate from a
     JSON escape such as \\ud800 cannot). Freshness follows the
     refresh_scryfall_mirror.py convention: compare the export's top-level
     `timestamp`, wherever it sits, against the stored spellbook.meta.json.
     The export's timestamp must have the form the real export uses, as in
     2026-10-20T15:16:11.894774+00:00: YYYY-MM-DDTHH:MM:SS in ASCII digits
     (HH 00 to 23, MM and SS 00 to 59), an optional fraction of 1 to 6 digits,
     then Z or an offset ±HH:MM (HH 00 to 23, MM 00 to 59), naming a real date
     and time (else a schema error).
     Each file is trusted for the corpus it records: the meta file's
     corpus_timestamp (the corpus of the last run that wrote it), and for the
     derivative files the matcher index's meta.corpusVersion, its sidecar's
     (matcher-index.meta.json) corpusVersion and each deck's
     spellbook-combos.json meta.corpusVersion. A record is a timestamp of that
     form read from a file that is strict JSON; a file that is missing or
     cannot be read, or a value of any other form, records none.
       - No run moves a derivative file to an older corpus: when a derivative
         file records a later instant than the run's export, the run names the
         newer files and exits 1 before the cache, the meta file or any
         derivative file changes (with an older cached export, run without
         --offline to download the newest).
       - A download byte-identical to the cached export (or an --offline run),
         with no --force or --deck, changes nothing when the meta file and
         every derivative file record the export's corpus: it is dropped,
         unscanned when the timestamp precedes the variants list. Any other run
         rebuilds the derivatives (a download that differs from the cache
         replaces it after the scan).
       - The meta file is removed once, before the cache is replaced and the
         rebuild starts, and written again at the rebuild's end, so after a run
         that stops part-way the next run rebuilds every deck if it has no
         --deck.
       - A --deck run rebuilds the matcher index and its own decks only (a
         --deck value must be a deck folder's name exactly; any other is warned
         about and skipped), writes the meta file, and ends by naming every
         other deck whose file does not record its corpus, with the commands
         that rebuild them (printed only when a deck is named; otherwise one line
         says every deck is on the corpus). One exception is a --deck run that
         installed its download while the meta file named the same corpus
         timestamp: it could not match the export it installed to the cached one
         (missing, unreadable or other bytes), so it cannot tell which other deck
         files were built from the one it installed. It names every deck it did
         not rebuild ("matching timestamp, export unverified" when its file
         records that timestamp) and writes no meta file, so the next run
         rebuilds every deck if it has no --deck; one that rebuilt every deck
         writes it.
     The limit that remains: files are identified by the corpus timestamp they
     record, so a file restored from, or an export replaced by, other bytes
     under an unchanged timestamp outside a run of this script is not
     detected; nor, when a --deck run starts without a meta file (a new tree,
     or one whose last run stopped part-way or withheld the meta file), are
     deck files built from an earlier export with the same timestamp: it
     trusts each file's timestamp and writes the meta file. The meta file must
     be this checkout's own: a worktree links only
     variants.json.gz. Schema access is defensive —
     validate expected fields, fail loud with a clear message. On the export of
     2026-10-20 (30.6 MB gz, 693 M characters, 115,439 variants) a full run
     over the 21 decks takes about 16 s and peaks at about 2 GB of memory
     (measured 2026-11-24).

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
         A run with the flag removes the old shards before it writes the new
         ones: if it stops part-way, the next run without the flag finishes the
         rebuild but leaves the shards incomplete, and --offline --force
         --emit-details writes them all again.

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
import filecmp
import gzip
import json
import os
import re
import sys
import tempfile
import unicodedata
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIV_DIR = PROJECT_ROOT / "priv_data" / "spellbook"
RAW_FILE = PRIV_DIR / "variants.json.gz"
META_FILE = PRIV_DIR / "spellbook.meta.json"
DATA_SPELLBOOK_DIR = PROJECT_ROOT / "data" / "spellbook"
MATCHER_INDEX_FILE = DATA_SPELLBOOK_DIR / "matcher-index.json"
MATCHER_META_FILE = DATA_SPELLBOOK_DIR / "matcher-index.meta.json"
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

def download_corpus() -> Path:
    """Download the export to a temporary file of this run's own beside RAW_FILE and
    return its path; the file is removed if the write fails.

    main() reads that file as the corpus, moves it over RAW_FILE only when its
    bytes differ from the cached export and the scan passes, and removes it on
    every other way out.
    """
    # The export's freshness lives inside the gz (top-level `timestamp`), and
    # Spellbook exposes no cheap metadata endpoint, so we always fetch the gz
    # (30.6 MB on 2026-10-20). The expensive work — regenerating + committing
    # derivatives — is what the freshness check in main() skips: only when the
    # download is byte-identical to the cached export, and the meta file, the matcher
    # index, its sidecar and every deck's file record its timestamp.
    PRIV_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {VARIANTS_URL} ...", file=sys.stderr)
    req = urllib.request.Request(VARIANTS_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read()
    # A name of this run's own, so runs at once neither publish nor remove each other's.
    fd, tmp = tempfile.mkstemp(dir=RAW_FILE.parent, prefix=RAW_FILE.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        print(f"  downloaded {len(raw) / 1e6:.1f} MB gz", file=sys.stderr)
    except BaseException:
        os.unlink(tmp)
        raise
    return Path(tmp)


def same_bytes(cached: Path, download: Path) -> bool:
    """True when the cached export holds the download's bytes. A cached file that is
    missing or cannot be read counts as different, so the download can replace it."""
    try:
        return filecmp.cmp(cached, download, shallow=False)
    except OSError:
        return False


def read_corpus(path: Path) -> "IterVariants":
    """The export at ``path`` (the cached export, or a download not yet in its place),
    ready to hand out its variants.

    Decompresses the gz into a single string and reads it strictly as one JSON
    object: the members before "variants" here, then (IterVariants) the variants
    one object at a time, the members after the list and the closing brace. Only
    one variant dict is live at once. The decompressed text itself (~690 MB) is
    held for the duration; this runs on the owner's machine, not on Vercel.
    """
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            text = fh.read()
    except (gzip.BadGzipFile, EOFError, zlib.error, UnicodeDecodeError) as exc:
        what = RAW_FILE.name if path == RAW_FILE else "the download"
        raise SchemaError(f"{what} is not a readable gzip export: {exc}") from exc
    return IterVariants(text)


def corpus_id(header: dict) -> tuple[str | None, str | None]:
    """The export's "timestamp" and "version" among the top-level members read so far, or
    None for one not read yet (it may sit after the variants list)."""
    timestamp, version = header.get("timestamp"), header.get("version")
    return (timestamp if isinstance(timestamp, str) and timestamp else None,
            version if isinstance(version, str) and version else None)


def _refuse_constant(name: str) -> None:
    raise SchemaError(f"the export holds {name}, which is not a JSON number.")


_DECODER = json.JSONDecoder(parse_constant=_refuse_constant)
_WHITESPACE = re.compile(r"[ \t\n\r]*")


def _skip(text: str, idx: int) -> int:
    """The index of the first character at or after ``idx`` that is not JSON whitespace."""
    return _WHITESPACE.match(text, idx).end()


def _value(text: str, idx: int) -> tuple[object, int]:
    """The JSON value that starts at ``idx`` and the index after it."""
    try:
        return _DECODER.raw_decode(text, idx)
    except json.JSONDecodeError as exc:
        if exc.pos >= len(text):
            raise SchemaError(f"the export is cut off (character {exc.pos}).") from exc
        raise SchemaError(f"the export is not valid JSON: {exc}") from exc


class IterVariants:
    """Read the export strictly as one JSON object. On construction: its members up to
    "variants" (kept in ``header``) and the list's opening bracket. On iteration: each
    variant object, then the members after the list (added to ``header``), the closing
    brace and nothing else.

    Raises SchemaError on anything else: no "variants" member, a "variants" that is not a
    list, an entry that is not an object, invalid JSON, text cut off or text after the end.
    """

    def __init__(self, text: str) -> None:
        self._text = text
        self.header: dict = {}
        idx = _skip(text, 0)
        if text[idx : idx + 1] != "{":
            raise SchemaError("the export is not a JSON object.")
        idx = _skip(text, idx + 1)
        more = text[idx : idx + 1] != "}"
        while more:
            key, idx = self._member_name(idx)
            if key == "variants":
                if text[idx : idx + 1] != "[":
                    raise SchemaError("the top-level 'variants' key is not followed by a list — API shape changed.")
                self._start = idx + 1
                return
            self.header[key], idx = _value(text, idx)
            more, idx = self._after_member(idx)
        raise SchemaError("export has no top-level 'variants' key — API shape changed.")

    def _member_name(self, idx: int) -> tuple[str, int]:
        """The member name at ``idx`` and the index of its value."""
        key, idx = _value(self._text, idx)
        idx = _skip(self._text, idx)
        if not isinstance(key, str) or self._text[idx : idx + 1] != ":":
            raise SchemaError(f"the export is not valid JSON: no member name at character {idx}.")
        return key, _skip(self._text, idx + 1)

    def _after_member(self, idx: int) -> tuple[bool, int]:
        """After a member: (True, the next member's index) past a ``,``, or (False, the index
        after it) past the closing ``}``."""
        idx = _skip(self._text, idx)
        c = self._text[idx : idx + 1]
        if c == ",":
            return True, _skip(self._text, idx + 1)
        if c == "}":
            return False, idx + 1
        if not c:
            raise SchemaError(f"the export is cut off (character {idx}).")
        raise SchemaError(f"the export is not valid JSON: expected ',' or '}}' at character {idx}.")

    def __iter__(self):
        text = self._text
        idx = _skip(text, self._start)
        entry = 0
        if text[idx : idx + 1] == "]":
            idx += 1
        else:
            while True:
                entry += 1
                variant, idx = _value(text, idx)
                if not isinstance(variant, dict):
                    raise SchemaError(f"entry {entry} of the variants list is not an object.")
                yield variant
                idx = _skip(text, idx)
                c = text[idx : idx + 1]
                if c == "]":
                    idx += 1
                    break
                if c != ",":
                    if not c:
                        raise SchemaError(f"the export is cut off (character {idx}).")
                    raise SchemaError(f"the export is not valid JSON: expected ',' or ']' at character {idx}.")
                idx = _skip(text, idx + 1)
        more, idx = self._after_member(idx)
        while more:
            key, idx = self._member_name(idx)
            self.header[key], idx = _value(text, idx)
            more, idx = self._after_member(idx)
        idx = _skip(text, idx)
        if idx != len(text):
            raise SchemaError(f"the export has text after its closing brace (character {idx}).")


# ─── derivative extraction ────────────────────────────────────────────────────

def extract_variant(v: dict) -> dict | None:
    """Pull the fields we retain from one raw variant, or None to skip it.

    Raises SchemaError, naming the variant, when a field this run reads is missing or
    has another type than in the real export: every field below is present on every
    variant there, null only where noted. A default would let a reshaped export
    change which combos match; a wrong type would stop the run later in a traceback
    or put a value into the derivative files that a browser cannot read. A string it reads
    that cannot be written as UTF-8 is refused too: kept, it would stop the run while it
    writes the derivative files, after the cache was replaced.
    """
    def need(obj: dict, key: str, ok, problem: str):
        """obj[key], present and accepted by ``ok``. A value refused for holding a string that
        cannot be written as UTF-8 is named as such."""
        if key in obj and ok(obj[key]):
            return obj[key]
        if key in obj and _unwritable(obj[key]):
            problem = f"has text that cannot be written as UTF-8 (a lone surrogate) in {key!r}"
        raise SchemaError(f"variant {v.get('id')!r} {problem}.")

    status = need(v, "status", _is_str, "has no string 'status'")
    if status not in KEEP_STATUS:
        return None
    if need(v, "spoiler", _is_bool, "has no boolean 'spoiler'"):
        return None
    legalities = need(v, "legalities", _is_dict, "has no 'legalities' object")
    if not need(legalities, "commander", _is_bool, "has no boolean commander legality"):
        return None

    variant_id = need(v, "id", lambda x: _is_str(x) and x != "", "has no string 'id'")
    uses = need(v, "uses", lambda x: _is_list_of(x, dict) and x != [], "has no 'uses' list of objects")
    raw_requires = need(v, "requires", lambda x: _is_list_of(x, dict), "has no 'requires' list of objects")
    raw_produces = need(v, "produces", lambda x: _is_list_of(x, dict), "has no 'produces' list of objects")
    texts = {key: need(v, key, _is_str, f"has no string '{key}'") for key in (
        "identity", "bracketTag", "manaNeeded", "easyPrerequisites", "notablePrerequisites",
        "description", "notes")}
    mana_value = need(v, "manaValueNeeded", _is_int, "has no integer 'manaValueNeeded'")
    prices = need(v, "prices",
                  lambda x: _is_dict(x) and all(_is_str(k) and _is_str(p) for k, p in x.items()),
                  "has no 'prices' object of strings")
    # Null on 36 variants of the real export.
    popularity = need(v, "popularity", lambda x: x is None or _is_int(x),
                      "has no integer or null 'popularity'")

    cards = []
    for use in uses:
        card = need(use, "card", _is_dict, "has a use with no 'card' object")
        cards.append(
            {
                "id": need(card, "id", _is_int, "has a use whose card has no integer 'id'"),
                "name": need(card, "name", lambda x: _is_str(x) and x != "",
                             "has a use whose card has no 'name'"),
                "oracleId": need(card, "oracleId", _is_str, "has a use whose card has no string 'oracleId'"),
                "mustBeCommander": need(use, "mustBeCommander", _is_bool,
                                        "has a use with no boolean 'mustBeCommander'"),
                "quantity": need(use, "quantity", _is_int, "has a use with no whole-number 'quantity'"),
                "zones": need(use, "zoneLocations", lambda x: isinstance(x, list) and all(map(_is_str, x)),
                              "has a use with no 'zoneLocations' list of strings"),
            }
        )

    templates = []
    for req in raw_requires:
        tpl = need(req, "template", _is_dict, "has a 'requires' entry with no 'template' object")
        templates.append(
            {
                "id": need(tpl, "id", _is_int, "has a template with no integer 'id'"),
                "name": need(tpl, "name", _is_str, "has a template with no string 'name'"),
                # Null on 1,279 templates of the real export.
                "query": need(tpl, "scryfallQuery", lambda x: x is None or _is_str(x),
                              "has a template with no string or null 'scryfallQuery'"),
                "quantity": need(req, "quantity", _is_int,
                                 "has a 'requires' entry with no whole-number 'quantity'"),
            }
        )

    produces = []
    for prod in raw_produces:
        feat = need(prod, "feature", _is_dict, "has a 'produces' entry with no 'feature' object")
        produces.append(
            {
                "id": need(feat, "id", _is_int, "has a feature with no integer 'id'"),
                "name": need(feat, "name", _is_str, "has a feature with no string 'name'"),
            }
        )

    return {
        "id": variant_id,
        "cards": cards,
        "templates": templates,
        "produces": produces,
        **texts,
        "manaValueNeeded": mana_value,
        "prices": prices,
        "popularity": popularity or 0,
    }


def _is_str(value: object) -> bool:
    """A string the run can write: ASCII (checked in constant time, the common case) or one
    that encodes as UTF-8."""
    return isinstance(value, str) and (value.isascii() or not _unwritable(value))


def _unwritable(value: object) -> bool:
    """True when ``value`` is a string, a list of strings or an object of string keys and
    values, the shapes of the strings the run reads, and one of those strings cannot be encoded
    as UTF-8: a lone surrogate, which a JSON escape such as \\ud800 gives. Any other value is
    False, so need() gives its shape message; nothing nested is searched, so no depth makes
    this check raise RecursionError."""
    if isinstance(value, str):
        strings = [value]
    elif isinstance(value, list):
        strings = value
    elif isinstance(value, dict):
        strings = [*value, *value.values()]
    else:
        return False
    if not all(isinstance(text, str) for text in strings):
        return False
    for text in strings:
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            return True
    return False


def _is_bool(value: object) -> bool:
    return isinstance(value, bool)


def _is_dict(value: object) -> bool:
    return isinstance(value, dict)


def _is_int(value: object) -> bool:
    """An integer, not a bool. Every number this run writes is one, so a float (1.5, or
    1e400, which reads as infinity) is refused with the rest."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_list_of(value: object, kind: type) -> bool:
    return isinstance(value, list) and all(isinstance(item, kind) for item in value)


def scan_variants(variants: "IterVariants") -> list[dict]:
    """Extract every variant; raise SchemaError unless at least 1000 are scanned and kept."""
    extracted: list[dict] = []
    seen_status: dict[str, int] = {}
    bracket_tags: dict[str, int] = {}
    scanned = 0
    for raw_v in variants:
        scanned += 1
        try:
            x = extract_variant(raw_v)
        except SchemaError as exc:
            raise SchemaError(f"{str(exc).rstrip('.')} (position {scanned} in the variants list).") from None
        seen_status[raw_v.get("status", "?")] = seen_status.get(raw_v.get("status", "?"), 0) + 1
        if x is None:
            continue
        bracket_tags[x["bracketTag"] or "?"] = bracket_tags.get(x["bracketTag"] or "?", 0) + 1
        extracted.append(x)

    if scanned < 1000:
        raise SchemaError(f"only {scanned} variants scanned — export looks truncated.")
    if len(extracted) < 1000:
        raise SchemaError(
            f"only {len(extracted)} of {scanned} variants kept — the status or legality fields look changed."
        )
    print(
        f"  scanned {scanned:,}; kept {len(extracted):,} (status {seen_status}); "
        f"bracket tags {bracket_tags}",
        file=sys.stderr,
    )
    return extracted


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


# ─── the fleet and the corpus each file records ───────────────────────────────

def deck_folders() -> list[str]:
    """The decks: each folder under data/commanders/ that holds a deck.json, by its name."""
    return sorted(p.name for p in COMMANDERS_DIR.iterdir() if (p / "deck.json").exists())


def deck_file(deck_id: str) -> Path:
    return COMMANDERS_DIR / deck_id / "spellbook-combos.json"


_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?"
    r"(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])")


def instant(value: object) -> datetime | None:
    """``value`` as a point in time, or None. Only the form the real export uses counts, as in
    ``2026-10-20T15:16:11.894774+00:00``: ``YYYY-MM-DDTHH:MM:SS`` in ASCII digits (HH 00 to 23,
    MM and SS 00 to 59), an optional fraction of 1 to 6 digits, then ``Z`` or an offset
    ``±HH:MM`` (HH 00 to 23, MM 00 to 59), naming a real date and time. The shape is checked
    before datetime.fromisoformat, which alone accepts more: an offset of +00:99 (read as
    +01:39), more than six fractional digits (cut to six, so two strings read as one instant),
    any character between the date and the time, and on Python 3.14 hour 24 (read as the next
    midnight)."""
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def recorded_corpus(path: Path, *keys: str) -> str | None:
    """The corpus the JSON file at ``path`` records under ``keys``: a timestamp that instant()
    accepts, as written. None when the file is missing or cannot be read (not UTF-8, not
    strict JSON, nested too deep) or records none (a level is not an object, or the value is
    missing or is not such a timestamp)."""
    try:
        value = _DECODER.decode(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError, SchemaError):
        return None
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value if instant(value) is not None else None


def deck_corpus(deck_id: str) -> str | None:
    return recorded_corpus(deck_file(deck_id), "meta", "corpusVersion")


def derivative_corpora(fleet: list[str]):
    """Each derivative file of this checkout with the corpus it records: every deck's file, the
    matcher index (its own meta) and the matcher index sidecar."""
    for deck_id in fleet:
        yield deck_file(deck_id), deck_corpus(deck_id)
    yield MATCHER_INDEX_FILE, recorded_corpus(MATCHER_INDEX_FILE, "meta", "corpusVersion")
    yield MATCHER_META_FILE, recorded_corpus(MATCHER_META_FILE, "corpusVersion")


def is_newer(recorded: str | None, corpus: str) -> bool:
    """True when ``recorded`` (a corpus as recorded_corpus returns it) is a later instant than
    ``corpus`` (the run's export timestamp, already checked to be one)."""
    return recorded is not None and instant(recorded) > instant(corpus)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Sync Commander Spellbook combo corpus")
    parser.add_argument("--force", action="store_true", help="Re-download + regenerate even if current")
    parser.add_argument("--offline", action="store_true", help="Use the cached gz; do not download")
    parser.add_argument("--emit-details", action="store_true", help="Write data/spellbook/details/ shards")
    parser.add_argument("--deck", action="append", default=[], help="Limit per-deck files to these ids (repeatable)")
    args = parser.parse_args(argv)

    # PROJECT_ROOT is resolved, so META_FILE resolves elsewhere only through a link on the
    # file or on a folder above it inside the project.
    meta_location = META_FILE.resolve()
    if meta_location != META_FILE:
        print(
            f"{META_FILE} leads to {meta_location}. The meta file records the corpus of the last "
            "run that wrote it, in this checkout; a run here checks it against this checkout's "
            "cached export and derivative files (data/spellbook/, "
            "data/commanders/*/spellbook-combos.json), so it must be this checkout's own file. "
            "To recover: "
            "priv_data/spellbook/ must be a real folder of this checkout "
            "(inside a real priv_data/) holding variants.json.gz (its own copy, or a link to "
            "another checkout's) and no linked meta file: remove the meta link (or replace the "
            "linked folder by such a real one), then run once with --offline --force and no "
            "--deck: that rebuilds every deck's file from that export without a download and "
            "writes this checkout's own meta file (if this checkout's files record a newer "
            "corpus than that export, it refuses and changes nothing: then run with --force and "
            "without --offline, which downloads the newest export). No file written.",
            file=sys.stderr,
        )
        return 1
    if args.offline and not RAW_FILE.exists():
        print(f"ERROR: {RAW_FILE} absent and --offline set.", file=sys.stderr)
        return 1

    # A download is read once, from this run's temporary file, and replaces RAW_FILE only
    # after the scan passes. Any other way out removes it.
    download = None
    try:
        if not args.offline:
            download = download_corpus()
        variants = read_corpus(download or RAW_FILE)

        prev_ts = recorded_corpus(META_FILE, "corpus_timestamp")
        fleet = deck_folders()

        def is_current(timestamp: str | None) -> bool:
            # The freshness short-circuit only applies to a full-fleet default run. A
            # targeted `--deck` regen is intentional hygiene after a decklist change
            # (the deck's own combos depend on its list, not just the corpus), so it must
            # always rebuild — otherwise the deck's spellbook-combos.json is silently
            # left stale. --force also always rebuilds. The meta file and every derivative file
            # (each deck's file, the matcher index and its sidecar) must record this corpus: a
            # deck a --deck run left on another one, or a file that is missing or records none,
            # makes the fleet stale.
            return (
                timestamp is not None
                and not args.force
                and not args.deck
                and prev_ts == timestamp
                and all(corpus == timestamp for _, corpus in derivative_corpora(fleet))
            )

        # The run changes nothing when it holds the cached export's own bytes (an --offline
        # run, or a byte-identical download) and the timestamp is current. A download that
        # differs from the cache in any byte (a missing, corrupt or unreadable cache included)
        # is scanned, replaces the cache and rebuilds, even with the same timestamp, unless a
        # derivative file records a newer corpus: that refusal (below) also changes nothing,
        # and the download does not replace the cache. An export whose timestamp sits after
        # the variants list is scanned first.
        unchanged = download is None or same_bytes(RAW_FILE, download)
        early_ts, _ = corpus_id(variants.header)
        if unchanged and is_current(early_ts):
            print(f"Corpus current ({early_ts}); derivatives up to date. Use --force to rebuild.", file=sys.stderr)
            return 0

        print("Extracting variants ...", file=sys.stderr)
        extracted = scan_variants(variants)
        corpus_ts, version = corpus_id(variants.header)
        if corpus_ts is None:
            raise SchemaError("export has no 'timestamp' — cannot version the corpus.")
        if instant(corpus_ts) is None:
            raise SchemaError(f"export timestamp {corpus_ts!r} is not a timestamp of the export's "
                              "form (YYYY-MM-DDTHH:MM:SS in ASCII digits, an optional fraction of 1 "
                              "to 6 digits, then Z or an offset ±HH:MM) — cannot order the corpus.")
        if version is not None and _unwritable(version):
            raise SchemaError(f"export version {version!r} has text that cannot be written as UTF-8 "
                              "(a lone surrogate).")
        version = version or "unknown"
        print(f"  corpus {corpus_ts}, spellbook v{version}", file=sys.stderr)

        # Never move a derivative file to an older corpus, whatever the flags: a derivative
        # file on a newer corpus than this run's export stops the run before the cache, the
        # meta file or any derivative file changes (a worktree's linked export can be older
        # than the deck files it checked out).
        newer = [(path, corpus) for path, corpus in derivative_corpora(fleet) if is_newer(corpus, corpus_ts)]
        if newer:
            source = "the cached export's" if download is None else "the download's"
            print(f"ERROR: these files record a newer corpus than {source} ({corpus_ts}):",
                  file=sys.stderr)
            for path, corpus in newer:
                print(f"    {path.relative_to(PROJECT_ROOT).as_posix()}  {corpus}", file=sys.stderr)
            advice = ("Run without --offline to download the newest export." if download is None
                      else "Spellbook served an export older than these files: run again without "
                           "--offline once it serves the newest.")
            print(f"No cache, meta or derivative file changed: no run moves a derivative file to "
                  f"an older corpus. {advice}", file=sys.stderr)
            return 1

        if unchanged and is_current(corpus_ts):
            print(f"Corpus current ({corpus_ts}); derivatives up to date. Use --force to rebuild.", file=sys.stderr)
            return 0

        # Nothing below is current until the meta file is written again at the end. It goes
        # before the cache is replaced and before the rebuild: a run that stops in between
        # (Ctrl-C, a broken deck.json, a full disk) leaves no meta file, so the next run
        # rebuilds every deck if it has no --deck, instead of calling the half-written files
        # up to date.
        META_FILE.unlink(missing_ok=True)
        if download and not unchanged:
            download.replace(RAW_FILE)
    finally:
        if download:
            download.unlink(missing_ok=True)

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
    write_json(MATCHER_META_FILE, matcher_index["meta"])
    print(
        f"  wrote {MATCHER_INDEX_FILE.relative_to(PROJECT_ROOT)} ({size / 1e6:.1f} MB, "
        f"{len(card_dict):,} cards) + matcher-index.meta.json",
        file=sys.stderr,
    )

    # 2. Per-deck spellbook-combos.json. A deck id is a folder name of the fleet, exactly.
    deck_ids = []
    for deck_id in dict.fromkeys(args.deck) if args.deck else fleet:
        if deck_id in fleet:
            deck_ids.append(deck_id)
        else:
            print(f"  WARN: {deck_id} is not the name of a deck folder (one holding a deck.json) "
                  "under data/commanders/; skipping.", file=sys.stderr)
    deck_report = []
    for deck_id in deck_ids:
        deck = json.loads((COMMANDERS_DIR / deck_id / "deck.json").read_text())
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
        # Old shards go before the new ones are written: a stop in between leaves them
        # incomplete, and a run without the flag does not write them; --offline --force
        # --emit-details writes them all again.
        if DETAILS_DIR.exists():
            for old in DETAILS_DIR.glob("*.json"):
                old.unlink()
        for key, rows in sorted(shards.items()):
            rows.sort(key=lambda d: d["id"])
            write_json(DETAILS_DIR / f"{key}.json", {"variants": rows})

    # When a run installed its download while the meta file named the same corpus timestamp,
    # it could not match the export it installed to the cached one (missing, unreadable or
    # other bytes). If it rebuilt only some decks, it cannot tell which of the others were built
    # from the one it installed: it writes no meta file, so the next run rebuilds every deck
    # if it has no --deck. Every other run writes it.
    rebuilt = set(deck_ids)
    unverified = download is not None and not unchanged and prev_ts == corpus_ts and rebuilt != set(fleet)
    if not unverified:
        write_json(META_FILE, {
            "corpus_timestamp": corpus_ts,
            "spellbook_version": version,
            "downloaded_at": generated_at,
            "variant_count": len(extracted),
            "card_count": len(card_dict),
            "details_estimated_mb": round(est_bytes / 1e6, 1),
            "source": VARIANTS_URL,
        })
    if args.deck:
        # A --deck run rebuilt the matcher index and its own decks only: name every other deck
        # whose file does not record this corpus (when it cannot verify the others, every other
        # deck), and the steps of AGENTS.md ("Combo Lab artifacts") that bring the fleet onto it.
        listed = [(deck_id, corpus) for deck_id, corpus in
                  [(deck_id, deck_corpus(deck_id)) for deck_id in fleet if deck_id not in rebuilt]
                  if unverified or corpus != corpus_ts]
        if listed:
            if unverified:
                print(f"  this checkout's meta file named this corpus ({corpus_ts}), but this run "
                      "could not match the export it installed to the cached one (missing, "
                      "unreadable or other bytes), so it cannot tell which of these decks' files "
                      "were built from the one it installed:", file=sys.stderr)
            else:
                print(f"  decks whose spellbook-combos.json is not on this run's corpus ({corpus_ts}):",
                      file=sys.stderr)
            for deck_id, corpus in listed:
                label = ("no corpus recorded" if corpus is None
                         else "matching timestamp, export unverified" if corpus == corpus_ts else corpus)
                print(f"    {deck_id:32s} {label}", file=sys.stderr)
            print("  to put every deck on it: uv run python scripts/sync_spellbook_combos.py "
                  "--offline --force", file=sys.stderr)
            print("  then, for each deck whose included[] set changed: "
                  "uv run python scripts/build_tier_b_candidates.py --deck ID", file=sys.stderr)
            if unverified:
                print("  no meta file written: run once without --deck next; that run rebuilds every deck.",
                      file=sys.stderr)
        else:
            print(f"  every deck's spellbook-combos.json is on this run's corpus ({corpus_ts}).",
                  file=sys.stderr)
    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SchemaError as exc:
        print(f"SCHEMA ERROR: {exc}", file=sys.stderr)
        print("Corpus left unchanged (degrade to 'corpus stale').", file=sys.stderr)
        sys.exit(2)
