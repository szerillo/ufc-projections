import json,math,random
E=json.load(open('sheet_E.json'))
def ll(p,y): p=min(max(p,1e-4),1-1e-4); return -(y*math.log(p)+(1-y)*math.log(1-p))
lg=lambda p: math.log(min(max(p,.01),.99)/(1-min(max(p,.01),.99))); sg=lambda z:1/(1+math.exp(-z))
for d in E: d['a']=lg(d['us']); d['g']=lg(d['s'])-d['a']
def fitk(S):
    best=None
    for k in range(-100,201,4):
        k/=100; L=sum(ll(sg(d['a']+k*d['g']),d['y']) for d in S)
        if best is None or L<best[1]: best=(k,L)
    return best[0]
cards=sorted(set(d['card'] for d in E))
def bar(S):
    L0=L1=0;w=0
    for c in cards:
        tr=[d for d in S if d['card']!=c]; te=[d for d in S if d['card']==c]; k=fitk(tr)
        a=sum(ll(sg(d['a']),d['y']) for d in te); b=sum(ll(sg(d['a']+k*d['g']),d['y']) for d in te); L0+=a;L1+=b;w+=b<a
    bs=sorted(fitk([d for c in [random.choice(cards) for _ in cards] for d in S if d['card']==c]) for _ in range(150))
    return (L1<L0) and w>=5 and bs[7]>0, L1<L0, w>=5, bs[7]>0
random.seed(7); res=[]
for scale in (1.0,2.0):
    res=[]
    for i in range(150):
        S=[dict(d,y=int(random.random()<sg(d['a']+scale*d['g']))) for d in E]
        res.append(bar(S))
    print('true k=%.1f: pass all three %.2f | LOCO better %.2f | 5+ cards %.2f | boot lower >0 %.2f'%(scale,*[sum(r[j] for r in res)/len(res) for j in range(4)]),flush=True)
