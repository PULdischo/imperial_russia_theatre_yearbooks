import json,re,sys
sys.path.insert(0,'/tmp/audit8')
rows=json.load(open('/tmp/audit9/corrections.json'))
def eset(s):
    out=[]
    for part in re.split(r'[,\s]+',s.strip()):
        m=re.fullmatch(r'e(\d+)-e?(\d+)',part)
        if m: out+=list(range(int(m.group(1)),int(m.group(2))+1))
        elif re.fullmatch(r'e\d+',part): out.append(int(part[1:]))
    return out
def clean(s): return s.strip().strip('"').strip()
assign={}   # (page,eN) -> chain
unparsed=[]
for r in rows:
    if r.get('bad'): continue
    c=r['correct']
    # strip trailing confidence-ish text already removed; handle multi-part
    parts=[p.strip() for p in re.split(r';\s*',c) if p.strip()]
    ok=True; local={}; prev=None
    if len(parts)==1 and not re.search(r'\(e\d',parts[0]) and '<' not in parts[0]:
        ch=clean(parts[0])
        for e in r['entries']: local[e]=ch
    else:
        for p in parts:
            m=re.match(r'^(.*?)\s*\(((?:e\d+(?:-e\d+)?(?:,\s*)?)+)\)\s*$',p)
            if not m or '<' in p: ok=False; break
            txt=clean(m.group(1)); es=eset(m.group(2))
            if txt.startswith('...') or txt.startswith('/'):
                if prev is None: ok=False; break
                pref=prev.rsplit(' / ',1)[0]; txt=pref+' / '+txt.lstrip('./ ').strip()
            for e in es: local[e]=txt
            prev=txt
    if not ok or any('<' in v or '...' in v for v in local.values()): unparsed.append(r); continue
    for e,v in local.items(): assign[(r['page'],e)]=(v,r['conf'])
json.dump({f'{k[0]}|{k[1]}':v for k,v in assign.items()},open('/tmp/audit9/assign.json','w'),ensure_ascii=False,indent=1)
print(len(assign),'rows assigned from',len(rows)-len(unparsed),'lines;',len(unparsed),'lines need manual handling')
for r in unparsed: print(' MANUAL',r['page'][14:],r['entries'][:4],'|',r['correct'][:230])
