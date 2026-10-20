"""DEC-1122: the reviewer's own mutants of PR #40, on top of the implementer's 51.

The same method as the kit's mutants.py: CI's command (CI=true, pytest -q -rfEs) from the
tree's root, sockets that raise on connect, https_proxy/http_proxy at 127.0.0.1:9,
SCRYFALL_LIMIT_DIR and TMPDIR in a scratch folder, no bytecode, every __pycache__ removed
before each run. The tree must be clean before and after each mutant.

Usage: uv run python /tmp/dec1122/my_mutants.py [ID ...]
Env: MUTANT_TREE, MUTANT_OUT, MUTANT_SCRATCH; KILL_FILE (optional): run only that pytest
target on each mutant instead of the whole suite.
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

TREE = Path(os.environ["MUTANT_TREE"])
TOK = "scripts/compute_tokens.py"
DUMP = "scripts/prerelease/dump_set.py"
FETCH = "tests/test_scryfall_fetch.py"

EXC_BRANCH = "    except Exception as e:\n        raise RequestFailed(url, body, e) from e\n"
HTTP_RAISE = "        raise RequestFailed(url, body, e) from e\n    except Exception as e:\n"
FRONT = '    names = sorted({name.split(" // ")[0] for name in names})\n'
MAIN_EXCEPT = "        except (scryfall_api.ScryfallRateLimited, RequestFailed) as e:\n"
FUZZY_EXCEPT = "            except urllib.error.HTTPError as e:  # a 404: Scryfall found no card\n"
EXACT_EXCEPT = "        return c\n    except urllib.error.HTTPError as e:  # a 404: Scryfall found no card\n"
SEARCH_EXCEPT = "    except urllib.error.HTTPError as e:  # a 404: no card matches the query\n"

MUTANTS = [
    ("R1", "_request wraps only a URLError or a ValueError: a timeout or a reset on read passes raw",
     TOK, [(EXC_BRANCH, EXC_BRANCH.replace("except Exception as e", "except (urllib.error.URLError, ValueError) as e"))]),
    ("R2", "_request's HTTP branch catches every URLError", TOK,
     [("    except urllib.error.HTTPError as e:\n        if pass_404",
       "    except urllib.error.URLError as e:\n        if pass_404")]),
    ("R3", "_request: pass_404 and e.code >= 404", TOK,
     [("if pass_404 and e.code == 404:", "if pass_404 and e.code >= 404:")]),
    ("R4", "_request: pass_404 and e.code <= 404", TOK,
     [("if pass_404 and e.code == 404:", "if pass_404 and e.code <= 404:")]),
    ("R5", "_request's HTTP branch drops the body (a failed batch reads GET)", TOK,
     [(HTTP_RAISE, HTTP_RAISE.replace("(url, body, e)", "(url, None, e)"))]),
    ("R6", "_request's other branch drops the body (a failed batch reads GET)", TOK,
     [(EXC_BRANCH, EXC_BRANCH.replace("(url, body, e)", "(url, None, e)"))]),
    ("R7", "_request raises RequestFailed without 'from e' (both branches)", TOK,
     [(HTTP_RAISE, HTTP_RAISE.replace(" from e\n", "\n", 1)),
      (EXC_BRANCH, EXC_BRANCH.replace(" from e\n", "\n"))]),
    ("R8", "the front faces keep the input order (dict.fromkeys), not sorted", TOK,
     [(FRONT, '    names = list(dict.fromkeys(name.split(" // ")[0] for name in names))\n')]),
    ("R9", "the method reads 'not body' instead of 'body is None'", TOK,
     [('method = "GET" if body is None else "POST"', 'method = "GET" if not body else "POST"')]),
    ("R10", "main catches every Exception as a failed request", TOK,
     [(MAIN_EXCEPT, "        except Exception as e:\n")]),
    ("R11", "the batch reads data['data'] (no default)", TOK,
     [('        cards.extend(data.get("data", []))\n', '        cards.extend(data["data"])\n')]),
    ("R12", "the batch reads data['not_found'] (no default)", TOK,
     [('for nf in data.get("not_found", []) if', 'for nf in data["not_found"] if')]),
    ("R13", "the not_found filter on an empty name is gone", TOK,
     [('for nf in data.get("not_found", []) if nf.get("name")\n', 'for nf in data.get("not_found", [])\n')]),
    ("R14", "fuzzy lookup catches every URLError (RequestFailed is not one)", TOK,
     [(FUZZY_EXCEPT, FUZZY_EXCEPT.replace("HTTPError", "URLError"))]),
    ("R15", "exact lookup catches every URLError", TOK,
     [(EXACT_EXCEPT, EXACT_EXCEPT.replace("HTTPError", "URLError"))]),
    ("R16", "search catches every URLError", TOK,
     [(SEARCH_EXCEPT, SEARCH_EXCEPT.replace("HTTPError", "URLError"))]),
    ("R17", "the front faces sort without case (key=str.lower)", TOK,
     [(FRONT, '    names = sorted({name.split(" // ")[0] for name in names}, key=str.lower)\n')]),
    # ------------------------------------------------ dump_set.py
    ("R18", "dump_set: exc.code >= 404 says 'does not know'", DUMP,
     [("        if exc.code == 404:\n", "        if exc.code >= 404:\n")]),
    ("R19", "dump_set: exc.code <= 404 says 'does not know'", DUMP,
     [("        if exc.code == 404:\n", "        if exc.code <= 404:\n")]),
    ("R20", "dump_set: the 404 text prints the code without repr", DUMP,
     [("does not know set code {code!r} ({exc.code})", "does not know set code {code} ({exc.code})")]),
    ("R21", "dump_set: the other-status text prints the code without repr", DUMP,
     [("for set code {code!r}\") from exc", "for set code {code}\") from exc")]),
    ("R22", "dump_set: the 404 text writes the literal 404", DUMP,
     [("does not know set code {code!r} ({exc.code})", "does not know set code {code!r} (404)")]),
    ("R23", "dump_set: the other-status text uses str(exc)", DUMP,
     [('f"Scryfall answered HTTP {exc.code} {exc.reason} for set code {code!r}"',
       'f"Scryfall answered {exc} for set code {code!r}"')]),
    # ------------------------------------------------ check 7 only (the kit's F5, run on check7_old_combined_case.py)
    ("F5", "RedirectCases: no reset when a case ends (the kit's F5)", FETCH,
     [("        self.addCleanup(reset_helper_state)\n\n    def test_opener_has_no_redirect_handler",
       "\n    def test_opener_has_no_redirect_handler")]),
]


def git(*args):
    env = {**os.environ, "HOME": os.environ.get("PAPERCLIP_GITHUB_HOST_HOME", os.environ["HOME"])}
    return subprocess.run(["git", *args], cwd=TREE, capture_output=True, text=True, env=env,
                          check=True).stdout


only = set(sys.argv[1:])
dead = "http://127.0.0.1:9"
scratch = Path(os.environ["MUTANT_SCRATCH"])
kill = os.environ.get("KILL_FILE")
env = {**os.environ, "CI": "true", "PYTHONDONTWRITEBYTECODE": "1",
       "https_proxy": dead, "HTTPS_PROXY": dead, "http_proxy": dead, "HTTP_PROXY": dead,
       "SCRYFALL_LIMIT_DIR": str(scratch / "limit"), "TMPDIR": str(scratch / "tmp")}
assert git("status", "--porcelain") == "", "the tree is not clean"
head = git("rev-parse", "HEAD").strip()
print("head", head, "kill", kill, flush=True)
guard = ("import socket, sys, pytest; socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw("
         "RuntimeError('a test reached the network')); sys.exit(pytest.main(sys.argv[1:]))")
rows = []
targets = ["HEAD"] if "HEAD" in only else []
for mid, text, rel, pairs in [("HEAD", "no mutant", TOK, [])] + MUTANTS:
    if only and mid not in only:
        continue
    path = TREE / rel
    original = path.read_text()
    mutated = original
    for old, new in pairs:
        assert mutated.count(old) == 1, (mid, old[:70], mutated.count(old))
        mutated = mutated.replace(old, new)
    assert mid == "HEAD" or mutated != original, mid
    for top in ("scripts", "tests", "priv_data"):
        for cache in (TREE / top).rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
    if kill:
        for cache in Path(kill).parent.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
    shutil.rmtree(scratch, ignore_errors=True)
    (scratch / "tmp").mkdir(parents=True)
    args = ["-q", "-rfEs", "-p", "no:cacheprovider"] + ([kill] if kill else [])
    try:
        path.write_text(mutated)
        r = subprocess.run(["uv", "run", "--with", "pytest", "python", "-c", guard, *args],
                           cwd=TREE, capture_output=True, text=True, env=env, timeout=900)
    finally:
        path.write_text(original)
    dirty = git("status", "--porcelain")
    assert dirty == "", (mid, dirty)
    failed = sorted(set(re.findall(r"^(?:FAILED|ERROR|SUBFAIL\w*)(?:\([^)]*\))? (\S+?::\S+)", r.stdout, re.M)))
    failed = [f.split("::", 1)[1] for f in failed]
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
    network = "a test reached the network" in r.stdout + r.stderr
    killed = r.returncode != 0
    rows.append({"id": mid, "mutant": text, "file": rel, "killed": killed, "rc": r.returncode,
                 "failed": failed, "tail": tail, "network": network})
    print(f"{mid} | {rel.split('/')[-1]} | {text} | {'KILLED' if killed else 'SURVIVED'} | "
          f"network={network} | {tail}", flush=True)
    for f in failed:
        print("      ", f)
    if os.environ.get("MUTANT_LOG_DIR"):
        Path(os.environ["MUTANT_LOG_DIR"], f"{mid}.log").write_text(r.stdout + "\n--- stderr\n" + r.stderr)
out = os.environ.get("MUTANT_OUT")
shutil.rmtree(scratch, ignore_errors=True)
if out:
    json.dump({"head": head, "kill": kill, "rows": rows}, open(out, "w"), indent=1)
print("survivors:", [r["id"] for r in rows if not r["killed"] and r["id"] != "HEAD"])
print("network:", [r["id"] for r in rows if r["network"]])
