import json,sys,re
sys.path.insert(0,'/tmp/audit6')
d=json.load(open('/tmp/audit4/decisions.json')); cl=json.load(open('/tmp/audit4/classified.json'))
samp={'|'.join(i) for i in json.load(open('/tmp/audit4/sample_ids.json'))}
edits=[]; skipped=[]
def add(page,e,field,old,new,src):
    edits.append(dict(page=page,entry=e,field=field,old=old,new=new,src=src))
SKIP_IDS={ # cosmetic punctuation/spacing print oddities: logged, not stored
 '1906-07_SP_p001|e030|space','1908-09_MSK_p000|e014|first','1907-08_SP_p003|e009|family'}
for r in d['agree']:
    if r['field']=='list' : skipped.append((r['id'],'list-number period omitted in print (cosmetic)')); continue
    if r['id'][10:] in SKIP_IDS: skipped.append((r['id'],'punctuation/spacing oddity')); continue
    if r['field'] in('ordinal','first/patronymic spelling','patronymic/first','first/patronymic','family/first','first/patronymic/ordinal','patronymic/first'): pass
    fld={'ordinal':'family','space':'family','first/patronymic spelling':'first'}.get(r['field'],r['field'])
    add(r['page'],r['entry'],fld,r['stored'],r['printed'],'verified')
for x in cl:
    i=f"{x['page']}|{x['entry']}|{x['field']}"
    if x['cls'] in('soft_hard','instr_i','mixed_script') and i not in samp:
        add(x['page'],x['entry'],x['field'],x['stored'],x['printed'],'mechanical')
json.dump(edits,open('/tmp/audit6/edits_generic.json','w'),ensure_ascii=False,indent=1)
json.dump(skipped,open('/tmp/audit6/skipped.json','w'),ensure_ascii=False,indent=1)
print(len(edits),'generic edits;',len(skipped),'skipped')
import collections
print(collections.Counter((e['field'],e['src']) for e in edits))
for e in edits:
    if e['field'] not in ('family','first','patronymic','instrument') : print('FIELD?',e)
    if any(ch in (e['new'] or '') for ch in '/') or re.search(r'-$',e['new'] or ''): print('SUSP',e['page'][10:],e['entry'],e['field'],repr(e['old']),'->',repr(e['new']))
