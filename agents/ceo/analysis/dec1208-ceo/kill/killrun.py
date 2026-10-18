"""killrun.py: for each survivor, apply it, run the kill file, record its failed cases, restore."""
import json, os, re, subprocess, sys
TREE = os.getcwd(); F = "scripts/auto_tag_roles.py"
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TREE=TREE, HOME=os.environ["PAPERCLIP_GITHUB_HOST_HOME"])
muts = {m[0]: m for m in json.load(open("/tmp/dec1208/mut/all_mutants.json"))}
labels = [l.strip() for l in open("/tmp/dec1208/kill/survivors.txt") if l.strip()]
def clean():
    subprocess.run("find scripts tests -name __pycache__ -type d -prune -exec rm -rf {} +", shell=True, cwd=TREE)
for label in labels:
    _, old, new = muts[label]
    text = open(F).read(); assert text.count(old) == 1, label
    open(F, "w").write(text.replace(old, new)); clean()
    r = subprocess.run(["uv", "run", "--with", "pytest", "python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        "/tmp/dec1208/kill/test_review_kills.py"], cwd=TREE, env=env, capture_output=True, text=True)
    lines = r.stdout.splitlines()
    count = next((re.sub(r" in [0-9.]+s", "", l) for l in lines if re.search(r"\d+ passed|\d+ failed", l)), "?")
    fails = [l.replace("../../../../../../tmp/dec1208/kill/", "").replace("/tmp/dec1208/kill/", "") for l in lines if l.startswith(("FAILED", "SUBFAILED"))]
    subprocess.run(["git", "checkout", "--", F], cwd=TREE, env=env); clean()
    ok = subprocess.run(["git", "diff", "--quiet"], cwd=TREE, env=env).returncode == 0
    print(f"=== {label}\n  kill file: {count}\n  " + "\n  ".join(f[:170] for f in fails) + f"\n  restored: {'git diff --quiet ok' if ok else 'RESTORE FAILED'}")
    sys.stdout.flush()
