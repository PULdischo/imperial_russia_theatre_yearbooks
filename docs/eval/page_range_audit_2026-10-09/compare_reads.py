"""Step 2: compare the blind readers' per-page headers/day-columns (hdr/report_N.txt) with the reference file
outputs/full_run/printed_page_numbers_all.csv, page by page (a spread = two printed pages: left = lower folio)."""
import csv, re, sys, glob, collections, datetime, json
MON={'января':1,'февраля':2,'марта':3,'апрѣля':4,'апреля':4,'мая':5,'іюня':6,'июня':6,'іюля':7,'июля':7,'августа':8,'сентября':9,'октября':10,'ноября':11,'декабря':12,'сентября.':9}
SCR=sys.argv[1]
ref=collections.defaultdict(list)
for r in csv.DictReader(open('outputs/full_run/printed_page_numbers_all.csv',encoding='utf-8')):
    if 'pair' in r['page_id'] and r['start_date']: ref[r['page_id']].append((int(r['printed_page_number']),r['start_date'],r['end_date']))
def dm(s):
    m=re.match(r'\s*(\d{1,2})\s+([А-Яа-яѣі]+)',s or '')
    return (int(m.group(1)), MON.get(m.group(2).lower(),0)) if m else None
def split_hdr(h):
    parts=[x.strip() for x in re.split(r'\s+-\s+', h)]
    return (dm(parts[0]), dm(parts[1])) if len(parts)==2 else (None,None)
reads={}
for f in sorted(glob.glob(f'{SCR}/hdr/report_*.txt')):
    for line in open(f,encoding='utf-8'):
        if not line.startswith('SPREAD'): continue
        d={}
        for part in line.strip().split(' | '):
            if part.startswith('SPREAD'): d['id']=part.split()[1]
            else:
                k,_,v=part.partition(':'); d[k.strip()]=v.strip()
        reads[d['id']]=d
print('spreads read', len(reads), 'of', len(ref), '| not yet read:', sorted(set(ref)-set(reads))[:10])
bad=[]; ok=0; unread=[]
for pid,d in sorted(reads.items()):
    rs=sorted(ref[pid]); season=pid.split('_')[1]; y1=int(season[:4])
    yr=lambda mo: y1 if mo>=8 else y1+1
    for side,(folio,s,e) in zip(('L','R'),rs):
        hs,he=split_hdr(d.get(f'{side} header',''))
        if not hs or not he or 0 in (hs[1],he[1]): unread.append((pid,side,d.get(f'{side} header'))); continue
        rs_=datetime.date(yr(hs[1]),hs[1],hs[0]).isoformat(); re_=datetime.date(yr(he[1]),he[1],he[0]).isoformat()
        if (rs_,re_)!=(s,e): bad.append((pid,side,folio,'printed',rs_,re_,'file',s,e,d.get(f'{side} cols'),d.get('NOTE')))
        else: ok+=1
print('pages matching',ok,'| differing',len(bad),'| unreadable',len(unread))
for b in bad: print(b)
for u in unread: print('UNREAD',u)
json.dump(dict(bad=bad,unread=unread,ok=ok),open('docs/eval/page_range_audit_2026-10-09/step2_result.json','w'),ensure_ascii=False,indent=1)
