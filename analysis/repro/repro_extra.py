import json,math
import numpy as np
M=json.load(open('/home/claude/work/mkt/gtd_market_post_june.json')); R=json.load(open('/tmp/rows2010.json'))
mo=np.array([int(m[0][5:7]) for m in M]); g=np.array([m[1]-m[2] for m in M])
X=np.c_[np.ones(len(g)),mo]; b,res,*_=np.linalg.lstsq(X,g,rcond=None); s2=((g-X@b)**2).sum()/(len(g)-2); se=math.sqrt(s2*np.linalg.inv(X.T@X)[1,1])
print('bout-level OLS trend per month %.1f se %.1f'%(100*b[1],100*se))
mm=sorted(set(mo)); gm=np.array([g[mo==k].mean() for k in mm]); w=np.array([(mo==k).sum() for k in mm])
Xm=np.c_[np.ones(len(mm)),mm]; W=np.diag(w); bm=np.linalg.solve(Xm.T@W@Xm,Xm.T@W@gm); print('weighted monthly trend %.1f'%(100*bm[1]))
q=[r[1] for r in R if '2026-01-01'<=r[0]<'2026-04-01']; print('2026 Q1 decisions %.1f%% n=%d'%(100*sum(q)/len(q),len(q)))
