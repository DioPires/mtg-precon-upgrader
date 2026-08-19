"""Import ManaBox deck exports and write the real printing of each card (DEC-546).

The collection already lives in ManaBox: priv_data/Owned.csv is a ManaBox export
and every row carries Set code, Collector number, Foil and Scryfall ID. What the
collection export cannot say is which deck holds which copy. Building the same
decks inside ManaBox adds exactly that missing fact, and this tool copies it into
data/commanders/{id}/deck.json.

Input: one export file per deck. Two shapes are accepted.

1. CSV export (ManaBox "Export deck" -> CSV). Header names are matched case
   insensitively; any of these columns are used when present:
       Name, Set code, Collector number, Foil, Scryfall ID, Quantity
2. Text export (ManaBox / Moxfield / Archidekt plain decklist), one line per card:
       3 Verdant Catacombs (MH2) 260
       1 Sol Ring (LTC) 284 *F*
   The trailing *F* or *E* marks foil or etched.

A text export has no Scryfall ID, so the tool resolves each line to a printing id
through priv_data/Owned.csv by (set code, collector number, finish). A line that
does not resolve is reported and left unwritten.

Reconciliation is the point, not a side effect. Every run diffs the export against
the deck.json decklist and reports three buckets: matched, in deck.json but absent
from the export, and in the export but absent from deck.json. Those last two mean
the sleeved deck and the repo disagree. Fix the disagreement before writing.

Version fields written into each matched decklist[] entry:
    "scryfall_id"      canonical printing id (unique per printing and art)
    "set"              set code
    "collector_number" collector number
    "finish"           "normal" | "foil" | "etched" (a Scryfall id does not carry finish)

Usage:
    uv run python scripts/import_manabox_decks.py --dir exports/
    uv run python scripts/import_manabox_decks.py --file exports/slivers.csv --deck slivers
    uv run python scripts/import_manabox_decks.py --dir exports/ --apply

With --dir, each file stem is the deck id: exports/titan-convergence.csv feeds
data/commanders/titan-convergence/deck.json.

Dry run is the default and never writes deck.json. --apply writes the matched
cards only. Exit code is 1 when any deck disagrees with its export, so the tool
works as a check in a script.
"""

import argparse
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
OWNED_CSV = os.path.join(ROOT, "priv_data", "Owned.csv")

TEXT_LINE = re.compile(
    r"^\s*(?P<qty>\d+)\s+"
    r"(?P<name>.+?)"
    r"\s+\((?P<set>[A-Za-z0-9]{2,6})\)"
    r"\s+(?P<cn>[A-Za-z0-9\-★]+)"
    r"(?:\s+\*(?P<finish>[FE])\*)?"
    r"\s*$"
)

FINISH_MARK = {"F": "foil", "E": "etched"}


def norm(name):
    """Front-face, casefolded name key. Matches ManaBox DFC naming to decklists."""
    return name.split(" // ")[0].strip().casefold()


def load_owned_index():
    """(set, collector_number, finish) -> scryfall id, from the collection export.

    A text decklist names a printing but not its id. The collection already knows
    the id for every physical card, so it fills the gap.
    """
    index = {}
    with open(OWNED_CSV) as f:
        for row in csv.DictReader(f):
            key = (
                row["Set code"].strip().casefold(),
                row["Collector number"].strip().casefold(),
                row["Foil"].strip().casefold(),
            )
            index[key] = row["Scryfall ID"]
    return index


def parse_csv_export(path):
    """Return [{name, set, collector_number, finish, scryfall_id, quantity}]."""
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return rows
        lookup = {h.strip().casefold(): h for h in reader.fieldnames}

        def col(row, *names):
            for n in names:
                header = lookup.get(n)
                if header is not None and row.get(header, "").strip():
                    return row[header].strip()
            return None

        for row in reader:
            name = col(row, "name", "card name", "card")
            if not name:
                continue
            qty = col(row, "quantity", "count", "qty") or "1"
            rows.append({
                "name": name,
                "set": col(row, "set code", "set", "edition"),
                "collector_number": col(row, "collector number", "collector_number", "number"),
                "finish": (col(row, "foil", "finish") or "normal").casefold(),
                "scryfall_id": col(row, "scryfall id", "scryfall_id"),
                "quantity": int(qty),
            })
    return rows


def parse_text_export(path):
    """Return parsed rows plus the lines that did not match the decklist grammar."""
    rows, bad = [], []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith(("#", "//")) or line.casefold() in {
                "deck", "commander", "sideboard", "maybeboard"
            }:
                continue
            m = TEXT_LINE.match(line)
            if not m:
                bad.append(line)
                continue
            rows.append({
                "name": m.group("name").strip(),
                "set": m.group("set"),
                "collector_number": m.group("cn"),
                "finish": FINISH_MARK.get(m.group("finish"), "normal"),
                "scryfall_id": None,
                "quantity": int(m.group("qty")),
            })
    return rows, bad


def parse_export(path):
    if path.casefold().endswith(".csv"):
        return parse_csv_export(path), []
    return parse_text_export(path)


