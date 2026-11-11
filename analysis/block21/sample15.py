# Item 4: every match made through the surname-key path (block 17 BFO-vs-bot, block 19 archive) and a seeded 15 to hand-check.
import json,random,unicodedata
def k5(x):
    x=unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode().split(' ')[-1].lower(); return ''.join(c for c in x if c.isalpha())[:5]
B={}
for t in open('/home/claude/work/b17/bfo_named.txt').read().strip().split(';'):
    e,k,m,itd=t.split('|'); B.setdefault(k,[]).append((e,int(m)/1000))
DM={'4318':'2026-09-12','4303':'2026-09-19','4368':'2026-09-26','4330':'2026-10-03','4378':'2026-10-10','4402':'2026-10-17','4403':'2026-10-17','4321':'2026-10-24','4427':'2026-10-31','4437':'2026-11-07','4439':'2026-11-07'}
M=[]
for x in json.load(open('/home/claude/work/b17/bp_close.json')):
    key='-'.join(sorted([k5(x['a']),k5(x['b'])]))
    if key in B: M.append(dict(src='b17 bot',bout=x['a']+' vs '+x['b'],key=key,ev=B[key][0][0],p=B[key][0][1]))
for r in json.load(open('/home/claude/work/audit/rows4.json')):
    if r.get('dec') is None or r.get('pdec') is None: continue
    a,b=r['bout'].split(' vs '); key='-'.join(sorted([k5(a),k5(b)]))
    hit=[(e,p) for e,p in B.get(key,[]) if DM.get(e)==r['card']]
    if hit: M.append(dict(src='b19 archive',bout=r['bout'],key=key,ev=hit[0][0],p=hit[0][1]))
print('surname-path matches: b17',sum(m['src']=='b17 bot' for m in M),'b19',sum(m['src']=='b19 archive' for m in M),'keys with >1 BFO row',sum(1 for k,v in B.items() if len(v)>1))
random.seed(21); S=random.sample(M,15)
json.dump(S,open('sample15.json','w'),indent=1)
for s in S: print(s)
