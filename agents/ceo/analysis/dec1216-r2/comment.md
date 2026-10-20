**Done. GitHub now holds every note, and the shared checkout is up to date: `git status` there prints nothing.** I did steps 1 to 4 as you approved them on the card.

Tier 0, done by me: this is housekeeping of my own notes and of the shared checkout, with no product code, under your go-ahead.

### Your question: should all of `priv_data/` be in `.gitignore`?

**No, I recommend against it.** The folder holds private files and also 23 files that the pipeline needs in git.

| Files | Size | Git |
|---|---|---|
| `Owned.csv`, `owned_formatted.csv` (your collection) | 1.8 MB | ignored |
| `scryfall-oracle.json` and its meta file (card mirror) | 31 MB | ignored |
| `spellbook/` (Commander Spellbook corpus) | 29 MB | ignored |
| `edhrec/*.json` (21 EDHREC rate files, one per deck) | 212 KB | tracked |
| `compute_purchase_list.py`, `format_owned_list.py` | 16 KB | tracked |
| `.claude/settings.local.json` | 4 KB | ignored since today |

- The private files are already ignored. GitHub holds none of them.
- The 21 EDHREC files feed `generate_candidate_pool.py`, `build_synergy_candidates.py` and `build_tier_b_candidates.py`. Swap runs work in scratch trees, and a scratch tree holds only tracked files. Today's DEC-1215 apply commit (`77ad5ee`) updated `edhrec/broodfire-hatchery.json` that way.
- A `priv_data/` line would not untrack those 23 files. But `git add` would then skip every new file in the folder without a warning, for example the rate file of a new deck.
- If you want the folder private by default, I can write it as an allow-list: ignore `priv_data/*` and allow only `edhrec/` and the two scripts. Tell me and I will do it.

Side note: three files on `main` say that `priv_data/edhrec/` is ignored (`scripts/build_synergy_candidates.py`, `prompts/phase-2/manifest.json`, and `scripts/card_lookup.py` for the whole folder). That text is wrong; the setup above is correct.

### What I did

1. **Push (step 1).** Commit `17ac92e` on `main` holds 300 note files, the merged `agents/ceo/TOOLS.md`, rule 8 in the CEO's `AGENTS.md`, the sentence in the 5 engineer `AGENTS.md` files, `patterns.md` and the DEC-993 erratum. gitleaks scanned all 312 changed files and found no leak. No CI run started, because the commit changes notes only.
   - I merged `TOOLS.md` lesson by lesson. It keeps every lesson from GitHub and adds the 24 lessons that only this checkout held. In 5 cases both copies held one lesson in two wordings; I kept the longer, newer wording.
2. **Update the checkout (step 2).** My proposal was not enough here. `git reset --mixed` alone would have listed about 600 product files as changed, because their copies on disk dated from 2026-10-14. `git pull` refuses too, because untracked files already held the same bytes. So I wrote `agents/ceo/sync_shared_checkout.py` and tested it on a scratch repository (8 cases). On the shared checkout it wrote 597 files, found 1,230 already current, deleted 11 and kept 1:
   - Deleted: 10 `.pyc` cache files and `web/src/data/cardImages.ts`. `main` removed all of them earlier.
   - Kept: `.claude/settings.local.json`, your local permission list.
3. **Cleanup (step 3).**
   - I deleted the 2 `.pid` files (their processes ended on 2026-10-12) and `agents/founding-eng/analysis/` (441 files).
   - I restored `RECONCILIATION.md`.
   - `.gitignore` now ignores `**/.claude/settings.local.json`, `.codex/` and `*.pid`. The first line replaces the `priv_data/.claude/` line of my proposal, because one line covers both copies.
   - Git no longer tracks `.claude/settings.local.json`. Your copy on this Mac stays.
4. **Rule (step 4).** A new last line in `TOOLS.md` says that a run pushes every file that it writes into the shared checkout. As its last git step, the run starts the sync script, and `git status --short` must then list none of its files. This comment's own file went through that path.

### Backup

Local branch `backup/dec1216-shared-checkout` (`be4d90a`) holds every file of the checkout as it was before this run, including the deleted folder and the local settings. I did not push it. When you no longer need it, delete it with `git branch -D backup/dec1216-shared-checkout`.
