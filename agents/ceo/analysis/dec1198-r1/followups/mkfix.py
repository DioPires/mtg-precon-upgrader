"""mkfix.py: write candidate fix files from the head's auto_tag_roles.py.

fix_p2.py: the cost lookahead also treats "exile this card from your graveyard" as spending the card.
fix_p3.py: a one-card draw is not a cantrip when the text outside reminder text gives it again
           (a copy, a mode chosen more than once, a return to hand, a prepared spell, a trigger on two events).
fix_p23.py: both.
"""
src = open("/tmp/dec1198/snap/atr_699cb7e.py").read()

p2_old = "(?!sacrifice this|discard this)"
p2_new = "(?!sacrifice this|discard this|exile this card from your graveyard)"

p3_old_const = '''

def _is_cantrip(oracle: str) -> bool:'''
p3_new_const = '''
# Outside reminder text: the card gives its one draw again (DEC-1198 P3).
_DRAW_AGAIN = re.compile(
    r"\\b(?:gravestorm|storm|replicate)\\b|\\bcopy (?:it|this spell)\\b|same mode more than once|"
    r"return this card from your graveyard to your hand|becomes prepared|"
    r"\\benters or (?:dies|is put into a graveyard)"
)


def _is_cantrip(oracle: str) -> bool:'''
p3_old_check = '''        return False
    start = oracle.rfind("\\n", 0, draws[0].start()) + 1'''
p3_new_check = '''        return False
    if _DRAW_AGAIN.search(re.sub(r"\\([^)]*\\)", "", oracle)):
        return False
    start = oracle.rfind("\\n", 0, draws[0].start()) + 1'''

for old in (p2_old, p3_old_const, p3_old_check):
    assert src.count(old) == 1, old
p2 = src.replace(p2_old, p2_new)
p3 = src.replace(p3_old_const, p3_new_const).replace(p3_old_check, p3_new_check)
p23 = p2.replace(p3_old_const, p3_new_const).replace(p3_old_check, p3_new_check)
for name, text in (("fix_p2", p2), ("fix_p3", p3), ("fix_p23", p23)):
    open(f"/tmp/dec1198/snap/atr_{name}.py", "w").write(text)
print("ok")
