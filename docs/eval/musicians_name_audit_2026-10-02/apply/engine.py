import json,re,sys,os
P='/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main/'
R=P+'outputs/full_run/raw/'
_cache={}
def load(page):
    if page not in _cache: _cache[page]=json.load(open(R+page+'.raw.json'))
    return _cache[page]
def bundle_row(page,e):
    for l in open(f'/tmp/audit4/{page}.txt',encoding='utf-8'):
        if l.startswith(e+' |'):
            c=[x.strip() for x in l.rstrip('\n').split(' | ')]
            return dict(list=c[1],fam=c[2],first=c[3],pat=c[4],instr=c[5],rank=c[6])
    raise KeyError((page,e))
def nz(v): return None if v in (None,'','-') else v
def resolve(page,e):
    es=load(page)['entries']; b=bundle_row(page,e)
    i=int(e[1:])-1
    def ok(x): return (nz(x.get('list_number'))==nz(b['list']) and (x.get('family_name') or '').strip()==b['fam'])
    if i<len(es) and ok(es[i]): return es[i]
    m=[x for x in es if ok(x) and nz(x.get('first_name'))==nz(b['first'])]
    if len(m)==1: return m[0]
    m=[x for x in es if ok(x)]
    if len(m)==1: return m[0]
    # shifted fallbacks: only family match
    m=[x for x in es if (x.get('family_name') or '').strip()==b['fam'] and nz(x.get('first_name'))==nz(b['first'])]
    if len(m)==1: return m[0]
    m=[x for x in es if nz(b['list']) and nz(x.get('list_number'))==nz(b['list'])]
    if len(m)==1: return m[0]
    raise LookupError(f'{page} {e} unresolved ({b["fam"]},{b["list"]})')
FIELD={'family':'family_name','first':'first_name','patronymic':'patronymic'}
def apply_field(page,e,field,old,new,log):
    x=resolve(page,e)
    if field in FIELD:
        k=FIELD[field]; cur=x.get(k)
        if (cur or '').strip()==(new or '').strip(): log.append((page,e,field,old,new,'ALREADY')); return
        if (cur or '').strip()!=(old or '').strip() and not (nz(cur) is None and nz(old) is None):
            raise AssertionError(f'{page} {e} {k}: raw={cur!r} != expected {old!r}')
        x[k]=new
    elif field=='instrument':
        n=0
        if (x.get('instrument') or '').strip()==(new or '').strip() and new: log.append((page,e,field,old,new,'ALREADY')); return
        if nz(old) is not None and (x.get('instrument') or '').strip()==old.strip():
            x['instrument']=new; log.append((page,e,field,old,new)); return
        if nz(old) is None:
            if nz(x.get('instrument')) is not None: raise AssertionError(f'{page} {e}: instrument already {x.get("instrument")!r}')
            x['instrument']=new; log.append((page,e,field,old,new)); return
        for k in ('rank_or_title','tenure_note_text'):
            v=x.get(k)
            if v and old in v: x[k]=v.replace(old,new); n+=1
        if not n: raise AssertionError(f'{page} {e}: instrument {old!r} not in rank/tenure ({x.get("rank_or_title")!r}|{x.get("tenure_note_text")!r})')
    else: raise ValueError(field)
    log.append((page,e,field,old,new))
def apply_ops(page,e,ops,log):
    """ops: dict of raw key -> (expected_old,new); strict."""
    x=resolve(page,e)
    for k,(old,new) in ops.items():
        cur=x.get(k)
        if k=='service_periods': pass
        elif old=='*': pass
        elif (cur or '').strip()!=(old or '').strip() and not (nz(cur) is None and nz(old) is None):
            raise AssertionError(f'{page} {e} {k}: raw={cur!r} != expected {old!r}')
        x[k]=new; log.append((page,e,k,cur if old=='*' else old,new))
def write_all():
    for p,d in _cache.items(): json.dump(d,open(R+p+'.raw.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
