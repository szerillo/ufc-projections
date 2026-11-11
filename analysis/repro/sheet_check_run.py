import json,math,random,statistics as st,sys,unicodedata
sys.path.insert(0,'/home/claude/ufc-projections/scripts'); from card_overrides import same
def nrm(s): return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
card={'9/19':'2026-09-19','9/26':'2026-09-26','10/3':'2026-10-03','10/10':'2026-10-10','10/17':'2026-10-17','10/24':'2026-10-24','10/31':'2026-10-31','11/7':'2026-11-07'}
rows4=[x for x in json.load(open('/home/claude/work/audit/rows4.json')) if x.get('status')!='no result match']
M={}
for l in open('/home/claude/work/props_retro/gtd_close.txt'):
    b,pr=l.strip().split('|'); bk={t[:2]:float(t[2:]) for t in pr.split(',')}
    if 'BR' in bk and 'UB' in bk and bk['BR']==bk['UB']: bk.pop('UB')
    if len(bk)>=2: M[nrm(b)]=st.median(bk.values())
D=[];miss=[];mism=[]
for l in open('snap.txt'):
    dt,a,b,play,y,lst,cl,out=l.strip().split('|')
    c=card[dt]
    if a=='Amaya': continue
    r=next((r for r in rows4 if r['card']==c and nrm(a) in nrm(r['bout']) and nrm(b.split('-')[0]) in nrm(r['bout'])),None)
    if r is None: r=next((r for r in rows4 if r['card']==c and (nrm(a) in nrm(r['bout']) or nrm(b.split('-')[0]) in nrm(r['bout']))),None)
    if r is None: miss.append(l.strip()); continue
    o=r['dec']
    if out!='' and int(out)!=o: mism.append((r['bout'],out,o))
    k=next((k for k in M if nrm(a) in k and nrm(b.split('-')[0]) in k),None)
    if k is None: k=next((k for k in M if (nrm(a) in k or nrm(b.split('-')[0]) in k) and any(same(p,q) for p in k.split(' vs ') for q in r['bout'].split(' vs '))),None)
    D.append(dict(card=c,bout=r['bout'],s=float(y),L=float(lst) if lst else None,us=M.get(k),y=o,play=play,blank=(out=='')))
print('rows',len(D),'unmatched',miss,'sheet-vs-mapping outcome mismatches',mism,'blank sheet outcomes',[d['bout'] for d in D if d['blank']])
E=[d for d in D if d['us'] is not None]; n=len(E); print('with US close',n)
def ll(p,y): p=min(max(p,1e-4),1-1e-4); return -(y*math.log(p)+(1-y)*math.log(1-p))
lg=lambda p: math.log(min(max(p,.01),.99)/(1-min(max(p,.01),.99))); sg=lambda z:1/(1+math.exp(-z))
print('log loss sheet %.4f US close %.4f'%(st.mean(ll(d['s'],d['y']) for d in E),st.mean(ll(d['us'],d['y']) for d in E)))
for nm,f in (('sheet - outcome',lambda d:d['s']-d['y']),('sheet - US close',lambda d:d['s']-d['us']),('US close - outcome',lambda d:d['us']-d['y'])):
    v=[f(d) for d in E]; m=st.mean(v); se=st.pstdev(v)/math.sqrt(n); print('%-18s %+.3f 90%% [%+.3f, %+.3f]'%(nm,m,m-1.645*se,m+1.645*se))
def bl(d,k): return sg(lg(d['us'])+k*(lg(d['s'])-lg(d['us'])))
def fitk(S): return min(((k/100,sum(ll(bl(d,k/100),d['y']) for d in S)) for k in range(-100,201,2)),key=lambda t:t[1])[0]
cards=sorted(set(d['card'] for d in E)); L0=L1=0;w=0
for c in cards:
    tr=[d for d in E if d['card']!=c]; te=[d for d in E if d['card']==c]; k=fitk(tr)
    a=sum(ll(d['us'],d['y']) for d in te); b=sum(ll(bl(d,k),d['y']) for d in te); L0+=a; L1+=b; w+=b<a
random.seed(20261111); bs=sorted(fitk([d for c in [random.choice(cards) for _ in cards] for d in E if d['card']==c]) for _ in range(1000))
print('LOCO: close %.4f blend %.4f; blend better on %d/%d cards; k_all %+.2f boot90 [%+.2f, %+.2f]'%(L0/n,L1/n,w,len(cards),fitk(E),bs[50],bs[949]))
lean=[d for d in D if ('GTD+' in d['play'] or 'ITD+' in d['play'] or '+' in d['play']) and d['us'] is not None]
for side in ('GTD','ITD'):
    S=[d for d in lean if d['play'].startswith(side)]
    if not S: continue
    hit=sum(d['y'] if side=='GTD' else 1-d['y'] for d in S); exp=sum(d['us'] if side=='GTD' else 1-d['us'] for d in S)
    print(side,'leans n=%d hits %d, close-implied %.1f'%(len(S),hit,exp))
