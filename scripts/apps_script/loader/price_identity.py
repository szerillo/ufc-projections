"""Price/TRAP code identity, loader v2.8 vs v2.9: every price function and the D/I best-price block, byte for byte."""
import hashlib, re, sys
A, B = open(sys.argv[1]).read(), open(sys.argv[2]).read()
def func(s, name):
    i = s.index("function " + name + "("); depth = 0; j = s.index("{", i)
    for k in range(j, len(s)):
        depth += s[k] == "{"; depth -= s[k] == "}"
        if depth == 0: return s[i:k + 1]
def block(s, start, end): i = s.index(start); return s[i:s.index(end, i) + len(end)]
items = [(n, lambda s, n=n: func(s, n)) for n in ["imp_", "toAmer_", "median_", "validOdds_", "payout_", "included_", "bettable_", "devig2_", "wmedian_", "exchFair_", "outliers_", "fmtOutl_", "writeCalculator_"]]
items += [("constants (EXCLUDE/EXCHANGE/OUTLIER/BETTABLE)", lambda s: "\n".join(l for l in s.splitlines() if re.match(r"var (EXCLUDE_BOOKS|EXCHANGE_BOOKS|OUTLIER_MIN|BETTABLE_BOOKS|EXCH_PROP_W)\b", l))),
          ("buildCard_ D/I best-price block (exRef .. bestPrice)", lambda s: block(s, "var exRef = exchFair_(books);", "return bb; };")),
          ("buildCard_ consensus + props (inc .. propStat return)", lambda s: block(s, "var inc = books.filter", "var lastTok")),
          ("writeTab_ D/I/S/T writers", lambda s: block(s, "    A.push([f.tag, f.dog, f.fav]);", "tbl.push([f.fav, mo(f.props.fav.dec), mo(f.props.fav.ko), mo(f.props.fav.sub), mo(f.props.fav.itd)]);"))]
bad = 0
for n, g in items:
    a, b = g(A), g(B)
    if n == "writeCalculator_":   # v2.9 adds the held-row lines only; the rest must be identical once they are taken out
        b = "\n".join(l for l in b.split("\n") if "HELD_ROW_" not in l and "loader-guard: a held row" not in l)
    same = a == b; bad += not same
    print(f"{'IDENTICAL' if same else 'DIFFERENT'}  {hashlib.sha256(a.encode()).hexdigest()[:12]} {hashlib.sha256(b.encode()).hexdigest()[:12]}  {n}")
print("price/TRAP code:", "byte-identical" if not bad else f"{bad} DIFFERENT"); sys.exit(1 if bad else 0)
