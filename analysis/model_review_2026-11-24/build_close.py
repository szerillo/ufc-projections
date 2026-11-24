# Pre-fight US-book no-vig close per bout from the odds bot's git history (origin/main data/*_odds.json).
# Close = last bot pull at or before the bout's scheduled_utc whose ML book prices were updated before scheduled_utc.
# US books only (fanduel, draftkings, betmgm, caesars), multiplicative de-vig per book, median; needs 2+ books.
# Also records the same for fight_distance (GTD yes) when present. Usage: build_close.py <repo> <out.json>
import json,subprocess,datetime as dt,statistics as st,sys
REPO,OUT=sys.argv[1],sys.argv[2]
files=[f for f in subprocess.check_output(['git','-C',REPO,'ls-tree','--name-only','origin/main','data/']).decode().split() if f.endswith('_odds.json')]
imp=lambda o:(-float(o)/(-float(o)+100)) if float(o)<0 else 100/(float(o)+100)
P=lambda s:dt.datetime.strptime(s[:19],'%Y-%m-%d %H:%M:%S')
BK=('fanduel','draftkings','betmgm','caesars')
def pair(rows,lab_a,lab_b,key_a,key_b,sched):
    a=next((m for m in rows if m.get(key_a)==lab_a),None); b=next((m for m in rows if m.get(key_b)==lab_b),None)
    if not a or not b: return None
    ps=[];ts=[];pa=[];pb=[]
    for k in BK:
        if k in a['books'] and k in b['books']:
            x,y=imp(a['books'][k]['cost']),imp(b['books'][k]['cost']); ps.append(x/(x+y)); pa.append(a['books'][k]['cost']); pb.append(b['books'][k]['cost'])
            ts+=[P(a['books'][k]['updated']),P(b['books'][k]['updated'])]
    if len(ps)<2 or max(ts)>sched: return None
    return dict(p=round(st.median(ps),4),n=len(ps),last=str(max(ts)),best_a=max(pa,key=lambda o:1/imp(o)),best_b=max(pb,key=lambda o:1/imp(o)))
out={}
for f in files:
    log=[l.split() for l in subprocess.check_output(['git','-C',REPO,'log','--format=%H %ct','origin/main','--',f]).decode().splitlines()]
    for sha,ct in reversed(log):
        pulled=dt.datetime.utcfromtimestamp(int(ct))
        try: d=json.loads(subprocess.check_output(['git','-C',REPO,'show',sha+':'+f],stderr=subprocess.DEVNULL))
        except Exception: continue
        for x in d.get('fights',[]):
            s=x.get('scheduled_utc')
            if not s or pulled>P(s): continue
            sched=P(s); A=x['fighter_a']['name']; B=x['fighter_b']['name']; m=x.get('markets',{})
            ml=pair(m.get('moneyline',[]),A,B,'label','label',sched) if m.get('moneyline') else None
            gd=pair(m.get('fight_distance',[]),'yes','no','selection','selection',sched) if m.get('fight_distance') else None
            k=(A,B,d.get('card'))
            r=out.setdefault(k,dict(card=d.get('card'),file=f,a=A,b=B,sched=s))
            if ml: r.update(ml_pa=ml['p'],ml_n=ml['n'],ml_last=ml['last'],ml_pulled=str(pulled),best_a=ml['best_a'],best_b=ml['best_b'],ml_mins_before=round((sched-pulled).total_seconds()/60,1))
            if gd: r.update(gtd=gd['p'],gtd_n=gd['n'],gtd_pulled=str(pulled))
json.dump(list(out.values()),open(OUT,'w'),indent=0)
v=[r for r in out.values() if 'ml_pa' in r]; print('bouts with ML close',len(v),'with GTD close',sum('gtd' in r for r in out.values()),'cards',len(set(r['card'] for r in v)))
mb=sorted(r['ml_mins_before'] for r in v); print('ML close pulled minutes before start: median %.0f p10 %.0f p90 %.0f'%(st.median(mb),mb[len(mb)//10],mb[9*len(mb)//10]))
