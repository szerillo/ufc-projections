import json
D=json.load(open('div.json'))
B=[("Hokit-Gane","Heavyweight",5,32,28.9,31.1,31),("Nunes-Harrison","Women's Bantamweight",5,37,47.7,68.5,44),
("Belgaroui-Borralho","Middleweight",3,62,49.6,40.7,56),("Holland-Medic","Welterweight",3,20,34.5,47.4,28),
("Gurule-Hasan","Flyweight",3,17,39.7,53.1,28),("Radtke-Thompson","Welterweight",3,57,49.7,47.4,54),
("Dober-Duncan","Lightweight",3,24,40.6,48.0,32),("Miller-McKinney","Lightweight",3,12,36.0,48.0,23),
("Almeida-Johnson","Middleweight",3,31,38.6,40.7,34),("Gordon-Costa","Lightweight",3,39,41.4,48.0,41),
("Chiasson-Mesquita","Women's Bantamweight",3,33,48.9,60.8,41),("Elder-Sanches","Lightweight",3,43,52.7,48.0,46)]
def T(L,Z,b): m=(0.30*Z+0.15*b)/0.45; return L+0.4*(m-L)
out=[];lines=[]
for nm,wc,r,L,Z,b,Q in B:
    s=T(L,Z,b); row=dict(bout=nm,div=wc,rounds=r,listed=L,Z=Z,sheet_base=b,sheet_display=Q,sheet=round(s,1))
    for k in ('post','shrunk'):
        nb=D[wc][k]*100; row[k]=round(T(L,Z,nb),1); row[k+'_zshift']=round(T(L,Z+(nb-b),nb),1); row[k+'_base']=round(nb,1)
    row['npost']=D[wc]['npost']; out.append(row)
    lean=lambda t:('GTD +%.1f'%(t-L) if t-L>=5 else ('ITD +%.1f'%(L-t) if L-t>=5 else '-'))
    lines.append('| %s | %s%s | %d | %.1f (%s) | %.1f (%s) [%.1f] | %.1f (%s) [%.1f] |'%(nm,wc.replace("Women's ","W-"),' 5R' if r==5 else '',L,s,lean(s),row['post'],lean(row['post']),row['post_zshift'],row['shrunk'],lean(row['shrunk']),row['shrunk_zshift']))
json.dump(out,open('ufc334_forward.json','w'),indent=1)
print('\n'.join(lines))
