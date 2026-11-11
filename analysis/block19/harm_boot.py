# Null check of the harm stop using the SAME card bootstrap as the lock (not a normal approximation).
# Null data: per-bout d = LL(close) - LL(sheet) from the sheet check (92 bouts, 8 cards), re-centred to mean 0 per bout pool.
# A forward record is built by drawing whole cards (with replacement) from those 8 cards until it passes each look's bout count.
import json,math,numpy as np
E=json.load(open('/home/claude/work/b14/sheet_E.json'))
def ll(p,y): p=min(max(p,1e-4),1-1e-4); return -(y*math.log(p)+(1-y)*math.log(1-p))
cards={}
for d in E: cards.setdefault(d['card'],[]).append(ll(d['us'],d['y'])-ll(d['s'],d['y']))
mu=np.mean([x for v in cards.values() for x in v]); C=[np.array(v)-mu for v in cards.values()]
looks=[250,500,750,970]; rng=np.random.default_rng(2026); S=2000; B=400
stops=np.zeros(4); anystop=0; passes=0; bnd=[4.05,2.86,2.34,2.02]; zs=[[] for _ in looks]; se_b=[[] for _ in looks]; means=[[] for _ in looks]
for s in range(S):
    rec=[];stopped=False
    for k,L in enumerate(looks):
        while sum(len(c) for c in rec)<L: rec.append(C[rng.integers(len(C))])
        sums=np.array([c.sum() for c in rec]); lens=np.array([len(c) for c in rec]); n=len(rec)
        m=sums.sum()/lens.sum()
        idx=rng.integers(n,size=(B,n)); bm=sums[idx].sum(1)/lens[idx].sum(1); se=bm.std(ddof=1)
        z=m/se; zs[k].append(z); se_b[k].append(se); means[k].append(m)
        if not stopped and z>=bnd[k]: passes+=1; stopped=True
        if not stopped and z< -1.645: stops[k]+=1; stopped=True
    anystop+=stopped
out={'sims':S,'boot_reps':B,'harm_stop_any_look':round(float(stops.sum())/S,4),'harm_stop_by_look':[round(x/S,4) for x in stops],'false_pass':round(passes/S,4)}
for k,L in enumerate(looks):
    out['look_%d'%L]=dict(mean_boot_se=round(float(np.mean(se_b[k])),5),true_sd_of_mean=round(float(np.std(means[k])),5),
        ratio=round(float(np.mean(se_b[k])/np.std(means[k])),3),one_look_rate_z_below_neg1645=round(float(np.mean(np.array(zs[k])<-1.645)),4))
json.dump(out,open('harm_boot_out.json','w'),indent=1); print(json.dumps(out,indent=1))
