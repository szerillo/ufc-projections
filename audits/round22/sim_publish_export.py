import json, sys, datetime as dt
p = "data/pending/ufc_334_projections.json"; x = json.load(open(p))
paste = {"Bilal Hasan": -1000, "Melquizael Costa": -385, "Jared Gordon": 310, "Samuel Sanches": -115}   # SIMULATED Sean paste (best US-regulated price in the report at 17:26Z)
for f in x["fights"]:
    for role in ("fav", "dog"):
        if f[role] in paste: f["inputs"][role + "_odds"] = paste[f[role]]
x["published_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z") if sys.argv[1] == "now" else sys.argv[1]
json.dump(x, open(p, "w"), indent=1)
print("export published_at", x["published_at"])
