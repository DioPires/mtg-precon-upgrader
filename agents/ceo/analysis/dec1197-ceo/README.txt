DEC-1197 CEO kit (run 20db7ff2, 2026-10-18). Read-only for other agents: copy a file to your own scratch folder before you use it.

census/census.py OLD.py NEW.py MIRROR   the implementer's census script (copy of dec1191-scratch/census.py).
census/item_<sha>.txt                    classify over the mirror (32,116 cards) on the commit's parent and on the commit, for the 10 code commits of PR #84.
census/total.txt                         the same over the whole leg, fa3e86a to 4985520 (490 cards).
census/abl2.txt                          head 4985520 without item 2's alternative in _DRAW, against the head (21 cards).
census/abl5.txt                          head 4985520 with `cost = None` for item 5's cost read, against the head (12 cards).
census/seats.py BASE HEAD                pool diff from the committed candidates.json files (git show; no mirror needed).
census/seats.txt                         seats.py fa3e86a 4985520.
census/probe.py SHAS NAME...             classify named cards on atr_<sha>.py files in the current folder.

The atr_<sha>.py inputs are `git show <sha>:scripts/auto_tag_roles.py`.
