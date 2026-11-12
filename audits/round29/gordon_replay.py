"""Kirk round 28 B: Gordon's rec on live sheet inputs (read 2026-11-12 ~20:35Z), v2.7 D vs v2.8 D, via scripts/sheet_v47.py."""
import sys; sys.path.insert(0, "/tmp/e5/scripts"); import sheet_v47 as S
R = [("Josh Hokit","Ciryl Gane",163,-180,.33,.41,.39,.420,.66,0),("Amanda Nunes","Kayla Harrison",155,-185,.31,.41,.37,.348,.70,1),
 ("Yousri Belgaroui","Caio Borralho",132,-155,.44,.26,.36,.578,.61,0),("Kevin Holland","Uros Medic",140,-150,.23,.34,.47,.585,.44,0),
 ("Luis Gurule","Bilal Hasan",650,-1000,.03,.09,.05,.185,.40,0),("Charles Radtke","Stephen Thompson",130,-152,.22,.29,.21,.456,.51,0),
 ("Drew Dober","Chris Duncan",155,-185,.34,.49,.25,.465,.37,0),("Jim Miller","Terrance McKinney",180,-200,.27,.50,.47,.358,.47,0),
 ("Cesar Almeida","Donte Johnson",145,-175,.19,.25,.47,.313,.42,0),("Jared Gordon","Melquizael Costa",420,-400,.03,.15,.19,.343,.57,0),
 ("Macy Chiasson","Bia Mesquita",210,-250,.07,.16,.28,.358,.45,1),("Alatengheili","Juan Diaz",320,-333,.04,.19,.0,.231,.38,0),
 ("Evan Elder","Samuel Sanches",102,-110,.32,.45,.60,.544,.41,0)]
def card(gd):
    rows = [dict(dog=a, fav=b, dog_odds=(gd if a == "Jared Gordon" else d), fav_odds=i, tap=t, junk=j, tip=tp, open_dog=o, markov=m, women=w) for a, b, d, i, t, j, tp, o, m, w in R]
    sh = S.markov_shift(rows)
    for r in rows: r["shift"] = sh
    return sh, {r["dog"]: S.row(r) for r in rows}
for lab, gd in (("v2.7 (live now): D +420 Caesars (TRAP)", 420), ("v2.8: D +310 FanDuel (TRAP excluded)", 310)):
    sh, out = card(gd); g = out["Jared Gordon"]
    print(f"{lab}\n  B42 {sh:.5f} | listed dog {g['listed']*100:.2f} | true dog {g['true_dog']*100:.2f} | dog edge {g['dog_edge']*100:+.2f} | fav edge {g['fav_edge']*100:+.2f} | fav no-vig {(1-g['listed'])*100:.2f} | flag {g['flag']} | rec {g['rec']}")
    if gd == 310:
        _, b = card(420); mv = max(abs(out[k]['true_dog'] - b[k]['true_dog']) for k in out if k != "Jared Gordon")
        changed = [k for k in out if out[k]['rec'] != b[k]['rec']]
        print(f"  other 12 fights: largest True % move {mv*100:.3f} pts (B42 moves); recs changed: {changed}")
