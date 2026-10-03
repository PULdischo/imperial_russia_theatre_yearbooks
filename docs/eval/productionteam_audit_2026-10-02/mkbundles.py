import duckdb,json,re,collections,os
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
pages=[r[0] for r in c.execute("select distinct page_id from raw.person_entry where entity_type='ProductionTeam' order by 1").fetchall()]
link={r[0]:str(r[1]) for r in c.execute("select entry_id,person_id from entities.person_link where entry_id like 'productionteam_%'").fetchall()}
CYR=re.compile(r'^[Ѐ-ӿ]+$')
MONTHS_OLD=['января','февраля','марта','апрѣля','мая','іюня','іюля','августа','сентября','октября','ноября','декабря']
def start(e):
    sp=e.get('service_periods') or []
    return (sp[0].get('start_date_text') or '').replace('съ ','').strip() if sp else ''
# modal start per person
byp=collections.defaultdict(list)
raws={}
for p in pages:
    raws[p]=json.load(open(f'outputs/full_run/raw/{p}.raw.json'))['entries']
    for i,e in enumerate(raws[p]):
        pid=link.get(f'{p}__e{i+1:03d}')
        if pid and start(e): byp[pid].append((start(e),p,i+1))
modal={}
for pid,l in byp.items():
    cnt=collections.Counter(x[0] for x in l); (m,n),=cnt.most_common(1)
    if len(l)>=3 and n>=2 and n<len(l): modal[pid]=(m,n,len(l))
groups=[];cur=[]
for p in pages:
    cur.append(p)
    if len(cur)==5: groups.append(cur);cur=[]
if cur: groups.append(cur)
json.dump(groups,open('/tmp/audit7/groups.json','w'))
tot=0
for p in pages:
    es=raws[p]; L=[f'# {p} ({len(es)} rows)  columns: eNNN | list | FAMILY | first | patronymic | rank_or_title | tenure_note_text | periods | AUTO-FLAGS\n# section blocks (institution // heading_path):']
    seen=[]
    for e in es:
        b=(e.get('institution'),e.get('heading_path'))
        if not seen or seen[-1]!=b: seen.append(b)
    for b in seen: L.append(f'#   {b[0]} // {b[1]}')
    dates=[]
    for i,e in enumerate(es):
        fl=[]
        fam=e.get('family_name') or ''; fn=e.get('first_name') or ''; pt=e.get('patronymic') or ''
        for nm,v in (('family',fam),('first',fn),('patr',pt)):
            core=re.sub(r'[ \-\.\(\)\d,йя]+','',v) if False else v
            if any(ch.isalpha() and not 'Ѐ'<=ch<='ӿ' for ch in v): fl.append(f'MIXED-SCRIPT({nm})')
        if re.fullmatch(r'[1-4Іl]-[йя]',fn.strip()) or re.fullmatch(r'[1-4Іl]-[йя]',pt.strip()): fl.append('ORDINAL-IN-FIRST/PATR')
        if ' ' in fam.strip() and not re.search(r'\d-[йя]$|^фонъ|^де |^ле |\(',fam.strip()): fl.append('SPACE-IN-FAMILY')
        if re.search(r'[бвгджзклмнпрстфхцчшщ]$',fam.strip().lower()): fl.append('FAMILY-NO-FINAL-ъ/ь?')
        hp=e.get('heading_path') or ''
        if re.search(r'/ \d+\.?$',hp): fl.append('HEADING-LISTNUM-LEAK')
        if e.get('heading_path') is None: fl.append('HEADING-NULL')
        t=e.get('tenure_note_text') or ''
        if not t.strip(): fl.append('NO-TENURE')
        sp=e.get('service_periods') or []
        if sp and sp[0].get('start_date_text') and sp[0]['start_date_text'].replace('съ ','') not in t: fl.append('PERIOD-NOT-IN-TENURE')
        for m in re.findall(r'\d{1,2} ([а-яѣі]+) (\d{4})',t):
            if m[0] not in MONTHS_OLD: fl.append(f'ODD-MONTH({m[0]})')
            if not 1840<=int(m[1])<=1910: fl.append(f'ODD-YEAR({m[1]})')
        pid=link.get(f'{p}__e{i+1:03d}')
        if pid in modal and start(e) and start(e)!=modal[pid][0]:
            fl.append('DATE-DIFFERS'); dates.append((i+1,fam,start(e),modal[pid]))
        per='; '.join(f"{s.get('start_date_text')}->{s.get('end_date_text')}({s.get('end_type')})" for s in sp) or '-'
        extra={k:v for k,v in e.items() if k not in ('institution','heading_path','list_number','family_name','first_name','patronymic','rank_or_title','tenure_note_text','service_periods') and v not in (None,'',[])}
        L.append(f"e{i+1:03d} | {e.get('list_number') or '-'} | {fam} | {fn or '-'} | {pt or '-'} | {e.get('rank_or_title') or '-'} | {t or '-'} | {per} | {','.join(fl) or '-'}"+(f" | EXTRA:{extra}" if extra else ''))
        tot+=1
        # per-row section label when it changes
    L.append('\n# row -> section (institution // heading_path) per entry:')
    for i,e in enumerate(es): L.append(f"#   e{i+1:03d}: {e.get('institution')} // {e.get('heading_path')}")
    for (n,fam,s,m) in dates: L.append(f'# DATE-CHECK e{n:03d} {fam} stored start: "{s}"  (same person\'s modal start: {m[0]} in {m[1]} of {m[2]} entries)')
    open(f'/tmp/audit7/{p}.txt','w',encoding='utf-8').write('\n'.join(L)+'\n')
print(len(pages),'pages',tot,'rows',len(groups),'groups; date-check rows total:',sum(1 for p in pages for l in open(f'/tmp/audit7/{p}.txt',encoding='utf-8') if l.startswith('# DATE-CHECK')))
import collections as C
fc=C.Counter()
for p in pages:
    for l in open(f'/tmp/audit7/{p}.txt',encoding='utf-8'):
        if l.startswith('e') and ' | ' in l:
            for f in l.rstrip().split(' | ')[8].split(','): fc[f.split('(')[0]]+=1
print(fc)
