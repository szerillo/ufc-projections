# Prior-only step detector (same as step.py rule: last 1,000 earlier bouts, min segment 50, abs z > 3).
# Episodes of NEGATIVE flags since 2013; reversion test on the next 200 bouts after the first flag.
import json,math,sys
exec(open('step.py').read().split('def run(')[0])
MS=int(sys.argv[1]) if len(sys.argv)>1 else 50
idx={d:i for i,d in enumerate(r[0] for r in R)}  # first index of date (dict keeps last; fix below)
first={}
for i,r in enumerate(R): first.setdefault(r[0],i)
ev=[d for d in dates if d>='2013-01-01']
fires=[]
for d in ev:
    i0=first[d]; W=R[max(0,i0-1000):i0]; Y=[r[1] for r in W]; z,i=bestsplit(Y,MS)
    if i is not None and abs(z)>3: fires.append((d,z,sum(Y[:i])/i,sum(Y[i:])/(len(Y)-i),W[i][0]))
eps=[];prev=None
for f in fires:
    sign=f[1]<0
    if eps and eps[-1]['sign']==sign and (dates.index(f[0])-dates.index(eps[-1]['last']))<=3: eps[-1]['last']=f[0]; eps[-1]['n']+=1; continue
    eps.append(dict(first=f[0],last=f[0],sign=sign,z=round(f[1],2),pre=round(f[2],3),post=round(f[3],3),split=f[4],n=1))
out=[]
for e in eps:
    i0=first[e['first']]; nxt=[r[1] for r in R[i0:i0+200]]
    if len(nxt)<200: e['next200']=None; e['verdict']='open'
    else:
        m=sum(nxt)/200; e['next200']=round(m,3)
        e['verdict']='reverted' if abs(m-e['pre'])<abs(m-e['post']) else 'persisted'
    out.append(e); print(e)
neg=[e for e in out if e['sign']]; done=[e for e in neg if e['verdict']!='open']
print('MS',MS,'negative episodes',len(neg),'closed',len(done),'reverted',sum(e['verdict']=='reverted' for e in done),'| positive episodes',len(out)-len(neg))
json.dump(out,open('falsealarm_ms%d.json'%MS,'w'),indent=1)
# Second reversion test: next 200 bouts vs the trailing-1,000 mean at the first flag
print('--- vs trailing-1000 mean')
for e in out:
    i0=first[e['first']]; t=sum(r[1] for r in R[i0-1000:i0])/1000; e['trail']=round(t,3)
    if e['next200'] is None: e['v2']='open'
    else: e['v2']='reverted' if abs(e['next200']-t)<abs(e['next200']-e['post']) else 'persisted'
    print(e['first'],'neg' if e['sign'] else 'pos','post %.3f trail %.3f next200 %s -> %s'%(e['post'],t,e['next200'],e['v2']))
for s,lab in ((True,'neg'),(False,'pos')):
    E=[e for e in out if e['sign']==s and e['first']<'2026']; print(lab,'pre-2026 episodes',len(E),'reverted (vs trailing)',sum(e['v2']=='reverted' for e in E))
json.dump(out,open('falsealarm_ms%d.json'%MS,'w'),indent=1)
