"""Cut two saved Scryfall search pages down to the printings that the order check reads (DEC-1138).

Both sources are answer 37 of a DEC-1079 live run: the search of Forest's paper printings
with ``order=usd`` (``q=oracleid:b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6 game:paper``,
``unique=prints``). Both runs saved them on 2026-10-14 under
``$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/
6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1079-scratch/live/``. Each page has ``has_more``
true and 175 printings.

- ``run2/answer-37.json`` (sent with ``dir=asc``, 851,568 bytes, SHA-256
  50ebb94c6017b0238cb7f3fbd1931dcf4cdeee0a11bbd5df6fe181aa61d4cc3a) gives
  ``forest-usd-run2-trimmed.json``: ``data[97:106]``, printings 98 to 106 (from 1). They are
  three without a sort key (``wc01``, ``wc01``, ``olep``, all memorabilia), then ``m20``,
  ``c15``, ``dtk`` and ``m14`` at ``usd`` 0.09, then ``war`` and ``hou`` at 0.10.
- ``run1/answer-37.json`` (sent without ``dir``, 889,666 bytes, SHA-256
  758e6848a59c5e19fc1981c49f38375703126b0e69e957730d70235e6cf28534) gives
  ``forest-usd-run1-trimmed.json``: ``data[169:175]``, its last six printings: ``wc02`` 1.82,
  ``wc03`` 1.79, ``cma`` 1.74, ``brb`` 1.74, ``wc97`` 1.72 and ``zen`` 1.60, the most expensive
  first.

Each fixture keeps every other top-level key and value of its page, and each kept card whole,
unchanged and in Scryfall's order. The script stops when a source's SHA-256 differs, or when
``json`` cannot write the source back to its own bytes (then a value could change). It writes
with ``indent=1``, as the fixtures of ``tests/fixtures/prerelease`` do. Cut on 2026-10-15.

Usage: uv run python tests/fixtures/scryfall/trim_page.py <the live folder above>
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent

CUTS = [
    # source, its SHA-256, the slice of ``data``, the fixture
    ("run2/answer-37.json", "50ebb94c6017b0238cb7f3fbd1931dcf4cdeee0a11bbd5df6fe181aa61d4cc3a",
     slice(97, 106), "forest-usd-run2-trimmed.json"),
    ("run1/answer-37.json", "758e6848a59c5e19fc1981c49f38375703126b0e69e957730d70235e6cf28534",
     slice(169, 175), "forest-usd-run1-trimmed.json"),
]


def main(live: Path) -> None:
    for source, sha256, cut, fixture in CUTS:
        raw = (live / source).read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha256:
            sys.exit(f"{source}: the SHA-256 is not {sha256}")
        page = json.loads(raw)
        if json.dumps(page, ensure_ascii=False, separators=(",", ":")).encode() != raw:
            sys.exit(f"{source}: json does not write the page back to its own bytes")
        if len(page["data"]) != 175:
            sys.exit(f"{source}: the page holds {len(page['data'])} printings, not 175")
        page["data"] = page["data"][cut]
        text = json.dumps(page, ensure_ascii=False, indent=1) + "\n"
        (HERE / fixture).write_text(text, encoding="utf-8")
        print(f"{fixture}: data[{cut.start}:{cut.stop}] of {source}, "
              f"{len(text.encode())} bytes")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
