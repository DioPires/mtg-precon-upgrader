"""DEC-1112 items 9 b and 9 c: the CEO's seeds S1 to S4 and the reviewer's own mutants.

Usage: mutants_mine.py <tree> <out.json>. Same method as the implementer's mutants3.py: each
mutant is (id, what, old, new); old must occur exactly once. The file is restored after each run.
"""
import json, os, re, subprocess, sys
from pathlib import Path

TREE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
TARGET = TREE / "scripts" / "fetch_card_metadata.py"
TESTS = ["tests/test_fetch_other_printings.py", "tests/test_scryfall_fetch.py",
         "tests/test_fetch_card_metadata_helpers.py", "tests/test_card_metadata_coverage.py"]

M = [
 # 9 b: the CEO's seeds (head line numbers)
 ("S1", "line 167: an inversion of one cent passes the order check",
  "(b is not None and a <= b)", "(b is not None and a <= b + 0.01)"),
 ("S2", "line 227: a card whose first search found nothing sends a second search",
  'if page is None or page["has_more"]:', 'if page is None or page["has_more"] or not page["data"]:'),
 ("S3", "line 174: a printing released later in the run's month counts",
  'card["released_at"] <= today and', 'card["released_at"][:7] <= today[:7] and'),
 ("S4", "line 230: a non-foil price of 0.00 does not count",
  "price = min((p for p in prices if p is not None), default=None)",
  "price = min((p for p in prices if p), default=None)"),
 # 9 c: _search_prints
 ("R1", "_search_prints: the search goes out as a POST with an empty JSON body",
  'scryfall_api.request(f"{SEARCH_URL}?{query}")', 'scryfall_api.request(f"{SEARCH_URL}?{query}", {})'),
 ("R2", "_search_prints: a page with has_more and fewer than 175 printings counts as complete",
  'return {"data": page["data"], "has_more": page["has_more"]}',
  'return {"data": page["data"], "has_more": page["has_more"] and len(page["data"]) >= 175}'),
 ("R3", "_search_prints: a 400 gives an empty page too",
  "and e.code == 404:", "and e.code in (400, 404):"),
 # 9 c: the lacking lines of fetch_metadata
 ("R4", "lacking: a card without a top-level oracle_id is grouped under None",
  'lacking.setdefault(card["oracle_id"], (card["name"], []))',
  'lacking.setdefault(card.get("oracle_id"), (card["name"], []))'),
 ("R5", "lacking: the pass fills a copy of the entry, not the stored entry",
  '(card["name"], []))[1].append(entry)', '(card["name"], []))[1].append(dict(entry))'),
 # 9 c: _prices_from_other_printings
 ("R6", "pass: a foil price counts as the price (the sort key, not the non-foil price)",
  'prices = [_price(card, currency) for card in page["data"] if _counts(card, today)]',
  'prices = [_sort_key(card, currency) for card in page["data"] if _counts(card, today)]'),
 ("R7", "pass: only the first entry of a card is counted as gained",
  "            gained[currency] += entries\n", "            gained[currency] += entries[:1]\n"),
 # 9 c: the count of other_printing
 ("R8", "count: a name counts when its entry gained a price in either currency",
  "filled = {id(entry) for entry in gained[currency]}",
  "filled = {id(entry) for c in CURRENCIES for entry in gained[c]}"),
 ("R9", "count: cards (distinct entries) instead of names",
  "other_printing[currency] = sum(id(entry) in filled for entry in metadata.values())",
  "other_printing[currency] = len({id(entry) for entry in metadata.values()} & filled)"),
 # 9 c: the spelling line (N5)
 ("R10", "spelling line: the names join with a comma",
  '"Scryfall also returned names that match no name asked: " + "; ".join(unmatched))',
  '"Scryfall also returned names that match no name asked: " + ", ".join(unmatched))'),
 # 9 c: write_outputs
 ("R11", "write_outputs: card-metadata.json ends with a newline",
  "output_file: json.dumps(metadata, indent=2, sort_keys=True),",
  'output_file: json.dumps(metadata, indent=2, sort_keys=True) + "\\n",'),
 ("R12", "write_outputs: the temporary files go to the system's temporary folder",
  'temps = {path: path.with_name(path.name + ".tmp") for path in texts}',
  'temps = {path: Path(__import__("tempfile").gettempdir()) / (path.name + ".tmp") for path in texts}'),
 ("R13", "write_outputs: the temporary files are removed only after a failure",
  """    finally:
        for temp in temps.values():
            temp.unlink(missing_ok=True)""",
  """    except BaseException:
        for temp in temps.values():
            temp.unlink(missing_ok=True)
        raise"""),
 ("R14", "write_outputs: the data file is written with ensure_ascii=False",
  "output_file: json.dumps(metadata, indent=2, sort_keys=True),",
  "output_file: json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False),"),
]

only = set(sys.argv[3:])
original = TARGET.read_text()
results = []
try:
    for mid, what, old, new in M:
        if only and mid not in only:
            continue
        n = original.count(old)
        if n != 1:
            results.append({"id": mid, "what": what, "error": f"pattern found {n} times"})
            print(mid, "PATTERN", n, flush=True)
            continue
        TARGET.write_text(original.replace(old, new))
        proc = subprocess.run(
            ["uv", "run", "--with", "pytest", "python", "-m", "pytest", "-q", "-rfE",
             "-p", "no:cacheprovider", *TESTS],
            cwd=TREE, capture_output=True, text=True, env={**os.environ, "CI": "true"})
        failed = sorted(set(re.findall(r"^(?:FAILED|ERROR|SUBFAILED\([^)]*\)) (\S+?)(?: - |$)",
                                       proc.stdout, re.M)))
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-300:]
        killed = bool(failed) or proc.returncode != 0
        results.append({"id": mid, "what": what, "killed": killed, "returncode": proc.returncode,
                        "failed": failed, "tail": tail})
        print(mid, "KILLED" if killed else "SURVIVED", len(failed), tail, flush=True)
        for f in failed:
            print("   ", f, flush=True)
finally:
    TARGET.write_text(original)
OUT.write_text(json.dumps(results, indent=1, ensure_ascii=False))
