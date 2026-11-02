import sys; sys.path.insert(0, "/tmp/fra_review")
from common import *
cards17, pub, v1, v2, v3, ds, names = setup()
n=len(names)
Y=[pub[k]["ever_drawn_win_rate"]*100 for k in names]; A=[v3[k]['grade'] for k in names]; Bd=[ds[k] for k in names]
def pct(v): r=ranks(v); m=len(v); return [(x-1)/(m-1)*100 for x in r]
py, pa, pb = pct(Y), pct(A), pct(Bd)
roles={k:(v3[k].get('roles') or ['none']) for k in names}
def has(k,role): return role in roles[k]
def mean(L): return sum(L)/len(L) if L else float('nan')
r_ay=pearson(pa,py)
print("role | n | mean v3pct | mean GIHpct | gap | boot95 | expected gap from regression to mean (r=%.2f) | excess | draftsim gap"%r_ay)
for role in ("removal","engine","threat","trick","fixing","bomb"):
    ix=[i for i,k in enumerate(names) if has(k,role)]
    if not ix: continue
    gaps=[py[i]-pa[i] for i in ix]
    lo,hi=boot_ci(lambda idx: mean([gaps[j] for j in idx]), len(ix))
    exp=mean([(r_ay-1)*(pa[i]-50) for i in ix])
    dgap=mean([py[i]-pb[i] for i in ix])
    print(f"{role} | {len(ix)} | {mean([pa[i] for i in ix]):.0f} | {mean([py[i] for i in ix]):.0f} | {mean(gaps):+.0f} | ({lo:+.0f},{hi:+.0f}) | {exp:+.0f} | {mean(gaps)-exp:+.0f} | {dgap:+.0f}")
# Within-grade comparison: removal vs others at same v3 grade
print("\nGIH WR by v3 grade, removal vs engine vs other")
for g in sorted(set(A)):
    def grp(f): return [Y[i] for i,k in enumerate(names) if A[i]==g and f(k)]
    rem=grp(lambda k: has(k,'removal')); eng=grp(lambda k: has(k,'engine')); oth=grp(lambda k: not has(k,'removal') and not has(k,'engine'))
    print(g, "removal", len(rem), "%.1f"%mean(rem) if rem else '-', "| engine", len(eng), "%.1f"%mean(eng) if eng else '-', "| other", len(oth), "%.1f"%mean(oth) if oth else '-')
# OLS: GIH WR ~ v3 grade + removal + engine (+ uncommon + colour dummies); bootstrap CIs
def ols(X, y):
    # normal equations, small
    p=len(X[0]); XtX=[[sum(X[r][i]*X[r][j] for r in range(len(X))) for j in range(p)] for i in range(p)]
    Xty=[sum(X[r][i]*y[r] for r in range(len(X))) for i in range(p)]
    # gaussian elimination
    M=[row[:]+[Xty[i]] for i,row in enumerate(XtX)]
    for c in range(p):
        piv=max(range(c,p), key=lambda r: abs(M[r][c])); M[c],M[piv]=M[piv],M[c]
        if abs(M[c][c])<1e-12: return None
        for r in range(p):
            if r!=c:
                f=M[r][c]/M[c][c]
                for j in range(c,p+1): M[r][j]-=f*M[c][j]
    return [M[i][p]/M[i][i] for i in range(p)]
cols="WUBRG"
def col(k):
    c=pub[k]['color']; return c if len(c)==1 else ('M' if len(c)>1 else 'C')
def design(idx, gradevec, extra_colour=True, rarity=True):
    X=[];yy=[]
    for i in idx:
        k=names[i]; row=[1.0, gradevec[i], 1.0 if has(k,'removal') else 0.0, 1.0 if has(k,'engine') else 0.0]
        if rarity: row.append(1.0 if pub[k]['rarity']=='uncommon' else 0.0)
        if extra_colour: row += [1.0 if col(k)==c else 0.0 for c in "UBRGM"]  # W and colourless baseline
        X.append(row); yy.append(Y[i])
    return X,yy
for lab,gv in (("v3",A),("draftsim",Bd)):
  for spec in ((False,False),(False,True),(True,True)):
    X,yy=design(range(n),gv,*spec); b=ols(X,yy)
    rng=random.Random(3); bs=[]
    for _ in range(3000):
        idx=[rng.randrange(n) for _ in range(n)]; Xb,yb=design(idx,gv,*spec); bb=ols(Xb,yb)
        if bb: bs.append(bb)
    def ci(j): v=sorted(x[j] for x in bs); return v[int(.025*len(v))], v[int(.975*len(v))-1]
    print(f"{lab} colour={spec[0]} rarity={spec[1]}: grade {b[1]:+.2f} pts/grade {ci(1)[0]:+.2f},{ci(1)[1]:+.2f}; removal {b[2]:+.2f} ({ci(2)[0]:+.2f},{ci(2)[1]:+.2f}); engine {b[3]:+.2f} ({ci(3)[0]:+.2f},{ci(3)[1]:+.2f})")
