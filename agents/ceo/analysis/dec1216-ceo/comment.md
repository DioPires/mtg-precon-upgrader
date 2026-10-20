**Answer: most of these files are already on GitHub. About 300 hold CEO notes that no run pushed, and they should be committed. A few are local files that must stay out of git.**

Tier 0: this is a question. I changed no file in the repository.

### Why you see them

- Several CEO runs share this checkout. Since DEC-1050 (2026-10-13), each run commits its notes in a scratch tree and pushes them to `origin/main`. No run pulls into the shared checkout, because a pull there can carry a sibling run's half-done edits.
- So the local `main` branch stopped moving on 2026-10-14 (`fc1c16a`, plus 4 local commits). `origin/main` is now 554 commits ahead of it.
- `git status` compares the files with that old local commit. So every file that a later commit added or changed looks new or modified, although GitHub already holds it.
- Agents load their instruction files from this checkout, so runs also wrote the current text into it. Some runs then pushed only part of their edits, or none.

### Census

Basis: `git fetch` at 16:4xZ today. `git status` lists 23 modified tracked files, 11 staged files, 1 deleted file and 1,226 untracked files.

| Group | Files | Commit? |
|---|---|---|
| Same bytes as `origin/main` | 12 modified tracked files (`AGENTS.md`, `CLAUDE.md`, `.mcp.json`, 2 memory files, 8 MCP server files) and 503 untracked files | No. They are already committed. |
| Older drafts of files that `origin/main` holds in a newer version | 3 files in `agents/ceo/analysis/dec1163-r1/` | No. |
| CEO notes that `origin/main` lacks | `agents/ceo/TOOLS.md` (24 lessons from 2026-10-14 to 2026-10-20), `agents/ceo/AGENTS.md` (Push and Merge rule 8), `agents/ceo/memory/patterns.md` (1 line), the DEC-993 erratum (2 lines), 3 local commits that no run pushed (12 kit files), 11 staged files and 275 untracked analysis files (4.8 MB) | **Yes.** |
| Engineer instruction files | 5 `agents/*/AGENTS.md` files: one sentence (set `HOME` for every batchmode Unity start, 2026-10-16) | **Yes.** |
| Local only | `.claude/settings.local.json` (this Mac's permission list), `priv_data/.claude/settings.local.json`, `.codex/config.toml` and 2 `.pid` files from Codex runs | **No.** |
| Engineer scratch | `agents/founding-eng/analysis/`: 441 files (5.6 MB) of measurements from DEC-1072, DEC-1102 and DEC-1131, with 2 `node_modules` links. All three issues are `done`, and `origin/main` tracks nothing in that folder. | No. Delete it. |
| Deleted in this checkout only | `design_handoff_grimoire/RECONCILIATION.md` (DEC-150). `origin/main` still holds it, and 2 files on `main` cite it. | No. Restore it. |

### Two risks

- **`TOOLS.md` diverged in both directions.** This checkout holds 24 lessons that GitHub lacks. GitHub holds 40 lessons that this checkout lacks, and 11 lines differ in wording. So the copy that the CEO loads misses lessons, and the record misses others. A plain copy in either direction loses lines. The fix is a merge that keeps each lesson once.
- **The repository is public.** A push publishes these notes. gitleaks scanned every file in the two "Yes" groups and found no secret.

### What I propose

A push to this repository publishes, so I need your go-ahead.

1. In a scratch tree on `origin/main`, merge both copies of `TOOLS.md` so that each lesson appears once. Add the other "Yes" files. Run gitleaks again, then push to `main`.
2. Make a backup branch of the local `main`. Then run `git reset --mixed origin/main` in the shared checkout. This command moves the branch and the index only and changes no file. After it, `git status` lists only real differences.
3. Clean up. Delete the 2 `.pid` files and the engineer scratch folder. Restore `RECONCILIATION.md`. Add `.codex/`, `priv_data/.claude/` and `*.pid` to `.gitignore`. Stop tracking `.claude/settings.local.json`, because Claude Code treats it as a personal file; your copy on this Mac stays.
4. Add one rule to `TOOLS.md`: a run that edits a note in the shared checkout pushes it in the same run, and its last step checks that `git status` in the shared checkout lists none of its files.

The card below asks which steps to take.
