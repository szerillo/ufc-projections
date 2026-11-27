import sys, math, random, json
sys.path.insert(0,'/tmp/b42h')
from common import *
def y_of(r):
    w=r.get('dog won'); return None if w not in ('0','1') else int(w)
def JG(r):
    J,G=f(r['Markov J']),f(r['dog listed G (sheet)'])
    return None if J is None or G is None else J-G
BUCK=[(0,0.25),(0.25,0.35),(0.35,0.45),(0.45,1.01)]
def bucket(G): return next(i for i,(a,b) in enumerate(BUCK) if a<=G<b)
def ols(xs,ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    sxx=sum((x-mx)**2 for x in xs); 
    b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sxx if sxx else 0
    return my-b*mx, b
def methods_for(ci):
    pk=CARDS[ci]; rr=card_rows(pk); prior=[r for p in CARDS[:ci] for r in card_rows(p)]
    pj=[JG(r) for r in prior if JG(r) is not None]
    fixed=sum(pj)/len(pj) if pj else 0.0
    M={}
    live=card_mean(pk)
    M['S0 live per-card B42']={id(r):q_of(r,live) for r in rr}
    M['A fixed offset (prior cards)']={id(r):q_of(r,fixed) for r in rr}
    # bucket offsets
    bm={}
    for i in range(len(BUCK)):
        xs=[JG(r) for r in prior if JG(r) is not None and bucket(f(r['dog listed G (sheet)']))==i]
        bm[i]=sum(xs)/len(xs) if len(xs)>=8 else fixed
    M['B offset by odds bucket (prior)']={id(r):q_of(r,bm[bucket(f(r['dog listed G (sheet)']))]) for r in rr}
    # slope calibration: E[y-G] = a + b (J-G) on prior graded rows -> H = G + a + b(J-G)
    pr=[(JG(r), y_of(r)-f(r['dog listed G (sheet)'])) for r in prior if JG(r) is not None and y_of(r) is not None]
    if len(pr)>=20:
        a,b=ols([x for x,_ in pr],[y for _,y in pr])
    else: a,b=0.0,0.0
    M['A2 slope calib (prior)']={id(r):q_of(r,0,H_override=(None if JG(r) is None else max(0.02,min(0.98,f(r['dog listed G (sheet)'])+a+b*JG(r))))) if JG(r) is not None else q_of(r,0) for r in rr}
    M['C shrink J halfway to G, no offset']={id(r):(q_of(r,0,H_override=f(r['dog listed G (sheet)'])+0.5*JG(r)) if JG(r) is not None else q_of(r,0)) for r in rr}
    M['D no offset']={id(r):q_of(r,0) for r in rr}
    M['ref: Markov off (beta 0)']={id(r):q_of(r,0,beta=0) for r in rr}
    return M, dict(fixed=fixed, live=live, buckets=bm, slope=(a,b))
def rec(r,q):
    G=f(r['dog listed G (sheet)']); pf=1-G
    aa=(r.get('flag AA') or ''); ok= aa.strip()=='ok'; sh=aa[:6]=='SHARPS'
    di,fi=imp(r['dog price (D)']),imp(r['fav price (I)'])
    if di is None or fi is None: return ('-',None)
    H=q-di; Mm=(1-q)-fi
    if pf>=0.8: return ('BET','fav80')
    if H>=0.08 and ok: return ('BET','dog')
    if Mm>=0.02 and sh: return ('BET','fav')
    if Mm>=0.03: return ('BET','fav')
    if H>=0.05 and ok: return ('lean','dog')
    if Mm>=0.02: return ('lean','fav')
    return ('-',None)
def pl(r,side):
    y=y_of(r)
    if y is None: return None
    o=f(r['dog price (D)'] if side=='dog' else r['fav price (I)'])
    win=(y==1) if side=='dog' else (y==0)
    if not win: return -1.0
    return o/100 if o>0 else 100/(-o)
