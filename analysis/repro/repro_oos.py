# Block 13 out-of-sample table: trend, last-245, last-490 (flat and step are in step.py).
import json,math
exec(open('step.py').read().split('def run(')[0])
import numpy as np
first={}
for i,r in enumerate(R): first.setdefault(r[0],i)
def fit_trend(t,y):
    b=np.zeros(2); X=np.c_[np.ones(len(t)),t]
    for _ in range(25):
        p=1/(1+np.exp(-X@b)); W=p*(1-p); H=X.T@(X*W[:,None]); g=X.T@(y-p); b+=np.linalg.solve(H+1e-9*np.eye(2),g)
    return b
yr=lambda d:int(d[:4])+(int(d[5:7])-1)/12+(int(d[8:10])-1)/365
res={k:{} for k in ('trend','last245','last490')}
for d in dates:
    if d<'2019-01-01': continue
    i0=first[d]; prior=[r for r in R[:i0] if r[0]>='2018-01-01']; te=[r for r in R if r[0]==d]
    t=np.array([yr(r[0]) for r in prior])-2018; y=np.array([r[1] for r in prior],float); b=fit_trend(t,y)
    pt=1/(1+math.exp(-(b[0]+b[1]*(yr(d)-2018))))
    res['trend'][d]=[ll(pt,r[1]) for r in te]
    for k,w in (('last245',245),('last490',490)):
        Y=[r[1] for r in R[i0-w:i0]]; res[k][d]=[ll(sum(Y)/w,r[1]) for r in te]
def summ(o):
    S={'2019-2025':[],'2026 to Jun 21':[],'Jun 22 - Nov 7 2026':[]}
    for d,v in o.items():
        k='2019-2025' if d<'2026-01-01' else ('2026 to Jun 21' if d<'2026-06-22' else 'Jun 22 - Nov 7 2026')
        S[k]+=v
    return {k:(round(sum(v)/len(v),4),len(v)) for k,v in S.items()}

for k,o in res.items(): print(k,summ(o))
