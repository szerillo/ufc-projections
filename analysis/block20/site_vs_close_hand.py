# Item 4: rerun block 19's locked comparison with the 5 hand-matched bouts added (BFO event pages read Nov 11 ~12:45 ET;
# the earlier surname keys were mispaired where a fighter row had no odds). Two stay dropped: only 1 US book (rule = 2+).
# Also: per-bout sd of d and the n for 80% power at the observed mean d. Site P(dec) is published on main (data/cards), so not engine-private.
import json,math,random,statistics as st,sys,collections
src=open('/home/claude/work/b19/site_vs_close.py').read()
src=src.replace("json.dump(out,open('site_vs_close_out.json','w'),indent=1); print(json.dumps(out,indent=1))","")
g={}; exec(src,g)
HAND={('2026-10-17','Chad Anheliger vs Steven Koslow'):0.382,('2026-10-31','Francis Marshall vs Dakota Hope'):0.538,
      ('2026-11-07','Waldo Cortes Acosta vs Johnny Walker'):0.245,('2026-11-07','Mantas Kondratavicius vs Andre Petroski'):0.234,
      ('2026-11-07','Seokhyeon Ko vs Wellington Turman'):0.490}
REPO=g['REPO']; rows=list(g['rows'])
for date,(cf,ef,evs) in g['cards'].items():
    C=json.load(open(f'{REPO}/data/cards/{cf}')); E=json.load(open(f'{REPO}/form/data/events/{ef}'))
    for fx in C['fights']:
        if (date,fx['bout']) not in HAND: continue
        a,b=fx['bout'].split(' vs ')
        ev=next((x for x in E['fights'] if {g['k5'](x['a']['name']),g['k5'](x['b']['name'])}=={g['k5'](a),g['k5'](b)}),None)
        y=g['gtd'](ev.get('result')) if ev else None
        if y is None: print('no outcome',fx['bout']); continue
        rows.append(dict(card=date,bout=fx['bout'],site=fx['duration']['p_dec']/100,close=HAND[(date,fx['bout'])],y=y))
ll=g['ll']; out={'locked_primary':g['out']['primary'],'with_hand_matched':g['summ'](rows,'site cards + 5 hand-matched')}
for k,R in (('primary_locked',g['rows']),('with_hand',rows),('archive_secondary',g['sec'])):
    d=[ll(r['close'],r['y'])-ll(r['site'],r['y']) for r in R]; m=st.mean(d); sd=st.stdev(d)
    out['power_'+k]=dict(n=len(d),mean_d=round(m,4),sd_d=round(sd,4),n_80pct_onesided5=round(((1.645+0.8416)*sd/abs(m))**2),n_80pct_onesided2p5=round(((1.96+0.8416)*sd/abs(m))**2))
json.dump(out,open('site_vs_close_hand_out.json','w'),indent=1); print(json.dumps(out,indent=1))
