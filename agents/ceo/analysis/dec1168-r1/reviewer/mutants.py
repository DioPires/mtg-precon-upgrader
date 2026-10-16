#!/usr/bin/env python3
"""DEC-1168 review: mutants of PR #68's two rules in web/src/styles/styles.css.

The first nine come from the implementer's dec1156/mutants.py (same edits);
M768, TPANEL, TENG, T480 and VMIN are the reviewer's own.

usage: mutants.py apply <id> <tree root>   writes the mutant in place
       mutants.py list
"""
import sys

CSS = "web/src/styles/styles.css"
HEAD = "@media (max-width: 990px) {\n  .gv1-engine-panel-head { flex-wrap: wrap; gap: 8px 16px; }\n}\n"
TITLE = "  .gv1-engine-panel-head h3 { font-size: clamp(30px, 10vw, 42px); }\n"
B480 = "@media (max-width: 480px) {\n  .gv1-scry-mobile-banner { display: block; }\n}\n"


def head(new_rule: str = None, query: str = "@media (max-width: 990px) {") -> str:
    rule = new_rule if new_rule is not None else "  .gv1-engine-panel-head { flex-wrap: wrap; gap: 8px 16px; }"
    return f"{query}\n{rule}\n}}\n"


# id: (description, [(old, new)], text appended at the end of the file)
MUTANTS = {
    "C30a": ("clamp minimum 30px -> 28px", [(TITLE, TITLE.replace("clamp(30px", "clamp(28px"))], ""),
    "C10a": ("clamp preferred 10vw -> 9vw", [(TITLE, TITLE.replace("10vw", "9vw"))], ""),
    "C42b": ("clamp maximum 42px -> 44px", [(TITLE, TITLE.replace("42px)", "44px)"))], ""),
    "TOUT": ("title rule out of the 768px block (all widths, end of file)", [(TITLE, "")],
             "\n/* mutant: the title rule at every width */\n" + TITLE.lstrip()),
    "TXL": ("title rule on .gv1-serif-xl in the 768px block (every user of the class)",
            [(TITLE, TITLE.replace(".gv1-engine-panel-head h3", ".gv1-serif-xl"))], ""),
    "WDEL": ("flex-wrap: wrap removed", [(HEAD, head("  .gv1-engine-panel-head { gap: 8px 16px; }"))], ""),
    "G8": ("row gap 8px -> 6px", [(HEAD, head("  .gv1-engine-panel-head { flex-wrap: wrap; gap: 6px 16px; }"))], ""),
    "B769": ("old lower bound min-width: 769px put back", [(HEAD, head(query="@media (min-width: 769px) and (max-width: 990px) {"))], ""),
    "B1000": ("upper bound 990px -> 1000px", [(HEAD, head(query="@media (max-width: 1000px) {"))], ""),
    # Reviewer's own.
    "M768": ("wrap query (max-width: 990px) -> (max-width: 768px)", [(HEAD, head(query="@media (max-width: 768px) {"))], ""),
    "TPANEL": ("title selector -> .gv1-engine-panel h3", [(TITLE, TITLE.replace(".gv1-engine-panel-head h3", ".gv1-engine-panel h3"))], ""),
    "TENG": ("title selector -> .gv1-engine h3", [(TITLE, TITLE.replace(".gv1-engine-panel-head h3", ".gv1-engine h3"))], ""),
    "T480": ("title rule moved into the @media (max-width: 480px) block",
             [(TITLE, ""), (B480, B480.replace("display: block; }\n", "display: block; }\n" + TITLE))], ""),
    "VMIN": ("clamp preferred 10vw -> 10vmin", [(TITLE, TITLE.replace("10vw", "10vmin"))], ""),
}


def main() -> None:
    if sys.argv[1] == "list":
        for k, v in MUTANTS.items():
            print(k, v[0])
        return
    _, _, mid, root = sys.argv
    desc, edits, tail = MUTANTS[mid]
    path = f"{root}/{CSS}"
    s = open(path).read()
    for old, new in edits:
        assert s.count(old) == 1, (mid, old)
        s = s.replace(old, new)
    open(path, "w").write(s + tail)
    print(mid, CSS, desc)


if __name__ == "__main__":
    main()
