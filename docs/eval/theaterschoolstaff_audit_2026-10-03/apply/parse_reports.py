import re,glob,json,collections,os
def expand(spec):
    out=[]
    for a,b in re.findall(r'e(\d+)(?:\s*-\s*e?(\d+))?',spec):
        a=int(a); b=int(b) if b else a
        out+=list(range(a,b+1))
    return out
items=[];missing=[];extra=[];smap=[]
for f in sorted(glob.glob('/tmp/tss/reports/*.txt')):
    season=os.path.basename(f)[:-4]
    txt=open(f,encoding='utf-8').read()
    sec=None
    for line in txt.split('\n'):
        l=line.strip()
        if l.startswith('FIELD DISCREPANCIES'): sec='F'; continue
        if l.startswith('MISSING / EXTRA'): sec='M'; continue
        if l.startswith('SECTION MAP'): sec='S'; continue
        if l.startswith('OTHER FINDINGS'): sec='O'; continue
        if l.startswith('PAGE SUMMARY'): sec='P'; continue
        m=re.match(r'^(?:theaterschoolstaff_\d{4}-\d{2}_)?(p00\d)\s*\|(.*)$',l)
        if not m or sec not in 'FMS': continue
        page=f'theaterschoolstaff_{season}_{m.group(1)}'; parts=[x.strip() for x in m.group(2).split(' | ')]
        if sec=='F' and len(parts)>=3:
            items.append(dict(season=season,page=page,rows=expand(parts[0]),field=parts[1].split()[0].lower() if parts[1] else '',stored=parts[2] if len(parts)>2 else '',printed=parts[3] if len(parts)>3 else '',raw=l))
        elif sec=='M': (extra if 'EXTRA' in l or 'NON-PERSON' in l else missing).append(dict(season=season,page=page,raw=l))
        elif sec=='S': smap.append(dict(season=season,page=page,rows=expand(parts[0]),raw=l))
json.dump(dict(items=items,missing=missing,extra=extra,smap=smap),open('/tmp/tss/parsed_reports.json','w'),ensure_ascii=False,indent=1)
print(len(items),'field lines;',len(missing),'missing lines;',len(extra),'extra lines;',len(smap),'section-map lines')
c=collections.Counter(); rows=collections.Counter()
for it in items:
    c[it['field']]+=1; rows[it['field']]+=max(1,len(it['rows']))
for k,v in c.most_common(25): print(f'{k:14s} lines {v:4d}  rows~{rows[k]}')
