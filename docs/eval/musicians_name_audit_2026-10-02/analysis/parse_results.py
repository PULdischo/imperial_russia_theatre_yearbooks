import re,glob,json,collections
rows=[];dates=[]
for f in sorted(glob.glob('results/group*.txt'), key=lambda s:int(re.findall(r'\d+',s)[0])):
    g=int(re.findall(r'\d+',f)[0]); sec=None
    for line in open(f,encoding='utf-8'):
        line=line.rstrip('\n').strip()
        if line.startswith('DISCREPANCIES'): sec='D';continue
        if line.startswith('DATE-CHECK'): sec='T';continue
        if line.startswith('OTHER FINDINGS') or line.startswith('PAGE SUMMARY'): sec=None;continue
        m=re.match(r'(musicians_\S+)\s*\|\s*(e\d+)\s*\|\s*(\w[\w/ -]*?)\s*\|\s*(.*)$',line)
        if sec=='D' and m:
            rows.append(dict(group=g,page=m.group(1),entry=m.group(2),field=m.group(3),rest=m.group(4)))
        elif sec=='T' and line.startswith('musicians_'):
            dates.append(dict(group=g,line=line))
json.dump(rows,open('all_discrepancies.json','w'),ensure_ascii=False,indent=1)
json.dump(dates,open('all_datechecks.json','w'),ensure_ascii=False,indent=1)
print(len(rows),len(dates))
print(collections.Counter(r['field'] for r in rows).most_common())
print(collections.Counter(r['group'] for r in rows))
nm=[d for d in dates if 'MATCH' not in d['line'] or 'DIFFERS' in d['line']]
print(len(nm))
for d in nm: print(d['group'],d['line'][:250])
