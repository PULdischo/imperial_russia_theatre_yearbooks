import sys,json,glob,os,collections
R='/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main/outputs/full_run/raw/'
FIELDS={'family_name','first_name','patronymic','list_number','rank_or_title','subject_taught','tenure_note_text'}
def nz(v): 
    v=(v or '').strip()
    return '' if v=='-' else v
def load(season):
    raws={}
    for f in sorted(glob.glob(R+f'theaterschoolstaff_{season}_p*.raw.json')):
        pg=os.path.basename(f)[:-9]; raws[pg]=json.load(open(f))['entries']
    return raws
def rd(path):
    if not os.path.exists(path): return None
    return [l.rstrip('\n').split('\t') for l in open(path,encoding='utf-8') if l.strip()]
def validate(season,verbose=True):
    raws=load(season); out={}
    st=rd(f'/tmp/tss/strict/{season}_struct.tsv'); fx=rd(f'/tmp/tss/strict/{season}_fix.tsv'); ms=rd(f'/tmp/tss/strict/{season}_missing.tsv')
    if st is None or fx is None or ms is None: print(season,'FILES MISSING',st is None,fx is None,ms is None); return
    probs=[]
    # struct coverage
    seen=set(); 
    for r in st:
        if len(r)<7: probs.append(('struct short line',r)); continue
        pg,e=r[0],r[1]; k=(pg,e)
        if k in seen: probs.append(('struct dup',k))
        seen.add(k)
        if pg not in raws: probs.append(('struct unknown page',pg)); continue
        if r[2] not in ('SPB','MSK'): probs.append(('struct bad school',r[:4]))
        if r[6] not in ('PERSON','NONPERSON'): probs.append(('struct bad kind',r[:7]))
    expect={(pg,'e%03d'%(i+1)) for pg,es in raws.items() for i in range(len(es))}
    miss=expect-seen; extra=seen-expect
    if miss: probs.append(('struct rows missing',sorted(miss)[:8],len(miss)))
    if extra: probs.append(('struct rows not in raw',sorted(extra)[:8],len(extra)))
    # fix assertions
    bad=0; 
    for r in fx:
        if len(r)<6: probs.append(('fix short line',r)); continue
        pg,e,fld,old,new,conf=r[:6]
        if fld not in FIELDS: probs.append(('fix bad field',r[:3])); continue
        if pg not in raws: probs.append(('fix unknown page',pg)); continue
        i=int(e[1:])-1
        if i>=len(raws[pg]): probs.append(('fix row out of range',pg,e)); continue
        cur=nz(str(raws[pg][i].get(fld) or ''))
        if cur!=nz(old): bad+=1; probs.append(('fix STORED mismatch',pg,e,fld,'raw=%r'%cur,'agent=%r'%old))
    print(season,'struct',len(st),'fix',len(fx),'missing',len(ms),'| problems',len(probs),'(stored mismatches %d)'%bad)
    if verbose:
        for p in probs[:12]: print('   ',p)
    return probs
if __name__=='__main__':
    for s in sys.argv[1:]: validate(s)
