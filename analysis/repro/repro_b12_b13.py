# Re-derive block 12-13 numbers from saved inputs. Inputs: /tmp/rows2010.json (date, decision 0/1, division;
# UFCStats via Greco1899 dataset, draw = decision, NC out) and work/mkt/gtd_market_post_june.json (date, US close mult, outcome).
import json,math,random,statistics as st
R=sorted(json.load(open('/tmp/rows2010.json'))); M=json.load(open('/home/claude/work/mkt/gtd_market_post_june.json'))
rate=lambda v:sum(v)/len(v)
def sel(lo,hi): return [r[1] for r in R if lo<=r[0]<hi]
out={}
# B12 s1 placebo scan: split (2018-01-01..cut) vs (cut..2026-11-08), cut at every event date 2025-26 with >=100 bouts each side
def scan(Y,D):
    cuts=sorted(set(d for d in D if '2025-01-01'<=d<'2026-11-08')); res=[]
    for c in cuts:
        a=[y for y,d in zip(Y,D) if d<c]; b=[y for y,d in zip(Y,D) if d>=c]
        if len(a)<100 or len(b)<100: continue
        p=rate(Y); z=(rate(b)-rate(a))/math.sqrt(p*(1-p)*(1/len(a)+1/len(b))); res.append((z,c,len(b)))
    return res
S=[r for r in R if '2018-01-01'<=r[0]<'2026-11-08']; Y=[r[1] for r in S]; D=[r[0] for r in S]
sc=sorted(scan(Y,D)); out['placebo_n_cuts']=len(sc); out['placebo_top']=[(c,round(z,2),n) for z,c,n in sc[:3]]
out['rank_2026-06-27']=[c for z,c,n in sc].index('2026-06-27')+1
random.seed(12); mx=[]
for _ in range(500):
    Ys=Y[:]; random.shuffle(Ys); mx.append(max(abs(z) for z,c,n in scan(Ys,D)))
mx.sort(); out['perm_bout_500_p95_p99_max']=(round(mx[474],2),round(mx[494],2),round(mx[-1],2))
# rates
out['2018-24']=(round(rate(sel('2018-01-01','2025-01-01')),4),len(sel('2018-01-01','2025-01-01')))
out['2026_to_Jun21']=(round(rate(sel('2026-01-01','2026-06-22')),4),len(sel('2026-01-01','2026-06-22')))
out['Jun22_Nov7']=(round(rate(sel('2026-06-22','2026-11-08')),4),len(sel('2026-06-22','2026-11-08')))
out['Jan2025_Nov7_2026']=(round(rate(sel('2025-01-01','2026-11-08')),4),len(sel('2025-01-01','2026-11-08')))
out['Jan2025_Jun21_2026']=(round(rate(sel('2025-01-01','2026-06-22')),4),len(sel('2025-01-01','2026-06-22')))
# B12 s3 market gap
def gap(rows):
    d=[p-y for _,p,y in rows]; n=len(d); m=rate(d); se=st.pstdev(d)/math.sqrt(n)
    return (n,round(100*rate([p for _,p,_ in rows]),1),round(100*rate([y for *_,y in rows]),1),round(100*m,1),round(100*(m-1.645*se),1),round(100*(m+1.645*se),1))
out['gap_all']=gap(M); out['gap_cards1_8']=gap([m for m in M if m[0]>='2026-09-19']); out['gap_cards2_8']=gap([m for m in M if m[0]>='2026-09-26'])
out['gap_by_month']={mo:gap([m for m in M if m[0][5:7]==mo])[::3] for mo in ('06','07','08','09','10','11')}
# B13 s2 yearly windows
yt={}
for y in range(2018,2027):
    a=[r[1] for r in R if r[0][:4]==str(y) and r[0][5:]<'05-16']; b=[r[1] for r in R if r[0][:4]==str(y) and '05-16'<=r[0][5:]<'11-08']; c=[r[1] for r in R if r[0][:4]==str(y) and r[0][5:]>='11-08']
    rest=a+c; yt[y]=(round(100*rate(a),1),len(a),round(100*rate(b),1),len(b),(round(100*rate(c),1),len(c)) if c else None,round(100*(rate(b)-rate(rest)),1))
out['year_table']=yt
# B13 s4 bias power (per-bout sd 0.45)
from statistics import NormalDist as N
for eff in (0.03,0.044,0.05):
    out['bias_n_%.3f'%eff]=(round(((N().inv_cdf(.95)+N().inv_cdf(.8))*0.45/eff)**2),round(((N().inv_cdf(.975)+N().inv_cdf(.8))*0.45/eff)**2))
json.dump(out,open('repro_b12_b13_out.json','w'),indent=1,default=str); print(json.dumps(out,indent=1,default=str))
