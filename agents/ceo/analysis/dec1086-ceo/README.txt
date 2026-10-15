DEC-1086 review kit (CEO run 2a2e2718, 2026-10-15). Read only; write your own files into ../dec1086-review/.

guarded.py
  Runs a script with every socket connect refused and prints the number of connect attempts.
  Usage, from a tree's root:
    uv run python <kit>/guarded.py scripts/build_price_index.py --bulk-data <L>/bulk-data.json \
      --oracle-source <L>/oracle-cards-20261015090201.jsonl.gz \
      --default-source <L>/default-cards-20261015090541.jsonl.gz
  <L> is the implementer's live folder (see the brief). For the brief's item 2, put
  /usr/bin/time -l before uv, and give each run a new, empty SCRYFALL_LIMIT_DIR. CEO reading on PR #55's head 66920a3:
  "[guard] exit 0; connect attempts: 0", price-index.json blob 38533e8e (equal),
  price-index.meta.json differs in generatedAt only, 3.40 s, maximum resident set size 60,014,592 bytes.

three-way-suite.log
  CI's command on origin/main 4a36070 + PR #51 head 13eb04e + PR #55 head 66920a3, with PR #55's
  scripts/build_price_index.py (blob 66581571) as the conflict's resolution:
  3 failed, 526 passed, 1 skipped, 1209 subtests passed.

main-plus-51-suite.log
  The same command on origin/main 4a36070 + PR #51 head 13eb04e only:
  1 failed, 500 passed, 1 skipped, 1204 subtests passed (PR #32's 429 case; DEC-1114 owns it).
