# DEC-1185 review. Usage: python3 -I mutate.py <tree/web> <mutant id>. Applies one mutant to the working tree.
# Adapted from /tmp/dec1177/mutate.py (paths and mutant set are this review's own).
import sys
web, mid = sys.argv[1], sys.argv[2]
SHOP = f"{web}/src/components/organisms/Shopping.tsx"
CMP = f"{web}/src/components/organisms/Compare.tsx"
STATES = f"{web}/src/styles/states.css"
LAB = f"{web}/src/styles/combo-lab.css"

def sub(path, old, new):
    s = open(path, encoding="utf-8").read()
    assert s.count(old) == 1, (mid, old, s.count(old))
    open(path, "w", encoding="utf-8").write(s.replace(old, new))

H = ' aria-hidden="true"'
# The sigil line and the message line of each state, as on the head.
NODECKS = ('<span className="gv1-rune" aria-hidden="true">◇</span>\n          <span className="gv1-mono-xs">No decks loaded.</span>')
ALLOWNED = ('<span className="gv1-rune" aria-hidden="true">◆</span>\n              <span className="gv1-mono-xs">All cards owned.')
CLEARED = ('<span className="gv1-rune" aria-hidden="true">◇</span>\n            <span className="gv1-mono-xs">No decks selected.')
COMPARE = ('<span className="gv1-rune" aria-hidden="true">◇</span>\n          <span id="compare-empty" className="gv1-mono-xs">')
LAB_RULE = "[data-gv1-screen=\"combolab\"] .gv1-empty::before{content:'◇';content:'◇' / '';font-style:normal;font-size:24px;color:var(--gv1-rune-dim);letter-spacing:0.4em}"
ST2 = "  content: '◇';\n  content: '◇' / '';\n"

M = {
  # The hand-backs' mutants: aria-hidden dropped from each span.
  "S1": lambda: sub(SHOP, NODECKS, NODECKS.replace(H, "", 1)),
  "S2": lambda: sub(SHOP, ALLOWNED, ALLOWNED.replace(H, "", 1)),
  "S3": lambda: sub(SHOP, CLEARED, CLEARED.replace(H, "", 1)),
  "S4": lambda: sub(CMP, COMPARE, COMPARE.replace(H, "", 1)),
  # The alternative text dropped; the alternative form alone.
  "C1": lambda: sub(STATES, ST2, "  content: '◇';\n"),
  "C2": lambda: sub(LAB, "content:'◇';content:'◇' / '';", "content:'◇';"),
  "C3": lambda: sub(STATES, ST2, "  content: '◇' / '';\n"),
  "C4": lambda: sub(LAB, "content:'◇';content:'◇' / '';", "content:'◇' / '';"),
  # The brief's list.
  "R1-shop-moved": lambda: sub(SHOP, NODECKS, NODECKS.replace(H, "", 1).replace('<span className="gv1-mono-xs">', '<span className="gv1-mono-xs" aria-hidden="true">')),
  "R2-cmp-moved": lambda: sub(CMP, COMPARE, COMPARE.replace(H, "", 1).replace('className="gv1-mono-xs">', 'className="gv1-mono-xs" aria-hidden="true">')),
  "R3-shop-div": lambda: (sub(SHOP, '<div className="gv1-empty">\n              ' + ALLOWNED, '<div className="gv1-empty" aria-hidden="true">\n              ' + ALLOWNED.replace(H, "", 1))),
  "R4-shop-false": lambda: sub(SHOP, CLEARED, CLEARED.replace(H, ' aria-hidden="false"', 1)),
  "R5-states-order": lambda: sub(STATES, ST2, "  content: '◇' / '';\n  content: '◇';\n"),
  "R6-lab-alt-x": lambda: sub(LAB, "content:'◇' / '';", "content:'◇' / 'x';"),
  # Own: the rest of each rewritten line.
  "O1-shop-nodecks-noclass": lambda: sub(SHOP, NODECKS, NODECKS.replace('<span className="gv1-rune" aria-hidden', '<span aria-hidden', 1)),
  "O2-shop-allowned-noclass": lambda: sub(SHOP, ALLOWNED, ALLOWNED.replace('<span className="gv1-rune" aria-hidden', '<span aria-hidden', 1)),
  "O3-shop-cleared-noclass": lambda: sub(SHOP, CLEARED, CLEARED.replace('<span className="gv1-rune" aria-hidden', '<span aria-hidden', 1)),
  "O4-cmp-noclass": lambda: sub(CMP, COMPARE, COMPARE.replace('<span className="gv1-rune" aria-hidden', '<span aria-hidden', 1)),
  "O5-shop-allowned-glyph": lambda: sub(SHOP, ALLOWNED, ALLOWNED.replace('>◆<', '>◇<', 1)),
  "O6-lab-fontsize": lambda: sub(LAB, LAB_RULE, LAB_RULE.replace("font-size:24px", "font-size:18px")),
  "O7-lab-no-letterspacing": lambda: sub(LAB, LAB_RULE, LAB_RULE.replace(";letter-spacing:0.4em", "")),
  "O8-lab-color": lambda: sub(LAB, LAB_RULE, LAB_RULE.replace("color:var(--gv1-rune-dim)", "color:var(--gv1-rune)")),
  "O9-lab-no-fontstyle": lambda: sub(LAB, LAB_RULE, LAB_RULE.replace("font-style:normal;", "")),
  "O10-states-alt-glyph": lambda: sub(STATES, "  content: '◇' / '';\n", "  content: '◆' / '';\n"),
  "O11-lab-after": lambda: sub(LAB, LAB_RULE, LAB_RULE.replace(".gv1-empty::before{", ".gv1-empty::after{")),
}
M[mid]()
print("applied", mid)
