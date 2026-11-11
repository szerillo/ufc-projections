# Block 17 analyses. Inputs: bfo_named.txt (BFO re-pull Nov 11: event id | name key | multiplicative GTD x1000 | median US ITD decimal x100),
# /home/claude/work/mkt/gtd_market_post_june.json (date, stored US close, outcome), /tmp/rows2010.json, bp_close.json (bot snapshots).
import json,math,random,statistics as st,collections,unicodedata
import numpy as np
from scipy.stats import beta,norm
out={}
# ---------- 1. 2026 episode under both reversion definitions (no re-run of the historical test)
def wilson(k,n,z):
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return (c-h)/d,(c+h)/d
R=sorted(json.load(open('/tmp/rows2010.json')))
i0=next(i for i,r in enumerate(R) if r[0]>='2026-06-27')
nx200=[r[1] for r in R[i0:i0+200]]; nxall=[r[1] for r in R[i0:] if r[0]<'2026-11-08']
for lab,ref in (('v1 pre-split rate in window',0.557),('v2 trailing-1000 mean',0.515)):
    for nm,v in (('next 200',nx200),('all after flag',nxall)):
        k=sum(v);n=len(v);x=k/n; z=(x-ref)/math.sqrt(ref*(1-ref)/n)
        out['rev %s | %s'%(lab,nm)]=dict(n=n,rate=round(x,3),ref=ref,z=round(z,2),ci90=[round(t,3) for t in wilson(k,n,1.645)],ci95=[round(t,3) for t in wilson(k,n,1.96)])
# ---------- 2. power
sd=0.1028; obs=0.0082; se=0.0107
def obf_power(mu_bout,N=100000,seed=1):
    rng=np.random.default_rng(seed); looks=np.array([250,500,750,970]); b=np.array([4.05,2.86,2.34,2.02]); m=mu_bout/sd
    S=np.cumsum(rng.standard_normal((N,4))*np.sqrt(np.diff(np.r_[0,looks])),axis=1)+m*looks; Z=S/np.sqrt(looks)
    alive=np.ones(N,bool); win=np.zeros(N,bool); fut=np.zeros(N,bool)
    for k in range(4):
        p=alive&(Z[:,k]>=b[k]); win|=p; alive&=~p; f=alive&(Z[:,k]<-1.645); fut|=f; alive&=~f
    return round(win.mean(),3),round(fut.mean(),3)
js=max(0,1-(se/obs)**2)*obs  # positive-part James-Stein toward 0
for lab,mu in (('in-sample 0.0082',obs),('half 0.0041',obs/2),('James-Stein shrunk %.4f'%js,js),('LOCO out-of-sample -0.0062',-0.0062)):
    out['power '+lab]=obf_power(mu)
for a,lab in ((0.05,'one-sided 5%'),(0.025,'one-sided 2.5%')):
    out['fixed n for 80%% at 0.0082, %s'%lab]=round(((norm.ppf(1-a)+norm.ppf(.8))*sd/obs)**2)
    out['fixed n for 80%% at 0.0041, %s'%lab]=round(((norm.ppf(1-a)+norm.ppf(.8))*sd/(obs/2))**2)
# ---------- 3. gap: which stored bouts are not in the BFO re-pull
DM={'4230':'2026-06-27','4252':'2026-07-11','4216':'2026-07-25','4285':'2026-08-01','4301':'2026-08-08','4297':'2026-08-15','4320':'2026-08-22','4311':'2026-08-22',
'4257':'2026-08-29','4326':'2026-09-05','4318':'2026-09-12','4303':'2026-09-19','4368':'2026-09-26','4330':'2026-10-03','4378':'2026-10-10',
'4402':'2026-10-17','4403':'2026-10-17','4321':'2026-10-24','4427':'2026-10-31','4437':'2026-11-07','4439':'2026-11-07'}
B=[]
for t in open('bfo_named.txt').read().strip().split(';'):
    e,k,m,itd=t.split('|'); B.append(dict(date=DM[e],ev=e,key=k,p=int(m)/1000,itd=int(itd)/100))
