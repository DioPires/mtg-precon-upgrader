"""fixmut.py: run the fix round's test file against (a) the head's classifier and (b) each mutant of the
fixed classifier, each in a fresh folder under OUT/fixmut/ (argv 1). Prints count lines and failed tests."""
import os, shutil, subprocess

# Kit copy (CEO, DEC-1192 fix round 1): inputs come from the kit, outputs go to OUT (argv[1]).
import sys
KIT = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dec1184-fix1"
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", UV_CACHE_DIR=os.environ["PAPERCLIP_GITHUB_HOST_HOME"] + "/.cache/uv")
fixed = open(f"{KIT}/expected/scripts/auto_tag_roles.py").read()
tests = open(f"{KIT}/expected/tests/test_auto_tag_roles.py").read()
OWN = 'return bool(re.match(r"(?:[^,]|,(?! then\\b))*? you (?:control|own)\\b", oracle[t.start():r.start()]))'
UYC = 'if r and re.match(r"(?: tapped)? under your control", oracle[r.end():end]):'
PT = r'if re.search(r"target creature gets? (?:-\d+/-\d+|[+-](?:\d+|x)/-(?:[1-9]\d*|x))", oracle):'
GY = "(?!target\\b|controls?\\b|then\\b)"
ST = 'r"attacking creature|blocking creature)"'
MUT = {
    "head-code": None,
    "F-M1-tapped-dropped": (UYC, UYC.replace("(?: tapped)?", "")),
    "F-M2-own-dropped": (OWN, OWN.replace("(?:control|own)", "(?:control)")),
    "F-M3-dotstar": (OWN, OWN.replace("(?:[^,]|,(?! then\\b))*?", ".*?")),
    "F-M3b-old-comma-stop": (OWN, OWN.replace("(?:[^,]|,(?! then\\b))*?", "[^,]*?")),
    "F-then-wordend-dropped": (OWN, OWN.replace(",(?! then\\b)", ",(?! then)")),
    "F-start-to-end": (OWN, OWN.replace("t.start()", "t.end()")),
    "F-M4-match-to-search": (UYC, UYC.replace("re.match(", "re.search(")),
    "F-M5-return-true": (OWN, "return True"),
    "F-M6-own-wordend-dropped": (OWN, OWN.replace("(?:control|own)\\b", "(?:control|own)")),
    "F-M10-span-from-oracle-start": (OWN, OWN.replace("oracle[t.start():r.start()]", "oracle[:r.start()]")),
    "F-M7-gy-then-wordend": (GY, GY.replace("then\\b", "then")),
    "F-item2-then-removed": (GY, GY.replace("|then\\b", "")),
    "F-M12-first-alt-dropped": (PT, PT.replace("(?:-\\d+/-\\d+|", "(?:")),
    "F-M13-target-dropped": (PT, PT.replace('r"target creature gets?', 'r"creature gets?')),
    "F-M14-power-1digit": (PT, PT.replace("(?:\\d+|x)/", "(?:\\d|x)/")),
    "F-M17-gets-only": (PT, PT.replace("gets? ", "gets ")),
    "F-P1-plus-dropped": (PT, PT.replace("[+-](?:", "[-](?:")),
    "F-P2-zero-cut": (PT, PT.replace("[1-9]\\d*", "\\d+")),
    "F-M18-blocking-dropped": (ST, 'r"attacking creature)"'),
    "F-M19-attacking-dropped": (ST, 'r"blocking creature)"'),
    "F-land-back": (ST, 'r"attacking creature|blocking creature|land)"'),
}
for label, mut in MUT.items():
    root = f"{OUT}/fixmut/{label}"
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root + "/scripts"); os.makedirs(root + "/tests")
    if mut is None:
        code = open(f"{KIT}/head/atr_3e69543.py").read()
    else:
        old, new = mut
        assert fixed.count(old) == 1, (label, fixed.count(old))
        code = fixed.replace(old, new)
    open(root + "/scripts/auto_tag_roles.py", "w").write(code)
    open(root + "/tests/test_auto_tag_roles.py", "w").write(tests)
    open(root + "/tests/__init__.py", "w").close()
    out = subprocess.run(["uv", "run", "--with", "pytest", "python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "tests/test_auto_tag_roles.py"], cwd=root, env=ENV, capture_output=True, text=True).stdout
    print(f"=== {label}")
    for l in out.splitlines():
        if l.startswith(("FAILED", "SUBFAIL")):
            print("  " + l.split("::", 1)[1].split(" - ")[0])
        elif " passed" in l or " failed" in l:
            print("  " + l.split(" in ")[0])
