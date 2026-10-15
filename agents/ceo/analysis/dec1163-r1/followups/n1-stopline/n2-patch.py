# DEC-1163 N2 trial: the summary section stays in the page with no class while no deck is selected,
# so the stop line's region is there before its text. Apply with `python3 n2-patch.py apply`.
import sys
P = '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1163-review/web/src/components/organisms/Shopping.tsx'
OLD1 = """      {selected.size > 0 && (
        <section className="gv1-section gv1-shop-section">
          <div className="gv1-shop-summary">
"""
NEW1 = """      <section className={selected.size > 0 ? 'gv1-section gv1-shop-section' : undefined}>
        {selected.size > 0 && (
          <div className="gv1-shop-summary">
"""
OLD2 = """          </div>
          <PricePausedLine waiting={waitingForPrice} pricesDate={shownPricesDate} />
        </section>
      )}
"""
NEW2 = """          </div>
        )}
        <PricePausedLine waiting={waitingForPrice} pricesDate={shownPricesDate} />
      </section>
"""
s = open(P).read()
assert s.count(OLD1) == 1 and s.count(OLD2) == 1
open(P, 'w').write(s.replace(OLD1, NEW1).replace(OLD2, NEW2))
print('applied')
