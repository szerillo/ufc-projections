#!/bin/bash
# Kirk round 34 plants: hold bouts back in the live file, rebuild every embed, verify. Run in a scratch copy of the branch.
set -u; W=$1; cd "$W"
cp data/ufc_334_projections.json /tmp/r36/p34_live_orig.json
cp -r embeds/ufc_334 /tmp/r36/p34_control_embeds
plant() {   # $1 label, rest: fav last names to hold back
  local label=$1; shift
  python3 - "$@" <<'PY'
import json,sys
d=json.load(open('/tmp/r36/p34_live_orig.json')); keep=[]; pend=[]
for f in d['fights']:
    if any(f['fav'].split()[-1]==x or f['dog'].split()[-1]==x for x in sys.argv[1:]): pend.append({"dog":f['dog'],"fav":f['fav'],"reason":"PLANT: fav price is not the Feed row's price (OPP-1)"})
    else: keep.append(f)
d['fights']=keep; d['line_pending']=pend; d['verified']['fights']=len(keep); d['verified']['line_pending']=len(pend)
json.dump(d,open('data/ufc_334_projections.json','w'))
PY
  echo "== PLANT $label: line_pending = $*"
  EMBED_PIPELINE=1 python3 scripts/build_fight_embeds.py 2>&1 | grep -E "^13 embeds|gaps" | grep -v " 0 gaps" | tail -4
  python3 scripts/verify_fight_embeds.py --slug ufc_334 2>&1 | grep -E "^LINE PENDING|^TOTAL|pending|LOCKS:" | grep -v "verified, 0 mismatches" | head -8
  python3 -I scripts/build_card_tables.py --slug ufc_334 | tail -1
  python3 -I scripts/verify_card_tables.py --slug ufc_334 | tail -1
  python3 -I scripts/diff_embed_numbers.py /tmp/r36/p34_control_embeds embeds/ufc_334 2>&1 | tail -3
  for n in $(python3 -c "import json;print(' '.join(str(json.load(open(p))['fight']) for p in __import__('glob').glob('embeds/ufc_334/fight_*.registry.json') if json.load(open(p)).get('proj_src')=='line_pending'))"); do
    f=embeds/ufc_334/fight_$(printf %02d $n).html; echo "   fight $n embed: state=$(grep -o 'data-state="[a-z-]*"' $f | head -1) note=$(grep -c 'did not match this bout, so no numbers are shown' $f) sheet-cells=$(grep -c 'class="proj"' $f) numbers=$(python3 -c "import json;print(len(json.load(open('${f%.html}.registry.json'))['rows']))")"
  done
}
plant "1 pending (fight 10)" Medic
plant "3 pending (fights 10, 1, 3)" Medic Sanches Mesquita
plant "main event pending (fight 13)" Gane
cp /tmp/r36/p34_live_orig.json data/ufc_334_projections.json
echo "== CONTROL: 0 pending, rebuilt with the new code"
python3 scripts/build_fight_embeds.py 2>&1 | tail -1
python3 scripts/verify_fight_embeds.py --slug ufc_334 2>&1 | grep -E "^LINE PENDING|^TOTAL|LOCKS:"