M=json.load(open('/home/claude/work/mkt/gtd_market_post_june.json'))
used=[False]*len(M); pair=[]
for b in B:
    j=next((j for j,m in enumerate(M) if not used[j] and m[0]==b['date'] and abs(m[1]-b['p'])<=0.0015),None)
    if j is None: j=next((j for j,m in enumerate(M) if not used[j] and m[0]==b['date'] and abs(m[1]-b['p'])<=0.02),None)
    if j is None: b['matched']=False; continue
    used[j]=True; b['matched']=True; b['y']=M[j][2]; b['stored']=M[j][1]; pair.append(b)
miss=[dict(i=j,date=M[j][0],stored_p=M[j][1],y=M[j][2]) for j in range(len(M)) if not used[j]]
out['stored bouts not matched']=miss
out['BFO bouts not matched to stored']=[(b['date'],b['key'],b['p']) for b in B if not b['matched']]
def gap(P,Y):
    d=[p-y for p,y in zip(P,Y)]; n=len(d); m=sum(d)/n; s=st.stdev(d)/math.sqrt(n); return dict(n=n,gap=round(100*m,1),ci90=[round(100*(m-1.645*s),1),round(100*(m+1.645*s),1)])
out['gap all 214']=gap([m[1] for m in M],[m[2] for m in M])
out['gap without the unmatched']=gap([M[j][1] for j in range(len(M)) if used[j]],[M[j][2] for j in range(len(M)) if used[j]])
out['gap the unmatched only']=gap([x['stored_p'] for x in miss],[x['y'] for x in miss])
# ---------- 4. post-hoc ITD flat 1u at median US ITD close price
def roi(S,seed=4):
    pnl=[(b['itd']-1) if b['y']==0 else -1 for b in S]; n=len(pnl); r=sum(pnl)/n
    cards=collections.defaultdict(list)
    for b,x in zip(S,pnl): cards[b['date']].append(x)
    C=list(cards.values()); rng=random.Random(seed); bs=[]
    for _ in range(4000):
        s=[rng.choice(C) for _ in C]; bs.append(sum(map(sum,s))/sum(map(len,s)))
    bs.sort(); return dict(n=n,cards=len(C),units=round(sum(pnl),2),roi=round(100*r,1),ci90=[round(100*bs[200],1),round(100*bs[3799],1)],finish_rate=round(sum(1-b['y'] for b in S)/n,3),mean_be=round(sum(1/b['itd'] for b in S)/n,3))
out['ITD Jun-Aug']=roi([b for b in pair if b['date']<'2026-09-01'])
out['ITD Sep-Nov']=roi([b for b in pair if b['date']>='2026-09-01'])
out['ITD all']=roi(pair)
# ---------- assumption: BFO last price vs BettingPros last pre-start snapshot
BP=json.load(open('bp_close.json'))
k5=lambda s:unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().split(' ')[-1].lower()
k5=lambda s,f=k5:''.join(c for c in f(s) if c.isalpha())[:5]
cmp=[]
for x in BP:
    key='-'.join(sorted([k5(x['a']),k5(x['b'])]))
    b=next((b for b in B if b['key']==key),None)
    if b: cmp.append(dict(bout=x['a']+' vs '+x['b'],sched=x['sched'],bp=x['p'],bfo=b['p'],diff=round(100*(b['p']-x['p']),1),bp_pull_mins_before=x['mins_before']))
d=[c['diff'] for c in cmp]
out['BFO vs bot: matched bouts']=len(cmp)
if d: out['BFO vs bot: mean abs diff pts']=round(st.mean(map(abs,d)),2); out['BFO vs bot: mean diff pts']=round(st.mean(d),2)
out['BFO vs bot: bouts with bot pull within 60 min']=[c for c in cmp if c['bp_pull_mins_before']<=60]
out['BFO vs bot: first 10 by bot pull closeness']=sorted(cmp,key=lambda c:c['bp_pull_mins_before'])[:10]
json.dump(out,open('analysis_out.json','w'),indent=1); print(json.dumps(out,indent=1))
# summary of BFO-vs-bot by how close the bot's last pre-start pull was
for lim in (30,60,24*60):
    S=[c for c in cmp if c['bp_pull_mins_before']<=lim]
    if S: out['BFO vs bot, pull within %d min'%lim]=dict(n=len(S),mean_abs=round(st.mean(abs(c['diff']) for c in S),2),mean=round(st.mean(c['diff'] for c in S),2),max_abs=max(abs(c['diff']) for c in S))
json.dump(out,open('analysis_out.json','w'),indent=1)
for k in list(out)[-3:]: print(k,out[k])
