import json,re,os,shutil
P='/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main/'
R=P+'outputs/full_run/raw/'
_c={}
def load(page):
    if page not in _c: _c[page]=json.load(open(R+page+'.raw.json'))
    return _c[page]
def ent(page,e):
    es=load(page)['entries']; i=int(e[1:])-1
    assert 0<=i<len(es),(page,e,'out of range',len(es)); return es[i]
def nz(v): return None if v in (None,'','-') else v
def same(a,b): return (nz(a) or '').strip()==(nz(b) or '').strip()
KEY={'family':'family_name','first':'first_name','patronymic':'patronymic','list':'list_number','title':'rank_or_title','tenure':'tenure_note_text'}
def set_field(page,e,field,old,new,log):
    x=ent(page,e); k=KEY.get(field,field); cur=x.get(k)
    if same(cur,new): log.append((page,e,k,old,new,'ALREADY')); return
    if old!='*' and not same(cur,old): raise AssertionError(f'{page} {e} {k}: raw={cur!r} != expected {old!r}')
    x[k]=new; log.append((page,e,k,cur,new))
def set_period(page,e,idx,start=None,end='KEEP',etype='KEEP',log=None):
    x=ent(page,e); sp=x['service_periods']; p=sp[idx]
    old=dict(p)
    if start is not None: p['start_date_text']=start
    if end!='KEEP': p['end_date_text']=end
    if etype!='KEEP': p['end_type']=etype
    if log is not None: log.append((page,e,'period',old,dict(p)))
def replace_in(page,e,key,old,new,log,periods=False):
    x=ent(page,e); v=x.get(key) or ''
    assert old in v,(page,e,key,old,v)
    x[key]=v.replace(old,new,1); log.append((page,e,key,v,x[key]))
    if periods:
        n=0
        for p in x.get('service_periods') or []:
            for kk in ('start_date_text','end_date_text'):
                if p.get(kk) and old in p[kk]: p[kk]=p[kk].replace(old,new); n+=1
def append_note(page,e,suffix,log,end=None,etype=None):
    """append a printed note after the date sentence; optionally set the end of the LAST service period."""
    x=ent(page,e); t=x.get('tenure_note_text') or ''
    assert suffix not in t,(page,e,'already has',suffix,t)
    base=t.rstrip()
    if base.endswith(').'): pass
    elif base.endswith(')'): base+='.'
    elif ')' not in base and base.endswith('.'): base+=').'
    new=base+' '+suffix; x['tenure_note_text']=new; log.append((page,e,'tenure_note_text',t,new))
    if end is not None:
        sp=x['service_periods']; assert sp,(page,e,'no periods')
        old=dict(sp[-1]); sp[-1]['end_date_text']=end; sp[-1]['end_type']=etype; log.append((page,e,'period',old,dict(sp[-1])))
def write_all():
    for p,d in _c.items(): json.dump(d,open(R+p+'.raw.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
