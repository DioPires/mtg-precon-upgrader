**Scan the whole history of `DioPires/mtg-precon-upgrader` for secrets, so that the board can make the repository public. Read only: change nothing in git or on GitHub.** Implementer: Interactive Tools Engineer (`ddb8e4ee`). Tier 1. Priority high. Budget about 90 minutes.

## Why
- Since 2026-10-16 10:01Z, GitHub refuses every Actions job in this private repository: the account used up its monthly minutes. Hub: [DEC-1178](/DEC/issues/DEC-1178).
- The board chose option B on card `c6017844` ([DEC-1155](/DEC/issues/DEC-1155)) at 10:13Z: make the repository public, after an engineer scans its history for secrets. Hosted jobs cost nothing on a public repository. The board changes the visibility only after the CEO passes your report on.
- Public means public for every commit that any ref reaches, including the 82 `refs/pull/*` heads, and for every pull request body and comment on GitHub. A secret in an old commit is as exposed as one on `main`.

## Facts at 10:20Z
- `git ls-remote origin` lists 104 refs: 21 branches, 82 `refs/pull/*`, and `HEAD`. `git rev-list --count --remotes` reads 1,524 commits.
- The repository has no Actions secrets (`gh secret list` prints nothing). There are 75 pull requests.
- Tracked files that hold settings: `.mcp.json` and `.claude/settings.local.json`. On `main`, `.mcp.json` passes only `SCRYFALL_LIMIT_DIR` and `XDG_CACHE_HOME` as environment values. A quick pattern search of `main`'s tip found no key. Nobody has searched the history.
- Commit author addresses: 1,435 commits use the owner's personal address, 84 use the GitHub `noreply` address, and 5 use `ceo@paperclip.local`.

## Setup
1. Export `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git`, `gh` and `brew` command.
2. Make the folder `/Users/dpires/.paperclip/instances/default/workspaces/ddb8e4ee-9ec6-45ae-81b7-144c85a9b26e/dec-scan/`. Keep the mirror, scripts, reports and logs there. Do not use the shared checkout, any `wt-*` tree, or `/tmp`.
3. Clone a mirror: `git clone --mirror https://github.com/DioPires/mtg-precon-upgrader.git <folder>/mirror.git`. A mirror holds the `refs/pull/*` heads too. Check that its ref count equals `git ls-remote origin | wc -l`.
4. Install `gitleaks` with `brew install gitleaks`. If the install fails, write a Python scan (run it with `python3 -I`) over `git -C <mirror> log --all -p` with the rules of step 3 below, and say so in the hand-back.
5. Never print a secret's whole value in a log, a comment or a report. Show its first 4 characters and its length. Use `--redact` with `gitleaks`.
6. Do not test a found key against its service. Do not push, rewrite history, change a GitHub setting or change the visibility.

## Scan
1. Run `gitleaks git <mirror> --log-opts="--all" --redact --report-format json --report-path <folder>/gitleaks.json`. Quote its summary line: the number of commits it scanned and the number of findings.
2. Read every version in the history of these paths: `.mcp.json`, `.claude/settings*.json`, `mcp-servers/**/config.py`, any `.env*`, `*.pem`, `*.key`, `*.p12` and `id_rsa*`. Use `git -C <mirror> log --all --format=%H -- <path>`, then `git show <commit>:<path>`. List each key name that holds a value which looks like a credential.
3. Search all commits' patches and all commit messages for these shapes, beside `gitleaks`'s own rules:
   - a JWT (`eyJ` + base64url + `.` + base64url + `.`), `PAPERCLIP_API_KEY=` with a value, and `Authorization: Bearer` with a value. Agent logs under `agents/` may quote a run's key.
   - GitHub tokens (`ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`, `github_pat_`), Anthropic (`sk-ant-`), OpenAI-style (`sk-` followed by 20 or more characters), Google and YouTube (`AIza`), AWS (`AKIA`), Slack (`xox`), and private key blocks (`-----BEGIN ... PRIVATE KEY`).
   - Vercel tokens, and any assignment of `password`, `secret`, `token` or `api_key` to a literal of 16 or more characters.
4. Scan the GitHub side with the same rules: the body, the review comments and the issue comments of all 75 pull requests (`gh api --paginate`). Check that no workflow file in the history prints an environment value into a run log (logs become public too).
5. Count, but do not judge, the personal data: commit author addresses by address, and the number of tracked files that hold `/Users/` home paths.

## Report (the hand-back comment)
1. **Verdict.** CLEAN (no credential in any object that a ref reaches, and none on GitHub's pull request pages) or FINDINGS.
2. **Counts.** Refs and commits scanned, `gitleaks`'s summary line, and pull request bodies and comments scanned.
3. **One row for each finding.** The rule, the path, the first and the last commit that hold it, whether `main`'s tip holds it, the kind of credential, and whether it is likely live (by its type and date only). Add the remedy. Rotation by the owner makes an old value useless. A history rewrite is a last resort and needs the board.
4. **A false positive.** Name its rule and path, and say why it is not a credential.
5. **Personal data.** The counts of scan step 5.
6. The paths of the logs and reports.

## Handoff
1. Post the report as a comment on this issue.
2. As the last action of the run, PATCH this issue with `assigneeAgentId` = `f9427c33-d719-4fd5-a3c5-cd2f65dd01e8` (CEO), `status` = `in_review`, and `executionPolicy.monitor` = `{"nextCheckAt": "<30 minutes ahead, ISO UTC>", "scheduledBy": "assignee", "notes": "Secrets scan hand-back in comment <id>."}`, all in one PATCH. The monitor covers an assignment wake that the server skips.
3. If the PATCH answers 422 `invalid_issue_disposition`, repeat it with `nextCheckAt` about ten hours ahead and `notes` under 500 characters. Never set `done`.
4. For a question in the middle of the leg: finish the parts that the question does not touch, post the question on this issue (question, evidence, your recommendation), and hand back with the same PATCH. Do not create a child issue for the CEO: the server refuses it with 409 `delegation_cycle`.

planned-by: CEO (run `a9b35256`, 2026-10-16). Parent: DEC-1178. Source: board answer B on card `c6017844`.
