# Match the fresh BFO re-pull (bfo176.txt: per event id, multiplicative,power de-vig x1000)
# to the 214-bout market set (mkt/gtd_market_post_june.json: date, multiplicative p, outcome) by date + p.
import json,math,collections
DM={'4230':'2026-06-27','4285':'2026-08-01','4326':'2026-09-05','4252':'2026-07-11','4216':'2026-07-25','4301':'2026-08-08','4297':'2026-08-15','4320':'2026-08-22','4311':'2026-08-22',
'4257':'2026-08-29','4318':'2026-09-12','4303':'2026-09-19','4368':'2026-09-26','4330':'2026-10-03','4378':'2026-10-10',
'4402':'2026-10-17','4403':'2026-10-17','4321':'2026-10-24','4427':'2026-10-31','4437':'2026-11-07','4439':'2026-11-07'}
B=[]
for g in open('bfo_all.txt').read().strip().split('/'):
    e,v=g.split(':')
    for t in v.split(): m,p=t.split(','); B.append([DM[e],int(m)/1000,int(p)/1000])
M=json.load(open('/home/claude/work/mkt/gtd_market_post_june.json'))
print('BFO',len(B),'market set',len(M))
used=[False]*len(M); pairs=[]; unmatchedB=[]
for b in B:
    j=next((j for j,m in enumerate(M) if not used[j] and m[0]==b[0] and abs(m[1]-b[1])<=0.0015),None)
    if j is None: j=next((j for j,m in enumerate(M) if not used[j] and m[0]==b[0] and abs(m[1]-b[1])<=0.02),None)
    if j is None: unmatchedB.append(b); continue
    used[j]=True; pairs.append((b,M[j]))
drop=[M[j] for j in range(len(M)) if not used[j]]
print('matched',len(pairs),'exact(<=0.0015)',sum(abs(b[1]-m[1])<=0.0015 for b,m in pairs),'BFO unmatched',len(unmatchedB),'market-set bouts not in BFO pull',len(drop))
print('drop by date',sorted(collections.Counter(d[0] for d in drop).items()))
print('BFO unmatched by date',sorted(collections.Counter(b[0] for b in unmatchedB).items()))
def gap(P,Y):
    d=[p-y for p,y in zip(P,Y)]; n=len(d); m=sum(d)/n; sd=math.sqrt(sum((x-m)**2 for x in d)/(n-1)); se=sd/math.sqrt(n)
    return '%+.1f [%+.1f, %+.1f] n=%d, mean close %.1f%%, outcome %.1f%%'%(100*m,100*(m-1.645*se),100*(m+1.645*se),n,100*sum(P)/n,100*sum(Y)/n)
print('all 214 (stored mult):',gap([m[1] for m in M],[m[2] for m in M]))
print('matched, stored mult  :',gap([m[1] for b,m in pairs],[m[2] for b,m in pairs]))
print('matched, fresh mult   :',gap([b[1] for b,m in pairs],[m[2] for b,m in pairs]))
print('matched, fresh power  :',gap([b[2] for b,m in pairs],[m[2] for b,m in pairs]))
print('dropped bouts          :',gap([m[1] for m in drop],[m[2] for m in drop]))
# Summer sensitivity on the full stored 214
for lab,f in (('Jun-Aug only',lambda m:m[0]<'2026-09-01'),('Sep-Nov only',lambda m:m[0]>='2026-09-01'),('without Jun 27, Jul 18, Aug 1, Sep 5',lambda m:m[0] not in ('2026-06-27','2026-07-18','2026-08-01','2026-09-05'))):
    S=[m for m in M if f(m)]; print(lab+':',gap([m[1] for m in S],[m[2] for m in S]))
