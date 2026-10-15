import pandas as pd,re,sys
d=pd.read_pickle('/private/tmp/claude-502/x/entries.pkl')
d['pos']=d.entry_id.str.extract(r'__e(\d+)$')[0].astype(int)
d=d.sort_values(['page_id','pos']).reset_index(drop=True)
M=str.maketrans({'ѣ':'е','і':'и','ї':'и','ѳ':'ф','ѵ':'и','ё':'е','й':'и','ь':'','ъ':''})
def n(s):
    if s is None or (isinstance(s,float)): return ''
    s=re.sub(r'\(.*?\)','',s).lower().strip()
    s=s.replace('ья','ия').replace('ье','ие').replace('ьи','ии')
    s=s.translate(M)
    s=re.sub(r'(.)\1',r'\1',re.sub(r'[^а-яa-z]','',s))
    return s
def lev(a,b):
    if a==b: return 0
    p=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        q=[i]
        for j,cb in enumerate(b,1): q.append(min(p[j]+1,q[-1]+1,p[j-1]+(ca!=cb)))
        p=q
    return p[-1]
def split_ord(f):
    m=re.match(r'^(.*?)[\s,]+(\d+)-?[йяе]',f or '')
    return (m.group(1),m.group(2)) if m else (f,'')
d['fbase']=[split_ord(f)[0] for f in d.fam]; d['ford']=[split_ord(f)[1] for f in d.fam]
d['nf']=d.fbase.map(n); d['nn']=d.fn.map(n); d['np']=d.pat.map(n)
d['shape']=(d.fn.fillna('').str.contains(r'\.')|d.pat.fillna('').str.contains(r'\.')|d.fn.fillna('').str.contains(r'(?:вна|вичъ|ична)$')|d.fam.fillna('').str.contains(r'\.'))
# per-page neighbours
pages={p:g for p,g in d.groupby('page_id')}
def cls(a_raw,b_raw,a,b,field):
    if a==b: return 'same' if a_raw==b_raw else 'orth'
    if a=='' or b=='': return 'missing'
    k=lev(a,b)
    if field=='pat': return 'sub_letter' if k<=2 else 'sub_whole'
    if field=='fn': return 'sub_letter' if k<=2 else 'sub_whole'
    return 'sub_letter' if k<=2 else 'sub_whole'
rows=[]
for pid,g in d.groupby('person_id'):
    g=g.sort_values(['season','entity_type','pos'])
    ks=[]; 
    for _,r in g.iterrows(): ks.append(r)
    # unique (season,tuple)
    seen=[];uniq=[]
    for r in ks:
        key=(r.season,r.fbase,r.fn,r.pat,r.ford)
        if key in seen: continue
        seen.append(key); uniq.append(r)
    for a,b in zip(uniq,uniq[1:]):
        rec={'person_id':pid,'s_old':a.season,'s_new':b.season,'list':b.entity_type,'city':b.city,'page_old':a.page_id,'page_new':b.page_id,'entry_old':a.entry_id,'entry_new':b.entry_id,
             'old':f'{a.fam}, {a.fn} {a.pat}','new':f'{b.fam}, {b.fn} {b.pat}','shape':bool(a['shape'] or b['shape']),'ppn_new':b.ppn}
        for f,(x,y,xr,yr) in {'fam':(a.nf,b.nf,a.fbase,b.fbase),'fn':(a.nn,b.nn,a.fn,b.fn),'pat':(a.np,b.np,a.pat,b.pat)}.items():
            rec[f]=cls(xr,yr,x,y,f)
        rec['ord']='ordchg' if a.ford!=b.ford else ''
        rec['same_season']=a.season==b.season
        rows.append(rec)
v=pd.DataFrame(rows)
def worst(r):
    order=['sub_whole','sub_letter','missing','orth']
    for o in order:
        for f in ('fam','fn','pat'):
            if r[f]==o: return o
    return 'none'
v['grade']=v.apply(worst,axis=1)
v.to_pickle('/private/tmp/claude-502/x/var.pkl'); d.to_pickle('/private/tmp/claude-502/x/d2.pkl')
print(len(v)); print(v.grade.value_counts())
print(v[v.grade.isin(['sub_whole','sub_letter'])].shape, v[v.grade.isin(['sub_whole','sub_letter'])&~v['shape']].shape)
print(v.same_season.sum())
