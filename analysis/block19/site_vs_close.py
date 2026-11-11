# Runs LOCK_site_vs_close.md (sha256 e8dba621..., commit a84d9a83) exactly as written.
import json,math,random,statistics as st,sys,unicodedata,collections
sys.path.insert(0,'/home/claude/ufc-projections/scripts'); from result_outcomes import gtd
REPO='/home/claude/ufc-projections'
cards={'2026-10-17':('ufc-fight-night-buckley-vs-malott.json','2026-10-17-ufc-fight-night-buckley-vs-malott.json',['4402','4403']),
       '2026-10-31':('ufc-fight-night-moicano-vs-nolan.json','2026-10-31-ufc-fight-night-moicano-vs-nolan.json',['4427']),
       '2026-11-07':('ufc-vegas-124-cortes-acosta-walker.json','2026-11-07-ufc-fight-night-cortes-acosta-vs-walker.json',['4437','4439'])}
def k5(x):
    x=unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode().split(' ')[-1].lower(); return ''.join(c for c in x if c.isalpha())[:5]
BFO={}
for t in open('/home/claude/work/b17/bfo_named.txt').read().strip().split(';'):
    e,k,m,itd=t.split('|'); BFO[(e,k)]=int(m)/1000
nm=lambda s:unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
rows=[];drop=[]
for date,(cf,ef,evs) in cards.items():
    C=json.load(open(f'{REPO}/data/cards/{cf}')); E=json.load(open(f'{REPO}/form/data/events/{ef}'))
    for fx in C['fights']:
        a,b=fx['bout'].split(' vs '); key='-'.join(sorted([k5(a),k5(b)]))
        close=next((BFO[(e,key)] for e in evs if (e,key) in BFO),None)
        ev=next((x for x in E['fights'] if {k5(x['a']['name']),k5(x['b']['name'])}=={k5(a),k5(b)}),None)
        y=gtd(ev.get('result')) if ev else None
        if close is None or y is None: drop.append((date,fx['bout'],'no close' if close is None else 'no outcome')); continue
        rows.append(dict(card=date,bout=fx['bout'],site=fx['duration']['p_dec']/100,close=close,y=y))
def ll(p,y): p=min(max(p,1e-4),1-1e-4); return -(y*math.log(p)+(1-y)*math.log(1-p))
def summ(R,label):
    o={'set':label,'n':len(R),'cards':len(set(r['card'] for r in R)),'decisions':sum(r['y'] for r in R)}
    for k in ('site','close'):
        o['brier_'+k]=round(st.mean((r[k]-r['y'])**2 for r in R),4); o['ll_'+k]=round(st.mean(ll(r[k],r['y']) for r in R),4)
        b=[r[k]-r['y'] for r in R]; m=st.mean(b); se=st.stdev(b)/math.sqrt(len(b)); o['bias_'+k]=[round(100*m,1),round(100*(m-1.645*se),1),round(100*(m+1.645*se),1)]
    d=[ll(r['close'],r['y'])-ll(r['site'],r['y']) for r in R]; o['mean_d (close LL - site LL)']=round(st.mean(d),4)
    C=collections.defaultdict(list)
    for r,x in zip(R,d): C[r['card']].append(x)
    C=list(C.values()); rng=random.Random(19)
    bs=sorted(sum(map(sum,s))/sum(map(len,s)) for s in ([rng.choice(C) for _ in C] for _ in range(4000)))
    o['card_boot90']=[round(bs[200],4),round(bs[3799],4)]
    bb=sorted(st.mean(rng.choice(d) for _ in d) for _ in range(4000)); o['bout_boot90']=[round(bb[200],4),round(bb[3799],4)]
    o['site_mean_vs_close_mean']=(round(100*st.mean(r['site'] for r in R),1),round(100*st.mean(r['close'] for r in R),1),round(100*st.mean(r['y'] for r in R),1))
    o['verdict_has_been_right']=bool(o['mean_d (close LL - site LL)']>0 and o['card_boot90'][0]>0)
    return o
out={'primary':summ(rows,'site cards Oct 17, Oct 31, Nov 7'),'dropped':drop}
# secondary: archive cards 1-8 (rows4), card 1 layout handled in rows4; matched to the same close by surnames
A=json.load(open('/home/claude/work/audit/rows4.json'))
DM={'4318':'2026-09-12','4303':'2026-09-19','4368':'2026-09-26','4330':'2026-10-03','4378':'2026-10-10','4402':'2026-10-17','4403':'2026-10-17','4321':'2026-10-24','4427':'2026-10-31','4437':'2026-11-07','4439':'2026-11-07'}
sec=[]
for r in A:
    if r.get('dec') is None or r.get('pdec') is None: continue
    a,b=r['bout'].split(' vs '); key='-'.join(sorted([k5(a),k5(b)]))
    c=next((p for (e,k),p in BFO.items() if k==key and DM.get(e)==r['card']),None)
    if c is None: continue
    sec.append(dict(card=r['card'],bout=r['bout'],site=r['pdec'],close=c,y=r['dec']))
out['secondary']=summ(sec,'Markov archive cards 1-8 (descriptive)')
json.dump(out,open('site_vs_close_out.json','w'),indent=1); print(json.dumps(out,indent=1))
