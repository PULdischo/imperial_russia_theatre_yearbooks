import json,re,collections
d=json.load(open('parsed_all.json'))
items=[];unp=[]
def ents(s):
    out=[]
    for part in re.split(r'[,\s/]+',s):
        part=part.strip()
        m=re.fullmatch(r'e(\d+)-e?(\d+)',part)
        if m: out+= [f'e{i:03d}' for i in range(int(m.group(1)),int(m.group(2))+1)]
        elif re.fullmatch(r'e\d+',part): out.append(part)
    return out
for r in d['disc']:
    m=re.match(r'([e\d,\s\-]+)\|\s*([^|]+?)\s*\|\s*STORED:\s*(.*?)\s*\|\s*PRINTED:\s*(.*?)(?:\s*\|\s*confidence:\s*(\S+(?:\([^)]*\))?)\s*\|?\s*(.*))?$',r['rest'])
    if not m: unp.append(r); continue
    es=ents(m.group(1)); fld=m.group(2).strip()
    items.append(dict(group=r['group'],page=r['page'],entries=es,field=fld,stored=m.group(3).strip().strip('"'),printed=m.group(4).strip().strip('"'),conf=m.group(5) or '',note=(m.group(6) or '')))
json.dump(items,open('items.json','w'),ensure_ascii=False,indent=1)
print(len(items),'parsed;',len(unp),'unparsed')
for u in unp[:20]: print('UNP',u['page'][14:],u['rest'][:200])
c=collections.Counter(i['field'] for i in items); print(c)
