import re,os,sys
B, N = sys.argv[1], sys.argv[2]
same_reg=diff_html=0; notes=[]; guard=set()
for f in sorted(os.listdir(B)):
    a=open(f'{B}/{f}','rb').read(); b=open(f'{N}/{f}','rb').read()
    if f.endswith('.json'):
        same_reg += a==b
        if a!=b: notes.append('json differs: '+f)
        continue
    bs=b.decode()
    m=re.search(r'<script>\(function\(\)\{var P=.*?</script>(?=</body></html>)',bs,flags=re.S); guard.add(re.sub(r'var P=.*?,el=','var P=..,el=',m.group(0)) if m else None)
    bs=bs.replace(m.group(0),'') if m else bs
    i=bs.find('<div id="sean-proj" data-state="numbers">'); 
    if i>=0:
        # drop the wrapper: opening tag and the closing </div> that ends it (balanced scan)
        j=i+len('<div id="sean-proj" data-state="numbers">'); depth=1; k=j
        for mm in re.finditer(r'<div\b|</div>',bs[j:]):
            depth += 1 if mm.group(0)=='<div' else -1
            if depth==0: k=j+mm.start(); break
        bs=bs[:i]+bs[j:k]+bs[k+6:]
    a_=a.decode()
    if bs!=a_:
        x=next(x for x,(p,q) in enumerate(zip(a_,bs)) if p!=q); notes.append(f'{f}: diverges at {x}')
    diff_html += bs!=a_
print(f'control: {same_reg}/14 JSON files (13 registries + card.json) byte-identical; {13-diff_html}/13 HTML byte-identical once the pending guard (one script, same text in all 13: {len(guard)} variant) and its #sean-proj wrapper are taken out')
print('\n'.join(notes[:5]))
