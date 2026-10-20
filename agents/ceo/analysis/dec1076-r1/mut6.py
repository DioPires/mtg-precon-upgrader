"""Apply each of the six DEC-1093 survivors to the scratch tree, run tests/test_scryfall_pins.py, restore."""
import os, subprocess, sys
from pathlib import Path
TREE = Path(os.environ.get("MUTANT_TREE", "/tmp/dec1076-ceo/tree"))
API = "scripts/scryfall_api.py"; IMG = "scripts/fetch_card_images.py"; TOK = "scripts/compute_tokens.py"
GC = "scripts/check_game_changers.py"; DUMP = "scripts/prerelease/dump_set.py"
M = [
 ("S1", API, 'parts.hostname != API_HOST:\n', 'not parts.hostname.endswith("scryfall.com"):\n'),
 ("S2", IMG, "        except (urllib.error.URLError, TimeoutError):\n", "        except (urllib.error.URLError, OSError):\n"),
 ("R4", TOK, "def _request(url: str, body: dict | None = None) -> dict:\n", "def _request(url: str, body: dict | None = {}) -> dict:\n"),
 ("R5", TOK, '        body = {"identifiers": [{"name": n} for n in batch]}\n', '        body = {"identifiers": [{"name": n.split(" // ")[0]} for n in batch]}\n'),
 ("R7", GC, "        page = json.loads(scryfall_api.request(url))\n", "        page = json.loads(scryfall_api.request(url, {}))\n"),
 ("R9", DUMP, "    return json.loads(scryfall_api.request(url))\n", "    return json.loads(scryfall_api.request(url, {}))\n"),
]
GUARD = ("import socket, sys, pytest; socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('a test reached the network')); "
         "sys.exit(pytest.main(['-q', '-p', 'no:cacheprovider', 'tests/test_scryfall_pins.py']))")
env = {**os.environ, "CI": "true", "https_proxy": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9"}
def run():
    r = subprocess.run(["uv", "run", "--with", "pytest", "python", "-c", GUARD], cwd=TREE, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout.strip().splitlines()[-1]
print("head", *run())
for mid, path, old, new in M:
    p = TREE / path; src = p.read_text()
    assert src.count(old) == 1, (mid, src.count(old))
    p.write_text(src.replace(old, new))
    try:
        rc, line = run()
    finally:
        subprocess.run(["git", "checkout", "--", path], cwd=TREE, check=True)
    print(mid, rc, line, "KILLED" if rc != 0 else "SURVIVED")
print("status:", repr(subprocess.run(["git", "status", "--porcelain"], cwd=TREE, capture_output=True, text=True).stdout))
