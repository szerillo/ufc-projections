# Null simulation of the forward pass bar (LOCK_forward_record_passbar.md): looks at 250/500/750/970 bouts,
# efficacy z >= 4.05/2.86/2.34/2.02; futility (non-binding) if upper one-sided 95% bound < 0, i.e. z < -1.645.
import numpy as np
rng=np.random.default_rng(20261111); N=100000
looks=np.array([250,500,750,970]); bnd=np.array([4.05,2.86,2.34,2.02])
inc=rng.standard_normal((N,4))*np.sqrt(np.diff(np.r_[0,looks]))
S=np.cumsum(inc,axis=1); Z=S/np.sqrt(looks)
def run(Z,futility):
    alive=np.ones(len(Z),bool); passed=np.zeros(len(Z),bool); stop=np.full(len(Z),-1)
    for k in range(4):
        p=alive&(Z[:,k]>=bnd[k]); passed|=p; stop[p]=k; alive&=~p
        if futility: f=alive&(Z[:,k]<-1.645); stop[f]=k; alive&=~f
    return passed.mean()
print('null alpha, efficacy only (binding-free):',run(Z,False))
print('null alpha, with futility stops:',run(Z,True))
print('null alpha first 10k runs:',run(Z[:10000],False))
# classical OBF for K=4 equal spacing one-sided 0.025: c=2.024 -> c*sqrt(4/k)
print('OBF c*sqrt(K/k):',[round(2.024*np.sqrt(4/k),2) for k in (1,2,3,4)])
# power at true edge 0.0082/bout, per-bout sd 0.103 (sheet-check estimate)
mu=0.0082/0.103
Za=(S+mu*looks)/np.sqrt(looks); print('power at 0.0082/bout:',run(Za,True))
