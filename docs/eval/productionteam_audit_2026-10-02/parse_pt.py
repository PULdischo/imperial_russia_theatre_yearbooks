import re,glob,json,collections
rows=[];sec=[];miss=[];dates=[]
for f in sorted(glob.glob('results/group*.txt'),key=lambda s:int(re.findall(r'\d+',s)[0])):
    g=int(re.findall(r'\d+',f)[0]); S=None
    for line in open(f,encoding='utf-8'):
        l=line.strip()
        if l.startswith('DISCREPANCIES'): S='D';continue
        if l.startswith('SECTION PROBLEMS'): S='S';continue
        if l.startswith('MISSING OR EXTRA'): S='M';continue
        if l.startswith('DATE-CHECK'): S='T';continue
        if l.startswith(('OTHER FINDINGS','PAGE SUMMARY')): S=None;continue
        m=re.match(r'(productionteam_\S+)\s*\|\s*(.*)$',l)
        if not m: continue
        if S=='D': rows.append(dict(group=g,page=m.group(1),rest=m.group(2)))
        elif S=='S': sec.append(dict(group=g,page=m.group(1),rest=m.group(2)))
        elif S=='M' and ('MISSING' in l or 'EXTRA' in l): miss.append(dict(group=g,page=m.group(1),rest=m.group(2)))
        elif S=='T': dates.append(dict(group=g,page=m.group(1),rest=m.group(2)))
json.dump(dict(disc=rows,sec=sec,miss=miss,dates=dates),open('parsed_all.json','w'),ensure_ascii=False,indent=1)
print(len(rows),'discrepancy lines;',len(sec),'section lines;',len(miss),'missing/extra;',len(dates),'date checks')
c=collections.Counter()
for r in rows:
    m=re.match(r'(e\d+(?:[,\-/ ]*e?\d+)*)\s*\|\s*([^|]+)\|',r['rest'])
    c[(m.group(2).strip().split('/')[0] if m else '?')]+=1
print(c.most_common())
print([d['rest'][:120] for d in dates if 'DIFFERS' in d['rest']])
