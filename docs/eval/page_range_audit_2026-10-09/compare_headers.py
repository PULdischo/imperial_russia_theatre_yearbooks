"""Step 1 of the printed-page-range audit (issue #139 follow-up): compare every row group of
outputs/full_run/printed_page_numbers_all.csv with the page's own printed date header
(outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv). For a two-page spread (pairNNN) the header
spans BOTH printed pages, so this checks the OUTER boundaries only (min start / max end); the inner boundary
between the two printed pages needs each page's own header read off the scan (step 2)."""
import csv, re, collections, datetime, json
MON={'января':1,'февраля':2,'марта':3,'апрѣля':4,'апреля':4,'мая':5,'іюня':6,'июня':6,'іюля':7,'июля':7,'августа':8,'сентября':9,'октября':10,'ноября':11,'декабря':12}
def parse(h, season):
    m=re.findall(r'(\d{1,2})\s*([А-Яа-яѣ]+)\.?', h.replace('г.','').replace('гг.',''))
    pairs=[(int(d),MON[w.lower()]) for d,w in m if w.lower() in MON]
    if len(pairs)<2: return None
    y1=int(season[:4]); 
    def yr(mo): return y1 if mo>=8 else y1+1
    (d1,m1),(d2,m2)=pairs[0],pairs[-1]
    return datetime.date(yr(m1),m1,d1).isoformat(), datetime.date(yr(m2),m2,d2).isoformat()
hdr={r['page_id']:r['header_text'] for r in csv.DictReader(open('outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv',encoding='utf-8'))}
rows=collections.defaultdict(list)
single=0
for r in csv.DictReader(open('outputs/full_run/printed_page_numbers_all.csv',encoding='utf-8')): rows[r['page_id']].append((r['start_date'],r['end_date'],r['printed_page_number'])) if r['start_date'] else None
out=[]; nohdr=[]; unparsed=[]
for pid,rs in sorted(rows.items()):
    season=pid.split('_')[1]
    if pid not in hdr: nohdr.append(pid); continue
    p=parse(hdr[pid],season)
    if not p: unparsed.append((pid,hdr[pid])); continue
    s=min(r[0] for r in rs); e=max(r[1] for r in rs)
    if (s,e)!=p: out.append((pid,hdr[pid],p,(s,e),[r[2] for r in rs]))
print('page_ids in CSV',len(rows),'| no header on file',len(nohdr),'| unparsed',len(unparsed),'| MISMATCH',len(out))
for o in out: print(o)
print('no header sample', nohdr[:5], collections.Counter(p.split('_')[1] for p in nohdr))
print('unparsed', unparsed[:5])
json.dump(dict(mismatch=out,nohdr=nohdr,unparsed=unparsed),open('docs/eval/page_range_audit_2026-10-09/step1_result.json','w'),ensure_ascii=False,indent=1)
