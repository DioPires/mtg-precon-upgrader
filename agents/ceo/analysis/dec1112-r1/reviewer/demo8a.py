"""DEC-1112 item 8 a: the head's run when the batch printing is a reversible_card without a price.

Run from a tree's root. FakeScryfall answers; no request leaves the process. The exception is
not caught here, so the exit code and the text are what `python scripts/fetch_card_metadata.py` gives.
"""
import json, sys, tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0, ".")
from tests.test_fetch_other_printings import PrintsScryfall, printing
from tests.test_scryfall_fetch import make_card, fetch_metadata

root = Path(tempfile.mkdtemp(prefix="dec1112-8a-"))
(root / "commanders/one").mkdir(parents=True)
(root / "commanders/one/deck.json").write_text(json.dumps({"commander": "Sol Ring", "decklist": [{"name": "Blood Crypt"}]}))
card = make_card("Blood Crypt // Blood Crypt", layout="reversible_card", usd=None, eur=None)
oracle_id = card.pop("oracle_id")
card["card_faces"] = [{"name": "Blood Crypt", "oracle_id": oracle_id}, {"name": "Blood Crypt", "oracle_id": oracle_id}]
fake = PrintsScryfall([make_card("Sol Ring"), card], {oracle_id: [printing("Blood Crypt", "rna", usd="9.00", eur="7.50")]})
output = root / "card-metadata.json"
try:
    with fake.installed(), mock.patch.object(fetch_metadata, "COMMANDERS_DIR", root / "commanders"):
        sys.exit(fetch_metadata.main(["--output-file", str(output)]))
finally:
    print(f"[demo] requests sent: {len(fake.sent)}; files in the output folder: "
          f"{sorted(p.name for p in root.iterdir())}", file=sys.stderr)