def resolve_ids(rows, owned_index):
    """Fill scryfall_id from the collection export. Return rows that stay unresolved."""
    unresolved = []
    for row in rows:
        if row["scryfall_id"]:
            continue
        key = (
            (row["set"] or "").casefold(),
            (row["collector_number"] or "").casefold(),
            row["finish"],
        )
        found = owned_index.get(key)
        if found:
            row["scryfall_id"] = found
        else:
            unresolved.append(row)
    return unresolved


def group_by_name(rows):
    """key -> list of distinct printings named by that key."""
    grouped = {}
    for row in rows:
        grouped.setdefault(norm(row["name"]), []).append(row)
    return grouped


def reconcile(deck, rows):
    """Diff one deck.json against its export.

    Returns (assignments, report). An assignment is (decklist entry, printing).
    """
    grouped = group_by_name(rows)
    assignments = []
    report = {"matched": 0, "missing_in_export": [], "extra_in_export": [],
              "split_printing": [], "unresolved": []}
    seen = set()

    for card in deck.get("decklist", []):
        key = norm(card["name"])
        printings = grouped.get(key)
        if not printings:
            report["missing_in_export"].append(card["name"])
            continue
        seen.add(key)
        distinct = {(p["scryfall_id"], p["finish"]) for p in printings}
        if len(distinct) > 1:
            # Several copies of one name in different printings. One flat field
            # cannot hold both, so a human decides what deck.json should say.
            report["split_printing"].append({"name": card["name"], "printings": printings})
            continue
        printing = printings[0]
        if not printing["scryfall_id"]:
            report["unresolved"].append({
                "name": card["name"],
                "set": printing["set"],
                "collector_number": printing["collector_number"],
                "finish": printing["finish"],
            })
            continue
        assignments.append((card, printing))
        report["matched"] += 1

    for key, printings in grouped.items():
        if key not in seen:
            report["extra_in_export"].append(printings[0]["name"])

    return assignments, report


def apply_assignments(assignments):
    for card, printing in assignments:
        card["scryfall_id"] = printing["scryfall_id"]
        card["set"] = printing["set"]
        card["collector_number"] = printing["collector_number"]
        card["finish"] = printing["finish"]


def collect_inputs(args):
    """Return [(deck_id, export_path)]."""
    pairs = []
    if args.dir:
        for path in sorted(glob.glob(os.path.join(args.dir, "*"))):
            ext = os.path.splitext(path)[1].casefold()
            if ext not in {".csv", ".txt"}:
                continue
            pairs.append((os.path.splitext(os.path.basename(path))[0], path))
    for spec in args.file or []:
        pairs.append((args.deck, spec) if args.deck else (
            os.path.splitext(os.path.basename(spec))[0], spec))
    return pairs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", help="directory of exports; each file stem is a deck id")
    ap.add_argument("--file", action="append", help="one export file; repeat for several")
    ap.add_argument("--deck", help="deck id for a single --file (default: the file stem)")
    ap.add_argument("--apply", action="store_true", help="write versions into deck.json")
    ap.add_argument("--json", dest="json_out", help="write a machine-readable report here")
    args = ap.parse_args()

    pairs = collect_inputs(args)
    if not pairs:
        ap.error("give --dir or --file")

    owned_index = load_owned_index()
    audit = {}
    clean = True

    for deck_id, path in pairs:
        deck_path = os.path.join(ROOT, "data", "commanders", deck_id, "deck.json")
        if not os.path.exists(deck_path):
            print(f"{deck_id}: no deck.json at {deck_path} — skipped")
            clean = False
            continue

        rows, bad_lines = parse_export(path)
        unresolved_rows = resolve_ids(rows, owned_index)
        with open(deck_path) as f:
            deck = json.load(f)

        assignments, report = reconcile(deck, rows)
        report["unparsed_lines"] = bad_lines
        report["unresolved_printings"] = len(unresolved_rows)

        problems = (len(report["missing_in_export"]) + len(report["extra_in_export"])
                    + len(report["split_printing"]) + len(report["unresolved"]) + len(bad_lines))
        if problems:
            clean = False

        if args.apply and assignments:
            apply_assignments(assignments)
            with open(deck_path, "w") as f:
                json.dump(deck, f, indent=2, ensure_ascii=False)
                f.write("\n")

        verb = "wrote" if args.apply else "would write"
        print(f"{deck_id}: {verb}={report['matched']} "
              f"missing-in-export={len(report['missing_in_export'])} "
              f"extra-in-export={len(report['extra_in_export'])} "
              f"split-printing={len(report['split_printing'])} "
              f"unresolved={len(report['unresolved'])} unparsed={len(bad_lines)}")
        for name in report["missing_in_export"]:
            print(f"    deck.json has, export lacks: {name}")
        for name in report["extra_in_export"]:
            print(f"    export has, deck.json lacks: {name}")
        for item in report["unresolved"]:
            print(f"    no printing id for: {item['name']} "
                  f"({item['set']}) {item['collector_number']} {item['finish']}")
        for line in bad_lines:
            print(f"    unparsed line: {line}")

        audit[deck_id] = report

    if not args.apply:
        print("\ndry run: no deck.json written. Re-run with --apply to write versions.")
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(audit, f, indent=2, ensure_ascii=False)
        print(f"report written: {args.json_out}")

    sys.exit(0 if clean else 1)


if __name__ == "__main__":
    main()
