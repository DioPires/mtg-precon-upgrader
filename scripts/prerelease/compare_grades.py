"""Compare our Sealed grades against Draftsim's published set review.

    uv run python scripts/prerelease/compare_grades.py --set-dir DIR --draftsim URL

Fetches the review page, reads every "Rating: N/10" back to the card it
belongs to, writes DIR/draftsim_grades.json, and prints the mean of each
scale, the correlation, the mean absolute difference and every card where the
two disagree by 3 points or more.

Expect a scale offset: Draftsim runs about a point below ours. What matters is
the big disagreements — re-read the oracle text for each one and write the
decision into DIR/grade_review_log.md.

Use --html FILE to parse a page saved earlier instead of fetching it.
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Draftsim serves a different page to unknown clients, so identify as a browser.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
RATING_RE = re.compile(r"rating\s*:?\s*(\d+(?:\.\d+)?)\s*/\s*10", re.I)


def normalize(text: str) -> str:
    """Curly punctuation to straight, runs of whitespace to one space."""
    for bad, good in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"')):
        text = text.replace(bad, good)
    text = text.replace(" ", " ").replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", text)


def html_to_text(raw: str) -> str:
    """Plain text of a page: scripts dropped, tags replaced by spaces."""
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return normalize(htmllib.unescape(raw))


def name_variants(name: str) -> list:
    """The spellings a review may use: the full name and the front face."""
    variants = [name]
    if " // " in name:
        variants.append(name.split(" // ")[0])
    return [normalize(v) for v in variants]


def parse_draftsim(raw_html: str, names: list) -> dict:
    """Map card name to Draftsim rating.

    Walks the page once. Every rating is credited to the most recent card name
    seen before it, and each card keeps only its first rating.
    """
    text = html_to_text(raw_html)
    variant_to_name: dict = {}
    for name in names:
        for variant in name_variants(name):
            key = variant.lower()
            # Longer spellings win, so "Card // Other" beats the front face alone.
            if key not in variant_to_name or len(name) > len(variant_to_name[key]):
                variant_to_name[key] = name
    if not variant_to_name:
        return {}
    ordered = sorted(variant_to_name, key=len, reverse=True)
    name_re = re.compile("|".join(re.escape(v) for v in ordered), re.I)

    events = [
        (m.start(), "name", variant_to_name[m.group(0).lower()])
        for m in name_re.finditer(text)
        if m.group(0).lower() in variant_to_name
    ]
    events += [(m.start(), "rating", float(m.group(1))) for m in RATING_RE.finditer(text)]
    events.sort(key=lambda e: e[0])

    out: dict = {}
    current = None
    for _, kind, value in events:
        if kind == "name":
            current = value
        elif current is not None and current not in out:
            out[current] = int(value) if float(value).is_integer() else value
    return out


def pearson(xs: list, ys: list) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else float("nan")


def report(ours: dict, theirs: dict) -> None:
    shared = sorted(set(ours) & set(theirs))
    print(f"matched {len(shared)} of {len(ours)} graded cards ({len(theirs)} ratings on the page)")
    if not shared:
        return
    a = [ours[n] for n in shared]
    b = [theirs[n] for n in shared]
    print(f"mean ours: {sum(a) / len(a):.2f}   mean Draftsim: {sum(b) / len(b):.2f}")
    print(f"correlation: {pearson(a, b):.3f}")
    print(f"mean abs diff: {sum(abs(x - y) for x, y in zip(a, b)) / len(a):.2f}")
    big = sorted(
        ((ours[n] - theirs[n], n) for n in shared if abs(ours[n] - theirs[n]) >= 3),
        key=lambda t: -abs(t[0]),
    )
    print(f"\ndisagreements of 3 or more ({len(big)}):")
    for diff, name in big:
        print(f"  {name}: ours {ours[name]}, Draftsim {theirs[name]} ({diff:+g})")
    unmatched = sorted(set(ours) - set(theirs))
    if unmatched:
        shown = ", ".join(unmatched[:20])
        more = f", and {len(unmatched) - 20} more" if len(unmatched) > 20 else ""
        print(f"\nno Draftsim rating found for {len(unmatched)} cards: {shown}{more}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--set-dir", required=True)
    ap.add_argument("--draftsim", help="URL of the Draftsim set review")
    ap.add_argument("--html", help="parse this saved HTML file instead of fetching")
    args = ap.parse_args()
    if not args.draftsim and not args.html:
        raise SystemExit("pass --draftsim URL or --html FILE")

    with open(os.path.join(args.set_dir, "grades.json"), encoding="utf-8") as fh:
        graded = json.load(fh)
    ours = {e["name"]: e["grade"] for e in graded}

    if args.html:
        with open(args.html, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    else:
        req = urllib.request.Request(args.draftsim, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

    theirs = parse_draftsim(raw, list(ours))
    out_path = os.path.join(args.set_dir, "draftsim_grades.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(dict(sorted(theirs.items())), fh, indent=1)
    print("wrote", out_path)
    report(ours, theirs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
