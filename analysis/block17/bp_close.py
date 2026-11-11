# For every card odds file on origin/main (BettingPros via the odds bot), walk git history and keep, per bout,
# the last snapshot whose fight_distance prices were all updated at or before scheduled start.
# Output: per bout, US-book (FD, DK, MGM, CZ) median multiplicative GTD %, latest book timestamp, minutes before scheduled start.
import json,subprocess,datetime as dt,statistics as st,sys
REPO='/home/claude/ufc-projections'
files=subprocess.check_output(['git','-C',REPO,'ls-tree','--name-only','origin/main','data/']).decode().split()
files=[f for f in files if f.endswith('_odds.json')]
def imp(o): o=float(o); return -o/(-o+100) if o<0 else 100/(o+100)
P=lambda s:dt.datetime.strptime(s,'%Y-%m-%d %H:%M:%S')
out={}
for f in files:
    shas=[l.split() for l in subprocess.check_output(['git','-C',REPO,'log','--format=%H %ct','origin/main','--',f]).decode().splitlines()]
    for sha,ct in reversed(shas):
        pulled=dt.datetime.utcfromtimestamp(int(ct))
        try: d=json.loads(subprocess.check_output(['git','-C',REPO,'show',sha+':'+f],stderr=subprocess.DEVNULL))
        except Exception: continue
        for x in d.get('fights',[]):
            fd=x.get('markets',{}).get('fight_distance'); s=x.get('scheduled_utc')
            if not fd or not s: continue
            yes=next((m for m in fd if m.get('selection')=='yes'),None); no=next((m for m in fd if m.get('selection')=='no'),None)
            if not yes or not no: continue
            ps=[];ts=[]
            for b in ('fanduel','draftkings','betmgm','caesars'):
                if b in yes['books'] and b in no['books']:
                    a,c=imp(yes['books'][b]['cost']),imp(no['books'][b]['cost']); ps.append(a/(a+c))
                    ts+= [P(yes['books'][b]['updated']),P(no['books'][b]['updated'])]
            if len(ps)<2 or pulled>P(s) or max(ts)>P(s): continue
            key=(x['fighter_a']['name'],x['fighter_b']['name'])
            out[key]=dict(card=d.get('card'),a=key[0],b=key[1],sched=s,p=round(st.median(ps),4),n=len(ps),last=str(max(ts)),mins_before=round((P(s)-pulled).total_seconds()/60,1),last_change_mins=round((P(s)-max(ts)).total_seconds()/60,1),pulled=str(pulled),snap=sha[:8])
json.dump(list(out.values()),open('bp_close.json','w'),indent=0)
v=list(out.values()); print('bouts',len(v),'cards',len(set(x['card'] for x in v)))
mb=sorted(x['mins_before'] for x in v); print('pull minutes before scheduled start: median %.0f, p10 %.0f, p90 %.0f, share within 5 min %.2f'%(st.median(mb),mb[len(mb)//10],mb[9*len(mb)//10],sum(m<=5 for m in mb)/len(mb)))
