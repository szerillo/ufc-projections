import openpyxl, pandas as pd, sys
def load(path='/tmp/rev/in/model.xlsx'):
    wb=openpyxl.load_workbook(path,data_only=True,read_only=True)
    out={}
    for t in ['Snapshots','PropSnap']:
        rows=[r for r in wb[t].iter_rows(values_only=True) if any(c not in (None,'') for c in r)]
        hdr=[h if h else f'c{i}' for i,h in enumerate(rows[0])]
        out[t]=pd.DataFrame(rows[1:],columns=hdr)
    return out['Snapshots'],out['PropSnap']
