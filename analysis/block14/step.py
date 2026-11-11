import json,math
R=sorted(json.load(open('/tmp/rows2010.json')))
dates=sorted(set(r[0] for r in R))
def ll(p,y): p=min(max(p,1e-4),1-1e-4); return -(y*math.log(p)+(1-y)*math.log(1-p))
def bestsplit(Y,minseg):
    n=len(Y); c=[0]
    for y in Y: c.append(c[-1]+y)
    best=(0,None)
    for i in range(minseg,n-minseg+1):
        a=c[i]/i; b=(c[n]-c[i])/(n-i); p=c[n]/n
        se=math.sqrt(p*(1-p)*(1/i+1/(n-i)))
        z=(b-a)/se if se>0 else 0
        if abs(z)>abs(best[0]): best=(z,i)
    return best
def run(rule,minseg=30,win=1000,zc=3):
    out={}
    for d in dates:
        if d<'2019-01-01': continue
        prior=[r for r in R if r[0]<d]; te=[r for r in R if r[0]==d]
        flat=[r[1] for r in prior if r[0]>='2018-01-01']; pf=sum(flat)/len(flat)
        if rule=='flat': p=pf
        elif rule=='prior_only':
            W=prior[-win:]; Y=[r[1] for r in W]; z,i=bestsplit(Y,minseg)
            p=sum(Y[i:])/len(Y[i:]) if (i is not None and abs(z)>zc) else pf
        elif rule.startswith('fixed:'):
            bd=rule[6:]
            post=[r[1] for r in prior if r[0]>=bd]
            p=sum(post)/len(post) if (d>bd and len(post)>=minseg) else pf
        out[d]=[ll(p,r[1]) for r in te]
    return out
def summ(o):
    S={'2019-2025':[],'2026 to Jun 21':[],'Jun 22 - Nov 7 2026':[]}
    for d,v in o.items():
        k='2019-2025' if d<'2026-01-01' else ('2026 to Jun 21' if d<'2026-06-22' else 'Jun 22 - Nov 7 2026')
        S[k]+=v
    return {k:(round(sum(v)/len(v),4),len(v)) for k,v in S.items()}
import sys
res={}
for rule in ['flat','prior_only','fixed:2026-05-16','fixed:2026-06-22']:
    o=run(rule); res[rule]=o; print(rule,summ(o),flush=True)
json.dump({k:v for k,v in res.items()},open('step_out.json','w'))
