import json,re,glob,collections
key=json.load(open('ab_key.json'))
cls={ (x['page'],x['entry'],x['field']):x for x in json.load(open('classified.json'))}
dec=collections.defaultdict(list); seen=set()
for f in sorted(glob.glob('/tmp/audit5/results/batch*.txt')):
    for line in open(f,encoding='utf-8'):
        m=re.match(r'ITEM (\S+) \| READ: (.*?) \| CHOICE: (\S+) \| confidence: (\w+)\s*\|?\s*(.*)$',line.strip())
        if not m: continue
        iid,read,ch,conf,note=m.groups()
        p,e,fld=iid.split('|'); x=cls.get((p,e,fld))
        if x is None: dec['unknown_id'].append((iid,line.strip()[:150])); continue
        seen.add(iid)
        rec=dict(id=iid,page=p,entry=e,field=fld,stored=x['stored'],printed=x['printed'],read=read.strip('"'),choice=ch,conf=conf,note=note,cls=x['cls'])
        if ch in('A','B'):
            which=key[iid][ch]
            rec['pick']=which
            if conf!='DIRECT': dec['uncertain'].append(rec)
            elif which=='R': dec['agree'].append(rec)
            else: dec['disagree_keep_stored'].append(rec)
        elif ch=='NEITHER': dec['neither'].append(rec)
        elif ch=='FREEFORM': dec['freeform'].append(rec)
        else: dec['cannot'].append(rec)
json.dump(dec,open('decisions.json','w'),ensure_ascii=False,indent=1)
print({k:len(v) for k,v in dec.items()})
allids={f"{x['page']}|{x['entry']}|{x['field']}" for x in cls.values()}
import os
sample={'|'.join(i) for i in json.load(open('sample_ids.json'))}
full={i for i in allids if cls[tuple(i.split('|'))]['cls'] not in('mixed_script','soft_hard','instr_i')}
print('expected items',len(full|sample),'seen',len(seen),'missing',len((full|sample)-seen))
for k in ('disagree_keep_stored','uncertain','neither','cannot'):
    print('==',k)
    for r in dec[k]: print(' ',r['id'][10:],'| stored',r['stored'],'| rev',r['printed'],'| read',r['read'],'|',r['pick'] if 'pick' in r else r['choice'],r['conf'],r['note'][:90])
