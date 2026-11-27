import json, math
d=json.load(open('/tmp/b42h/snap.json')); v=d['values']; H=v[0]
ROWS=[dict(zip(H,r)) for r in v[1:]]
def f(x):
    try: return float(x)
    except: return None
def kadj(k):
    k=(k or '').strip()
    if k=='G': return -0.04
    if k=='GF': return 0.04
    if k=='R': return -0.04
    try: return float(k)
    except: return 0.0
def women(tag): return 1 if (tag or '').strip().lower().startswith('w') else 0
def q_of(r, shift, beta=0.15, fmax=0.15, fmin=0.075, wadj=-0.04, H_override=None):
    G=f(r['dog listed G (sheet)']); J=f(r['Markov J'])
    if H_override is not None: Hh=H_override
    else: Hh = G if J is None else max(0.02,min(0.98,J-shift))
    C=f(r['Tap C']); D=f(r['Junk D'])
    pub=[x for x in (C,D) if x is not None]
    mx=max(pub) if pub else None; mn=min(pub) if pub else None
    q=G+beta*(Hh-G)+wadj*women(r['tag'])+kadj(r['K code'])
    if mx is not None: q-=fmax*max(0,mx-G)
    if mn is not None: q-=fmin*max(0,mn-G)
    return max(0.02,min(0.98,q))
CARDS=[]
for r in ROWS:
    if r['pk'] not in CARDS: CARDS.append(r['pk'])
def card_rows(pk): return [r for r in ROWS if r['pk']==pk]
def card_mean(pk, rows=None):
    rr=rows if rows is not None else card_rows(pk)
    x=[f(r['Markov J'])-f(r['dog listed G (sheet)']) for r in rr if f(r['Markov J']) is not None and f(r['dog listed G (sheet)']) is not None]
    return sum(x)/len(x) if x else 0.0
def imp(o):
    o=f(o); 
    if o is None: return None
    return 100/(o+100) if o>0 else -o/(-o+100)
