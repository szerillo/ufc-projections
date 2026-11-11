# Assumption check: harm-stop false-stop rate when cards are clustered by event month (resampling unit = month block,
# both in building the null record and in the bootstrap), vs the card-level version (block 19: 16.9%).
import json,math,numpy as np
E=json.load(open('/home/claude/work/b14/sheet_E.json'))
def ll(p,y): p=min(max(p,1e-4),1-1e-4); return -(y*math.log(p)+(1-y)*math.log(1-p))
months={}
for d in E: months.setdefault(d['card'][:7],[]).append(ll(d['us'],d['y'])-ll(d['s'],d['y']))
mu=np.mean([x for v in months.values() for x in v]); M=[np.array(v)-mu for v in months.values()]
print('month blocks:',{k:len(v) for k,v in months.items()})
looks=[250,500,750,970]; bnd=[4.05,2.86,2.34,2.02]; rng=np.random.default_rng(2026); S=2000; B=400
stops=np.zeros(4); passes=0; ratio=[[] for _ in looks]; means=[[] for _ in looks]
for s in range(S):
    rec=[];stopped=False
    for k,L in enumerate(looks):
        while sum(len(c) for c in rec)<L: rec.append(M[rng.integers(len(M))])
        sums=np.array([c.sum() for c in rec]); lens=np.array([len(c) for c in rec]); n=len(rec)
        m=sums.sum()/lens.sum(); idx=rng.integers(n,size=(B,n)); bm=sums[idx].sum(1)/lens[idx].sum(1); se=bm.std(ddof=1)
        z=m/se; ratio[k].append(se); means[k].append(m)
        if not stopped and z>=bnd[k]: passes+=1; stopped=True
        if not stopped and z<-1.645: stops[k]+=1; stopped=True
out=dict(unit='event month',sims=S,boot_reps=B,harm_stop_any_look=round(float(stops.sum())/S,4),harm_stop_by_look=[round(x/S,4) for x in stops],false_pass=round(passes/S,4),
  se_calibration=[round(float(np.mean(ratio[k])/np.std(means[k])),3) for k in range(4)],card_level_block19=0.1685)
json.dump(out,open('harm_boot_month_out.json','w'),indent=1); print(json.dumps(out,indent=1))
