# Prerelease analyses

One folder per set, named by its Scryfall set code. The tools are in
[`scripts/prerelease/`](../../scripts/prerelease/README.md), and the process is in
[`docs/prerelease-playbook.md`](../../docs/prerelease-playbook.md).

| Set | Folder | Event | Cheat sheet | Back-test |
|---|---|---|---|---|
| Reality Fracture | [`fra/`](fra/) | 25 or 26 September 2026 | [`cheat_sheet.md`](fra/cheat_sheet.md), [`cheat_sheet.pdf`](fra/cheat_sheet.pdf) | Done on 1 November 2026: [`backtest/retro.md`](fra/backtest/retro.md) and [`backtest/adversarial-review.md`](fra/backtest/adversarial-review.md) |
| Star Trek | [`trk/`](trk/) | 6 November 2026 | [`cheat_sheet.md`](trk/cheat_sheet.md), [`cheat_sheet.pdf`](trk/cheat_sheet.pdf) | Due about 1 December 2026 |

## Where the folders came from

DEC-1222 moved them here on 2 November 2026:

- `fra/` was `agents/ceo/analysis/dec925/` (issue DEC-925).
- `fra/backtest/` was `agents/ceo/analysis/dec1218/fra-retro/` (issue DEC-1218).
- `trk/` was `agents/ceo/analysis/prerelease/trk/` (issue DEC-1218).

Files written before the move, such as reports, sim outputs and logs, still
quote the old paths. `git log --follow <file>` shows a file's history from
before the move.
