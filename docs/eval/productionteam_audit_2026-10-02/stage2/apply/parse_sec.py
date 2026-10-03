import re,glob,json
def ents(s):
    out=[]
    for part in re.split(r'[,\s]+',s.strip()):
        m=re.fullmatch(r'e(\d+)-e?(\d+)',part)
        if m: out+=[int(x) for x in range(int(m.group(1)),int(m.group(2))+1)]
        elif re.fullmatch(r'e\d+',part): out.append(int(part[1:]))
    return out
rows=[]
for f in sorted(glob.glob('results/group*.txt'),key=lambda s:int(re.findall(r'\d+',s)[0])):
    g=int(re.findall(r'\d+',f)[0]); S=None
    for line in open(f,encoding='utf-8'):
        l=line.strip()
        if l.startswith('CORRECTIONS'): S='C'; continue
        if l.startswith(('OTHER FINDINGS','PAGE SUMMARY')): S=None; continue
        if S!='C' or not l.startswith('productionteam_'): continue
        m=re.match(r'(productionteam_\S+)\s*\|\s*([e\d,\-\s]+?)\s*\|\s*PROPOSED:(.*?)\|\s*CORRECT:(.*?)\|\s*confidence:\s*(.*)$',l)
        if not m: rows.append(dict(group=g,raw=l,bad=True)); continue
        rows.append(dict(group=g,page=m.group(1),entries=ents(m.group(2)),proposed=m.group(3).strip(),correct=m.group(4).strip(),conf=m.group(5)[:200],raw=l,bad=False))
json.dump(rows,open('corrections.json','w'),ensure_ascii=False,indent=1)
print(len(rows),'lines;',sum(1 for r in rows if r['bad']),'unparsed')
import collections
multi=[r for r in rows if not r['bad'] and re.search(r'\(e\d+|\be\d+\)|;',r['correct'])]
print(len(multi),'multi-part lines')
for r in multi[:12]: print(r['page'][14:],r['entries'][:3],'|',r['correct'][:200])
for r in rows:
    if r['bad']: print('BAD',r['raw'][:200])
